"""
Cloud tasks for events.
"""

import logging

from django.utils import timezone

from common.cloud_tasks import task

logger = logging.getLogger(__name__)


@task()
def send_event_reminders(lookahead_days: int = 14):
    """Reconcile reminder ScheduledEmail rows for upcoming events.

    The authoritative path enqueues reminders at registration confirmation
    time via ``events.services.enqueue_event_reminders``. This task is a
    self-healing backstop: it walks confirmed registrations on upcoming
    events and re-runs the idempotent enqueue. The unique constraint on
    ScheduledEmail prevents duplicates.

    Runs cheaply on the cron tick — no work is done unless a registration
    is missing reminders.

    Args:
        lookahead_days: Only reconcile events starting within this window.
    """
    from events.models import Event
    from events.services import enqueue_event_reminders
    from registrations.models import Registration

    now = timezone.now()
    horizon = now + timezone.timedelta(days=lookahead_days)

    events = Event.objects.filter(
        status__in=[Event.Status.PUBLISHED, Event.Status.LIVE],
        starts_at__gt=now,
        starts_at__lte=horizon,
        deleted_at__isnull=True,
    )

    total_reg = 0
    total_rows = 0
    for event in events.iterator():
        confirmed = Registration.objects.filter(
            event=event,
            status=Registration.Status.CONFIRMED,
            deleted_at__isnull=True,
        )
        for reg in confirmed.iterator():
            total_reg += 1
            total_rows += enqueue_event_reminders(reg)

    logger.info("Reminder reconciler scanned %s registrations, ensured %s rows", total_reg, total_rows)
    return total_rows


@task()
def auto_complete_events():
    """
    Auto-complete events that have ended.
    """
    from events.models import Event

    now = timezone.now()

    # Events that ended more than 30 minutes ago
    events = Event.objects.filter(
        status='live',
    )

    count = 0
    for event in events:
        if event.ends_at and now > event.ends_at + timezone.timedelta(minutes=30):
            event.complete()
            count += 1

    logger.info(f"Auto-completed {count} events")
    return count


@task()
def update_event_counts(event_id: int):
    """
    Update denormalized counts for an event.
    """
    from events.models import Event

    try:
        event = Event.objects.get(id=event_id)
        event.update_counts()
        return True
    except Event.DoesNotExist:
        return False


@task()
def notify_event_cancelled(event_id: int):
    """
    Notify all registrants that an event has been cancelled.

    Args:
        event_id: ID of the cancelled event
    """
    from events.models import Event
    from integrations.models import EmailLog
    from integrations.tasks import send_email
    from registrations.models import Registration

    try:
        event = Event.objects.get(id=event_id)

        if event.status != 'cancelled':
            logger.warning(f"Event {event_id} is not cancelled, skipping notification")
            return 0

        # Get all confirmed registrations
        registrations = Registration.objects.filter(event=event, status='confirmed', deleted_at__isnull=True).select_related(
            'user'
        )

        count = 0
        for reg in registrations:
            # Create email log
            email_log = EmailLog.objects.create(
                recipient_email=reg.email,
                recipient_name=reg.full_name,
                recipient_user=reg.user,
                email_type=EmailLog.EmailType.EVENT_UPDATE,
                subject=f"Event Cancelled: {event.title}",
                event=event,
                registration=reg,
            )
            # Queue for sending
            send_email.delay(email_log.id)
            count += 1

        logger.info(f"Queued {count} cancellation notifications for event {event_id}")
        return count

    except Event.DoesNotExist:
        logger.error(f"Event {event_id} not found")
        return 0


@task()
def send_invitations(invitation_ids: list):
    """
    Send event invitations.

    Args:
        invitation_ids: List of EventInvitation IDs to send
    """
    from events.models import EventInvitation
    from integrations.models import EmailLog
    from integrations.tasks import send_email

    count = 0
    for inv_id in invitation_ids:
        try:
            invitation = EventInvitation.objects.select_related('event').get(id=inv_id)

            if invitation.status != 'pending':
                continue

            # Create email log
            email_log = EmailLog.objects.create(
                recipient_email=invitation.email,
                recipient_name=invitation.name,
                email_type=EmailLog.EmailType.INVITATION,
                subject=f"You're invited: {invitation.event.title}",
                event=invitation.event,
            )

            # Queue for sending
            send_email.delay(email_log.id)

            # Mark invitation as sent
            invitation.status = 'sent'
            invitation.sent_at = timezone.now()
            invitation.save(update_fields=['status', 'sent_at', 'updated_at'])

            count += 1

        except EventInvitation.DoesNotExist:
            logger.warning(f"Invitation {inv_id} not found")
            continue

    logger.info(f"Sent {count} invitations")
    return count
