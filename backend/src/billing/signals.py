"""
Billing signals for subscription events.
"""

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_free_subscription(sender, instance, created, **kwargs):
    """Create a free subscription when a new organizer is created."""
    from billing.models import Subscription

    if created and instance.account_type == 'organizer':
        Subscription.objects.get_or_create(
            user=instance,
            defaults={
                'plan': Subscription.Plan.FREE,
                'status': Subscription.Status.ACTIVE,
            },
        )
