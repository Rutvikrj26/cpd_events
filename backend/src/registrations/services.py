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

from django.db import transaction
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

        result = {
            "registration": registration,
            "status": registration.status,
            "created": True,
            "requires_payment": not is_free,
        }

        if is_free:
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
