"""Webhook event handlers, dispatched from the async worker.

Every purchase goes through Stripe Checkout Sessions. Fulfilment flips the
relevant local row (Registration / CourseEnrollment / ProgramEnrollment) in
response to ``checkout.session.completed``. The PaymentIntent path is gone —
the only reason we keep ``payment_intent.payment_failed`` is to flag the
odd Checkout Session that completes with a failed intent (rare, but
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


def _upsert_purchase_from_session(session_data, *, user, course=None, event=None, program=None):
    """Idempotent CoursePurchase upsert keyed on stripe_checkout_session_id.

    Single source of truth for every paid surface (event/course/program).
    Caller passes exactly one of course/event/program — the model-level
    ``purchase_one_target`` CheckConstraint will raise loudly if that
    invariant is broken.

    Re-fetches the session with ``expand=total_details`` if the webhook
    payload doesn't carry tax breakdown. Stripe only includes
    ``total_details`` in webhook payloads when the session was created with
    ``expand`` set; we set it on create (see ``billing.checkout``) but we
    also defend against legacy / replayed sessions here.
    """
    from billing.models import CoursePurchase

    if not session_data.get("total_details"):
        from billing.client import get_stripe

        try:
            stripe = get_stripe()
            refreshed = stripe.checkout.Session.retrieve(
                session_data.get("id"),
                expand=["total_details", "total_details.breakdown"],
            )
            session_data = refreshed.to_dict() if hasattr(refreshed, "to_dict") else dict(refreshed)
        except Exception as exc:
            logger.warning(
                "stripe.checkout.expand_total_details_failed",
                extra={"session_id": session_data.get("id"), "error": str(exc)},
            )

    amount_total = int(session_data.get("amount_total") or 0)
    tax_amount = int((session_data.get("total_details") or {}).get("amount_tax") or 0)
    subtotal = int(session_data.get("amount_subtotal") or max(amount_total - tax_amount, 0))

    purchase, _created = CoursePurchase.objects.update_or_create(
        stripe_checkout_session_id=session_data.get("id") or "",
        defaults={
            "user": user,
            "course": course,
            "event": event,
            "program": program,
            "amount_cents": amount_total,
            "subtotal_cents": subtotal,
            "tax_cents": tax_amount,
            "currency": (session_data.get("currency") or "usd").upper(),
            "stripe_payment_intent_id": session_data.get("payment_intent") or "",
            "status": CoursePurchase.Status.COMPLETED,
        },
    )
    return purchase, session_data


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


def _registration_uuids_from_metadata(metadata, session_data) -> list[str]:
    """Extract one or more Registration UUIDs from a Stripe webhook payload.

    Three shapes supported:
      - new multi-attendee:    ``metadata.registration_uuids = "uuid1,uuid2,..."``
      - new multi-overflow:    plus ``metadata.registration_uuids_2 = "..."``
      - legacy single:         ``metadata.registration_uuid = "uuid"``
                               or ``session_data.client_reference_id``
    """
    uuids: list[str] = []
    primary = (metadata or {}).get("registration_uuids")
    secondary = (metadata or {}).get("registration_uuids_2")
    if primary:
        uuids.extend(u.strip() for u in primary.split(",") if u.strip())
    if secondary:
        uuids.extend(u.strip() for u in secondary.split(",") if u.strip())
    if uuids:
        return uuids
    legacy = (metadata or {}).get("registration_uuid") or session_data.get("client_reference_id")
    return [legacy] if legacy else []


def _fulfil_event_registration(session_data):
    from registrations.models import Registration

    metadata = session_data.get("metadata") or {}
    reg_uuids = _registration_uuids_from_metadata(metadata, session_data)
    if not reg_uuids:
        logger.error(
            "stripe.checkout.event_registration.missing_uuid",
            extra={"session_id": session_data.get("id")},
        )
        return

    registrations = list(
        Registration.objects.select_related("event", "user").filter(uuid__in=reg_uuids)
    )
    if not registrations:
        logger.error(
            "stripe.checkout.event_registration.not_found",
            extra={"registration_uuids": reg_uuids},
        )
        return

    # All registrations in one session must point at the same event —
    # the checkout service guarantees this. We use the first to seed
    # the receipt row.
    reg = registrations[0]

    # Canonical receipt — written before we touch the Registrations so
    # that the unique ``stripe_checkout_session_id`` on CoursePurchase is
    # the serialisation point for concurrent webhook deliveries. The
    # purchase aggregates the whole batch (one CoursePurchase, N regs).
    purchase, session_data = _upsert_purchase_from_session(
        session_data, user=reg.user, event=reg.event,
    )

    # The handler is idempotent: every step below is safe to re-run. No global
    # short-circuit on ``payment_status == PAID`` — that would skip downstream
    # side effects (promo recording, confirmation email) when reconciliation
    # or a webhook retry arrives after a prior run already set the row to PAID.
    #
    # Multi-attendee: amounts are aggregated on the CoursePurchase, but each
    # Registration carries its per-ticket subtotal. We split the receipt
    # totals proportionally across N registrations so per-row reporting
    # stays meaningful.
    n = len(registrations)
    per_total = _cents_to_decimal(purchase.amount_cents // n) if n else Decimal("0")
    per_tax = _cents_to_decimal(purchase.tax_cents // n) if n else Decimal("0")
    per_subtotal = _cents_to_decimal(purchase.subtotal_cents // n) if n else Decimal("0")
    new_pi = purchase.stripe_payment_intent_id
    new_session_id = purchase.stripe_checkout_session_id

    with transaction.atomic():
        locked = list(
            Registration.objects.select_for_update().filter(pk__in=[r.pk for r in registrations])
        )
        for r in locked:
            new_status = (
                Registration.Status.CONFIRMED
                if r.status == Registration.Status.PENDING
                else r.status
            )
            dirty = []
            if r.total_amount != per_total:
                r.total_amount = per_total
                dirty.append("total_amount")
            if r.amount_paid != per_subtotal:
                r.amount_paid = per_subtotal
                dirty.append("amount_paid")
            if r.tax_amount != per_tax:
                r.tax_amount = per_tax
                dirty.append("tax_amount")
            if r.payment_status != Registration.PaymentStatus.PAID:
                r.payment_status = Registration.PaymentStatus.PAID
                dirty.append("payment_status")
            if (new_pi or "") and r.payment_intent_id != (new_pi or ""):
                r.payment_intent_id = new_pi or ""
                dirty.append("payment_intent_id")
            if new_session_id and r.stripe_checkout_session_id != new_session_id:
                r.stripe_checkout_session_id = new_session_id
                dirty.append("stripe_checkout_session_id")
            if r.status != new_status:
                r.status = new_status
                dirty.append("status")
            if r.purchase_id != purchase.pk:
                r.purchase = purchase
                dirty.append("purchase")
            if dirty:
                dirty.append("updated_at")
                r.save(update_fields=dirty)
        # Refresh the local list so post-atomic side-effects see fresh state.
        registrations = locked

    # Promo-code recording. Tied to the receipt; we only need to call once.
    try:
        from promo_codes.services import record_usage_from_checkout_session

        record_usage_from_checkout_session(
            session_data, purchase=purchase, registration=registrations[0], user=registrations[0].user,
        )
    except Exception as exc:
        logger.warning(
            "stripe.checkout.event_registration.promo_usage_failed",
            extra={"registration_uuids": [str(r.uuid) for r in registrations], "error": str(exc)},
        )

    # Confirmation emails — one per attendee.
    for r in registrations:
        if r.status == Registration.Status.CONFIRMED:
            try:
                from registrations.tasks import send_registration_confirmation

                send_registration_confirmation.delay(r.id)
            except Exception as exc:
                logger.warning(
                    "stripe.checkout.event_registration.email_failed",
                    extra={"registration_uuid": str(r.uuid), "error": str(exc)},
                )

    # Anonymous-paid claim hooks — one CLAIM link per anonymous attendee.
    # Issued *after* the atomic block so a webhook retry sees a fully-
    # fulfilled row (PAID + CONFIRMED) before deciding whether to send.
    # Idempotent: the unique partial index on MagicLink(registration,
    # purpose=CLAIM, status=PENDING) collapses concurrent retries.
    for r in registrations:
        if r.user_id is None and r.payment_status == Registration.PaymentStatus.PAID:
            try:
                from accounts.services import create_registration_claim
                from accounts.tasks import send_magic_link_email

                link = create_registration_claim(r)
                send_magic_link_email(link.id)
            except Exception as exc:
                logger.warning(
                "stripe.checkout.event_registration.claim_link_failed",
                extra={"registration_uuid": str(r.uuid), "error": str(exc)},
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

    purchase, session_data = _upsert_purchase_from_session(
        session_data, user=user, course=course,
    )

    session_id = purchase.stripe_checkout_session_id or ""
    enrollment, created = CourseEnrollment.objects.get_or_create(
        user=user,
        course=course,
        defaults={
            "status": CourseEnrollment.Status.ACTIVE,
            "stripe_checkout_session_id": session_id,
        },
    )
    enrollment_dirty = []
    if not created and enrollment.status != CourseEnrollment.Status.ACTIVE:
        enrollment.status = CourseEnrollment.Status.ACTIVE
        enrollment_dirty.append("status")
    if not enrollment.stripe_checkout_session_id and session_id:
        enrollment.stripe_checkout_session_id = session_id
        enrollment_dirty.append("stripe_checkout_session_id")
    if enrollment_dirty:
        enrollment_dirty.append("updated_at")
        enrollment.save(update_fields=enrollment_dirty)

    course.update_counts()

    try:
        from promo_codes.services import record_usage_from_checkout_session

        record_usage_from_checkout_session(session_data, purchase=purchase, user=user)
    except Exception as exc:
        logger.warning(
            "stripe.checkout.course.promo_usage_failed",
            extra={"course_uuid": course_uuid, "error": str(exc)},
        )


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

    purchase, session_data = _upsert_purchase_from_session(
        session_data, user=user, program=program,
    )
    session_id = purchase.stripe_checkout_session_id or ""

    enrollment, _ = ProgramEnrollment.objects.get_or_create(
        user=user,
        program=program,
        defaults={"stripe_checkout_session_id": session_id},
    )
    if not enrollment.stripe_checkout_session_id and session_id:
        enrollment.stripe_checkout_session_id = session_id
    enrollment.activate()
    program.update_counts()

    try:
        from promo_codes.services import record_usage_from_checkout_session

        record_usage_from_checkout_session(session_data, purchase=purchase, user=user)
    except Exception as exc:
        logger.warning(
            "stripe.checkout.program.promo_usage_failed",
            extra={"program_uuid": program_uuid, "error": str(exc)},
        )


# ---------------------------------------------------------------------------
# Refunds
# ---------------------------------------------------------------------------


def handle_charge_refunded(event):
    """Webhook is now informational — RefundPurchaseView already updated state.

    We still write ``RefundRecord`` rows so admins can audit refunds initiated
    from the Stripe Dashboard (i.e. without going through our endpoint), and
    we still send the user notification for event refunds since that's a
    purchase-side concern.
    """
    from billing.models import CoursePurchase, RefundRecord
    from registrations.models import Registration

    data = _data(event)
    payment_intent_id = data.get("payment_intent")
    refunds = (data.get("refunds") or {}).get("data") or []

    purchase = None
    registration = None
    if payment_intent_id:
        purchase = (
            CoursePurchase.objects
            .select_related("event")
            .prefetch_related("registrations")
            .filter(stripe_payment_intent_id=payment_intent_id)
            .first()
        )
        if purchase and purchase.event_id:
            registration = purchase.registrations.first()

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
            "purchase": purchase,
            "stripe_payment_intent_id": payment_intent_id or "",
            "amount_cents": refund.get("amount", 0),
            "currency": (refund.get("currency") or "").upper(),
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

    # Mirror the unified-refund cascade for refunds that originated outside
    # our endpoint (Stripe Dashboard direct refund). The endpoint path above
    # already did this work, so this branch is a no-op for in-app refunds.
    amount = data.get("amount", 0)
    amount_refunded = data.get("amount_refunded", 0)
    if amount and amount_refunded >= amount:
        if purchase and purchase.status != CoursePurchase.Status.REFUNDED:
            purchase.status = CoursePurchase.Status.REFUNDED
            purchase.save(update_fields=["status", "updated_at"])
        if registration:
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
                        action_url="/registrations?tab=events",
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
    """Find the local CoursePurchase + (if event) linked Registration."""
    from billing.models import CoursePurchase

    purchase = None
    registration = None
    if payment_intent_id:
        purchase = (
            CoursePurchase.objects
            .select_related("event")
            .prefetch_related("registrations")
            .filter(stripe_payment_intent_id=payment_intent_id)
            .first()
        )
        if purchase and purchase.event_id:
            registration = purchase.registrations.first()
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
    # Checkout — primary fulfilment path for course/event/program purchases
    "checkout.session.completed": handle_checkout_session_completed,
    "checkout.session.async_payment_succeeded": handle_checkout_session_async_payment_succeeded,
    "checkout.session.async_payment_failed": handle_checkout_session_async_payment_failed,
    "checkout.session.expired": handle_checkout_session_expired,
    # Refunds
    "charge.refunded": handle_charge_refunded,
    "refund.updated": handle_refund_updated,
    # Disputes
    "charge.dispute.created": handle_charge_dispute_created,
    "charge.dispute.updated": handle_charge_dispute_updated,
    "charge.dispute.closed": handle_charge_dispute_closed,
    # Odd-paths worth logging
    "payment_intent.payment_failed": handle_payment_intent_failed,
}
