"""
Tests for critical Stripe webhook workflows.

Tests the fixes implemented for:
1. account.updated webhook handling for both Organization AND User
2. charges_enabled validation before payment intent creation
3. Race condition prevention with select_for_update locking
"""

import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, PropertyMock, patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status


@override_settings(STRIPE_WEBHOOK_SECRET='test_webhook_secret')
class TestAccountUpdatedWebhook(TestCase):
    """Tests for account.updated webhook handler supporting both Organization and User."""

    endpoint = '/webhooks/stripe/'

    @patch('stripe.Webhook.construct_event')
    def test_account_updated_updates_organization(self, mock_construct_event):
        """account.updated should update Organization when stripe_connect_id matches."""
        from accounts.models import User
        from organizations.models import Organization

        # Create an organizer
        organizer = User.objects.create_user(
            email='org_owner@test.com', password='testpass123', full_name='Org Owner', account_type='organizer'
        )

        org = Organization.objects.create(
            name='Test Org',
            created_by=organizer,
            stripe_connect_id='acct_org_test123',
            stripe_account_status='pending',
            stripe_charges_enabled=False,
        )

        event_data = {
            'type': 'account.updated',
            'data': {
                'object': {
                    'id': 'acct_org_test123',
                    'charges_enabled': True,
                    'details_submitted': True,
                }
            },
        }
        mock_construct_event.return_value = event_data  # Return dict directly

        response = self.client.post(
            self.endpoint, json.dumps(event_data), content_type='application/json', HTTP_STRIPE_SIGNATURE='test_sig'
        )

        assert response.status_code == status.HTTP_200_OK

        org.refresh_from_db()
        assert org.stripe_charges_enabled is True
        assert org.stripe_account_status == 'active'

    @patch('stripe.Webhook.construct_event')
    def test_account_updated_updates_user(self, mock_construct_event):
        """account.updated should update User when stripe_connect_id matches and no Org found."""
        from accounts.models import User

        # Create an organizer with Connect account
        organizer = User.objects.create_user(
            email='solo_org@test.com',
            password='testpass123',
            full_name='Solo Organizer',
            account_type='organizer',
            stripe_connect_id='acct_user_test456',
            stripe_account_status='pending',
            stripe_charges_enabled=False,
        )

        event_data = {
            'type': 'account.updated',
            'data': {
                'object': {
                    'id': 'acct_user_test456',
                    'charges_enabled': True,
                    'details_submitted': True,
                }
            },
        }
        mock_construct_event.return_value = event_data  # Return dict directly

        response = self.client.post(
            self.endpoint, json.dumps(event_data), content_type='application/json', HTTP_STRIPE_SIGNATURE='test_sig'
        )

        assert response.status_code == status.HTTP_200_OK

        organizer.refresh_from_db()
        assert organizer.stripe_charges_enabled is True
        assert organizer.stripe_account_status == 'active'

    @patch('stripe.Webhook.construct_event')
    def test_account_updated_pending_verification_status(self, mock_construct_event):
        """account.updated should set pending_verification when details_submitted but not charges_enabled."""
        from accounts.models import User

        organizer = User.objects.create_user(
            email='pending_org@test.com',
            password='testpass123',
            full_name='Pending Organizer',
            account_type='organizer',
            stripe_connect_id='acct_pending_test',
            stripe_account_status='restricted',
            stripe_charges_enabled=False,
        )

        event_data = {
            'type': 'account.updated',
            'data': {
                'object': {
                    'id': 'acct_pending_test',
                    'charges_enabled': False,
                    'details_submitted': True,
                }
            },
        }
        mock_construct_event.return_value = event_data  # Return dict directly

        response = self.client.post(
            self.endpoint, json.dumps(event_data), content_type='application/json', HTTP_STRIPE_SIGNATURE='test_sig'
        )

        assert response.status_code == status.HTTP_200_OK

        organizer.refresh_from_db()
        assert organizer.stripe_charges_enabled is False
        assert organizer.stripe_account_status == 'pending_verification'

    @patch('stripe.Webhook.construct_event')
    def test_account_updated_unknown_account_logs_warning(self, mock_construct_event):
        """account.updated for unknown account should log a warning."""
        import logging

        event_data = {
            'type': 'account.updated',
            'data': {
                'object': {
                    'id': 'acct_unknown_999',
                    'charges_enabled': True,
                    'details_submitted': True,
                }
            },
        }
        mock_construct_event.return_value = event_data  # Return dict directly

        with self.assertLogs(level=logging.WARNING) as cm:
            response = self.client.post(
                self.endpoint, json.dumps(event_data), content_type='application/json', HTTP_STRIPE_SIGNATURE='test_sig'
            )

        assert response.status_code == status.HTTP_200_OK
        assert any('unknown Connect account' in output or 'acct_unknown_999' in output for output in cm.output)


