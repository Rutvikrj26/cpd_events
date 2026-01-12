"""
Cloud tasks for billing.
"""

import logging
from datetime import UTC, timedelta

from django.utils import timezone

from common.cloud_tasks import task

logger = logging.getLogger(__name__)


@task()
def reset_subscription_usage():
    """
    Reset usage counters for all active subscriptions.

    Run monthly on 1st.
    """
    from billing.models import Subscription

    now = timezone.now()
    count = 0
    for sub in Subscription.objects.filter(status__in=['active', 'trialing']):
        if sub.current_period_end and sub.current_period_end > now:
            continue
        if sub.last_usage_reset_at and sub.current_period_end and sub.last_usage_reset_at >= sub.current_period_end:
            continue
        sub.reset_usage()
        count += 1

    logger.info(f"Reset usage for {count} subscriptions")
    return count


@task()
def expire_trials():
    """
    Expire trials that have ended.

    Business Rule: Auto-downgrade to attendee plan.
    - Sets subscription status to CANCELED
    - Downgrades subscription plan to ATTENDEE
    - Downgrades user account_type to ATTENDEE
    - Sends notification email
    - Creates in-app notification
    """
    from billing.models import Subscription
    from integrations.services import email_service

    now = timezone.now()
    trials = Subscription.objects.filter(
        status=Subscription.Status.TRIALING,
        trial_ends_at__isnull=False,
        trial_ends_at__lte=now,
    ).select_related('user')

    expired_count = 0
    for sub in trials:
        previous_plan = sub.plan

        # Downgrade subscription to attendee
        sub.status = Subscription.Status.CANCELED
        sub.plan = Subscription.Plan.ATTENDEE
        sub.canceled_at = now
        sub.cancellation_reason = 'Trial expired - auto-downgraded'
        sub.save(update_fields=['status', 'plan', 'canceled_at', 'cancellation_reason', 'updated_at'])

        # Downgrade user account type
        sub.user.downgrade_to_attendee()

        # Send expiration email
        try:
            email_service.send_email(
                template='trial_expired',
                recipient=sub.user.email,
                context={
                    'user_name': sub.user.full_name,
                    'previous_plan': previous_plan,
                    'trial_ended_at': sub.trial_ends_at.strftime('%B %d, %Y'),
                },
            )
        except Exception as exc:
            logger.warning(f"Failed to send trial expired email to {sub.user.email}: {exc}")

        # Create in-app notification
        try:
            from accounts.notifications import create_notification

            create_notification(
                user=sub.user,
                notification_type='trial_expired',
                title='Trial expired',
                message=f'Your {previous_plan} trial has ended. Upgrade to continue creating events and courses.',
                action_url='/billing',
                metadata={'previous_plan': previous_plan},
            )
        except Exception as exc:
            logger.warning(f"Failed to create trial expired notification: {exc}")

        expired_count += 1
        logger.info(f"Expired trial for user {sub.user.email}, downgraded from {previous_plan} to attendee")

    logger.info(f"Expired {expired_count} trials")
    return expired_count


@task()
def send_trial_ending_reminders():
    """
    Send email to users whose trial ends in 3 days.
    """
    from billing.models import Subscription
    from integrations.services import email_service

    # Find trials ending in 3 days
    target_date = timezone.now().date() + timedelta(days=3)

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
        try:
            from accounts.notifications import create_notification

            create_notification(
                user=sub.user,
                notification_type='trial_ending',
                title='Trial ending soon',
                message=f"Your trial ends on {sub.trial_ends_at.strftime('%B %d, %Y')}.",
                action_url='/billing',
                metadata={'plan': sub.plan},
            )
        except Exception as exc:
            logger.warning("Failed to create trial ending notification: %s", exc)
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
def handle_expired_payment_methods():
    """
    Handle expired payment methods and notify users.
    """
    from django.db import models

    from billing.models import PaymentMethod
    from integrations.services import email_service

    now = timezone.now()
    expired_defaults = (
        PaymentMethod.objects.filter(
            is_default=True,
            card_exp_year__isnull=False,
            card_exp_month__isnull=False,
        )
        .filter(
            models.Q(card_exp_year__lt=now.year) | (models.Q(card_exp_year=now.year) & models.Q(card_exp_month__lt=now.month))
        )
        .select_related('user')
    )

    handled = 0
    for method in expired_defaults:
        method.is_default = False
        method.save(update_fields=['is_default', 'updated_at'])

        replacement = PaymentMethod.objects.filter(user=method.user).exclude(pk=method.pk).order_by('-created_at')

        for candidate in replacement:
            if not candidate.is_expired:
                candidate.set_as_default()
                break

        email_service.send_email(
            template='payment_method_expired',
            recipient=method.user.email,
            context={
                'user_name': method.user.full_name,
                'card_brand': method.card_brand,
                'card_last4': method.card_last4,
                'exp_month': method.card_exp_month,
                'exp_year': method.card_exp_year,
            },
        )
        try:
            from accounts.notifications import create_notification

            create_notification(
                user=method.user,
                notification_type='payment_method_expired',
                title='Payment method expired',
                message=f"Your {method.card_brand} card ending in {method.card_last4} expired.",
                action_url='/settings?tab=billing',
                metadata={'card_last4': method.card_last4},
            )
        except Exception as exc:
            logger.warning("Failed to create payment method notification: %s", exc)
        handled += 1

    logger.info(f"Handled {handled} expired payment methods")
    return handled


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
            sub.current_period_start = timezone.datetime.fromtimestamp(stripe_sub.current_period_start, tz=UTC)
            sub.current_period_end = timezone.datetime.fromtimestamp(stripe_sub.current_period_end, tz=UTC)
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
            },
        )
    except RefundRecord.DoesNotExist:
        return False
