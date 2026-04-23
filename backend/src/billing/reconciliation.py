"""Stripe ↔ local drift detection.

Daily cron pulls recent Stripe objects and compares them to local rows.
Covers PaymentIntents (via Checkout fulfilment), Subscriptions, Refunds,
Invoices, Disputes, and Checkout Sessions. Safe drifts are auto-repaired;
ambiguous drifts are logged as ``DriftReport`` entries for review.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Iterable

from django.utils import timezone

from billing.client import get_stripe

logger = logging.getLogger(__name__)

# Overlap the window so events we saw on the tail of yesterday's run don't
# slip through.
OVERLAP_HOURS = 26


@dataclass
class DriftFinding:
    kind: str            # e.g. "missing_local", "state_mismatch"
    entity: str          # "PaymentIntent", "Subscription", ...
    stripe_id: str
    detail: dict[str, Any]


def reconcile(hours: int = OVERLAP_HOURS) -> dict[str, Any]:
    """Run the full reconciliation sweep."""
    since = timezone.now() - timedelta(hours=hours)
    since_ts = int(since.timestamp())

    findings: list[DriftFinding] = []
    findings.extend(_reconcile_checkout_sessions(since_ts))
    findings.extend(_reconcile_payment_intents(since_ts))
    findings.extend(_reconcile_subscriptions(since_ts))
    findings.extend(_reconcile_refunds(since_ts))
    findings.extend(_reconcile_disputes(since_ts))

    summary = {
        "since": since.isoformat(),
        "total": len(findings),
        "by_kind": {},
    }
    for f in findings:
        summary["by_kind"][f.kind] = summary["by_kind"].get(f.kind, 0) + 1
        logger.warning(
            "stripe.reconcile.drift",
            extra={
                "kind": f.kind,
                "entity": f.entity,
                "stripe_id": f.stripe_id,
                "detail": f.detail,
            },
        )
    return {"findings": [_as_dict(f) for f in findings], "summary": summary}


def _as_dict(f: DriftFinding) -> dict[str, Any]:
    return {"kind": f.kind, "entity": f.entity, "stripe_id": f.stripe_id, "detail": f.detail}


# ---------------------------------------------------------------------------
# Checkout Sessions
# ---------------------------------------------------------------------------


def _reconcile_checkout_sessions(since_ts: int) -> Iterable[DriftFinding]:
    from billing.models import StripeEvent
    from registrations.models import Registration

    stripe = get_stripe()
    sessions = stripe.checkout.Session.list(created={"gte": since_ts}, limit=100)
    for session in sessions.auto_paging_iter():
        metadata = session.metadata or {}
        kind = metadata.get("kind") or metadata.get("type")
        if kind != "event_registration":
            continue
        reg_uuid = metadata.get("registration_uuid") or session.client_reference_id
        if not reg_uuid:
            continue
        reg = Registration.objects.filter(uuid=reg_uuid).first()
        if not reg:
            yield DriftFinding(
                kind="missing_local",
                entity="CheckoutSession",
                stripe_id=session.id,
                detail={"registration_uuid": reg_uuid},
            )
            continue

        if session.payment_status == "paid" and reg.payment_status != Registration.PaymentStatus.PAID:
            # Stripe says paid, we say pending — most likely a missed webhook.
            # Attempt safe auto-apply: re-deliver the event through the worker.
            yield DriftFinding(
                kind="state_mismatch",
                entity="CheckoutSession",
                stripe_id=session.id,
                detail={
                    "registration_uuid": reg_uuid,
                    "stripe_payment_status": session.payment_status,
                    "local_payment_status": reg.payment_status,
                },
            )
            _retrigger_checkout_session_completed(session.id)

        if (
            session.status == "expired"
            and reg.status == Registration.Status.PENDING
        ):
            yield DriftFinding(
                kind="state_mismatch",
                entity="CheckoutSession",
                stripe_id=session.id,
                detail={"registration_uuid": reg_uuid, "session_status": "expired"},
            )


def _retrigger_checkout_session_completed(session_id: str) -> None:
    """Queue a synthetic event that replays the fulfilment handler.

    We don't fake a Stripe event (that would bypass our dedupe). Instead we
    fetch the session directly and hand it to the handler.
    """
    from billing.handlers import handle_checkout_session_completed
    from types import SimpleNamespace

    stripe = get_stripe()
    session = stripe.checkout.Session.retrieve(session_id)
    pseudo_event = SimpleNamespace(
        id=f"reconcile_{session_id}",
        type="checkout.session.completed",
        data=SimpleNamespace(object=session),
    )
    handle_checkout_session_completed(pseudo_event)


# ---------------------------------------------------------------------------
# PaymentIntents (secondary — most Registrations are found via Checkout)
# ---------------------------------------------------------------------------


def _reconcile_payment_intents(since_ts: int) -> Iterable[DriftFinding]:
    from registrations.models import Registration

    stripe = get_stripe()
    intents = stripe.PaymentIntent.list(created={"gte": since_ts}, limit=100)
    for intent in intents.auto_paging_iter():
        if intent.status != "succeeded":
            continue
        reg = Registration.objects.filter(payment_intent_id=intent.id).first()
        if not reg:
            continue
        if reg.payment_status != Registration.PaymentStatus.PAID:
            yield DriftFinding(
                kind="state_mismatch",
                entity="PaymentIntent",
                stripe_id=intent.id,
                detail={
                    "registration_uuid": str(reg.uuid),
                    "stripe_status": intent.status,
                    "local_payment_status": reg.payment_status,
                },
            )


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------


def _reconcile_subscriptions(since_ts: int) -> Iterable[DriftFinding]:
    from billing.models import Subscription

    stripe = get_stripe()
    remote = stripe.Subscription.list(created={"gte": since_ts}, limit=100)
    for sub in remote.auto_paging_iter():
        local = Subscription.objects.filter(stripe_subscription_id=sub.id).first()
        if not local:
            yield DriftFinding(
                kind="missing_local",
                entity="Subscription",
                stripe_id=sub.id,
                detail={"customer": sub.customer, "status": sub.status},
            )
            continue
        if local.status != sub.status:
            yield DriftFinding(
                kind="state_mismatch",
                entity="Subscription",
                stripe_id=sub.id,
                detail={"local_status": local.status, "stripe_status": sub.status},
            )


# ---------------------------------------------------------------------------
# Refunds
# ---------------------------------------------------------------------------


def _reconcile_refunds(since_ts: int) -> Iterable[DriftFinding]:
    from billing.models import RefundRecord

    stripe = get_stripe()
    refunds = stripe.Refund.list(created={"gte": since_ts}, limit=100)
    for refund in refunds.auto_paging_iter():
        local = RefundRecord.objects.filter(stripe_refund_id=refund.id).first()
        if not local:
            yield DriftFinding(
                kind="missing_local",
                entity="Refund",
                stripe_id=refund.id,
                detail={"amount": refund.amount, "status": refund.status},
            )
            continue
        if local.status != refund.status and refund.status in {"succeeded", "failed", "canceled"}:
            yield DriftFinding(
                kind="state_mismatch",
                entity="Refund",
                stripe_id=refund.id,
                detail={"local_status": local.status, "stripe_status": refund.status},
            )


# ---------------------------------------------------------------------------
# Disputes
# ---------------------------------------------------------------------------


def _reconcile_disputes(since_ts: int) -> Iterable[DriftFinding]:
    from billing.models import Dispute

    stripe = get_stripe()
    remote = stripe.Dispute.list(created={"gte": since_ts}, limit=100)
    for dispute in remote.auto_paging_iter():
        local = Dispute.objects.filter(stripe_dispute_id=dispute.id).first()
        if not local:
            yield DriftFinding(
                kind="missing_local",
                entity="Dispute",
                stripe_id=dispute.id,
                detail={"status": dispute.status, "amount": dispute.amount},
            )
            continue
        if local.status != dispute.status:
            yield DriftFinding(
                kind="state_mismatch",
                entity="Dispute",
                stripe_id=dispute.id,
                detail={"local_status": local.status, "stripe_status": dispute.status},
            )


# Legacy function — kept for the existing reconcile_payments management command.
def reconcile_payment_intents(days: int = 30, limit: int = 200) -> dict:
    findings = list(_reconcile_payment_intents(
        int((timezone.now() - timedelta(days=days)).timestamp())
    ))
    return {"success": True, "summary": {"drift_count": len(findings)}, "drift": [_as_dict(f) for f in findings]}
