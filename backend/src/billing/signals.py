"""
Billing signals for subscription events.
"""

from datetime import timedelta

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


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

    # Organizers get PROFESSIONAL plan with trial period
    from billing.models import StripeProduct
    
    # Try to find configured trial days for Professional plan
    try:
        product = StripeProduct.objects.filter(plan=Subscription.Plan.PROFESSIONAL, is_active=True).first()
        trial_days = product.trial_period_days if product else 30  # Default to 30 if product missing
    except Exception:
        trial_days = 30  # Safe fallback
        
    Subscription.objects.get_or_create(
        user=instance,
        defaults={
            'plan': Subscription.Plan.PROFESSIONAL,
            'status': Subscription.Status.TRIALING,
            'trial_ends_at': timezone.now() + timedelta(days=trial_days),
        },
    )
