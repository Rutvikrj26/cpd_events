from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Registration


@receiver(post_save, sender=Registration)
@receiver(post_delete, sender=Registration)
def update_event_counts(sender, instance, **kwargs):
    """
    Update event counts when a registration is saved or deleted.
    """
    # Simply call the event's update_counts method
    # This recalculates registration_count, waitlist_count, etc.
    instance.event.update_counts()
