"""Unified checkout service — one path for every purchase kind.

Every purchase (event ticket, course, program, subscription) produces a
``stripe.checkout.Session`` and returns its URL. The frontend always does
"POST → redirect". Fulfilment happens in ``billing.handlers`` on
``checkout.session.completed``.

Design notes:
- Every mutating call passes an idempotency key scoped to the business
  intent (``<kind>:<entity_uuid>:<step>:v1``), so retries collapse.
- ``automatic_tax`` and ``allow_promotion_codes`` are always on; Stripe
  Checkout picks payment methods itself based on the account's dashboard
  settings, so we don't pass ``payment_method_types`` at all.
- Metadata carries back-pointers to our DB (``kind``, ``*_uuid``, ``user_id``,
  ``env``) so Dashboard lookups resolve to the local row.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from django.conf import settings

from billing.client import get_stripe

logger = logging.getLogger(__name__)


@dataclass
class CheckoutResult:
    url: str
    session_id: str


# ---------------------------------------------------------------------------
# Customer upsert
# ---------------------------------------------------------------------------


def get_or_create_stripe_customer(user) -> str:
    """Return the user's Stripe Customer id, creating one on first call.

    Uses the user's uuid in the idempotency key so concurrent logins collapse
    to one Customer create. Writes back ``User.stripe_customer_id``.
    """
    if getattr(user, "stripe_customer_id", None):
        return user.stripe_customer_id

    stripe = get_stripe()
    customer = stripe.Customer.create(
        email=user.email,
        name=getattr(user, "full_name", None) or user.email,
        metadata={"user_id": str(user.pk), "user_uuid": str(user.uuid)},
        idempotency_key=f"customer:user:{user.uuid}:v1",
    )
    user.stripe_customer_id = customer.id
    user.save(update_fields=["stripe_customer_id", "updated_at"])
    return customer.id


# ---------------------------------------------------------------------------
# CheckoutService
# ---------------------------------------------------------------------------


def _env_tag() -> str:
    return "prod" if not settings.DEBUG else "dev"


def _frontend_url(path: str) -> str:
    base = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
    return f"{base}{path}"


def _success_and_cancel(kind: str) -> tuple[str, str]:
    # Include ``kind`` in success too so /checkout/success can route the
    # learner to the right dashboard (events → /registrations, courses →
    # /dashboard, programs → /my-programs) without a second API round-trip.
    success = _frontend_url(f"/checkout/success?session_id={{CHECKOUT_SESSION_ID}}&kind={kind}")
    cancel = _frontend_url(f"/checkout/cancel?kind={kind}")
    return success, cancel


class CheckoutService:
    """One method per purchase kind. All return a ``CheckoutResult``."""

    # ------------------------------------------------------------------
    # Event ticket
    # ------------------------------------------------------------------
    def for_event_registration(self, registration) -> CheckoutResult:
        from events.models import Event

        event: Event = registration.event
        if event.price <= 0:
            raise ValueError("Free events should not use Checkout — fulfil directly.")

        stripe = get_stripe()
        user = registration.user
        customer_id = get_or_create_stripe_customer(user) if user else None

        success_url, cancel_url = _success_and_cancel("event")

        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": event.currency.lower(),
                    "product_data": {
                        "name": event.title,
                        "description": (event.short_description or "")[:500] or None,
                        "metadata": {"event_uuid": str(event.uuid)},
                    },
                    "unit_amount": int(event.price * 100),
                    "tax_behavior": "exclusive",
                },
                "quantity": 1,
            }],
            customer=customer_id,
            customer_email=None if customer_id else registration.email,
            client_reference_id=str(registration.uuid),
            metadata={
                "kind": "event_registration",
                "registration_uuid": str(registration.uuid),
                "event_uuid": str(event.uuid),
                "user_id": str(user.pk) if user else "",
                "env": _env_tag(),
            },
            automatic_tax={"enabled": True},
            allow_promotion_codes=True,
            customer_update={"address": "auto", "name": "auto"} if customer_id else None,
            billing_address_collection="required",
            success_url=success_url,
            cancel_url=cancel_url,
            expires_at=None,  # default 24h
            idempotency_key=f"checkout:event_reg:{registration.uuid}:v1",
        )

        registration.stripe_checkout_session_id = session.id
        registration.save(update_fields=["stripe_checkout_session_id", "updated_at"])
        logger.info(
            "stripe.checkout.event_registration",
            extra={"session_id": session.id, "registration_uuid": str(registration.uuid)},
        )
        return CheckoutResult(url=session.url, session_id=session.id)

    # ------------------------------------------------------------------
    # Course purchase
    # ------------------------------------------------------------------
    def for_course_enrollment(self, user, course) -> CheckoutResult:
        if course.price_cents <= 0:
            raise ValueError("Free courses should enroll directly, not via Checkout.")

        stripe = get_stripe()
        customer_id = get_or_create_stripe_customer(user)
        success_url, cancel_url = _success_and_cancel("course")

        line_items = self._course_line_items(course)

        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=line_items,
            customer=customer_id,
            client_reference_id=str(course.uuid),
            metadata={
                "kind": "course_enrollment",
                "course_uuid": str(course.uuid),
                "user_id": str(user.pk),
                "env": _env_tag(),
            },
            automatic_tax={"enabled": True},
            allow_promotion_codes=True,
            customer_update={"address": "auto", "name": "auto"},
            billing_address_collection="required",
            success_url=success_url,
            cancel_url=cancel_url,
            idempotency_key=f"checkout:course:{course.uuid}:user:{user.uuid}:v1",
        )
        logger.info(
            "stripe.checkout.course_enrollment",
            extra={"session_id": session.id, "course_uuid": str(course.uuid), "user_id": user.pk},
        )
        return CheckoutResult(url=session.url, session_id=session.id)

    def _course_line_items(self, course) -> list[dict[str, Any]]:
        if course.stripe_price_id:
            return [{"price": course.stripe_price_id, "quantity": 1}]
        return [{
            "price_data": {
                "currency": course.currency.lower(),
                "product_data": {
                    "name": course.title,
                    "description": (course.short_description or "")[:500] or None,
                    "metadata": {"course_uuid": str(course.uuid)},
                },
                "unit_amount": course.price_cents,
                "tax_behavior": "exclusive",
            },
            "quantity": 1,
        }]

    # ------------------------------------------------------------------
    # Program purchase (bundle)
    # ------------------------------------------------------------------
    def for_program_enrollment(self, user, program) -> CheckoutResult:
        if program.price_cents <= 0:
            raise ValueError("Free programs should enroll directly, not via Checkout.")

        stripe = get_stripe()
        customer_id = get_or_create_stripe_customer(user)
        success_url, cancel_url = _success_and_cancel("program")

        if program.stripe_price_id:
            line_items = [{"price": program.stripe_price_id, "quantity": 1}]
        else:
            line_items = [{
                "price_data": {
                    "currency": program.currency.lower(),
                    "product_data": {
                        "name": program.title,
                        "description": (program.short_description or "")[:500] or None,
                        "metadata": {"program_uuid": str(program.uuid)},
                    },
                    "unit_amount": program.price_cents,
                    "tax_behavior": "exclusive",
                },
                "quantity": 1,
            }]

        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=line_items,
            customer=customer_id,
            client_reference_id=str(program.uuid),
            metadata={
                "kind": "program_enrollment",
                "program_uuid": str(program.uuid),
                "user_id": str(user.pk),
                "env": _env_tag(),
            },
            automatic_tax={"enabled": True},
            allow_promotion_codes=True,
            customer_update={"address": "auto", "name": "auto"},
            billing_address_collection="required",
            success_url=success_url,
            cancel_url=cancel_url,
            idempotency_key=f"checkout:program:{program.uuid}:user:{user.uuid}:v1",
        )
        logger.info(
            "stripe.checkout.program_enrollment",
            extra={"session_id": session.id, "program_uuid": str(program.uuid), "user_id": user.pk},
        )
        return CheckoutResult(url=session.url, session_id=session.id)


checkout_service = CheckoutService()
