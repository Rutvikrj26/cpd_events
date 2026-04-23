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


def refund_payment_intent(payment_intent_id: str, *, reason: str | None = None) -> dict[str, Any]:
    """Issue a full refund on a PaymentIntent.

    Tax reversal is automatic because the original charge used
    ``automatic_tax``. Caller is responsible for updating local domain state
    (Registration / CoursePurchase) — typically that happens via the
    ``charge.refunded`` webhook handler.
    """
    stripe = get_stripe()
    idempotency_key = f"refund:{payment_intent_id}:v1"
    kwargs: dict[str, Any] = {"payment_intent": payment_intent_id}
    if reason:
        kwargs["reason"] = reason
    refund = stripe.Refund.create(idempotency_key=idempotency_key, **kwargs)
    return {"refund_id": refund.id, "status": refund.status, "amount_cents": refund.amount}
