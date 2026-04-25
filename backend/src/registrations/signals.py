from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import Registration


@receiver(pre_save, sender=Registration)
def _capture_registration_state(sender, instance, **kwargs):
    """Stash previous status so post_save can detect cancellation transitions."""
    if instance.pk is None:
        instance._old_status = None
        return
    try:
        prev = sender.objects.only('status').get(pk=instance.pk)
        instance._old_status = prev.status
    except sender.DoesNotExist:
        instance._old_status = None


@receiver(post_save, sender=Registration)
@receiver(post_delete, sender=Registration)
def update_event_counts(sender, instance, **kwargs):
    """
    Update event counts when a registration is saved or deleted.
    """
    # Simply call the event's update_counts method
    # This recalculates registration_count, waitlist_count, etc.
    instance.event.update_counts()


@receiver(post_save, sender=Registration)
def _cancel_reminders_on_registration_cancel(sender, instance, created, **kwargs):
    """When a registration moves to CANCELLED, cancel its pending reminders."""
    if created:
        return
    old_status = getattr(instance, '_old_status', None)
    if instance.status == Registration.Status.CANCELLED and old_status != Registration.Status.CANCELLED:
        from events.services import cancel_event_reminders

        cancel_event_reminders(registration=instance, reason='registration_cancelled')

