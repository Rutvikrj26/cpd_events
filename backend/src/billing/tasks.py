"""Cloud tasks for billing.

Course-based deployment. The SaaS-era subscription tasks were removed when
the Subscription/Invoice/InstitutionPlan models were dropped. What remains:
the Stripe-event worker, an expired-payment-method sweeper, and refund
notifications.
"""

import logging
import traceback

from django.db import transaction
from django.utils import timezone

from common.cloud_tasks import task

logger = logging.getLogger(__name__)


@task()
def process_stripe_event(event_id: str):
    """Worker entry-point for a StripeEvent row.

    Re-fetches the canonical event from Stripe, dispatches to the matching
    handler, and flips ``processed_at``. Duplicates collapse because the row
    is locked for update and the handler no-ops when ``processed_at`` is set.
    """
    from billing.client import get_stripe
    from billing.handlers import dispatch
    from billing.models import StripeEvent

    try:
        with transaction.atomic():
            try:
                row = StripeEvent.objects.select_for_update().get(pk=event_id)
            except StripeEvent.DoesNotExist:
                logger.error("stripe.event.row_missing", extra={"stripe_event_id": event_id})
                return False
            if row.processed_at:
                logger.info(
                    "stripe.event.already_processed",
                    extra={"stripe_event_id": event_id, "stripe_event_type": row.event_type},
                )
                return True

            stripe = get_stripe()
            try:
                canonical = stripe.Event.retrieve(event_id)
            except Exception as exc:
                row.error = f"fetch failed: {exc}"
                row.save(update_fields=["error"])
                logger.exception("stripe.event.fetch_failed", extra={"stripe_event_id": event_id})
                raise

            try:
                dispatch(canonical)
            except Exception as exc:
                row.error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"[:4000]
                row.save(update_fields=["error"])
                logger.exception(
                    "stripe.event.handler_failed",
                    extra={
                        "stripe_event_id": event_id,
                        "stripe_event_type": row.event_type,
                    },
                )
                raise

            row.processed_at = timezone.now()
            row.error = ""
            row.save(update_fields=["processed_at", "error"])
            logger.info(
                "stripe.event.processed",
                extra={"stripe_event_id": event_id, "stripe_event_type": row.event_type},
            )
            return True
    except Exception:
        # Re-raise so the task runtime can retry. Row state above already
        # captured the error for investigation.
        raise


@task()
def handle_expired_payment_methods():
    """Demote expired default payment methods and notify users."""
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
            models.Q(card_exp_year__lt=now.year)
            | (models.Q(card_exp_year=now.year) & models.Q(card_exp_month__lt=now.month))
        )
        .select_related("user")
    )

    handled = 0
    for method in expired_defaults:
        method.is_default = False
        method.save(update_fields=["is_default", "updated_at"])

        replacement = (
            PaymentMethod.objects.filter(user=method.user)
            .exclude(pk=method.pk)
            .order_by("-created_at")
        )
        for candidate in replacement:
            if not candidate.is_expired:
                candidate.set_as_default()
                break

        try:
            email_service.send_email(
                template="payment_method_expired",
                recipient=method.user.email,
                context={
                    "user_name": getattr(method.user, "full_name", method.user.email),
                    "card_brand": method.card_brand,
                    "card_last4": method.card_last4,
                    "exp_month": method.card_exp_month,
                    "exp_year": method.card_exp_year,
                },
            )
        except Exception as exc:
            logger.warning("Failed to send payment_method_expired email: %s", exc)

        try:
            from accounts.notifications import create_notification

            create_notification(
                user=method.user,
                notification_type="payment_method_expired",
                title="Payment method expired",
                message=f"Your {method.card_brand} card ending in {method.card_last4} expired.",
                action_url="/settings?tab=billing",
                metadata={"card_last4": method.card_last4},
            )
        except Exception as exc:
            logger.warning("Failed to create payment method notification: %s", exc)
        handled += 1

    logger.info(f"Handled {handled} expired payment methods")
    return handled


@task()
def send_refund_notification(refund_id: int):
    """Email a customer when their refund is processed."""
    from billing.models import RefundRecord
    from integrations.services import email_service

    try:
        refund = RefundRecord.objects.select_related(
            "registration", "registration__event"
        ).get(id=refund_id)
    except RefundRecord.DoesNotExist:
        return False

    if not refund.registration:
        return False

    registration = refund.registration
    return email_service.send_email(
        template="refund_processed",
        recipient=registration.email,
        context={
            "user_name": registration.full_name,
            "event_title": registration.event.title,
            "refund": refund,
            "registration": registration,
            "event": registration.event,
        },
    )
