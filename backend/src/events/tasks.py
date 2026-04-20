"""
Cloud tasks for events.
"""

import logging

from django.utils import timezone

from common.cloud_tasks import task

logger = logging.getLogger(__name__)


@task()
def send_event_reminders(hours_before: int = 24, stagger_seconds: int = 2):
    """
    Queue reminder emails for upcoming events. Reminders are scheduled
    (not sent immediately) and staggered to avoid provider rate limits.

    Args:
        hours_before: Reminder is targeted this many hours before start.
        stagger_seconds: Gap between scheduled sends within an event's batch.
    """
    from events.models import Event
    from integrations.services import schedule_bulk_emails
    from registrations.models import Registration

    now = timezone.now()
    target_time = now + timezone.timedelta(hours=hours_before)

    events = Event.objects.filter(
        status__in=['published', 'live'], starts_at__gt=now, starts_at__lte=target_time + timezone.timedelta(minutes=30)
    )

    total = 0
    for event in events:
        registrations = Registration.objects.filter(event=event, status='confirmed').select_related('user')
        recipients = [
            {
                'email': reg.user.email,
                'name': reg.user.full_name,
                'user': reg.user,
                'registration': reg,
                'context': {
                    'user_name': reg.user.full_name,
                    'event_title': event.title,
                    'event_date': event.starts_at.strftime('%B %d, %Y at %I:%M %p'),
                    'join_url': '',
                },
            }
            for reg in registrations
            if reg.user and reg.user.email
        ]
        total += schedule_bulk_emails(
            recipients=recipients,
            template_key='event_reminder',
            send_at=now,
            stagger_seconds=stagger_seconds,
            event=event,
            batch_key=f'event_reminder:{event.id}:{hours_before}h',
        )

    logger.info("Queued %s reminder emails across %s events", total, events.count())
    return total


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
