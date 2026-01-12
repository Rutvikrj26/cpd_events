import json
import logging
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Max
from rest_framework.exceptions import ValidationError

from billing.services import stripe_payment_service
from events.models import Event
from promo_codes.services import PromoCodeError, promo_code_service
from registrations.models import CustomFieldResponse, Registration

logger = logging.getLogger(__name__)


class RegistrationService:
    """
    Service for managing event registrations.
    Handles validation, capacity checks, promo codes, and payments.
    """

    def register_participant(self, event: Event, data: dict[str, Any], user=None) -> dict[str, Any]:
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
        # Note: status will be set based on payment requirement later
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

        # 4.5. Determine Registration Status
        # For paid events: status = PENDING until payment confirmed
        # For free events: status = CONFIRMED immediately
        status_to_set = Registration.Status.PENDING if final_price > 0 else Registration.Status.CONFIRMED

        billing_country = data.get('billing_country', '').upper().strip()
        billing_state = data.get('billing_state', '').strip()
        billing_postal_code = data.get('billing_postal_code', '').strip()
        billing_city = data.get('billing_city', '').strip()

        billing_details_provided = bool(billing_country and billing_postal_code)

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
                platform_fee_amount=Decimal('0.00'),
                service_fee_amount=Decimal('0.00'),
                processing_fee_amount=Decimal('0.00'),
                tax_amount=Decimal('0.00'),
                total_amount=final_price,
                billing_country=billing_country,
                billing_state=billing_state,
                billing_postal_code=billing_postal_code,
                billing_city=billing_city,
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

            if billing_details_provided:
                intent_data = stripe_payment_service.create_payment_intent(
                    registration,
                    ticket_amount_cents=int(final_price * 100),
                )

                if intent_data['success']:
                    client_secret = intent_data['client_secret']
                    registration.payment_intent_id = intent_data['payment_intent_id']
                    if intent_data.get('service_fee_cents') is not None:
                        registration.platform_fee_amount = Decimal(intent_data['service_fee_cents']) / Decimal('100')
                        registration.service_fee_amount = Decimal(intent_data['service_fee_cents']) / Decimal('100')
                        registration.processing_fee_amount = Decimal(intent_data.get('processing_fee_cents', 0)) / Decimal(
                            '100'
                        )
                        registration.tax_amount = Decimal(intent_data.get('tax_cents', 0)) / Decimal('100')
                        registration.total_amount = Decimal(intent_data.get('total_amount_cents', 0)) / Decimal('100')
                        registration.stripe_tax_calculation_id = intent_data.get('tax_calculation_id', '')
                        registration.save(
                            update_fields=[
                                'payment_intent_id',
                                'platform_fee_amount',
                                'service_fee_amount',
                                'processing_fee_amount',
                                'tax_amount',
                                'total_amount',
                                'stripe_tax_calculation_id',
                                'updated_at',
                            ]
                        )
                    else:
                        registration.save(update_fields=['payment_intent_id', 'updated_at'])
                else:
                    registration.delete()
                    raise ValidationError(intent_data['error'])

        # Queue Zoom registrant addition (async)
        if registration.status == Registration.Status.CONFIRMED:
            from registrations.tasks import add_zoom_registrant

            add_zoom_registrant.delay(registration.id)

        return {
            'registration': registration,
            'client_secret': client_secret,
            'status': registration.status,
            'created': True,
            'requires_payment': final_price > 0,
        }

    def _add_to_waitlist(self, event, user, email, full_name, data):
        """Internal method to add to waitlist."""
        waitlist_pos = self._get_next_waitlist_position(event)
        ticket_price = Decimal(str(event.price or 0))

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
                amount_paid=ticket_price,
                platform_fee_amount=Decimal('0.00'),
                service_fee_amount=Decimal('0.00'),
                processing_fee_amount=Decimal('0.00'),
                tax_amount=Decimal('0.00'),
                total_amount=ticket_price,
                billing_country=data.get('billing_country', '').upper().strip(),
                billing_state=data.get('billing_state', '').strip(),
                billing_postal_code=data.get('billing_postal_code', '').strip(),
                billing_city=data.get('billing_city', '').strip(),
            )

            # Save Custom Fields
            self._save_custom_fields(event, registration, data.get('custom_field_responses', {}))

        return {'registration': registration, 'status': 'waitlisted', 'message': 'Added to waitlist', 'created': True}

    def _save_custom_fields(self, event, registration, responses: dict[str, Any]):
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
                CustomFieldResponse.objects.create(registration=registration, field=field_obj, value=serialize_val(value))

    def _get_next_waitlist_position(self, event):
        """Get next available waitlist position."""
        max_pos = (
            Registration.objects.filter(event=event, status=Registration.Status.WAITLISTED).aggregate(Max('waitlist_position'))[
                'waitlist_position__max'
            ]
            or 0
        )
        return max_pos + 1


