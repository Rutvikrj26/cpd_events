"""Billing services.

Stripe primitives (Checkout Sessions, Portal Sessions, Customer upsert) live
in ``billing.checkout``. This module is kept thin for a few ancillary helpers
used outside the Checkout path — mostly for admin/reconciliation tooling.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from billing.client import get_stripe

logger = logging.getLogger(__name__)


def list_payment_intents(created_gte: datetime | None = None, limit: int = 200) -> list[Any]:
    """Page through Stripe PaymentIntents for reconciliation.

    Reused by the daily ``reconcile_stripe`` command; not used in the
    primary purchase flow (that's all Checkout Sessions now).
    """
    stripe = get_stripe()
    params: dict[str, Any] = {"limit": 100}
    if created_gte:
        params["created"] = {"gte": int(created_gte.timestamp())}

    out: list[Any] = []
    response = stripe.PaymentIntent.list(**params)
    for intent in response.auto_paging_iter():
        out.append(intent)
        if len(out) >= limit:
            break
    return out


def refund_payment_intent(
    payment_intent_id: str,
    *,
    amount_cents: int | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Issue a refund on a PaymentIntent.

    Args:
        payment_intent_id: the Stripe PaymentIntent to refund.
        amount_cents: optional partial amount. If omitted, Stripe refunds the
            full remaining refundable amount.
        reason: one of Stripe's enum values (``duplicate``, ``fraudulent``,
            ``requested_by_customer``) or None.

    Tax reversal is automatic because the original charge used
    ``automatic_tax``. Caller is responsible for updating local domain state
    (Registration / CoursePurchase) — typically that happens via the
    ``charge.refunded`` webhook handler.

    Idempotency: the key includes amount so successive partial refunds for
    different amounts don't collide with one another, while retries of the
    same partial refund call collapse to a single Stripe refund.
    """
    stripe = get_stripe()
    amount_tag = amount_cents if amount_cents is not None else "full"
    idempotency_key = f"refund:{payment_intent_id}:{amount_tag}:v1"
    kwargs: dict[str, Any] = {"payment_intent": payment_intent_id}
    if amount_cents is not None:
        kwargs["amount"] = int(amount_cents)
    if reason:
        kwargs["reason"] = reason
    refund = stripe.Refund.create(idempotency_key=idempotency_key, **kwargs)
    return {"refund_id": refund.id, "status": refund.status, "amount_cents": refund.amount}
