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
    - 'organizer': Creates ORGANIZER plan with trial
    - 'course_manager': Creates LMS plan with trial
    - 'organization': Organization plan (custom setup)
    """
    from billing.models import Subscription

    if not created:
        return

    if instance.account_type not in ['organizer', 'course_manager']:
        # Attendees get ATTENDEE plan
        Subscription.objects.get_or_create(
            user=instance,
            defaults={
                'plan': Subscription.Plan.ATTENDEE,
                'status': Subscription.Status.ACTIVE,
            },
        )
        return

    # Organizers and course managers get trial plan
    from billing.models import StripeProduct

    plan = Subscription.Plan.ORGANIZER if instance.account_type == 'organizer' else Subscription.Plan.LMS

    # Try to find configured trial days for plan
    try:
        product = StripeProduct.objects.filter(plan=plan, is_active=True).first()
        trial_days = product.trial_period_days if product else 0
    except Exception:
        trial_days = 0

    Subscription.objects.get_or_create(
        user=instance,
        defaults={
            'plan': plan,
            'status': Subscription.Status.TRIALING,
            'trial_ends_at': timezone.now() + timedelta(days=trial_days),
        },
    )