# Singleton instance
registration_service = RegistrationService()


class PaymentConfirmationService:
    """
    Synchronous payment confirmation with retry logic.
    Replaces webhook-dependent payment confirmation for registrations.
    """

    def __init__(self):
        self._stripe = None

    @property
    def stripe(self):
        """Lazy load Stripe SDK."""
        if self._stripe is None:
            try:
                import stripe
                from django.conf import settings

                stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', None)
                self._stripe = stripe
            except ImportError:
                logger.warning("Stripe SDK not installed")
                return None
        return self._stripe

    @property
    def is_configured(self) -> bool:
        """Check if Stripe is properly configured."""
        from django.conf import settings

        return bool(getattr(settings, 'STRIPE_SECRET_KEY', None))

    def confirm_registration_payment(self, registration, max_retries: int = 3, retry_delay: float = 1.0) -> dict:
        """
        Confirm payment status directly with Stripe.

        Args:
            registration: The Registration instance with payment_intent_id
            max_retries: Number of retries for processing payments
            retry_delay: Delay between retries in seconds

        Returns:
            dict with status ('paid', 'processing', 'failed', 'error') and details
        """
        import time
        from typing import Any

        if not self.is_configured:
            return {'status': 'error', 'message': 'Payment system not configured'}

        if not registration.payment_intent_id:
            return {'status': 'error', 'message': 'No payment intent found for this registration'}

        def extract_transfer_id(intent_obj: Any) -> str | None:
            charges = getattr(intent_obj, 'charges', None)
            if charges and getattr(charges, 'data', None):
                charge = charges.data[0]
                if isinstance(charge, dict):
                    transfer_id = charge.get('transfer')
                else:
                    transfer_id = getattr(charge, 'transfer', None)
                if isinstance(transfer_id, str) and transfer_id.strip():
                    return transfer_id
            return None

        for attempt in range(max_retries):
            try:
                intent = stripe_payment_service.retrieve_payment_intent(registration.payment_intent_id)
                if not intent:
                    return {'status': 'error', 'message': 'Payment intent not found'}

                if intent.status == 'succeeded':
                    transfer_id = extract_transfer_id(intent)
                    # Update registration with locking to prevent race conditions
                    with transaction.atomic():
                        # Refetch with lock
                        locked_reg = Registration.objects.select_for_update().get(pk=registration.pk)
                        event = Event.objects.select_for_update().get(pk=locked_reg.event_id)

                        # Idempotency check inside lock
                        if locked_reg.payment_status == Registration.PaymentStatus.PAID:
                            logger.info(f"Registration {registration.uuid} already confirmed (idempotent skip)")
                            return {
                                'status': 'paid',
                                'registration_uuid': str(registration.uuid),
                                'amount_paid': float(locked_reg.total_amount),
                            }

                        confirmed_count = Registration.objects.filter(
                            event=event,
                            status=Registration.Status.CONFIRMED,
                            deleted_at__isnull=True,
                        ).count()
                        if event.max_attendees and confirmed_count >= event.max_attendees:
                            refund_result = stripe_payment_service.refund_payment_intent(
                                registration.payment_intent_id,
                                registration=locked_reg,
                            )

                            if refund_result['success']:
                                locked_reg.payment_status = Registration.PaymentStatus.REFUNDED
                                locked_reg.total_amount = Decimal(intent.amount_received) / Decimal('100')
                                locked_reg.save(update_fields=['payment_status', 'total_amount', 'updated_at'])
                                try:
                                    from promo_codes.models import PromoCodeUsage

                                    PromoCodeUsage.release_for_registration(locked_reg)
                                except Exception as e:
                                    logger.warning("Failed to release promo code usage for %s: %s", locked_reg.uuid, e)
                                logger.info(f"Registration {registration.uuid} refunded due to capacity limits")
                                return {
                                    'status': 'event_full',
                                    'message': 'Event is fully booked. Payment has been refunded.',
                                }

                            logger.error(f"Refund failed for registration {registration.uuid}: {refund_result['error']}")
                            return {
                                'status': 'error',
                                'message': 'Payment succeeded but refund failed. Please contact support.',
                            }

                        locked_reg.payment_status = Registration.PaymentStatus.PAID
                        locked_reg.total_amount = Decimal(intent.amount_received) / Decimal('100')

                        # Update status to CONFIRMED if it was PENDING
                        updated_fields = ['payment_status', 'total_amount', 'updated_at']
                        if locked_reg.status == Registration.Status.PENDING:
                            locked_reg.status = Registration.Status.CONFIRMED
                            updated_fields.append('status')
                        if transfer_id and not locked_reg.stripe_transfer_id:
                            locked_reg.stripe_transfer_id = transfer_id
                            updated_fields.append('stripe_transfer_id')
                        locked_reg.save(update_fields=updated_fields)

                        if transfer_id:
                            try:
                                from billing.models import TransferRecord

                                ticket_amount_cents = None
                                metadata = getattr(intent, 'metadata', {}) or {}
                                if isinstance(metadata, dict):
                                    ticket_amount_cents = metadata.get('ticket_amount_cents')
                                if ticket_amount_cents is None:
                                    ticket_amount_cents = int((locked_reg.amount_paid or 0) * 100)

                                TransferRecord.objects.get_or_create(
                                    stripe_transfer_id=transfer_id,
                                    defaults={
                                        'event': event,
                                        'registration': locked_reg,
                                        'recipient': event.owner,
                                        'stripe_payment_intent_id': locked_reg.payment_intent_id,
                                        'amount_cents': int(ticket_amount_cents),
                                        'currency': event.currency.lower(),
                                        'description': f"Transfer for {event.title}",
                                    },
                                )
                            except Exception as exc:
                                logger.warning("Failed to create transfer record for %s: %s", locked_reg.uuid, exc)

                    # Update original instance to reflect changes
                    registration.payment_status = locked_reg.payment_status
                    registration.total_amount = locked_reg.total_amount
                    registration.status = locked_reg.status
                    registration.stripe_transfer_id = locked_reg.stripe_transfer_id

                    tax_result = stripe_payment_service.create_tax_transaction_for_registration(registration)
                    if tax_result.get('success'):
                        registration.stripe_tax_transaction_id = tax_result.get('tax_transaction_id')
                    else:
                        logger.warning(
                            "Failed to create tax transaction for registration %s: %s",
                            registration.uuid,
                            tax_result.get('error'),
                        )

                    # Trigger Zoom registrant addition after payment confirmed
                    if registration.status == Registration.Status.CONFIRMED:
                        from registrations.tasks import add_zoom_registrant

                        add_zoom_registrant.delay(registration.id)

                    logger.info(f"Registration {registration.uuid} payment confirmed: PAID")
                    return {
                        'status': 'paid',
                        'registration_uuid': str(registration.uuid),
                        'amount_paid': float(registration.total_amount),
                    }

                elif intent.status == 'processing':
                    # Payment still processing, retry after delay
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    logger.info(f"Registration {registration.uuid} payment still processing after {max_retries} attempts")
                    return {'status': 'processing', 'message': 'Payment is still being processed. Please wait.'}

                elif intent.status in ['requires_payment_method', 'requires_confirmation', 'canceled']:
                    # Payment failed
                    registration.payment_status = Registration.PaymentStatus.FAILED
                    registration.save(update_fields=['payment_status', 'updated_at'])
                    try:
                        from promo_codes.models import PromoCodeUsage

                        PromoCodeUsage.release_for_registration(registration)
                    except Exception as e:
                        logger.warning("Failed to release promo code usage for %s: %s", registration.uuid, e)

                    error_msg = 'Payment failed'
                    if intent.last_payment_error:
                        error_msg = intent.last_payment_error.get('message', 'Payment failed')

                    logger.warning(f"Registration {registration.uuid} payment failed: {error_msg}")
                    return {'status': 'failed', 'message': error_msg}

                else:
                    # Unknown status
                    logger.warning(f"Registration {registration.uuid} has unknown payment status: {intent.status}")
                    return {'status': 'error', 'message': f'Unknown payment status: {intent.status}'}

            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                logger.error(f"Failed to confirm payment for registration {registration.uuid}: {e}")
                return {'status': 'error', 'message': str(e)}

        return {'status': 'error', 'message': 'Could not confirm payment status after retries'}


# Singleton instance
payment_confirmation_service = PaymentConfirmationService()
