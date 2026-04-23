"""Webhook event handlers, dispatched from the async worker.

Every purchase goes through Stripe Checkout Sessions. Fulfilment flips the
relevant local row (Registration / CourseEnrollment / ProgramEnrollment /
Subscription) in response to ``checkout.session.completed``. The PaymentIntent
path is gone — the only reason we keep ``payment_intent.payment_failed`` is to
flag the odd Checkout Session that completes with a failed intent (rare, but
surfaces in admin).
"""

from __future__ import annotations

import logging
from datetime import UTC
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def dispatch(event) -> None:
    """Entry point called by the cloud task worker."""
    handler = _DISPATCH.get(event.type)
    if handler is None:
        logger.info(
            "stripe.webhook.unhandled",
            extra={"stripe_event_id": event.id, "stripe_event_type": event.type},
        )
        return
    handler(event)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _from_ts(value):
    if value in (None, 0, ""):
        return None
    try:
        return timezone.datetime.fromtimestamp(int(value), tz=UTC)
    except (TypeError, ValueError):
        return None


def _data(event):
    obj = event.data.object
    return obj.to_dict() if hasattr(obj, "to_dict") else dict(obj)


def _cents_to_decimal(cents) -> Decimal:
    try:
        return Decimal(int(cents)) / Decimal("100")
    except (TypeError, ValueError):
        return Decimal("0")


# ---------------------------------------------------------------------------
# Subscription lifecycle
# ---------------------------------------------------------------------------


def _resolve_plan_from_subscription(data):
    from billing.models import InstitutionPlan

    items = (data.get("items") or {}).get("data") or []
    if not items:
        return None
    price = items[0].get("price")
    if not isinstance(price, dict):
        return None
    price_id = price.get("id")
    if not price_id:
        return None
    return InstitutionPlan.objects.filter(stripe_price_id=price_id).first()


def _apply_subscription_fields(subscription, data, *, plan):
    subscription.status = data.get("status", subscription.status)
    subscription.cancel_at_period_end = data.get("cancel_at_period_end", False)
    subscription.current_period_start = _from_ts(data.get("current_period_start")) or subscription.current_period_start
    subscription.current_period_end = _from_ts(data.get("current_period_end")) or subscription.current_period_end
    if data.get("canceled_at"):
        subscription.canceled_at = _from_ts(data["canceled_at"])
    if plan is not None:
        subscription.institution_plan = plan


def handle_subscription_created(event):
    """Create or update the local Subscription row on first Stripe write.

    Subscription checkout (Phase 4) sets ``subscription_data.metadata.user_id``
    so we can attach to the learner. Falls back to looking up by customer id.
    """
    from billing.models import Subscription

    User = get_user_model()
    data = _data(event)
    customer_id = data.get("customer")
    subscription_id = data.get("id")
    if not customer_id or not subscription_id:
        return

    metadata = data.get("metadata") or {}
    user_id = metadata.get("user_id")
    user = None
    if user_id:
        user = User.objects.filter(pk=user_id).first()
    if user is None:
        user = User.objects.filter(stripe_customer_id=customer_id).first()
    if user is None:
        logger.warning(
            "stripe.subscription.no_user",
            extra={"customer_id": customer_id, "stripe_subscription_id": subscription_id},
        )
        return

    plan = _resolve_plan_from_subscription(data)
    sub, _ = Subscription.objects.update_or_create(
        user=user,
        defaults={
            "stripe_customer_id": customer_id,
            "stripe_subscription_id": subscription_id,
            "institution_plan": plan,
        },
    )
    _apply_subscription_fields(sub, data, plan=plan)
    sub.save()


def handle_subscription_updated(event):
    from billing.models import Subscription

    data = _data(event)
    subscription_id = data.get("id")
    if not subscription_id:
        return
    sub = Subscription.objects.filter(stripe_subscription_id=subscription_id).first()
    if not sub:
        logger.warning("stripe.subscription.missing", extra={"subscription_id": subscription_id})
        return
    _apply_subscription_fields(sub, data, plan=_resolve_plan_from_subscription(data))
    sub.save()


def handle_subscription_deleted(event):
    from billing.models import Subscription

    data = _data(event)
    subscription_id = data.get("id")
    if not subscription_id:
        return
    sub = Subscription.objects.filter(stripe_subscription_id=subscription_id).first()
    if not sub:
        return
    sub.status = Subscription.Status.CANCELED
    sub.canceled_at = timezone.now()
    sub.save(update_fields=["status", "canceled_at", "updated_at"])


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------


