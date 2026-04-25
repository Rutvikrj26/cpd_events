"""
Cloud tasks for registrations.
"""

import logging

from common.cloud_tasks import task

logger = logging.getLogger(__name__)


@task()
def send_registration_confirmation(registration_id: int):
    """
    Send a registration confirmation email, exactly once per registration.

    Idempotent: the prior-send check runs against ``EmailLog`` (the authoritative
    record of what was sent), so re-invocations from webhook retries or
    reconciliation are safe no-ops.

    Args:
        registration_id: ID of the registration to confirm
    """
    from integrations.models import EmailLog
    from registrations.models import Registration

    try:
        registration = Registration.objects.select_related('event', 'user').get(id=registration_id)
    except Registration.DoesNotExist:
        logger.error("Registration %s not found", registration_id)
        return False

    if registration.status != 'confirmed':
        logger.warning("Registration %s is not confirmed, skipping", registration_id)
        return False

    already_sent = EmailLog.objects.filter(
        registration=registration,
        email_type=EmailLog.EmailType.REGISTRATION_CONFIRM,
    ).exists()
    if already_sent:
        logger.info("Registration %s already has a confirmation EmailLog, skipping", registration_id)
        return True

    # Build rich confirmation context (calendar deep links, join URL, etc.)
    # so the registration_confirmation template renders in full and the .ics
    # attachment is included for one-click "Add to Calendar" in inboxes.
    from events.services import _reminder_context, build_event_ics, enqueue_event_reminders
    from integrations.services import email_service

    email_log = EmailLog.objects.create(
        recipient_email=registration.email,
        recipient_name=registration.full_name,
        recipient_user=registration.user,
        email_type=EmailLog.EmailType.REGISTRATION_CONFIRM,
        subject=f"Registration Confirmed: {registration.event.title}",
        event=registration.event,
        registration=registration,
    )

    try:
        ctx = _reminder_context(registration.event, registration)
        ics = build_event_ics(
            registration.event,
            attendee_email=registration.email,
            attendee_name=registration.full_name,
        )
        attachments = [('event.ics', ics, 'text/calendar; method=PUBLISH; charset=utf-8')]
        email_service.send_log(email_log, context=ctx, attachments=attachments)
    except Exception:
        logger.exception("Failed to send confirmation email for registration %s", registration_id)

    # Enqueue scheduled reminders for this registration. Idempotent — repeat
    # invocations are safe under the unique constraint on ScheduledEmail.
    try:
        enqueue_event_reminders(registration)
    except Exception:
        logger.exception("Failed to enqueue reminders for registration %s", registration_id)

    logger.info("Sent confirmation email for registration %s", registration_id)
    return True


@task()
def send_registration_confirmations(registration_ids: list):
    """
    Send registration confirmation emails in batch.

    Args:
        registration_ids: List of registration IDs
    """
    count = 0
    for reg_id in registration_ids:
        send_registration_confirmation.delay(reg_id)
        count += 1

    logger.info("Queued %s registration confirmations", count)
    return count
