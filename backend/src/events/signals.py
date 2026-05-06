"""Signals for the events app.

Two responsibilities:

1.  Stash the previous values of fields that drive reminder lifecycle
    (`status`, `starts_at`) before save, so post_save can detect transitions.
2.  On post_save, reschedule reminders when the event is rescheduled or
    cancelled, and cancel reminders when the event is cancelled.
"""

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Event

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Event)
def _capture_event_lifecycle_state(sender, instance, **kwargs):
    """Stash old status / starts_at on the instance for post_save to compare."""
    if instance.pk is None:
        instance._old_status = None
        instance._old_starts_at = None
        return
    try:
        prev = sender.objects.only('status', 'starts_at').get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._old_status = None
        instance._old_starts_at = None
        return
    instance._old_status = prev.status
    instance._old_starts_at = prev.starts_at


@receiver(post_save, sender=Event)
def _handle_event_lifecycle(sender, instance, created, **kwargs):
    """React to status / starts_at transitions for reminder + meeting lifecycle."""
    from events.services import cancel_event_reminders, reschedule_event_reminders

    old_status = getattr(instance, '_old_status', None)
    old_starts_at = getattr(instance, '_old_starts_at', None)

    if instance.status == Event.Status.CANCELLED and old_status != Event.Status.CANCELLED:
        cancel_event_reminders(event=instance, reason='event_cancelled')
        # Tear down any provisioned Zoom meeting so registrants can't
        # join a cancelled event. Best-effort; failures log and continue.
        try:
            from conferencing.models import VideoRoom
            from conferencing.service import get_video_provider
            from django.contrib.contenttypes.models import ContentType
            ct = ContentType.objects.get_for_model(Event)
            room = VideoRoom.objects.filter(
                content_type=ct, object_id=instance.id, provider='zoom',
            ).exclude(status=VideoRoom.Status.ENDED).first()
            if room and room.zoom_meeting_id:
                provider = get_video_provider()
                if provider.is_configured():
                    provider.delete_room(room.zoom_meeting_id)
                room.mark_ended()
        except Exception:
            logger.exception('Failed to tear down Zoom meeting for cancelled event %s', instance.id)
        return

    # Transition into PUBLISHED — provision the Zoom meeting up-front so
    # registrants have something to attach to. No-op for LiveKit (rooms
    # are on-demand) and for re-saves where status didn't actually
    # transition.
    became_published = (
        instance.status == Event.Status.PUBLISHED
        and old_status != Event.Status.PUBLISHED
    )
    if became_published:
        try:
            from conferencing.meetings import provision_meeting_for_event
            provision_meeting_for_event(instance)
        except Exception:
            logger.exception('Failed to provision Zoom meeting for event %s', instance.id)

    starts_changed = old_starts_at is not None and old_starts_at != instance.starts_at
    if starts_changed and instance.status in (Event.Status.PUBLISHED, Event.Status.LIVE):
        reschedule_event_reminders(instance)
