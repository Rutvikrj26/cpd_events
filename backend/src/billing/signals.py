"""
Billing signals for subscription events.

In single-tenant mode, subscriptions are managed at the institutional level,
not auto-created per user. This signal is disabled in single-tenant mode.
"""

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_subscription_for_user(sender, instance, created, **kwargs):
    """
    Auto-create subscription for new users.

    Disabled in single-tenant mode — subscriptions are managed
    by the institution billing configuration (Phase 4).
    """
    from common.config.deployment import DEPLOYMENT_MODE

    if DEPLOYMENT_MODE == "single_tenant":
        return

    if not created:
        return

    # Legacy SaaS mode: create default subscription
    from billing.models import Subscription

    Subscription.objects.get_or_create(
        user=instance,
        defaults={
            'plan': Subscription.Plan.ATTENDEE,
            'status': Subscription.Status.ACTIVE,
        },
    )
