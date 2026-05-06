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

    # When the event runs on Zoom, register the attendee with Zoom first.
    # Zoom then emails the attendee the calendar invite + personalized join
    # URL directly — we DO NOT attach .ics or echo a meeting URL in our
    # confirmation email. Reminder cron is also short-circuited (Zoom owns
    # reminders). This block is a no-op for non-Zoom providers.
    using_zoom = _try_register_with_zoom(registration)

    # Build rich confirmation context (calendar deep links, join URL, etc.)
    # so the registration_confirmation template renders in full. The .ics
    # attachment is omitted on the Zoom path because Zoom emails its own
    # calendar invite directly to the registrant.
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
        if using_zoom:
            # Suppress meeting URL/.ics — Zoom emails them. Our confirmation
            # email is now a slim "thanks, payment received" receipt.
            ctx = {**ctx, 'join_url': '', 'meeting_invite_via_zoom': True}
            attachments = []
        else:
            ics = build_event_ics(
                registration.event,
                attendee_email=registration.email,
                attendee_name=registration.full_name,
            )
            attachments = [('event.ics', ics, 'text/calendar; method=PUBLISH; charset=utf-8')]
        email_service.send_log(email_log, context=ctx, attachments=attachments)
    except Exception:
        logger.exception("Failed to send confirmation email for registration %s", registration_id)

    # Enqueue scheduled reminders ONLY for non-Zoom events. Zoom owns the
    # reminder cadence on its end (configured per-meeting at create time).
    if not using_zoom:
        try:
            enqueue_event_reminders(registration)
        except Exception:
            logger.exception("Failed to enqueue reminders for registration %s", registration_id)

    logger.info("Sent confirmation email for registration %s", registration_id)
    return True


def _try_register_with_zoom(registration) -> bool:
    """If the event's video room is on Zoom, register the attendee there.

    Returns True iff Zoom registration succeeded (or had already run for
    this registration). Mutates the Registration row with
    ``zoom_registrant_id`` and ``zoom_registrant_join_url`` on success.
    Failures are logged and return False — caller falls back to local
    .ics + reminder delivery so the user still gets the meeting URL.
    """
    if registration.zoom_registrant_id:
        return True  # already registered on a previous run; idempotent.

    from django.contrib.contenttypes.models import ContentType
    from conferencing.models import VideoRoom
    from conferencing.service import get_video_provider
    from events.models import Event

    ct = ContentType.objects.get_for_model(Event)
    room = (
        VideoRoom.objects.filter(content_type=ct, object_id=registration.event_id, provider='zoom')
        .exclude(status=VideoRoom.Status.ENDED)
        .first()
    )
    if room is None or not room.zoom_meeting_id:
        return False  # not a Zoom event (or meeting not yet provisioned).

    provider = get_video_provider()
    if not provider.is_configured():
        logger.warning(
            'Zoom provider not configured; falling back to local invite for registration %s',
            registration.id,
        )
        return False

    try:
        info = provider.register_attendee(
            room.zoom_meeting_id, registration.email, registration.full_name,
        )
    except Exception:
        logger.exception('Zoom register_attendee raised for registration %s', registration.id)
        return False

    if not info.registrant_id:
        # Zoom rejected the registration (e.g. already registered with a
        # different name). Fall back to local invite.
        return False

    registration.zoom_registrant_id = info.registrant_id
    registration.zoom_registrant_join_url = info.join_url
    registration.save(update_fields=[
        'zoom_registrant_id', 'zoom_registrant_join_url', 'updated_at',
    ])
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