class TestChargesEnabledValidation(TestCase):
    """Tests for charges_enabled validation before payment intent creation."""

    def test_payment_intent_fails_when_org_charges_disabled(self):
        """create_payment_intent should fail if organization has charges_enabled=False."""
        from accounts.models import User
        from billing.services import StripePaymentService
        from events.models import Event
        from organizations.models import Organization
        from registrations.models import Registration

        organizer = User.objects.create_user(
            email='disabled_org@test.com', password='testpass123', full_name='Disabled Org Owner', account_type='organizer'
        )

        org = Organization.objects.create(
            name='Disabled Org',
            created_by=organizer,
            stripe_connect_id='acct_disabled_org',
            stripe_charges_enabled=False,  # Not enabled
            stripe_account_status='pending',
        )

        event = Event.objects.create(
            title='Paid Event',
            owner=organizer,
            organization=org,
            price=Decimal('99.00'),
            currency='usd',
            status='published',
            starts_at=timezone.now() + timedelta(days=7),
        )

        registration = Registration.objects.create(
            event=event, email='attendee@test.com', full_name='Test Attendee', status='confirmed', payment_status='pending'
        )

        service = StripePaymentService()

        with patch.object(StripePaymentService, 'is_configured', new_callable=PropertyMock) as mock_config:
            mock_config.return_value = True
            result = service.create_payment_intent(registration)

        assert result['success'] is False
        assert 'disabled' in result['error'].lower()

    def test_payment_intent_fails_when_user_charges_disabled(self):
        """create_payment_intent should fail if organizer user has charges_enabled=False."""
        from accounts.models import User
        from billing.services import StripePaymentService
        from events.models import Event
        from registrations.models import Registration

        organizer = User.objects.create_user(
            email='disabled_user@test.com',
            password='testpass123',
            full_name='Disabled User Organizer',
            account_type='organizer',
            stripe_connect_id='acct_disabled_user',
            stripe_charges_enabled=False,  # Not enabled
        )

        event = Event.objects.create(
            title='Solo Paid Event',
            owner=organizer,
            organization=None,
            price=Decimal('50.00'),
            currency='usd',
            status='published',
            starts_at=timezone.now() + timedelta(days=7),
        )

        registration = Registration.objects.create(
            event=event, email='attendee2@test.com', full_name='Test Attendee 2', status='confirmed', payment_status='pending'
        )

        service = StripePaymentService()
        with patch.object(StripePaymentService, 'is_configured', new_callable=PropertyMock) as mock_config:
            mock_config.return_value = True
            result = service.create_payment_intent(registration)

        assert result['success'] is False
        assert 'disabled' in result['error'].lower()

    def test_payment_intent_succeeds_when_charges_enabled(self):
        """create_payment_intent should succeed if charges_enabled=True."""
        from accounts.models import User
        from billing.services import StripePaymentService
        from events.models import Event
        from registrations.models import Registration

        organizer = User.objects.create_user(
            email='enabled_user@test.com',
            password='testpass123',
            full_name='Enabled User Organizer',
            account_type='organizer',
            stripe_connect_id='acct_enabled_user',
            stripe_charges_enabled=True,  # Enabled
        )

        event = Event.objects.create(
            title='Valid Paid Event',
            owner=organizer,
            organization=None,
            price=Decimal('75.00'),
            currency='usd',
            status='published',
            starts_at=timezone.now() + timedelta(days=7),
        )

        registration = Registration.objects.create(
            event=event,
            email='attendee3@test.com',
            full_name='Test Attendee 3',
            status='confirmed',
            payment_status='pending',
            billing_country='US',
            billing_postal_code='94105',
        )

        service = StripePaymentService()

        mock_intent = MagicMock()
        mock_intent.client_secret = 'pi_test_secret'
        mock_intent.id = 'pi_test123'

        with (
            patch.object(StripePaymentService, 'is_configured', new_callable=PropertyMock) as mock_config,
            patch.object(service, '_stripe') as mock_stripe,
        ):
            mock_config.return_value = True
            base_calc = MagicMock()
            base_calc.amount_total = 10000
            base_calc.tax_amount_exclusive = 1300
            base_calc.id = 'tax_base'

            final_calc = MagicMock()
            final_calc.amount_total = 10500
            final_calc.tax_amount_exclusive = 1300
            final_calc.id = 'tax_final'

            mock_stripe.tax.Calculation.create.side_effect = [base_calc, final_calc]
            mock_stripe.PaymentIntent.create.return_value = mock_intent
            result = service.create_payment_intent(registration)

        assert result['success'] is True
        assert result['client_secret'] == 'pi_test_secret'
        call_kwargs = mock_stripe.PaymentIntent.create.call_args.kwargs
        assert call_kwargs['transfer_data']['destination'] == 'acct_enabled_user'
        assert call_kwargs['transfer_data']['amount'] == 7500
        assert 'application_fee_amount' not in call_kwargs


