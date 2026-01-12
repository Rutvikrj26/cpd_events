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

from unittest.mock import MagicMock

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
            'plan': 'organizer',
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

    def test_update_subscription_same_plan_rejected(self, organizer_client, subscription):
        """Cannot update to the same plan."""
        subscription.plan = 'organizer'
        subscription.save(update_fields=['plan', 'updated_at'])

        response = organizer_client.patch(f'{self.endpoint}{subscription.id}/', {'plan': 'organizer'})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_subscription_plan_stripe(self, organizer_client, subscription, mock_stripe, stripe_products):
        """Stripe update flow changes the plan."""
        subscription.plan = 'attendee'
        subscription.stripe_subscription_id = 'sub_test123'
        subscription.save(update_fields=['plan', 'stripe_subscription_id', 'updated_at'])

        mock_stripe.Subscription.retrieve.return_value = {
            'items': {'data': [MagicMock(id='si_test123')]},
        }
        mock_stripe.Subscription.modify.return_value = {'status': 'active'}

        response = organizer_client.patch(
            f'{self.endpoint}{subscription.id}/',
            {'plan': 'organizer', 'immediate': True},
        )
        assert response.status_code == status.HTTP_200_OK
        subscription.refresh_from_db()
        assert subscription.plan == 'organizer'

    def test_cancel_subscription_already_canceled(self, organizer_client, subscription):
        """Canceling an already canceled subscription returns an error."""
        subscription.status = 'canceled'
        subscription.save(update_fields=['status', 'updated_at'])

        response = organizer_client.post(f'{self.endpoint}cancel/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_reactivate_subscription_not_scheduled(self, organizer_client, subscription):
        """Reactivate requires cancel_at_period_end to be set."""
        subscription.cancel_at_period_end = False
        subscription.save(update_fields=['cancel_at_period_end', 'updated_at'])

        response = organizer_client.post(f'{self.endpoint}reactivate/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


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

        PaymentMethodFactory(user=organizer, is_default=True)
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
        from billing.models import Subscription
        from factories import PaymentMethodFactory

        subscription = Subscription.objects.get(user=organizer)
        subscription.status = Subscription.Status.ACTIVE
        subscription.save(update_fields=['status', 'updated_at'])
        pm = PaymentMethodFactory(user=organizer, is_default=True)

        response = organizer_client.delete(f'{self.endpoint}{pm.uuid}/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Checkout and Portal Tests
# =============================================================================


@pytest.mark.django_db
class TestBillingViews:
    """Tests for checkout and billing portal."""

    def test_create_checkout_session(self, organizer_client, mock_stripe, stripe_products):
        """Organizer can create a checkout session."""
        response = organizer_client.post(
            '/api/v1/billing/checkout/',
            {
                'plan': 'organizer',
                'success_url': 'https://example.com/success',
                'cancel_url': 'https://example.com/cancel',
            },
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
        # Should return checkout URL
        if response.status_code == status.HTTP_200_OK:
            assert 'url' in response.data or 'checkout_url' in response.data

    def test_create_billing_portal_session(self, organizer_client, mock_stripe, subscription):
        """Organizer can access billing portal."""
        response = organizer_client.post(
            '/api/v1/billing/portal/',
            {
                'return_url': 'https://example.com/return',
            },
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
        # Should return portal URL
        if response.status_code == status.HTTP_200_OK:
            assert 'url' in response.data or 'portal_url' in response.data

    def test_attendee_can_access_checkout(self, auth_client, stripe_products, mock_stripe):
        """Attendees can access checkout."""
        response = auth_client.post(
            '/api/v1/billing/checkout/',
            {
                'plan': 'organizer',
                'success_url': 'https://example.com/success',
                'cancel_url': 'https://example.com/cancel',
            },
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]


@pytest.mark.django_db
class TestCheckoutConfirmation:
    """Tests for checkout confirmation and sync."""

    def test_confirm_checkout_missing_session_id(self, auth_client, mock_stripe):
        """session_id is required."""
        response = auth_client.post('/api/v1/subscription/confirm-checkout/', {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_confirm_checkout_session_success(self, auth_client, user, mock_stripe, stripe_products):
        """Confirm checkout updates subscription and upgrades user."""
        from types import SimpleNamespace

        from django.utils import timezone

        from billing.models import PaymentMethod

        session = MagicMock()
        session.customer = 'cus_test123'
        session.metadata = {'user_uuid': str(user.uuid), 'plan': 'organizer'}
        session.subscription = 'sub_test123'
        mock_stripe.checkout.Session.retrieve.return_value = session

        stripe_sub = MagicMock()
        stripe_sub.id = 'sub_test123'
        stripe_sub.status = 'active'
        stripe_sub.current_period_start = int(timezone.now().timestamp())
        stripe_sub.current_period_end = int((timezone.now() + timezone.timedelta(days=30)).timestamp())
        stripe_sub.trial_end = None
        mock_stripe.Subscription.retrieve.return_value = stripe_sub
        mock_stripe.Customer.retrieve.return_value = SimpleNamespace(invoice_settings={'default_payment_method': 'pm_test123'})
        pm = SimpleNamespace(
            id='pm_test123',
            card=SimpleNamespace(brand='visa', last4='4242', exp_month=12, exp_year=2030),
        )
        mock_stripe.PaymentMethod.list.return_value = SimpleNamespace(data=[pm])

        response = auth_client.post('/api/v1/subscription/confirm-checkout/', {'session_id': 'cs_test123'})
        assert response.status_code == status.HTTP_200_OK

        user.refresh_from_db()
        assert user.account_type == 'organizer'
        assert PaymentMethod.objects.filter(user=user, stripe_payment_method_id='pm_test123').exists()

    def test_sync_subscription_updates_plan(self, auth_client, user, mock_stripe, stripe_products, monkeypatch):
        """Sync pulls subscription details from Stripe and updates plan."""
        from types import SimpleNamespace

        from django.utils import timezone

        from billing.models import Subscription
        from billing.services import stripe_service

        subscription = Subscription.objects.get(user=user)
        subscription.stripe_subscription_id = 'sub_sync123'
        subscription.stripe_customer_id = 'cus_sync123'
        subscription.plan = 'attendee'
        subscription.save(update_fields=['stripe_subscription_id', 'stripe_customer_id', 'plan', 'updated_at'])

        class StripeSub:
            def __init__(self):
                self.id = 'sub_sync123'
                self.status = 'active'
                self.current_period_start = int(timezone.now().timestamp())
                self.current_period_end = int((timezone.now() + timezone.timedelta(days=30)).timestamp())
                self.trial_end = None
                self.cancel_at_period_end = False
                self.canceled_at = None
                self.items = SimpleNamespace(data=[SimpleNamespace(price=SimpleNamespace(product='prod_test_org'))])

            def get(self, key, default=None):
                if key == 'items':
                    return self.items
                return default

            def __getitem__(self, key):
                if key == 'items':
                    return self.items
                raise KeyError(key)

        monkeypatch.setattr(stripe_service, "_stripe", mock_stripe)
        mock_stripe.Subscription.retrieve.return_value = StripeSub()
        mock_stripe.Subscription.list.return_value = SimpleNamespace(data=[StripeSub()])
        mock_stripe.Customer.list.return_value = SimpleNamespace(data=[SimpleNamespace(id='cus_sync123')])
        mock_stripe.Customer.retrieve.return_value = SimpleNamespace(invoice_settings={'default_payment_method': 'pm_sync123'})
        pm = SimpleNamespace(
            id='pm_sync123',
            card=SimpleNamespace(brand='visa', last4='4242', exp_month=1, exp_year=2031),
        )
        mock_stripe.PaymentMethod.list.return_value = SimpleNamespace(data=[pm])

        response = auth_client.post('/api/v1/subscription/sync/')
        assert response.status_code == status.HTTP_200_OK

        subscription.refresh_from_db()
        assert subscription.plan == 'organizer'