def handle_invoice_paid(event):
    from billing.models import Invoice, Subscription

    data = _data(event)
    invoice_id = data.get("id")
    customer_id = data.get("customer")
    if not invoice_id or not customer_id:
        return
    sub = Subscription.objects.filter(stripe_customer_id=customer_id).first()
    if not sub:
        return
    Invoice.objects.update_or_create(
        stripe_invoice_id=invoice_id,
        defaults={
            "user": sub.user,
            "subscription": sub,
            "amount_cents": data.get("amount_paid", 0),
            "currency": data.get("currency", "usd"),
            "status": Invoice.Status.PAID,
            "invoice_pdf_url": data.get("invoice_pdf", ""),
            "hosted_invoice_url": data.get("hosted_invoice_url", ""),
            "paid_at": timezone.now(),
            "period_start": _from_ts(data.get("period_start")),
            "period_end": _from_ts(data.get("period_end")),
        },
    )


def handle_invoice_payment_failed(event):
    from billing.models import Invoice, Subscription

    data = _data(event)
    invoice_id = data.get("id")
    customer_id = data.get("customer")
    if not invoice_id or not customer_id:
        return
    sub = Subscription.objects.filter(stripe_customer_id=customer_id).first()
    if not sub:
        return
    sub.status = Subscription.Status.PAST_DUE
    sub.save(update_fields=["status", "updated_at"])
    Invoice.objects.update_or_create(
        stripe_invoice_id=invoice_id,
        defaults={
            "user": sub.user,
            "subscription": sub,
            "amount_cents": data.get("amount_due", 0),
            "currency": data.get("currency", "usd"),
            "status": Invoice.Status.OPEN,
        },
    )
    try:
        from integrations.services import email_service

        email_service.send_email(
            template="payment_failed",
            recipient=sub.user.email,
            context={
                "invoice_number": data.get("number", ""),
                "amount_due": f"{data.get('amount_due', 0) / 100:.2f}",
                "currency": data.get("currency", "usd").upper(),
                "pay_url": data.get("hosted_invoice_url", ""),
                "user_name": getattr(sub.user, "full_name", sub.user.email),
            },
        )
    except Exception as exc:
        logger.warning("stripe.invoice.email_failed", extra={"error": str(exc)})
    try:
        from accounts.notifications import create_notification

        create_notification(
            user=sub.user,
            notification_type="payment_failed",
            title="Payment failed",
            message="We could not process your latest payment. Please update your billing details.",
            action_url="/settings?tab=billing",
            metadata={
                "invoice_number": data.get("number", ""),
                "amount_due_cents": data.get("amount_due", 0),
                "currency": data.get("currency", "usd"),
            },
        )
    except Exception as exc:
        logger.warning("stripe.invoice.notif_failed", extra={"error": str(exc)})


# ---------------------------------------------------------------------------
# Checkout fulfilment — the primary path for every purchase kind
# ---------------------------------------------------------------------------


def handle_checkout_session_completed(event):
    data = _data(event)
    metadata = data.get("metadata") or {}
    kind = metadata.get("kind") or metadata.get("type")  # legacy 'type' tolerated
    session_id = data.get("id", "unknown")
    payment_status = data.get("payment_status", "")
    log_extra = {"session_id": session_id, "kind": kind, "payment_status": payment_status}
    logger.info("stripe.checkout.completed", extra=log_extra)

    # async payment methods (ACH/SEPA) complete later with async_payment_succeeded
    if payment_status == "unpaid":
        logger.info("stripe.checkout.awaiting_async_payment", extra=log_extra)
        return

    if kind == "event_registration":
        _fulfil_event_registration(data)
    elif kind == "course_enrollment":
        _fulfil_course_enrollment(data)
    elif kind == "program_enrollment":
        _fulfil_program_enrollment(data)
    elif kind == "subscription_signup":
        # customer.subscription.created does the work; this is a no-op log.
        logger.info("stripe.checkout.subscription_signup_ack", extra=log_extra)
    else:
        logger.warning("stripe.checkout.unknown_kind", extra=log_extra)


def handle_checkout_session_async_payment_succeeded(event):
    data = _data(event)
    kind = (data.get("metadata") or {}).get("kind")
    if kind == "event_registration":
        _fulfil_event_registration(data)
    elif kind == "course_enrollment":
        _fulfil_course_enrollment(data)
    elif kind == "program_enrollment":
        _fulfil_program_enrollment(data)


