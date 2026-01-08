"""
Cloud tasks for billing.
"""

import logging

from django.utils import timezone
from datetime import timezone as dt_timezone

from common.cloud_tasks import task

logger = logging.getLogger(__name__)


@task()
def reset_subscription_usage():
    """
    Reset usage counters for all active subscriptions.

    Run monthly on 1st.
    """
    from billing.models import Subscription

    count = 0
    for sub in Subscription.objects.filter(status__in=['active', 'trialing']):
        sub.reset_usage()
        count += 1

    logger.info(f"Reset usage for {count} subscriptions")
    return count


@task()
def send_trial_ending_reminders():
    """
    Send email to users whose trial ends in 3 days.
    """
    from billing.models import Subscription
    from integrations.services import email_service

    # Find trials ending in 3 days
    target_date = timezone.now().date() + timezone.timedelta(days=3)

    trials = Subscription.objects.filter(status='trialing', trial_ends_at__date=target_date).select_related('user')

    count = 0
    for sub in trials:
        email_service.send_email(
            template='trial_ending',
            recipient=sub.user.email,
            context={
                'user_name': sub.user.full_name,
                'trial_ends_at': sub.trial_ends_at.strftime('%B %d, %Y'),
                'plan': sub.get_plan_display(),
            },
        )
        count += 1

    logger.info(f"Sent {count} trial ending reminders")
    return count


@task()
def send_payment_failed_email(subscription_id: int):
    """
    Send email when payment fails.
    """
    from billing.models import Subscription
    from integrations.services import email_service

    try:
        sub = Subscription.objects.select_related('user').get(id=subscription_id)
    except Subscription.DoesNotExist:
        return False

    return email_service.send_email(
        template='payment_failed',
        recipient=sub.user.email,
        context={
            'user_name': sub.user.full_name,
            'plan': sub.get_plan_display(),
        },
    )


@task()
def sync_stripe_subscription(subscription_id: int):
    """
    Sync subscription data from Stripe.
    """
    from billing.models import Subscription
    from billing.services import stripe_service

    try:
        sub = Subscription.objects.get(id=subscription_id)
        if not sub.stripe_subscription_id:
            return False

        stripe_sub = stripe_service.get_subscription(sub.stripe_subscription_id)
        if stripe_sub:
            sub.status = stripe_sub.status
            sub.current_period_start = timezone.datetime.fromtimestamp(
                stripe_sub.current_period_start, tz=dt_timezone.utc
            )
            sub.current_period_end = timezone.datetime.fromtimestamp(
                stripe_sub.current_period_end, tz=dt_timezone.utc
            )
            sub.save()
            return True

        return False

    except Subscription.DoesNotExist:
        return False
    except Subscription.DoesNotExist:
        return False


@task()
def send_refund_notification(refund_id: int):
    """
    Send email when refund is processed.
    """
    from billing.models import RefundRecord
    from integrations.services import email_service

    try:
        refund = RefundRecord.objects.select_related('registration', 'registration__event').get(id=refund_id)
        if not refund.registration:
            return False
            
        registration = refund.registration
        
        return email_service.send_email(
            template='refund_processed',
            recipient=registration.email,
            context={
                'user_name': registration.full_name,
                'event_title': registration.event.title,
                'refund': refund,
                'registration': registration,
                'event': registration.event,
            }
        )
    except RefundRecord.DoesNotExist:
        return False
