"""Unified checkout service — one path for every purchase kind.

Every purchase (event ticket, course, program) produces a
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


# We always re-fetch line items + tax breakdown so the webhook payload (and
# any reconciliation re-fetch) carries enough data for ``CoursePurchase`` to
# populate ``subtotal_cents`` and ``tax_cents`` without a second round-trip.
# Per the Stripe Checkout Session API, ``total_details`` is only populated
# on retrieval when the session was created with ``expand`` set.
SESSION_EXPAND = ["total_details", "total_details.breakdown", "line_items"]


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


def _validated_url(candidate: str | None, fallback: str) -> str:
    """Same-origin guard for client-supplied success/cancel URLs.

    Prevents a malicious caller from redirecting Stripe-issued tokens to
    a third-party origin. We anchor on ``settings.FRONTEND_URL``; if the
    candidate doesn't start with that base (or the env isn't configured),
    we fall back to the canonical kind-routed URL.
    """
    if not candidate:
        return fallback
    base = (getattr(settings, "FRONTEND_URL", "") or "").rstrip("/")
    if not base or not candidate.startswith(base):
        logger.warning("stripe.checkout.url_rejected", extra={"candidate": candidate})
        return fallback
    return candidate


def _resolve_redirect_urls(kind: str, success_url: str | None, cancel_url: str | None) -> tuple[str, str]:
    """Apply the same-origin guard and append the session-id placeholder.

    The placeholder is appended unconditionally so the ``verify-session``
    polling on the frontend (CheckoutReturn) always has the session id to
    look up, regardless of which client URL was supplied.
    """
    default_success, default_cancel = _success_and_cancel(kind)
    success = _validated_url(success_url, default_success)
    cancel = _validated_url(cancel_url, default_cancel)
    if success_url and "{CHECKOUT_SESSION_ID}" not in success:
        sep = "&" if "?" in success else "?"
        success = f"{success}{sep}session_id={{CHECKOUT_SESSION_ID}}&kind={kind}"
    if cancel_url and "kind=" not in cancel:
        sep = "&" if "?" in cancel else "?"
        cancel = f"{cancel}{sep}kind={kind}"
    return success, cancel


class CheckoutService:
    """One method per purchase kind. All return a ``CheckoutResult``."""

    # ------------------------------------------------------------------
    # Event ticket
    # ------------------------------------------------------------------
    def for_event_registration(
        self,
        registration,
        *,
        success_url: str | None = None,
        cancel_url: str | None = None,
    ) -> CheckoutResult:
        from events.models import Event

        event: Event = registration.event
        if event.price <= 0:
            raise ValueError("Free events should not use Checkout — fulfil directly.")

        stripe = get_stripe()
        user = registration.user
        # Paid events require login — see registrations.services. The customer
        # FK is therefore always set; we keep the email fallback only as a
        # defensive belt for any historical guest path that survived.
        customer_id = get_or_create_stripe_customer(user) if user else None
        success_url, cancel_url = _resolve_redirect_urls("event", success_url, cancel_url)

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
            expand=SESSION_EXPAND,
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
    # Multi-attendee event purchase (single-buyer)
    # ------------------------------------------------------------------
    def for_event_registrations(
        self,
        registrations,
        *,
        success_url: str | None = None,
        cancel_url: str | None = None,
    ) -> CheckoutResult:
        """One Stripe Checkout Session covering N event registrations.

        Used by multi-attendee single-buyer flows. All registrations
        must be for the same event. The returned session has
        ``quantity = N`` on a single line_item; Stripe ``automatic_tax``
        applies tax to the full subtotal. Webhook fulfilment reads
        ``metadata.registration_uuids`` (comma-separated) to fan out
        across all rows.
        """
        from events.models import Event

        registrations = list(registrations)
        if not registrations:
            raise ValueError("for_event_registrations: empty list")
        if len(registrations) == 1:
            return self.for_event_registration(registrations[0], success_url=success_url, cancel_url=cancel_url)

        event: Event = registrations[0].event
        if any(r.event_id != event.pk for r in registrations):
            raise ValueError("All registrations must be for the same event")
        if event.price <= 0:
            raise ValueError("Free events should not use Checkout — fulfil directly.")

        stripe = get_stripe()
        # Buyer = the authenticated owner of any registration in the
        # batch, if any (in multi-attendee, the buyer might or might not
        # also be an attendee). For pure-anonymous batches we send
        # `customer_email` instead, picking the first attendee's address.
        buyer = next((r.user for r in registrations if r.user_id is not None), None)
        customer_id = get_or_create_stripe_customer(buyer) if buyer else None
        buyer_email = buyer.email if buyer else registrations[0].email

        success_url, cancel_url = _resolve_redirect_urls("event", success_url, cancel_url)

        # Stripe metadata values are string-typed and capped at 500
        # chars. UUIDs are 36 chars + comma; comfortably fits up to ~13
        # entries. RegistrationService caps at 25 — split across two
        # metadata keys (`registration_uuids` + `registration_uuids_2`)
        # in the rare case we exceed one slot.
        all_uuids = [str(r.uuid) for r in registrations]
        joined = ",".join(all_uuids)
        meta = {
            "kind": "event_registration",
            "event_uuid": str(event.uuid),
            "user_id": str(buyer.pk) if buyer else "",
            "env": _env_tag(),
            "attendee_count": str(len(registrations)),
        }
        if len(joined) <= 480:
            meta["registration_uuids"] = joined
        else:
            mid = len(all_uuids) // 2
            meta["registration_uuids"] = ",".join(all_uuids[:mid])
            meta["registration_uuids_2"] = ",".join(all_uuids[mid:])
        # ``client_reference_id`` carries one row's UUID so the existing
        # legacy single-handler path still resolves a registration if a
        # webhook arrives stale-shaped. The handler prefers
        # ``registration_uuids`` if present.
        client_ref = all_uuids[0]

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
                "quantity": len(registrations),
            }],
            customer=customer_id,
            customer_email=None if customer_id else buyer_email,
            client_reference_id=client_ref,
            metadata=meta,
            automatic_tax={"enabled": True},
            allow_promotion_codes=True,
            customer_update={"address": "auto", "name": "auto"} if customer_id else None,
            billing_address_collection="required",
            success_url=success_url,
            cancel_url=cancel_url,
            expires_at=None,
            expand=SESSION_EXPAND,
            # Idempotency: same set of registration UUIDs → same session.
            # Sort to stabilise the key against client-side ordering noise.
            idempotency_key=f"checkout:event_regs:{':'.join(sorted(all_uuids))}:v1",
        )

        # Stamp every registration with the session id so the existing
        # single-handler legacy path can still find the row by session.
        for reg in registrations:
            reg.stripe_checkout_session_id = session.id
            reg.save(update_fields=["stripe_checkout_session_id", "updated_at"])
        logger.info(
            "stripe.checkout.event_registrations",
            extra={"session_id": session.id, "count": len(registrations)},
        )
        return CheckoutResult(url=session.url, session_id=session.id)

    # ------------------------------------------------------------------
    # Course purchase
    # ------------------------------------------------------------------
    def for_course_enrollment(
        self,
        user,
        course,
        *,
        success_url: str | None = None,
        cancel_url: str | None = None,
    ) -> CheckoutResult:
        if course.price_cents <= 0:
            raise ValueError("Free courses should enroll directly, not via Checkout.")

        stripe = get_stripe()
        customer_id = get_or_create_stripe_customer(user)
        success_url, cancel_url = _resolve_redirect_urls("course", success_url, cancel_url)

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
            expand=SESSION_EXPAND,
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
    def for_program_enrollment(
        self,
        user,
        program,
        *,
        success_url: str | None = None,
        cancel_url: str | None = None,
    ) -> CheckoutResult:
        if program.price_cents <= 0:
            raise ValueError("Free programs should enroll directly, not via Checkout.")

        stripe = get_stripe()
        customer_id = get_or_create_stripe_customer(user)
        success_url, cancel_url = _resolve_redirect_urls("program", success_url, cancel_url)

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
            expand=SESSION_EXPAND,
            idempotency_key=f"checkout:program:{program.uuid}:user:{user.uuid}:v1",
        )
        logger.info(
            "stripe.checkout.program_enrollment",
            extra={"session_id": session.id, "program_uuid": str(program.uuid), "user_id": user.pk},
        )
        return CheckoutResult(url=session.url, session_id=session.id)


checkout_service = CheckoutService()
