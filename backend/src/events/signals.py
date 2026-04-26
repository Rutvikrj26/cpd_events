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
    """React to status / starts_at transitions for reminder lifecycle."""
    from events.services import cancel_event_reminders, reschedule_event_reminders

    old_status = getattr(instance, '_old_status', None)
    old_starts_at = getattr(instance, '_old_starts_at', None)

    if instance.status == Event.Status.CANCELLED and old_status != Event.Status.CANCELLED:
        cancel_event_reminders(event=instance, reason='event_cancelled')
        return

    starts_changed = old_starts_at is not None and old_starts_at != instance.starts_at
    if starts_changed and instance.status in (Event.Status.PUBLISHED, Event.Status.LIVE):
        reschedule_event_reminders(instance)
