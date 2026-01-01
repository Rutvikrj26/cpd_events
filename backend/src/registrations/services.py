
import logging
import json
from decimal import Decimal
from typing import Any, Dict

from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from common.utils import error_response
from events.models import Event
from registrations.models import Registration, CustomFieldResponse
from promo_codes.services import promo_code_service, PromoCodeError
from billing.services import stripe_payment_service

logger = logging.getLogger(__name__)


class RegistrationService:
    """
    Service for managing event registrations.
    Handles validation, capacity checks, promo codes, and payments.
    """

    def register_participant(self, event: Event, data: Dict[str, Any], user=None) -> Dict[str, Any]:
        """
        Register a participant for an event.

        Args:
            event: The Event instance.
            data: Validated data from serializer.
            user: Authenticated user (optional).

        Returns:
            Dict containing registration details.
        """
        # 1. Basic Validation
        if not event.is_open_for_registration:
            raise ValidationError("Event registration is closed.")

        email = data.get('email', '').lower()
        full_name = data.get('full_name', '')
        
        if user:
            email = user.email
            full_name = full_name or user.full_name

        # 2. Duplicate Check
        existing_query = Registration.objects.filter(event=event, deleted_at__isnull=True)
        if user:
            is_registered = existing_query.filter(user=user).exists()
        else:
            is_registered = existing_query.filter(email__iexact=email).exists()

        if is_registered:
            raise ValidationError("Already registered for this event.")

        # 3. Capacity & Waitlist Check
        status_to_set = Registration.Status.CONFIRMED
        
        if event.max_attendees:
            confirmed_count = event.registrations.filter(status=Registration.Status.CONFIRMED).count()
            if confirmed_count >= event.max_attendees:
                if event.waitlist_enabled:
                    return self._add_to_waitlist(event, user, email, full_name, data)
                else:
                    raise ValidationError("Event is at capacity.")

        # 4. Promo Code Validation & Pricing
        promo_code_str = data.get('promo_code', '').strip()
        validated_promo_code = None
        final_price = event.price
        
        if promo_code_str and not event.is_free:
            try:
                promo_code = promo_code_service.find_code(promo_code_str, event)
                if not promo_code:
                    raise ValidationError("Invalid promo code.")
                
                promo_code_service.validate_code(promo_code, event, email, user)
                
                discount_amount = promo_code.calculate_discount(event.price)
                final_price = max(Decimal('0.00'), event.price - discount_amount)
                validated_promo_code = promo_code
            except PromoCodeError as e:
                raise ValidationError(str(e))

        # 5. Create Registration (Atomic)
        with transaction.atomic():
            registration = Registration.objects.create(
                event=event,
                user=user,
                email=email,
                full_name=full_name,
                professional_title=data.get('professional_title', ''),
                organization_name=data.get('organization_name', ''),
                status=status_to_set,
                allow_public_verification=data.get('allow_public_verification', True),
                source=Registration.Source.SELF,
                amount_paid=final_price,
            )

            # Apply Promo Code
            if validated_promo_code:
                promo_code_service.apply_code(validated_promo_code, registration, event.price)

            # Save Custom Fields
            self._save_custom_fields(event, registration, data.get('custom_field_responses', {}))

        # 6. Payment Processing
        client_secret = None
        payment_intent_id = None

        if final_price > 0:
            if not stripe_payment_service.is_configured:
                # Cleanup if payment system fails
                registration.delete()
                raise ValidationError("Payment system not configured.")

            registration.payment_status = Registration.PaymentStatus.PENDING
            registration.save(update_fields=['payment_status', 'updated_at'])

            intent_data = stripe_payment_service.create_payment_intent(registration, amount_cents=int(final_price * 100))
            
            if intent_data['success']:
                client_secret = intent_data['client_secret']
                registration.payment_intent_id = intent_data['payment_intent_id']
                registration.save(update_fields=['payment_intent_id', 'updated_at'])
            else:
                registration.delete()
                raise ValidationError(intent_data['error'])
        
        return {
            'registration': registration,
            'client_secret': client_secret,
            'status': registration.status,
            'created': True
        }

    def _add_to_waitlist(self, event, user, email, full_name, data):
        """Internal method to add to waitlist."""
        waitlist_pos = self._get_next_waitlist_position(event)

        with transaction.atomic():
            registration = Registration.objects.create(
                event=event,
                user=user,
                email=email,
                full_name=full_name,
                professional_title=data.get('professional_title', ''),
                organization_name=data.get('organization_name', ''),
                status=Registration.Status.WAITLISTED,
                waitlist_position=waitlist_pos,
                allow_public_verification=data.get('allow_public_verification', True),
                source=Registration.Source.SELF,
                amount_paid=0,
            )

            # Save Custom Fields
            self._save_custom_fields(event, registration, data.get('custom_field_responses', {}))
        
        return {
            'registration': registration,
            'status': 'waitlisted',
            'message': 'Added to waitlist',
            'created': True
        }

    def _save_custom_fields(self, event, registration, responses: Dict[str, Any]):
        """Save custom field responses."""
        if not responses:
            return

        # Helper to safely serialize list/dict
        def serialize_val(v):
            if isinstance(v, (dict, list)):
                return json.dumps(v)
            return str(v)

        # Get valid field UUIDs for this event
        valid_fields = {str(f.uuid): f for f in event.custom_fields.all()}
        
        for field_uuid, value in responses.items():
            field_obj = valid_fields.get(field_uuid)
            if field_obj:
                CustomFieldResponse.objects.create(
                    registration=registration,
                    field=field_obj,
                    value=serialize_val(value)
                )

    def _get_next_waitlist_position(self, event):
        """Get next available waitlist position."""
        max_pos = Registration.objects.filter(
            event=event, 
            status=Registration.Status.WAITLISTED
        ).aggregate(Max('waitlist_position'))['waitlist_position__max'] or 0
        return max_pos + 1


# Singleton instance
registration_service = RegistrationService()
