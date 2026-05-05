"""Registration service.

Flow:
    free event     → create Registration(status=CONFIRMED, payment=NA), done.
    paid event     → create Registration(status=PENDING, payment=PENDING),
                     return a Stripe Checkout Session URL. The frontend
                     redirects; fulfilment happens in
                     ``billing.handlers.handle_checkout_session_completed``.
    event at cap   → route to waitlist when enabled; else reject.

Stripe-hosted Promotion Codes handle discounts at checkout time. We no
longer pre-compute discounts or write ``PromoCodeUsage`` before payment —
that happens in the fulfilment handler from the session payload.
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import Max
from rest_framework.exceptions import ValidationError

from events.models import Event
from registrations.models import CustomFieldResponse, Registration

logger = logging.getLogger(__name__)


class RegistrationService:
    """Create and manage Registrations; delegate payment to Stripe Checkout."""

    def register_participant(self, event: Event, data: dict[str, Any], user=None) -> dict[str, Any]:
        if not event.is_open_for_registration:
            raise ValidationError("Event registration is closed.")

        email = (data.get("email") or "").lower()
        full_name = data.get("full_name", "")

        if user:
            email = user.email
            full_name = full_name or user.full_name

        if not email:
            raise ValidationError("Email is required.")

        # Anonymous flow: an email already attached to a User account
        # cannot complete an anonymous registration. We refuse here
        # rather than silently linking — the registrant might not be
        # the account owner. The frontend renders an inline auth
        # challenge with a "Sign in" CTA and the prefill email.
        if user is None:
            from accounts.models import User as UserModel
            if UserModel.objects.filter(email__iexact=email).exists():
                raise ValidationError({
                    "code": "EMAIL_HAS_ACCOUNT",
                    "message": "An account with this email already exists. Sign in to register, or use a different email.",
                })

        # Duplicate check
        existing = Registration.objects.filter(event=event, deleted_at__isnull=True)
        already = (
            existing.filter(user=user).exists() if user else existing.filter(email__iexact=email).exists()
        )
        if already:
            raise ValidationError("Already registered for this event.")

        # Capacity + waitlist
        if event.max_attendees:
            confirmed = event.registrations.filter(status=Registration.Status.CONFIRMED).count()
            if confirmed >= event.max_attendees:
                if event.waitlist_enabled:
                    return self._add_to_waitlist(event, user, email, full_name, data)
                raise ValidationError("Event is at capacity.")

        # Create the row. Paid events stay PENDING until checkout completes.
        is_free = event.price <= 0
        status_to_set = Registration.Status.CONFIRMED if is_free else Registration.Status.PENDING
        payment_status = (
            Registration.PaymentStatus.NA if is_free else Registration.PaymentStatus.PENDING
        )

        # The pre-check above ("already") isn't race-safe. The DB-level
        # ``unique_together = [['event', 'email']]`` constraint is the backstop;
        # we translate the IntegrityError into the same ValidationError so the
        # view's ``ALREADY_REGISTERED`` mapping is hit and callers get a 409-
        # shaped response instead of a 500.
        try:
            with transaction.atomic():
                registration = Registration.objects.create(
                    event=event,
                    user=user,
                    email=email,
                    full_name=full_name,
                    professional_title=data.get("professional_title", ""),
                    organization_name=data.get("organization_name", ""),
                    status=status_to_set,
                    payment_status=payment_status,
                    allow_public_verification=data.get("allow_public_verification", True),
                    source=Registration.Source.SELF,
                    amount_paid=Decimal("0.00") if is_free else Decimal(str(event.price)),
                    tax_amount=Decimal("0.00"),
                    total_amount=Decimal("0.00") if is_free else Decimal(str(event.price)),
                )
                self._save_custom_fields(event, registration, data.get("custom_field_responses", {}))
        except IntegrityError as exc:
            logger.info(
                "registration.race_lost",
                extra={"event_id": event.pk, "email": email, "error": str(exc)},
            )
            raise ValidationError("Already registered for this event.") from exc

        result = {
            "registration": registration,
            "status": registration.status,
            "created": True,
            "requires_payment": not is_free,
        }

        if is_free:
            # Free anonymous registrations get a magic-link claim email
            # immediately. Paid anonymous registrations defer this to the
            # Stripe webhook fulfilment handler so the link only fires
            # after payment has actually succeeded.
            if registration.user_id is None:
                self._issue_anonymous_claim(registration)
            result["anonymous"] = registration.user_id is None
            return result

        # Paid → create a Stripe Checkout Session and return its URL.
        from billing.checkout import checkout_service

        try:
            checkout = checkout_service.for_event_registration(registration)
        except Exception as exc:
            logger.exception("stripe.checkout.event_registration_failed")
            registration.delete()
            raise ValidationError(f"Could not start checkout: {exc}") from exc

        result["checkout_url"] = checkout.url
        result["checkout_session_id"] = checkout.session_id
        result["anonymous"] = registration.user_id is None
        return result

    def _issue_anonymous_claim(self, registration) -> None:
        """Create + queue a CLAIM magic-link email for a guest registration.

        Idempotent: re-running for the same registration refreshes the
        existing pending link rather than duplicating. We swallow email-
        send failures so a flaky email service doesn't cascade into a
        registration failure — the support tooling can re-issue.
        """
        try:
            from accounts.services import create_registration_claim
            from accounts.tasks import send_magic_link_email

            link = create_registration_claim(registration)
            send_magic_link_email(link.id)
        except Exception:
            logger.exception(
                "registration.claim_link_send_failed",
                extra={"registration_uuid": str(registration.uuid)},
            )

    # ------------------------------------------------------------------
    # Multi-attendee single-buyer
    # ------------------------------------------------------------------
    #
    # One Stripe transaction → N Registration rows. Each anonymous
    # attendee gets their own CLAIM magic link. Buyer (the authenticated
    # user, if any) doesn't get an extra row unless they're in the
    # attendee list.

    MAX_ATTENDEES_PER_TXN = 25

    def register_attendees(self, event: Event, attendees: list[dict], user=None) -> dict[str, Any]:
        """Register N attendees for ``event`` in a single transaction.

        Each attendee dict carries the per-row fields (email, full_name,
        professional_title, organization_name, allow_public_verification)
        plus optional ``custom_field_responses`` keyed identically across
        all attendees (event-level fields are global for now; per-
        attendee custom fields are a future iteration).

        Returns the same shape as ``register_participant`` but with a
        ``registrations`` list and (for paid events) one shared
        ``checkout_url`` covering the whole batch.
        """
        if not event.is_open_for_registration:
            raise ValidationError("Event registration is closed.")
        if not attendees:
            raise ValidationError("At least one attendee is required.")
        if len(attendees) > self.MAX_ATTENDEES_PER_TXN:
            raise ValidationError(f"Cannot register more than {self.MAX_ATTENDEES_PER_TXN} attendees in one transaction.")

        # Normalise emails + dedupe within the batch. Duplicate emails in
        # the same submission would fail the (event, email) unique
        # constraint and leave a partial transaction; reject up front.
        seen_emails: set[str] = set()
        normalised: list[dict] = []
        for raw in attendees:
            email = (raw.get("email") or "").strip().lower()
            if not email:
                raise ValidationError("Each attendee must have an email.")
            if email in seen_emails:
                raise ValidationError({
                    "code": "DUPLICATE_EMAIL_IN_BATCH",
                    "message": f"The email {email} appears more than once. Each attendee must have a distinct email.",
                })
            seen_emails.add(email)
            normalised.append({**raw, "email": email})

        # If unauthenticated, every attendee email must NOT correspond to
        # an existing User. The buyer (the auth'd user, if any) is allowed
        # to register N attendees including themselves, but for anonymous
        # buyers we want the same EMAIL_HAS_ACCOUNT guard as single.
        if user is None:
            from accounts.models import User as UserModel
            colliding = list(
                UserModel.objects.filter(email__in=[a["email"] for a in normalised])
                .values_list("email", flat=True)
            )
            if colliding:
                raise ValidationError({
                    "code": "EMAIL_HAS_ACCOUNT",
                    "message": f"An account already exists for {colliding[0]}. Sign in to register, or use a different email for this attendee.",
                    "email": colliding[0],
                })

        # Capacity check — count attendees against remaining seats. The
        # waitlist branch is intentionally NOT supported for multi-attendee
        # in this iteration: partial-batch waitlisting is a UX rabbit
        # hole. If demand requires it we can split per-row later.
        if event.max_attendees:
            confirmed = event.registrations.filter(status=Registration.Status.CONFIRMED).count()
            if confirmed + len(normalised) > event.max_attendees:
                raise ValidationError({
                    "code": "EVENT_FULL",
                    "message": "Not enough seats remaining for the requested attendees.",
                })

        is_free = event.price <= 0
        registrations: list[Registration] = []

        with transaction.atomic():
            for attendee in normalised:
                # Per-attendee duplicate check — the row may already exist
                # for an authenticated user adding themselves twice, or
                # from a previous run.
                if Registration.objects.filter(
                    event=event, deleted_at__isnull=True, email__iexact=attendee["email"],
                ).exists():
                    raise ValidationError(f"{attendee['email']} is already registered for this event.")

                try:
                    reg = Registration.objects.create(
                        event=event,
                        user=user if attendee["email"].lower() == (user.email.lower() if user else None) else None,
                        email=attendee["email"],
                        full_name=attendee.get("full_name", ""),
                        professional_title=attendee.get("professional_title", ""),
                        organization_name=attendee.get("organization_name", ""),
                        status=Registration.Status.CONFIRMED if is_free else Registration.Status.PENDING,
                        payment_status=Registration.PaymentStatus.NA if is_free else Registration.PaymentStatus.PENDING,
                        allow_public_verification=attendee.get("allow_public_verification", True),
                        source=Registration.Source.SELF,
                        amount_paid=Decimal("0.00") if is_free else Decimal(str(event.price)),
                        tax_amount=Decimal("0.00"),
                        total_amount=Decimal("0.00") if is_free else Decimal(str(event.price)),
                    )
                except IntegrityError as exc:
                    logger.info(
                        "registration.race_lost",
                        extra={"event_id": event.pk, "email": attendee["email"], "error": str(exc)},
                    )
                    raise ValidationError(f"{attendee['email']} is already registered for this event.") from exc

                # Custom fields are event-level (global per submission),
                # so each registration receives the same response set.
                self._save_custom_fields(event, reg, attendee.get("custom_field_responses", {}))
                registrations.append(reg)

        result: dict[str, Any] = {
            "registrations": registrations,
            "registration": registrations[0] if registrations else None,  # backward-compat for single callers
            "status": registrations[0].status if registrations else None,
            "created": True,
            "requires_payment": not is_free,
            "anonymous": all(r.user_id is None for r in registrations),
        }

        if is_free:
            # Issue a CLAIM email per anonymous attendee.
            for reg in registrations:
                if reg.user_id is None:
                    self._issue_anonymous_claim(reg)
            return result

        # Paid: one checkout session covers the whole batch. Stripe
        # attributes the `quantity` to a single line_item; tax splits
        # proportionally on its end.
        from billing.checkout import checkout_service
        try:
            checkout = checkout_service.for_event_registrations(registrations)
        except Exception as exc:
            logger.exception("stripe.checkout.event_registrations_failed")
            for reg in registrations:
                reg.delete()
            raise ValidationError(f"Could not start checkout: {exc}") from exc

        result["checkout_url"] = checkout.url
        result["checkout_session_id"] = checkout.session_id
        return result

    # ------------------------------------------------------------------
    # Waitlist
    # ------------------------------------------------------------------
    def _add_to_waitlist(self, event, user, email, full_name, data):
        waitlist_pos = self._get_next_waitlist_position(event)
        ticket_price = Decimal(str(event.price or 0))
        with transaction.atomic():
            registration = Registration.objects.create(
                event=event,
                user=user,
                email=email,
                full_name=full_name,
                professional_title=data.get("professional_title", ""),
                organization_name=data.get("organization_name", ""),
                status=Registration.Status.WAITLISTED,
                waitlist_position=waitlist_pos,
                allow_public_verification=data.get("allow_public_verification", True),
                source=Registration.Source.SELF,
                amount_paid=ticket_price,
                tax_amount=Decimal("0.00"),
                total_amount=ticket_price,
            )
            self._save_custom_fields(event, registration, data.get("custom_field_responses", {}))
        return {
            "registration": registration,
            "status": "waitlisted",
            "message": "Added to waitlist",
            "created": True,
            "requires_payment": False,
        }

    # ------------------------------------------------------------------
    # Custom fields
    # ------------------------------------------------------------------
    def _save_custom_fields(self, event, registration, responses: dict[str, Any]):
        if not responses:
            return

        def serialize_val(v):
            if isinstance(v, (dict, list)):
                return json.dumps(v)
            return str(v)

        valid_fields = {str(f.uuid): f for f in event.custom_fields.all()}
        for field_uuid, value in responses.items():
            field_obj = valid_fields.get(field_uuid)
            if field_obj:
                CustomFieldResponse.objects.create(
                    registration=registration, field=field_obj, value=serialize_val(value)
                )

    def _get_next_waitlist_position(self, event):
        max_pos = (
            Registration.objects.filter(event=event, status=Registration.Status.WAITLISTED)
            .aggregate(Max("waitlist_position"))["waitlist_position__max"]
            or 0
        )
        return max_pos + 1


registration_service = RegistrationService()
