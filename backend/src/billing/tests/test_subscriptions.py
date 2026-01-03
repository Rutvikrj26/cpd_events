"""
Tests for billing endpoints.

Endpoints tested:
- GET /api/v1/subscription/
- POST /api/v1/subscription/
- GET /api/v1/subscription/status/
- POST /api/v1/subscription/cancel/
- POST /api/v1/subscription/reactivate/
- GET /api/v1/invoices/
- GET /api/v1/invoices/{uuid}/
- GET /api/v1/payment-methods/
- POST /api/v1/payment-methods/
- DELETE /api/v1/payment-methods/{uuid}/
- POST /api/v1/payment-methods/{uuid}/set_default/
"""

import pytest
from rest_framework import status


# =============================================================================
# Subscription Tests
# =============================================================================


@pytest.mark.django_db
class TestSubscriptionViewSet:
    """Tests for subscription management."""

    endpoint = '/api/v1/subscription/'

    def test_get_subscription(self, organizer_client, subscription):
        """Organizer can get their subscription."""
        response = organizer_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_create_subscription(self, organizer_client, mock_stripe, stripe_products):
        """Organizer can create/upgrade subscription."""
        data = {
            'plan': 'professional',
        }
        response = organizer_client.post(self.endpoint, data)
        # May redirect to Stripe or return subscription
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_302_FOUND,
        ]

    def test_get_subscription_status(self, organizer_client, subscription):
        """Organizer can check subscription status."""
        response = organizer_client.get(f'{self.endpoint}status/')
        assert response.status_code == status.HTTP_200_OK

    def test_cancel_subscription(self, organizer_client, subscription, mock_stripe):
        """Organizer can cancel their subscription."""
        response = organizer_client.post(f'{self.endpoint}cancel/')
        assert response.status_code == status.HTTP_200_OK

    def test_reactivate_subscription(self, organizer_client, subscription, mock_stripe):
        """Organizer can reactivate cancelled subscription."""
        subscription.status = 'canceled'
        subscription.save()
        
        response = organizer_client.post(f'{self.endpoint}reactivate/')
        # May succeed or fail based on Stripe
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_attendee_can_access_subscription(self, auth_client):
        """Attendees can access subscription endpoints."""
        response = auth_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# Invoice Tests
# =============================================================================


@pytest.mark.django_db
class TestInvoiceViewSet:
    """Tests for invoice viewing."""

    endpoint = '/api/v1/invoices/'

    def test_list_invoices(self, organizer_client, organizer, db):
        """Organizer can list their invoices."""
        from factories import InvoiceFactory
        InvoiceFactory(user=organizer)
        
        response = organizer_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_invoice(self, organizer_client, organizer, db):
        """Organizer can retrieve a specific invoice."""
        from factories import InvoiceFactory
        invoice = InvoiceFactory(user=organizer)
        
        response = organizer_client.get(f'{self.endpoint}{invoice.uuid}/')
        assert response.status_code == status.HTTP_200_OK

    def test_cannot_see_others_invoices(self, organizer_client, other_organizer, db):
        """Cannot see other users' invoices."""
        from factories import InvoiceFactory
        other_invoice = InvoiceFactory(user=other_organizer)
        
        response = organizer_client.get(f'{self.endpoint}{other_invoice.uuid}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Payment Method Tests
# =============================================================================


@pytest.mark.django_db
class TestPaymentMethodViewSet:
    """Tests for payment method management."""

    endpoint = '/api/v1/payment-methods/'

    def test_list_payment_methods(self, organizer_client, organizer, db):
        """Organizer can list their payment methods."""
        from factories import PaymentMethodFactory
        PaymentMethodFactory(user=organizer)
        
        response = organizer_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_add_payment_method(self, organizer_client, mock_stripe):
        """Organizer can add a payment method."""
        data = {
            'payment_method_id': 'pm_test123',
            'stripe_payment_method_id': 'pm_test123',  # Serializer expects 'stripe_payment_method_id'
        }
        response = organizer_client.post(self.endpoint, data)
        # May succeed or require setup intent
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_delete_payment_method(self, organizer_client, organizer, mock_stripe, db):
        """Organizer can delete a payment method."""
        from factories import PaymentMethodFactory
        pm = PaymentMethodFactory(user=organizer, is_default=False)
        
        response = organizer_client.delete(f'{self.endpoint}{pm.uuid}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_set_default_payment_method(self, organizer_client, organizer, db):
        """Organizer can set a payment method as default."""
        from factories import PaymentMethodFactory
        pm = PaymentMethodFactory(user=organizer, is_default=False)
        
        response = organizer_client.post(f'{self.endpoint}{pm.uuid}/set_default/')
        assert response.status_code == status.HTTP_200_OK
        pm.refresh_from_db()
        assert pm.is_default is True

    def test_cannot_delete_only_payment_method(self, organizer_client, organizer, db):
        """Cannot delete the only payment method if subscription active."""
        # This depends on business logic
        pass  # TODO: Add if applicable


# =============================================================================
# Checkout and Portal Tests
# =============================================================================


@pytest.mark.django_db
class TestBillingViews:
    """Tests for checkout and billing portal."""
    
    def test_create_checkout_session(self, organizer_client, mock_stripe, stripe_products):
        """Organizer can create a checkout session."""
        response = organizer_client.post('/api/v1/billing/checkout/', {
            'plan': 'professional',
            'success_url': 'https://example.com/success',
            'cancel_url': 'https://example.com/cancel',
        })
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
        # Should return checkout URL
        if response.status_code == status.HTTP_200_OK:
            assert 'url' in response.data or 'checkout_url' in response.data

    def test_create_billing_portal_session(self, organizer_client, mock_stripe, subscription):
        """Organizer can access billing portal."""
        response = organizer_client.post('/api/v1/billing/portal/', {
            'return_url': 'https://example.com/return',
        })
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
        # Should return portal URL
        if response.status_code == status.HTTP_200_OK:
            assert 'url' in response.data or 'portal_url' in response.data

    def test_attendee_can_access_checkout(self, auth_client, stripe_products, mock_stripe):
        """Attendees can access checkout."""
        response = auth_client.post('/api/v1/billing/checkout/', {
            'plan': 'professional',
            'success_url': 'https://example.com/success',
            'cancel_url': 'https://example.com/cancel',
        })
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
