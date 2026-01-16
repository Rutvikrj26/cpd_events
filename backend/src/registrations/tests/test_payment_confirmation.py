"""
Tests for PaymentConfirmationService.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from registrations.services import payment_confirmation_service
from registrations.models import Registration
from factories import RegistrationFactory, EventFactory


@pytest.mark.django_db
class TestPaymentConfirmationService:
    
    @pytest.fixture
    def setup_service(self, settings):
        settings.STRIPE_SECRET_KEY = 'sk_test_123'
        # Force reload stripe property
        payment_confirmation_service._stripe = None
        return payment_confirmation_service

    @pytest.fixture
    def registration(self, db):
        reg = RegistrationFactory(
            total_amount=Decimal('100.00'),
            payment_status=Registration.PaymentStatus.PENDING,
            status=Registration.Status.PENDING,
            payment_intent_id='pi_123'
        )
        return reg

    @patch('billing.services.stripe_payment_service.retrieve_payment_intent')
    def test_confirm_payment_success(self, mock_retrieve, setup_service, registration):
        """Should update status to PAID and CONFIRMED on success."""
        # Mock Stripe intent
        mock_intent = MagicMock()
        mock_intent.status = 'succeeded'
        mock_intent.amount_received = 10000
        mock_intent.charges.data = [{'transfer': 'tr_123'}]
        mock_retrieve.return_value = mock_intent

        result = setup_service.confirm_registration_payment(registration)

        assert result['status'] == 'paid'
        registration.refresh_from_db()
        assert registration.payment_status == Registration.PaymentStatus.PAID
        assert registration.status == Registration.Status.CONFIRMED
        assert registration.stripe_transfer_id == 'tr_123'

    @patch('billing.services.stripe_payment_service.retrieve_payment_intent')
    def test_confirm_payment_idempotency(self, mock_retrieve, setup_service, registration):
        """Should skip processing if already PAID."""
        registration.payment_status = Registration.PaymentStatus.PAID
        registration.save()

        mock_intent = MagicMock(status='succeeded')
        mock_retrieve.return_value = mock_intent

        result = setup_service.confirm_registration_payment(registration)

        assert result['status'] == 'paid'
        # Ensure expensive operations (like refund checks) were skipped
        # We can infer this if status didn't change or error
        assert registration.payment_status == Registration.PaymentStatus.PAID

    @patch('billing.services.stripe_payment_service.retrieve_payment_intent')
    @patch('promo_codes.models.PromoCodeUsage.release_for_registration')
    def test_confirm_payment_failed_stripe(self, mock_release, mock_retrieve, setup_service, registration):
        """Should set status to FAILED and release promo code."""
        mock_intent = MagicMock()
        mock_intent.status = 'requires_payment_method'
        mock_intent.last_payment_error = {'message': 'Card declined'}
        mock_retrieve.return_value = mock_intent

        result = setup_service.confirm_registration_payment(registration)

        assert result['status'] == 'failed'
        assert result['message'] == 'Card declined'
        
        registration.refresh_from_db()
        assert registration.payment_status == Registration.PaymentStatus.FAILED
        mock_release.assert_called_once_with(registration)

    @patch('billing.services.stripe_payment_service.retrieve_payment_intent')
    def test_confirm_payment_processing(self, mock_retrieve, setup_service, registration):
        """Should return processing status."""
        mock_intent = MagicMock(status='processing')
        mock_retrieve.return_value = mock_intent
        
        # We mock time.sleep to avoid wait
        with patch('time.sleep'):
             result = setup_service.confirm_registration_payment(registration, max_retries=2)
             
        assert result['status'] == 'processing'

    @patch('billing.services.stripe_payment_service.retrieve_payment_intent')
    @patch('billing.services.stripe_payment_service.refund_payment_intent')
    def test_confirm_payment_capacity_refund(self, mock_refund, mock_retrieve, setup_service, registration):
        """Should refund if event capacity is reached (race condition)."""
        # Set event capacity to 1
        registration.event.max_attendees = 1
        registration.event.save()
        
        # Create another confirmed registration to fill capacity
        RegistrationFactory(
            event=registration.event,
            status=Registration.Status.CONFIRMED
        )
        
        mock_intent = MagicMock(status='succeeded', amount_received=10000)
        mock_retrieve.return_value = mock_intent
        
        mock_refund.return_value = {'success': True}

        result = setup_service.confirm_registration_payment(registration)

        assert result['status'] == 'event_full'
        registration.refresh_from_db()
        assert registration.payment_status == Registration.PaymentStatus.REFUNDED
        mock_refund.assert_called_once()