@override_settings(STRIPE_WEBHOOK_SECRET='test_webhook_secret')
class TestPaymentConfirmationLocking(TestCase):
    """Tests for race condition prevention with select_for_update locking."""

    def test_confirm_payment_is_idempotent(self):
        """Payment confirmation should be idempotent - second call returns success without re-processing."""
        from accounts.models import User
        from events.models import Event
        from registrations.models import Registration
        from registrations.services import PaymentConfirmationService

        organizer = User.objects.create_user(
            email='idem_org@test.com',
            password='testpass123',
            full_name='Idempotent Organizer',
            account_type='organizer',
            stripe_connect_id='acct_idem_org',
            stripe_charges_enabled=True,
        )

        event = Event.objects.create(
            title='Idempotent Event',
            owner=organizer,
            price=Decimal('50.00'),
            currency='usd',
            status='published',
            starts_at=timezone.now() + timedelta(days=7),
        )

        registration = Registration.objects.create(
            event=event,
            email='paid_attendee@test.com',
            full_name='Already Paid',
            status='confirmed',
            payment_status=Registration.PaymentStatus.PAID,
            payment_intent_id='pi_already_paid',
            amount_paid=Decimal('50.00'),
            total_amount=Decimal('50.00'),
        )

        service = PaymentConfirmationService()

        mock_intent = MagicMock()
        mock_intent.status = 'succeeded'
        mock_intent.amount_received = 5000

        with (
            patch.object(PaymentConfirmationService, 'is_configured', new_callable=PropertyMock) as mock_config,
            patch('registrations.services.stripe_payment_service.retrieve_payment_intent') as mock_retrieve,
            patch('registrations.services.stripe_payment_service.create_tax_transaction_for_registration') as mock_tax,
        ):

            mock_config.return_value = True

            mock_retrieve.return_value = mock_intent
            mock_tax.return_value = {'success': True, 'tax_transaction_id': 'txn_123'}

            result = service.confirm_registration_payment(registration)

        assert result['status'] == 'paid'
        assert result['amount_paid'] == 50.0

        # Registration should keep original values
        registration.refresh_from_db()
        assert registration.payment_status == Registration.PaymentStatus.PAID
        mock_tax.assert_not_called()

    @patch('stripe.Webhook.construct_event')
    def test_webhook_payment_confirmation_is_idempotent(self, mock_construct_event):
        """Webhook payment confirmation should skip already-paid registrations."""
        from accounts.models import User
        from events.models import Event
        from registrations.models import Registration

        organizer = User.objects.create_user(
            email='webhook_org@test.com', password='testpass123', full_name='Webhook Organizer', account_type='organizer'
        )

        event = Event.objects.create(
            title='Webhook Event',
            owner=organizer,
            price=Decimal('75.00'),
            currency='usd',
            status='published',
            starts_at=timezone.now() + timedelta(days=7),
        )

        registration = Registration.objects.create(
            event=event,
            email='webhook_paid@test.com',
            full_name='Webhook Paid',
            status='confirmed',
            payment_status=Registration.PaymentStatus.PAID,
            payment_intent_id='pi_webhook_test',
            amount_paid=Decimal('75.00'),
        )

        event_data = {
            'type': 'payment_intent.succeeded',
            'data': {
                'object': {
                    'id': 'pi_webhook_test',
                    'amount_received': 7500,
                    'metadata': {'registration_id': str(registration.uuid)},
                }
            },
        }
        mock_construct_event.return_value = event_data  # Return dict directly

        response = self.client.post(
            '/webhooks/stripe/', json.dumps(event_data), content_type='application/json', HTTP_STRIPE_SIGNATURE='test_sig'
        )

        assert response.status_code == status.HTTP_200_OK

        registration.refresh_from_db()
        assert registration.payment_status == Registration.PaymentStatus.PAID
        assert registration.amount_paid == Decimal('75.00')

    def test_confirm_payment_updates_pending_to_paid(self):
        """Payment confirmation should update PENDING to PAID."""
        from accounts.models import User
        from events.models import Event
        from registrations.models import Registration
        from registrations.services import PaymentConfirmationService

        organizer = User.objects.create_user(
            email='confirm_org@test.com',
            password='testpass123',
            full_name='Confirm Organizer',
            account_type='organizer',
            stripe_connect_id='acct_confirm_org',
            stripe_charges_enabled=True,
        )

        event = Event.objects.create(
            title='Confirmation Event',
            owner=organizer,
            price=Decimal('100.00'),
            currency='usd',
            status='published',
            starts_at=timezone.now() + timedelta(days=7),
        )

        registration = Registration.objects.create(
            event=event,
            email='pending_attendee@test.com',
            full_name='Pending Attendee',
            status='confirmed',
            payment_status=Registration.PaymentStatus.PENDING,
            payment_intent_id='pi_pending_test',
            amount_paid=Decimal('100.00'),
        )

        service = PaymentConfirmationService()

        mock_intent = MagicMock()
        mock_intent.status = 'succeeded'
        mock_intent.amount_received = 10000

        with (
            patch.object(PaymentConfirmationService, 'is_configured', new_callable=PropertyMock) as mock_config,
            patch('registrations.services.stripe_payment_service.retrieve_payment_intent') as mock_retrieve,
            patch('registrations.services.stripe_payment_service.create_tax_transaction_for_registration') as mock_tax,
        ):

            mock_config.return_value = True

            mock_retrieve.return_value = mock_intent
            mock_tax.return_value = {'success': True, 'tax_transaction_id': 'txn_456'}

            result = service.confirm_registration_payment(registration)

        assert result['status'] == 'paid'

        registration.refresh_from_db()
        assert registration.payment_status == Registration.PaymentStatus.PAID
        assert registration.amount_paid == Decimal('100.00')
        mock_tax.assert_called_once()

    @patch('stripe.Webhook.construct_event')
    def test_webhook_payment_confirmation_creates_tax_transaction(self, mock_construct_event):
        """Webhook payment confirmation should create a tax transaction for paid registrations."""
        from accounts.models import User
        from events.models import Event
        from registrations.models import Registration

        organizer = User.objects.create_user(
            email='webhook_pending@test.com',
            password='testpass123',
            full_name='Webhook Pending Organizer',
            account_type='organizer',
        )

        event = Event.objects.create(
            title='Webhook Pending Event',
            owner=organizer,
            price=Decimal('60.00'),
            currency='usd',
            status='published',
            starts_at=timezone.now() + timedelta(days=7),
        )

        registration = Registration.objects.create(
            event=event,
            email='pending_webhook@test.com',
            full_name='Pending Webhook',
            status='pending',
            payment_status=Registration.PaymentStatus.PENDING,
            payment_intent_id='pi_webhook_pending',
            amount_paid=Decimal('60.00'),
        )

        event_data = {
            'type': 'payment_intent.succeeded',
            'data': {
                'object': {
                    'id': 'pi_webhook_pending',
                    'amount_received': 6000,
                    'metadata': {'registration_id': str(registration.uuid)},
                }
            },
        }
        mock_construct_event.return_value = event_data

        with patch('billing.services.stripe_payment_service.create_tax_transaction_for_registration') as mock_tax:
            mock_tax.return_value = {'success': True, 'tax_transaction_id': 'txn_789'}
            response = self.client.post(
                '/webhooks/stripe/', json.dumps(event_data), content_type='application/json', HTTP_STRIPE_SIGNATURE='test_sig'
            )

        assert response.status_code == status.HTTP_200_OK
        registration.refresh_from_db()
        assert registration.payment_status == Registration.PaymentStatus.PAID
        mock_tax.assert_called_once()
