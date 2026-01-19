
from decimal import Decimal
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from billing.services import RefundService
from registrations.models import Registration


@pytest.mark.django_db
class TestRefundFeeDeduction:
    """Tests for verifying that Stripe processing fees are deducted from refund amounts."""

    def setup_method(self):
        self.service = RefundService()
        # Mock the stripe object on the service
        self.service._stripe = MagicMock()

        # Patch is_configured to avoid settings dependency
        self.is_configured_patcher = patch(
            'billing.services.StripeService.is_configured',
            new_callable=PropertyMock,
            return_value=True
        )
        self.is_configured_patcher.start()

        # Patch RefundRecord.objects.create to avoid DB insert issues with mocked registration
        self.refund_record_patcher = patch('billing.models.RefundRecord.objects.create')
        self.mock_refund_record_create = self.refund_record_patcher.start()

        # Patch TransferRecord.objects.filter to avoid DB issues
        self.transfer_record_patcher = patch('billing.models.TransferRecord.objects.filter')
        self.mock_transfer_record_filter = self.transfer_record_patcher.start()

    def teardown_method(self):
        self.is_configured_patcher.stop()
        self.refund_record_patcher.stop()
        self.transfer_record_patcher.stop()

    def _create_mock_registration(self):
        """Create a mock registration object."""
        registration = MagicMock(spec=Registration)
        registration.payment_intent_id = "pi_123"
        registration.uuid = "reg-uuid-123"
        registration.total_amount = Decimal("100.00")
        registration.amount_paid = Decimal("100.00")
        registration.stripe_transfer_id = "tr_123"
        registration.user = None  # Simplify notification logic
        return registration

    def test_process_refund_deducts_fees_on_full_refund(self):
        """
        Verify that when a full refund is requested (amount_cents=None),
        the refund amount sent to Stripe is (original_amount - processing_fee).
        """
        registration = self._create_mock_registration()

        # Setup Stripe PaymentIntent Mock
        mock_pi = MagicMock()
        mock_pi.amount_received = 10000  # $100.00

        # Setup Balance Transaction Mock (The Fee)
        mock_bt = MagicMock()
        mock_bt.fee = 320  # $3.20 fee

        # Link them together
        mock_pi.latest_charge.balance_transaction = mock_bt

        # Setup Retrieve call
        self.service._stripe.PaymentIntent.retrieve.return_value = mock_pi

        # Setup Refund Create response
        mock_refund = MagicMock()
        mock_refund.id = "re_123"
        mock_refund.amount = 9680  # 10000 - 320
        mock_refund.currency = "usd"
        mock_refund.status = "succeeded"
        self.service._stripe.Refund.create.return_value = mock_refund

        # --- Execute ---
        result = self.service.process_refund(registration, amount_cents=None)

        # --- Verify ---
        assert result['success'] is True, f"Expected success but got: {result.get('error')}"

        # Check Stripe Retrieve call includes balance_transaction expansion
        self.service._stripe.PaymentIntent.retrieve.assert_called_once_with(
            "pi_123", expand=['latest_charge.balance_transaction']
        )

        # Check Stripe Refund Create call uses deducted amount
        # Expected amount: 10000 (paid) - 320 (fee) = 9680
        self.service._stripe.Refund.create.assert_called_once_with(
            payment_intent="pi_123",
            amount=9680,
            reason='requested_by_customer',
            reverse_transfer=True
        )

        # Verify RefundRecord.objects.create was called with correct amount
        call_kwargs = self.mock_refund_record_create.call_args.kwargs
        assert call_kwargs['amount_cents'] == 9680

    def test_process_refund_respects_manual_amount(self):
        """
        Verify that if a specific amount is passed, we use that instead of calculating.
        """
        registration = self._create_mock_registration()

        # Mock PI retrieve (still need to set up due to impl fetching fee anyway)
        mock_pi = MagicMock()
        mock_pi.amount_received = 10000
        mock_pi.latest_charge.balance_transaction.fee = 320
        self.service._stripe.PaymentIntent.retrieve.return_value = mock_pi

        mock_refund = MagicMock()
        mock_refund.id = "re_manual"
        mock_refund.amount = 5000
        mock_refund.currency = "usd"
        mock_refund.status = "succeeded"
        self.service._stripe.Refund.create.return_value = mock_refund

        # --- Execute ---
        result = self.service.process_refund(registration, amount_cents=5000)

        # --- Verify ---
        assert result['success'] is True, f"Expected success but got: {result.get('error')}"

        # Check Stripe Refund Create call uses the manual amount, not calculated
        self.service._stripe.Refund.create.assert_called_once_with(
            payment_intent="pi_123",
            amount=5000,
            reason='requested_by_customer',
            reverse_transfer=True
        )

    def test_process_refund_returns_error_if_amount_zero_after_fee(self):
        """
        Verify that if the fee equals or exceeds the amount, we return an error.
        """
        registration = self._create_mock_registration()

        # Setup PI where fee equals amount (edge case)
        mock_pi = MagicMock()
        mock_pi.amount_received = 100  # $1.00
        mock_pi.latest_charge.balance_transaction.fee = 100  # $1.00 fee - all eaten by fee
        self.service._stripe.PaymentIntent.retrieve.return_value = mock_pi

        # --- Execute ---
        result = self.service.process_refund(registration, amount_cents=None)

        # --- Verify ---
        assert result['success'] is False
        assert 'zero or negative' in result['error'].lower()

        # Stripe Refund should NOT have been called
        self.service._stripe.Refund.create.assert_not_called()
