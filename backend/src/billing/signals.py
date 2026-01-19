"""
Billing signals for subscription events.
"""

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_subscription_for_new_user(sender, instance, created, **kwargs):
    """
    Create a free ATTENDEE subscription for all new users.

    Users can upgrade to ORGANIZER, LMS, or PRO plans via checkout flow.
    """
    from billing.models import Subscription

    if not created:
        return

    # All new users start with free ATTENDEE plan
    Subscription.objects.get_or_create(
        user=instance,
        defaults={
            "plan": Subscription.Plan.ATTENDEE,
            "status": Subscription.Status.ACTIVE,
        },
    )