def handle_checkout_session_async_payment_failed(event):
    from registrations.models import Registration

    data = _data(event)
    metadata = data.get("metadata") or {}
    if metadata.get("kind") != "event_registration":
        return
    reg_uuid = metadata.get("registration_uuid") or data.get("client_reference_id")
    if not reg_uuid:
        return
    reg = Registration.objects.filter(uuid=reg_uuid).first()
    if reg and reg.payment_status != Registration.PaymentStatus.PAID:
        reg.payment_status = Registration.PaymentStatus.FAILED
        reg.save(update_fields=["payment_status", "updated_at"])


def handle_checkout_session_expired(event):
    from registrations.models import Registration

    data = _data(event)
    metadata = data.get("metadata") or {}
    if metadata.get("kind") != "event_registration":
        return
    reg_uuid = metadata.get("registration_uuid") or data.get("client_reference_id")
    if not reg_uuid:
        return
    with transaction.atomic():
        reg = Registration.objects.select_for_update().filter(uuid=reg_uuid).first()
        if reg and reg.status == Registration.Status.PENDING:
            reg.status = Registration.Status.CANCELLED
            reg.payment_status = Registration.PaymentStatus.FAILED
            reg.cancelled_at = timezone.now()
            reg.cancellation_reason = "Checkout session expired without payment."
            reg.save(
                update_fields=[
                    "status",
                    "payment_status",
                    "cancelled_at",
                    "cancellation_reason",
                    "updated_at",
                ]
            )


def _fulfil_event_registration(session_data):
    from registrations.models import Registration

    metadata = session_data.get("metadata") or {}
    reg_uuid = metadata.get("registration_uuid") or session_data.get("client_reference_id")
    if not reg_uuid:
        logger.error(
            "stripe.checkout.event_registration.missing_uuid",
            extra={"session_id": session_data.get("id")},
        )
        return

    with transaction.atomic():
        reg = Registration.objects.select_for_update().filter(uuid=reg_uuid).first()
        if not reg:
            logger.error(
                "stripe.checkout.event_registration.not_found",
                extra={"registration_uuid": reg_uuid},
            )
            return
        if reg.payment_status == Registration.PaymentStatus.PAID:
            return

        amount_total = session_data.get("amount_total", 0) or 0
        tax_amount = (session_data.get("total_details") or {}).get("amount_tax", 0) or 0
        reg.total_amount = _cents_to_decimal(amount_total)
        reg.amount_paid = _cents_to_decimal(amount_total)
        reg.tax_amount = _cents_to_decimal(tax_amount)
        reg.payment_status = Registration.PaymentStatus.PAID
        reg.payment_intent_id = session_data.get("payment_intent") or ""
        reg.stripe_checkout_session_id = session_data.get("id") or reg.stripe_checkout_session_id

        status_changed = False
        if reg.status == Registration.Status.PENDING:
            reg.status = Registration.Status.CONFIRMED
            status_changed = True

        reg.save(
            update_fields=[
                "total_amount",
                "amount_paid",
                "tax_amount",
                "payment_status",
                "payment_intent_id",
                "stripe_checkout_session_id",
                "status",
                "updated_at",
            ]
        )

    # Record any applied promotion codes from the session payload.
    try:
        from promo_codes.services import record_usage_from_checkout_session

        record_usage_from_checkout_session(session_data, registration=reg, user=reg.user)
    except Exception as exc:
        logger.warning(
            "stripe.checkout.event_registration.promo_usage_failed",
            extra={"registration_uuid": reg_uuid, "error": str(exc)},
        )

    if status_changed:
        try:
            from registrations.tasks import send_registration_confirmation

            send_registration_confirmation.delay(reg.id)
        except Exception as exc:
            logger.warning(
                "stripe.checkout.event_registration.email_failed",
                extra={"registration_uuid": reg_uuid, "error": str(exc)},
            )


def _fulfil_course_enrollment(session_data):
    from learning.models import Course, CourseEnrollment

    metadata = session_data.get("metadata") or {}
    course_uuid = metadata.get("course_uuid")
    user_id = metadata.get("user_id")
    if not course_uuid or not user_id:
        logger.error(
            "stripe.checkout.course.metadata_missing",
            extra={"session_id": session_data.get("id")},
        )
        return

    User = get_user_model()
    user = User.objects.filter(pk=user_id).first()
    course = Course.objects.filter(uuid=course_uuid).first()
    if not user or not course:
        logger.error(
            "stripe.checkout.course.missing",
            extra={"session_id": session_data.get("id"), "course_uuid": course_uuid, "user_id": user_id},
        )
        return

    enrollment, created = CourseEnrollment.objects.get_or_create(
        user=user,
        course=course,
        defaults={"status": CourseEnrollment.Status.ACTIVE},
    )
    if not created and enrollment.status != CourseEnrollment.Status.ACTIVE:
        enrollment.status = CourseEnrollment.Status.ACTIVE
        enrollment.save(update_fields=["status", "updated_at"])
    course.update_counts()


