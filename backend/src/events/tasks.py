"""
Celery tasks for events.
"""

from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_event_reminders(hours_before: int = 24):
    """
    Send reminders for upcoming events.
    
    Args:
        hours_before: Hours before event to send reminder
    """
    from events.models import Event
    from registrations.models import Registration
    from integrations.services import email_service
    
    now = timezone.now()
    target_time = now + timezone.timedelta(hours=hours_before)
    
    # Find events starting in the target window
    events = Event.objects.filter(
        status__in=['published', 'live'],
        starts_at__gt=now,
        starts_at__lte=target_time + timezone.timedelta(minutes=30)
    )
    
    count = 0
    for event in events:
        # Get confirmed registrations
        registrations = Registration.objects.filter(
            event=event,
            status='confirmed'
        ).select_related('user')
        
        for reg in registrations:
            email_service.send_email(
                template='event_reminder',
                recipient=reg.user.email,
                context={
                    'user_name': reg.user.full_name,
                    'event_title': event.title,
                    'event_date': event.starts_at.strftime('%B %d, %Y at %I:%M %p'),
                    'join_url': event.zoom_join_url or '',
                }
            )
            count += 1
    
    logger.info(f"Sent {count} event reminders")
    return count


@shared_task
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


@shared_task
def create_zoom_meeting(event_id: int):
    """
    Create Zoom meeting for an event.
    """
    from events.models import Event
    from events.services import zoom_meeting_service
    
    try:
        event = Event.objects.get(id=event_id)
        result = zoom_meeting_service.create_meeting(event)
        return result.get('success', False)
    except Event.DoesNotExist:
        return False


@shared_task
def sync_zoom_attendance(event_id: int):
    """
    Sync Zoom attendance data for an event.
    """
    from events.models import Event
    from integrations.services import attendance_matcher
    
    try:
        event = Event.objects.get(id=event_id)
        result = attendance_matcher.match_attendance(event)
        logger.info(f"Synced attendance for event {event_id}: {result}")
        return result
    except Event.DoesNotExist:
        return {}


@shared_task
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
