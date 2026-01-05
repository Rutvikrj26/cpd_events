"""
Tests for Stripe webhook handling.

Endpoints tested:
- POST /webhooks/stripe/
"""

import pytest
import json
import hmac
import hashlib
import time
from unittest.mock import patch, MagicMock
from rest_framework import status


# =============================================================================
# Stripe Webhook Tests
# =============================================================================


@pytest.mark.django_db
class TestStripeWebhook:
    """Tests for Stripe webhook handlers."""

    endpoint = '/webhooks/stripe/'

    def create_stripe_signature(self, payload, secret='test_webhook_secret'):
        """Create a valid Stripe webhook signature."""
        timestamp = int(time.time())
        signed_payload = f'{timestamp}.{payload}'
        signature = hmac.new(
            secret.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return f't={timestamp},v1={signature}'

    @patch('stripe.Webhook.construct_event')
    def test_subscription_created(self, mock_construct_event, api_client, organizer, db, settings):
        """Handle subscription.created event."""
        from billing.models import Subscription
        settings.STRIPE_WEBHOOK_SECRET = 'test_webhook_secret'
        
        event_data = {
            'type': 'customer.subscription.created',
            'data': {
                'object': {
                    'id': 'sub_test123',
                    'customer': 'cus_test123',
                    'status': 'active',
                    'items': {'data': [{'price': {'id': 'price_team'}}]},
                }
            }
        }
        mock_construct_event.return_value = MagicMock(**event_data)
        
        response = api_client.post(
            self.endpoint,
            json.dumps(event_data),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='test_sig'
        )
        # Webhook should return 200 to acknowledge receipt
        assert response.status_code == status.HTTP_200_OK

    @patch('stripe.Webhook.construct_event')
    def test_subscription_created_updates_subscription(self, mock_construct_event, api_client, user, settings):
        """Subscription created updates local subscription and user role."""
        from billing.models import Subscription
        from django.utils import timezone

        settings.STRIPE_WEBHOOK_SECRET = 'test_webhook_secret'
        subscription = Subscription.objects.get(user=user)
        subscription.plan = 'professional'
        subscription.stripe_customer_id = 'cus_created123'
        subscription.save(update_fields=['plan', 'stripe_customer_id', 'updated_at'])

        event_data = {
            'type': 'customer.subscription.created',
            'data': {
                'object': {
                    'id': 'sub_created123',
                    'customer': 'cus_created123',
                    'status': 'active',
                    'current_period_start': int(timezone.now().timestamp()),
                    'current_period_end': int((timezone.now() + timezone.timedelta(days=30)).timestamp()),
                }
            }
        }
        mock_construct_event.return_value = event_data

        response = api_client.post(
            self.endpoint,
            json.dumps(event_data),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='test_sig'
        )
        assert response.status_code == status.HTTP_200_OK

        subscription.refresh_from_db()
        assert subscription.stripe_subscription_id == 'sub_created123'
        assert subscription.status == 'active'
        user.refresh_from_db()
        assert user.account_type == 'organizer'

    @patch('stripe.Webhook.construct_event')
    def test_subscription_updated(self, mock_construct_event, api_client, subscription, settings):
        settings.STRIPE_WEBHOOK_SECRET = 'test_webhook_secret'
        """Handle subscription.updated event."""
        event_data = {
            'type': 'customer.subscription.updated',
            'data': {
                'object': {
                    'id': subscription.stripe_subscription_id if hasattr(subscription, 'stripe_subscription_id') else 'sub_test',
                    'status': 'active',
                }
            }
        }
        mock_construct_event.return_value = MagicMock(**event_data)
        
        response = api_client.post(
            self.endpoint,
            json.dumps(event_data),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='test_sig'
        )
        assert response.status_code == status.HTTP_200_OK

    @patch('stripe.Webhook.construct_event')
    def test_subscription_updated_sets_cancel_flags(self, mock_construct_event, api_client, user, settings):
        """Subscription updated sets cancel flags."""
        from billing.models import Subscription
        from django.utils import timezone

        settings.STRIPE_WEBHOOK_SECRET = 'test_webhook_secret'
        subscription = Subscription.objects.get(user=user)
        subscription.stripe_subscription_id = 'sub_update123'
        subscription.plan = 'professional'
        subscription.save(update_fields=['stripe_subscription_id', 'plan', 'updated_at'])

        event_data = {
            'type': 'customer.subscription.updated',
            'data': {
                'object': {
                    'id': 'sub_update123',
                    'status': 'canceled',
                    'cancel_at_period_end': True,
                    'current_period_start': int(timezone.now().timestamp()),
                    'current_period_end': int((timezone.now() + timezone.timedelta(days=30)).timestamp()),
                    'canceled_at': int(timezone.now().timestamp()),
                }
            }
        }
        mock_construct_event.return_value = event_data

        response = api_client.post(
            self.endpoint,
            json.dumps(event_data),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='test_sig'
        )
        assert response.status_code == status.HTTP_200_OK

        subscription.refresh_from_db()
        assert subscription.cancel_at_period_end is True
        assert subscription.status == 'canceled'

    @patch('stripe.Webhook.construct_event')
    def test_subscription_deleted(self, mock_construct_event, api_client, subscription, settings):
        settings.STRIPE_WEBHOOK_SECRET = 'test_webhook_secret'
        """Handle subscription.deleted event."""
        event_data = {
            'type': 'customer.subscription.deleted',
            'data': {
                'object': {
                    'id': subscription.stripe_subscription_id if hasattr(subscription, 'stripe_subscription_id') else 'sub_test',
                }
            }
        }
        mock_construct_event.return_value = MagicMock(**event_data)
        
        response = api_client.post(
            self.endpoint,
            json.dumps(event_data),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='test_sig'
        )
        assert response.status_code == status.HTTP_200_OK

    @patch('stripe.Webhook.construct_event')
    def test_subscription_deleted_marks_canceled(self, mock_construct_event, api_client, user, settings):
        """Subscription deleted marks local subscription canceled."""
        from billing.models import Subscription

        settings.STRIPE_WEBHOOK_SECRET = 'test_webhook_secret'
        subscription = Subscription.objects.get(user=user)
        subscription.stripe_subscription_id = 'sub_delete123'
        subscription.save(update_fields=['stripe_subscription_id', 'updated_at'])

        event_data = {
            'type': 'customer.subscription.deleted',
            'data': {
                'object': {
                    'id': 'sub_delete123',
                }
            }
        }
        mock_construct_event.return_value = event_data

        response = api_client.post(
            self.endpoint,
            json.dumps(event_data),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='test_sig'
        )
        assert response.status_code == status.HTTP_200_OK

        subscription.refresh_from_db()
        assert subscription.status == 'canceled'

    @patch('stripe.Webhook.construct_event')
    def test_invoice_paid(self, mock_construct_event, api_client, organizer, settings):
        settings.STRIPE_WEBHOOK_SECRET = 'test_webhook_secret'
        """Handle invoice.paid event."""
        event_data = {
            'type': 'invoice.paid',
            'data': {
                'object': {
                    'id': 'in_test123',
                    'customer': 'cus_test123',
                    'amount_paid': 2999,
                    'currency': 'usd',
                    'status': 'paid',
                }
            }
        }
        mock_construct_event.return_value = MagicMock(**event_data)
        
        response = api_client.post(
            self.endpoint,
            json.dumps(event_data),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='test_sig'
        )
        assert response.status_code == status.HTTP_200_OK

    @patch('stripe.Webhook.construct_event')
    def test_invoice_paid_creates_invoice_and_resets_usage(self, mock_construct_event, api_client, user, settings):
        """invoice.paid creates invoice and resets usage counters."""
        from billing.models import Subscription, Invoice
        from django.utils import timezone

        settings.STRIPE_WEBHOOK_SECRET = 'test_webhook_secret'
        subscription = Subscription.objects.get(user=user)
        subscription.stripe_customer_id = 'cus_paid123'
        subscription.events_created_this_period = 3
        subscription.certificates_issued_this_period = 5
        subscription.save(update_fields=[
            'stripe_customer_id',
            'events_created_this_period',
            'certificates_issued_this_period',
            'updated_at',
        ])

        event_data = {
            'type': 'invoice.paid',
            'data': {
                'object': {
                    'id': 'in_paid123',
                    'customer': 'cus_paid123',
                    'amount_paid': 2999,
                    'currency': 'usd',
                    'period_start': int(timezone.now().timestamp()),
                    'period_end': int((timezone.now() + timezone.timedelta(days=30)).timestamp()),
                }
            }
        }
        mock_construct_event.return_value = event_data

        response = api_client.post(
            self.endpoint,
            json.dumps(event_data),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='test_sig'
        )
        assert response.status_code == status.HTTP_200_OK

        subscription.refresh_from_db()
        assert subscription.events_created_this_period == 0
        assert subscription.certificates_issued_this_period == 0
        invoice = Invoice.objects.get(stripe_invoice_id='in_paid123')
        assert invoice.status == Invoice.Status.PAID

    @patch('stripe.Webhook.construct_event')
    def test_invoice_payment_failed(self, mock_construct_event, api_client, subscription, settings):
        settings.STRIPE_WEBHOOK_SECRET = 'test_webhook_secret'
        """Handle invoice.payment_failed event."""
        event_data = {
            'type': 'invoice.payment_failed',
            'data': {
                'object': {
                    'id': 'in_test123',
                    'customer': 'cus_test123',
                    'attempt_count': 1,
                }
            }
        }
        mock_construct_event.return_value = MagicMock(**event_data)
        
        response = api_client.post(
            self.endpoint,
            json.dumps(event_data),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='test_sig'
        )
        assert response.status_code == status.HTTP_200_OK

    @patch('stripe.Webhook.construct_event')
    def test_invoice_payment_failed_marks_past_due(self, mock_construct_event, api_client, user, settings):
        """invoice.payment_failed marks subscription past due and creates invoice."""
        from billing.models import Subscription, Invoice
        from integrations.services import email_service

        settings.STRIPE_WEBHOOK_SECRET = 'test_webhook_secret'
        subscription = Subscription.objects.get(user=user)
        subscription.stripe_customer_id = 'cus_failed123'
        subscription.save(update_fields=['stripe_customer_id', 'updated_at'])

        event_data = {
            'type': 'invoice.payment_failed',
            'data': {
                'object': {
                    'id': 'in_failed123',
                    'customer': 'cus_failed123',
                    'amount_due': 1299,
                    'currency': 'usd',
                }
            }
        }
        mock_construct_event.return_value = event_data

        with patch.object(email_service, 'send_email') as mock_send:
            response = api_client.post(
                self.endpoint,
                json.dumps(event_data),
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='test_sig'
            )

        assert response.status_code == status.HTTP_200_OK
        subscription.refresh_from_db()
        assert subscription.status == Subscription.Status.PAST_DUE
        invoice = Invoice.objects.get(stripe_invoice_id='in_failed123')
        assert invoice.status == Invoice.Status.OPEN
        mock_send.assert_called_once()

    @patch('stripe.Webhook.construct_event')
    def test_invoice_finalized_creates_open_invoice(self, mock_construct_event, api_client, user, settings):
        """invoice.finalized creates an open invoice record."""
        from billing.models import Subscription, Invoice
        from django.utils import timezone

        settings.STRIPE_WEBHOOK_SECRET = 'test_webhook_secret'
        subscription = Subscription.objects.get(user=user)
        subscription.stripe_customer_id = 'cus_finalized123'
        subscription.save(update_fields=['stripe_customer_id', 'updated_at'])

        event_data = {
            'type': 'invoice.finalized',
            'data': {
                'object': {
                    'id': 'in_finalized123',
                    'customer': 'cus_finalized123',
                    'amount_due': 1599,
                    'currency': 'usd',
                    'due_date': int((timezone.now() + timezone.timedelta(days=7)).timestamp()),
                }
            }
        }
        mock_construct_event.return_value = event_data

        response = api_client.post(
            self.endpoint,
            json.dumps(event_data),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='test_sig'
        )
        assert response.status_code == status.HTTP_200_OK
        invoice = Invoice.objects.get(stripe_invoice_id='in_finalized123')
        assert invoice.status == Invoice.Status.OPEN

    @patch('stripe.Webhook.construct_event')
    def test_payment_method_attached(self, mock_construct_event, api_client, organizer, settings):
        settings.STRIPE_WEBHOOK_SECRET = 'test_webhook_secret'
        """Handle payment_method.attached event."""
        event_data = {
            'type': 'payment_method.attached',
            'data': {
                'object': {
                    'id': 'pm_test123',
                    'customer': 'cus_test123',
                    'card': {
                        'brand': 'visa',
                        'last4': '4242',
                    }
                }
            }
        }
        mock_construct_event.return_value = MagicMock(**event_data)
        
        response = api_client.post(
            self.endpoint,
            json.dumps(event_data),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='test_sig'
        )
        assert response.status_code == status.HTTP_200_OK

    @patch('stripe.Webhook.construct_event')
    def test_payment_method_detached_removes_local(self, mock_construct_event, api_client, organizer, settings, db):
        """payment_method.detached removes local payment method."""
        from billing.models import PaymentMethod
        from factories import PaymentMethodFactory

        settings.STRIPE_WEBHOOK_SECRET = 'test_webhook_secret'
        pm = PaymentMethodFactory(user=organizer, stripe_payment_method_id='pm_detached123')

        event_data = {
            'type': 'payment_method.detached',
            'data': {
                'object': {
                    'id': 'pm_detached123',
                }
            }
        }
        mock_construct_event.return_value = event_data

        response = api_client.post(
            self.endpoint,
            json.dumps(event_data),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='test_sig'
        )
        assert response.status_code == status.HTTP_200_OK
        assert not PaymentMethod.objects.filter(id=pm.id).exists()

    @patch('stripe.Webhook.construct_event')
    def test_unknown_event_type(self, mock_construct_event, api_client, settings):
        settings.STRIPE_WEBHOOK_SECRET = 'test_webhook_secret'
        """Unknown event types are acknowledged but not processed."""
        event_data = {
            'type': 'unknown.event.type',
            'data': {'object': {}}
        }
        mock_construct_event.return_value = MagicMock(**event_data)
        
        response = api_client.post(
            self.endpoint,
            json.dumps(event_data),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='test_sig'
        )
        # Should still return 200 to acknowledge
        assert response.status_code == status.HTTP_200_OK

    @patch('stripe.Webhook.construct_event')
    def test_invalid_signature(self, mock_construct_event, api_client, settings):
        settings.STRIPE_WEBHOOK_SECRET = 'test_webhook_secret'
        """Invalid signature is rejected."""
        from stripe import SignatureVerificationError
        mock_construct_event.side_effect = SignatureVerificationError(
            'Invalid signature', 'test_sig'
        )
        
        response = api_client.post(
            self.endpoint,
            json.dumps({'type': 'test'}),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='invalid_sig'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