def _fulfil_program_enrollment(session_data):
    from learning.models import Program, ProgramEnrollment

    metadata = session_data.get("metadata") or {}
    program_uuid = metadata.get("program_uuid")
    user_id = metadata.get("user_id")
    if not program_uuid or not user_id:
        logger.error("stripe.checkout.program.metadata_missing", extra={"session_id": session_data.get("id")})
        return

    User = get_user_model()
    user = User.objects.filter(pk=user_id).first()
    program = Program.objects.filter(uuid=program_uuid).first()
    if not user or not program:
        return

    enrollment, _ = ProgramEnrollment.objects.get_or_create(
        user=user,
        program=program,
        defaults={"stripe_checkout_session_id": session_data.get("id", "")},
    )
    if not enrollment.stripe_checkout_session_id:
        enrollment.stripe_checkout_session_id = session_data.get("id", "")
    enrollment.activate()
    program.update_counts()


# ---------------------------------------------------------------------------
# Refunds
# ---------------------------------------------------------------------------


def handle_charge_refunded(event):
    from billing.models import RefundRecord
    from registrations.models import Registration

    data = _data(event)
    payment_intent_id = data.get("payment_intent")
    refunds = (data.get("refunds") or {}).get("data") or []

    registration = None
    if payment_intent_id:
        registration = Registration.objects.filter(payment_intent_id=payment_intent_id).first()

    for refund in refunds:
        refund_id = refund.get("id")
        if not refund_id:
            continue
        status = refund.get("status")
        status_value = {
            "succeeded": RefundRecord.Status.SUCCEEDED,
            "failed": RefundRecord.Status.FAILED,
            "canceled": RefundRecord.Status.CANCELED,
        }.get(status, RefundRecord.Status.PENDING)

        defaults = {
            "registration": registration,
            "stripe_payment_intent_id": payment_intent_id or "",
            "amount_cents": refund.get("amount", 0),
            "currency": refund.get("currency", "usd"),
            "status": status_value,
            "reason": refund.get("reason") or RefundRecord.Reason.REQUESTED_BY_CUSTOMER,
            "description": "Recorded via Stripe webhook",
        }
        record, created = RefundRecord.objects.get_or_create(
            stripe_refund_id=refund_id, defaults=defaults
        )
        if not created:
            record.status = status_value
            record.error_message = refund.get("failure_reason", "") or record.error_message
            record.save(update_fields=["status", "error_message", "updated_at"])

    if registration:
        amount = data.get("amount", 0)
        amount_refunded = data.get("amount_refunded", 0)
        if amount and amount_refunded >= amount:
            registration.payment_status = Registration.PaymentStatus.REFUNDED
            registration.status = Registration.Status.CANCELLED
            registration.save(update_fields=["payment_status", "status", "updated_at"])
            if registration.user:
                try:
                    from accounts.notifications import create_notification

                    create_notification(
                        user=registration.user,
                        notification_type="refund_processed",
                        title="Refund processed",
                        message=f"Your refund for {registration.event.title} has been processed.",
                        action_url="/my-events",
                        metadata={"registration_uuid": str(registration.uuid)},
                    )
                except Exception as exc:
                    logger.warning("stripe.refund.notif_failed", extra={"error": str(exc)})


def handle_refund_updated(event):
    """Bank-rejection path for already-recorded refunds."""
    from billing.models import RefundRecord

    data = _data(event)
    refund_id = data.get("id")
    status = data.get("status")
    if not refund_id:
        return
    record = RefundRecord.objects.filter(stripe_refund_id=refund_id).first()
    if not record:
        return
    status_value = {
        "succeeded": RefundRecord.Status.SUCCEEDED,
        "failed": RefundRecord.Status.FAILED,
        "canceled": RefundRecord.Status.CANCELED,
    }.get(status, record.status)
    record.status = status_value
    if status == "failed":
        record.error_message = data.get("failure_reason", "") or record.error_message
    record.save(update_fields=["status", "error_message", "updated_at"])


def handle_payment_intent_failed(event):
    """Surface PaymentIntent failures (rare under Checkout) for investigation."""
    data = _data(event)
    logger.warning(
        "stripe.payment_intent.failed",
        extra={
            "payment_intent_id": data.get("id"),
            "last_error": (data.get("last_payment_error") or {}).get("message"),
        },
    )


# ---------------------------------------------------------------------------
# Disputes (chargebacks)
# ---------------------------------------------------------------------------


