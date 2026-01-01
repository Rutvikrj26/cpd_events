"""
Billing signals for subscription events.
"""

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_subscription_for_organizer(sender, instance, created, **kwargs):
    """
    Create a subscription when a new organizer is created.
    
    Plans:
    - 'attendee': Creates ATTENDEE plan (no events, for attendees only)
    - 'organizer': Creates PROFESSIONAL plan with ACTIVE status (paid plan)
    - 'organization': Enterprise plan (custom setup)
    """
    from billing.models import Subscription

    if not created:
        return
        
    if instance.account_type != 'organizer':
        # Attendees get ATTENDEE plan
        Subscription.objects.get_or_create(
            user=instance,
            defaults={
                'plan': Subscription.Plan.ATTENDEE,
                'status': Subscription.Status.ACTIVE,
            },
        )
        return

    # Organizers get PROFESSIONAL plan
    Subscription.objects.get_or_create(
        user=instance,
        defaults={
            'plan': Subscription.Plan.PROFESSIONAL,
            'status': Subscription.Status.ACTIVE,
        },
    )
