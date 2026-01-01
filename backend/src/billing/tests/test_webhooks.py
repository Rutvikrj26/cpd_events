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
    def test_subscription_created(self, mock_construct_event, api_client, organizer, db):
        """Handle subscription.created event."""
        from billing.models import Subscription
        
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
    def test_subscription_updated(self, mock_construct_event, api_client, subscription):
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
    def test_subscription_deleted(self, mock_construct_event, api_client, subscription):
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
    def test_invoice_paid(self, mock_construct_event, api_client, organizer):
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
    def test_invoice_payment_failed(self, mock_construct_event, api_client, subscription):
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
    def test_payment_method_attached(self, mock_construct_event, api_client, organizer):
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
    def test_unknown_event_type(self, mock_construct_event, api_client):
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
    def test_invalid_signature(self, mock_construct_event, api_client):
        """Invalid signature is rejected."""
        from stripe.error import SignatureVerificationError
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