def _resolve_dispute_targets(payment_intent_id, charge_id):
    """Find the local Registration / CoursePurchase behind this dispute."""
    from billing.models import CoursePurchase
    from registrations.models import Registration

    registration = None
    purchase = None
    if payment_intent_id:
        registration = Registration.objects.filter(payment_intent_id=payment_intent_id).first()
        purchase = CoursePurchase.objects.filter(stripe_payment_intent_id=payment_intent_id).first()
    return registration, purchase


def _upsert_dispute(event, dispute_data, *, fire_alert: str | None = None):
    from billing.models import Dispute

    stripe_dispute_id = dispute_data.get("id")
    if not stripe_dispute_id:
        return None
    payment_intent_id = dispute_data.get("payment_intent") or ""
    charge_id = dispute_data.get("charge") or ""
    registration, purchase = _resolve_dispute_targets(payment_intent_id, charge_id)

    evidence_details = dispute_data.get("evidence_details") or {}
    evidence_due_by = _from_ts(evidence_details.get("due_by"))
    status = dispute_data.get("status") or "needs_response"
    reason = dispute_data.get("reason") or "general"
    outcome = ""
    closed_at = None
    submitted_at = _from_ts(evidence_details.get("submission_count_at"))
    if status in {"won", "lost", "warning_closed"}:
        outcome = status
        closed_at = timezone.now()

    dispute, created = Dispute.objects.update_or_create(
        stripe_dispute_id=stripe_dispute_id,
        defaults={
            "stripe_charge_id": charge_id,
            "stripe_payment_intent_id": payment_intent_id,
            "registration": registration,
            "course_purchase": purchase,
            "amount_cents": dispute_data.get("amount") or 0,
            "currency": dispute_data.get("currency", "usd"),
            "reason": reason,
            "status": status,
            "evidence_due_by": evidence_due_by,
            "submitted_at": submitted_at,
            "closed_at": closed_at,
            "outcome": outcome,
            "raw_payload": dispute_data,
        },
    )

    if fire_alert == "created":
        _alert_dispute_created(dispute)
    elif fire_alert == "lost":
        _alert_dispute_lost(dispute)

    return dispute


def handle_charge_dispute_created(event):
    _upsert_dispute(event, _data(event), fire_alert="created")


def handle_charge_dispute_updated(event):
    _upsert_dispute(event, _data(event))


def handle_charge_dispute_closed(event):
    data = _data(event)
    dispute = _upsert_dispute(event, data)
    if dispute and dispute.is_lost:
        _alert_dispute_lost(dispute)


def _alert_dispute_created(dispute):
    logger.warning(
        "stripe.dispute.created",
        extra={
            "dispute_id": dispute.stripe_dispute_id,
            "amount_cents": dispute.amount_cents,
            "due_by": dispute.evidence_due_by.isoformat() if dispute.evidence_due_by else None,
        },
    )


def _alert_dispute_lost(dispute):
    logger.error(
        "stripe.dispute.lost",
        extra={
            "dispute_id": dispute.stripe_dispute_id,
            "amount_cents": dispute.amount_cents,
            "registration_uuid": str(dispute.registration.uuid) if dispute.registration else None,
        },
    )


# ---------------------------------------------------------------------------
# Dispatch table — trimmed to what drives state
# ---------------------------------------------------------------------------

_DISPATCH = {
    # Checkout — primary fulfilment path
    "checkout.session.completed": handle_checkout_session_completed,
    "checkout.session.async_payment_succeeded": handle_checkout_session_async_payment_succeeded,
    "checkout.session.async_payment_failed": handle_checkout_session_async_payment_failed,
    "checkout.session.expired": handle_checkout_session_expired,
    # Refunds
    "charge.refunded": handle_charge_refunded,
    "refund.updated": handle_refund_updated,
    # Subscription lifecycle
    "customer.subscription.created": handle_subscription_created,
    "customer.subscription.updated": handle_subscription_updated,
    "customer.subscription.deleted": handle_subscription_deleted,
    # Billing
    "invoice.paid": handle_invoice_paid,
    "invoice.payment_failed": handle_invoice_payment_failed,
    "invoice.payment_action_required": handle_invoice_payment_failed,  # same action: set PAST_DUE, email
    # Disputes
    "charge.dispute.created": handle_charge_dispute_created,
    "charge.dispute.updated": handle_charge_dispute_updated,
    "charge.dispute.closed": handle_charge_dispute_closed,
    # Odd-paths worth logging
    "payment_intent.payment_failed": handle_payment_intent_failed,
}
