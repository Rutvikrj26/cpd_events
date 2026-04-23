"""Promo code → Stripe sync.

Promo codes are redeemed at Stripe Checkout, not validated server-side: every
``stripe.checkout.Session`` we create sets ``allow_promotion_codes=True``,
and Stripe handles restriction checks (active, expiry, max uses, first-time).

Our ``PromoCode`` rows mirror a Stripe ``Coupon`` + ``PromotionCode``. The
``sync_to_stripe`` helper creates/updates those objects whenever a ``PromoCode``
is saved. ``PromoCodeUsage`` rows are written by the fulfilment handler
(``billing.handlers._fulfil_event_registration`` and friends) after Stripe
confirms payment — never pre-applied.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from billing.client import get_stripe

from .models import PromoCode

logger = logging.getLogger(__name__)


class PromoCodeSyncError(Exception):
    """Raised when syncing a promo code to Stripe fails."""


def sync_to_stripe(promo_code: PromoCode) -> PromoCode:
    """Create or update the matching Stripe Coupon + PromotionCode.

    Idempotent — uses business-intent idempotency keys so repeat calls with
    the same promo data collapse to one Stripe-side object. Safe to call from
    ``PromoCode.save()`` via a cloud task.
    """
    stripe = get_stripe()

    # 1. Coupon — carries the discount value + restrictions Stripe natively
    #    supports (expiry, max redemptions).
    coupon_kwargs: dict = {
        "name": promo_code.code,
        "metadata": {"promo_code_uuid": str(promo_code.uuid)},
    }
    if promo_code.discount_type == PromoCode.DiscountType.PERCENTAGE:
        coupon_kwargs["percent_off"] = float(promo_code.discount_value)
    else:
        coupon_kwargs["amount_off"] = int(Decimal(promo_code.discount_value) * 100)
        coupon_kwargs["currency"] = (promo_code.currency or "USD").lower()
    if promo_code.valid_until:
        coupon_kwargs["redeem_by"] = int(promo_code.valid_until.timestamp())
    if promo_code.max_uses:
        coupon_kwargs["max_redemptions"] = promo_code.max_uses
    coupon_kwargs["duration"] = "once"

    try:
        if promo_code.stripe_coupon_id:
            coupon = stripe.Coupon.retrieve(promo_code.stripe_coupon_id)
            # Stripe Coupons are mostly immutable — only name + metadata can change.
            stripe.Coupon.modify(
                coupon.id,
                name=coupon_kwargs["name"],
                metadata=coupon_kwargs["metadata"],
            )
        else:
            coupon = stripe.Coupon.create(
                **coupon_kwargs,
                idempotency_key=f"promo:coupon:{promo_code.uuid}:v1",
            )
            promo_code.stripe_coupon_id = coupon.id
    except Exception as exc:
        logger.exception("stripe.promo.coupon_sync_failed", extra={"promo_uuid": str(promo_code.uuid)})
        raise PromoCodeSyncError(f"Coupon sync failed: {exc}") from exc

    # 2. PromotionCode — the redeemable string buyers type at checkout.
    restrictions = {
        "first_time_transaction": bool(promo_code.first_time_only),
    }
    if promo_code.minimum_order_amount and promo_code.minimum_order_amount > 0:
        restrictions["minimum_amount"] = int(Decimal(promo_code.minimum_order_amount) * 100)
        restrictions["minimum_amount_currency"] = (promo_code.currency or "USD").lower()

    promo_kwargs: dict = {
        "coupon": promo_code.stripe_coupon_id,
        "code": promo_code.code,
        "active": bool(promo_code.is_active),
        "metadata": {"promo_code_uuid": str(promo_code.uuid)},
        "restrictions": restrictions,
    }
    if promo_code.valid_until:
        promo_kwargs["expires_at"] = int(promo_code.valid_until.timestamp())
    if promo_code.max_uses_per_user:
        promo_kwargs["max_redemptions"] = promo_code.max_uses_per_user

    try:
        if promo_code.stripe_promotion_code_id:
            stripe.PromotionCode.modify(
                promo_code.stripe_promotion_code_id,
                active=promo_kwargs["active"],
                metadata=promo_kwargs["metadata"],
            )
        else:
            promotion = stripe.PromotionCode.create(
                **promo_kwargs,
                idempotency_key=f"promo:code:{promo_code.uuid}:v1",
            )
            promo_code.stripe_promotion_code_id = promotion.id
    except Exception as exc:
        logger.exception("stripe.promo.code_sync_failed", extra={"promo_uuid": str(promo_code.uuid)})
        raise PromoCodeSyncError(f"PromotionCode sync failed: {exc}") from exc

    promo_code.save(update_fields=["stripe_coupon_id", "stripe_promotion_code_id", "updated_at"])
    logger.info(
        "stripe.promo.synced",
        extra={
            "promo_uuid": str(promo_code.uuid),
            "stripe_coupon_id": promo_code.stripe_coupon_id,
            "stripe_promotion_code_id": promo_code.stripe_promotion_code_id,
        },
    )
    return promo_code


def record_usage_from_checkout_session(session_data: dict, registration=None, user=None):
    """Write ``PromoCodeUsage`` rows for a completed Checkout Session.

    Called by the fulfilment handler. ``session_data`` is the raw dict of a
    ``stripe.checkout.Session``; we inspect ``total_details.breakdown.discounts``
    for every applied promotion code and resolve it to a local ``PromoCode``
    via ``stripe_promotion_code_id``.
    """
    from .models import PromoCodeUsage

    total_details = session_data.get("total_details") or {}
    breakdown = total_details.get("breakdown") or {}
    discounts = breakdown.get("discounts") or []

    if not discounts:
        return []

    amount_subtotal = session_data.get("amount_subtotal") or 0
    currency = session_data.get("currency", "usd")
    usages = []

    for entry in discounts:
        discount = entry.get("discount") or {}
        promo_code_id = discount.get("promotion_code")
        if not promo_code_id:
            continue

        local = PromoCode.objects.filter(stripe_promotion_code_id=promo_code_id).first()
        if not local:
            logger.warning(
                "stripe.promo.unknown_code",
                extra={"stripe_promotion_code_id": promo_code_id, "session_id": session_data.get("id")},
            )
            continue

        discount_cents = entry.get("amount") or 0
        original_price = Decimal(amount_subtotal) / Decimal("100")
        discount_amount = Decimal(discount_cents) / Decimal("100")
        final_price = max(Decimal("0.00"), original_price - discount_amount)

        usage = PromoCodeUsage.objects.create(
            promo_code=local,
            registration=registration,
            user_email=(registration.email if registration else (user.email if user else "")),
            user=user or (registration.user if registration else None),
            original_price=original_price,
            discount_amount=discount_amount,
            final_price=final_price,
        )
        local.increment_usage()
        usages.append(usage)
        logger.info(
            "stripe.promo.usage_recorded",
            extra={
                "promo_uuid": str(local.uuid),
                "registration_uuid": str(registration.uuid) if registration else None,
                "discount_amount": str(discount_amount),
                "currency": currency,
            },
        )

    return usages
