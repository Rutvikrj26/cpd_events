"""
Tests for StripeService.
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from billing.models import StripePrice, StripeProduct, Subscription
from billing.services import StripeService


@pytest.mark.django_db
class TestStripeService:
    @pytest.fixture
    def stripe_service(self, settings):
        settings.STRIPE_SECRET_KEY = "sk_test_123"
        service = StripeService()
        # Force load stripe lib and mock it
        _ = service.stripe
        return service

    @pytest.fixture
    def mock_stripe(self, stripe_service):
        """Mock the internal stripe library."""
        with patch.object(stripe_service, "_stripe") as mock:
            yield mock

    @pytest.fixture
    def user(self, django_user_model):
        import uuid

        return django_user_model.objects.create_user(email=f"test_{uuid.uuid4()}@example.com", password="password")

    @pytest.fixture
    def stripe_product(self):
        prod = StripeProduct.objects.create(
            plan="organizer", stripe_product_id="prod_123", name="Organizer Plan", is_active=True
        )
        StripePrice.objects.create(
            product=prod,
            stripe_price_id="price_month",
            billing_interval="month",
            amount_cents=1000,
            currency="usd",
            is_active=True,
        )
        return prod

    def test_create_subscription_success(self, stripe_service, mock_stripe, user, stripe_product):
        """Test successful subscription creation flow."""
        # Setup mocks
        mock_stripe.Customer.create.return_value = MagicMock(id="cus_123")

        mock_sub_response = MagicMock(
            id="sub_123", status="active", current_period_start=1700000000, current_period_end=1702592000, trial_end=None
        )
        mock_sub_response.latest_invoice.payment_intent.client_secret = "cs_123"
        mock_stripe.Subscription.create.return_value = mock_sub_response

        # Call service
        result = stripe_service.create_subscription(user=user, plan="organizer", payment_method_id="pm_123")

        assert result["success"] is True
        assert result["client_secret"] == "cs_123"

        # Verify DB updates
        sub = Subscription.objects.get(user=user)
        assert sub.stripe_subscription_id == "sub_123"
        assert sub.stripe_customer_id == "cus_123"
        assert sub.plan == "organizer"
        assert sub.status == "active"

        # Verify Stripe calls
        mock_stripe.Customer.create.assert_called_once()
        mock_stripe.Subscription.create.assert_called_once()

        # Check arguments
        call_kwargs = mock_stripe.Subscription.create.call_args[1]
        assert call_kwargs["items"][0]["price"] == "price_month"
        assert call_kwargs["customer"] == "cus_123"

    def test_create_subscription_existing_active(self, stripe_service, user):
        """Should fail if user already has active subscription."""
        # Update the signal-created subscription or get_or_create
        sub, _ = Subscription.objects.get_or_create(user=user)
        sub.stripe_subscription_id = "sub_existing"
        sub.status = Subscription.Status.ACTIVE
        sub.plan = "organizer"
        sub.save()
        user.refresh_from_db()

        result = stripe_service.create_subscription(user, "organizer")
        assert result["success"] is False
        assert "already has an active subscription" in result["error"]

    def test_update_subscription_immediate_proration(self, stripe_service, mock_stripe, django_user_model, stripe_product):
        """
        Verify immediate update passes correct proration behavior to Stripe.
        This tests the User's specific request about proration Handoff.
        """
        import uuid

        user = django_user_model.objects.create_user(email=f"test_u1_{uuid.uuid4()}@example.com", password="pass")

        # Update existing subscription (created by signal)
        sub = Subscription.objects.get(user=user)
        sub.stripe_subscription_id = "sub_123"
        sub.stripe_customer_id = "cus_123"
        sub.status = Subscription.Status.ACTIVE
        sub.plan = "attendee"
        sub.save()

        # Mock Stripe Retrieve
        mock_stripe_sub = MagicMock(id="sub_123")
        mock_stripe_sub.__getitem__.return_value = {"data": [MagicMock(id="si_123")]}  # items['data']
        mock_stripe.Subscription.retrieve.return_value = mock_stripe_sub

        # Mock Stripe Modify
        mock_stripe.Subscription.modify.return_value = {"status": "active"}

        # Call update
        result = stripe_service.update_subscription(subscription=sub, new_plan="organizer", immediate=True)

        assert result["success"] is True

        # Verify proration flag
        mock_stripe.Subscription.modify.assert_called_once()
        call_kwargs = mock_stripe.Subscription.modify.call_args[1]

        assert call_kwargs["proration_behavior"] == "always_invoice"
        assert call_kwargs["items"] == [{"id": "si_123", "price": "price_month"}]

    def test_update_subscription_scheduled(self, stripe_service, mock_stripe, django_user_model, stripe_product):
        """Verify scheduled update creates a subscription schedule."""
        import uuid

        user = django_user_model.objects.create_user(email=f"test_u_sched_{uuid.uuid4()}@example.com", password="pass")

        sub = Subscription.objects.get(user=user)
        sub.stripe_subscription_id = "sub_123"
        sub.status = Subscription.Status.ACTIVE
        sub.plan = "attendee"
        sub.save()

        # Mock Retrieve
        current_period_end = int(timezone.now().timestamp()) + 86400
        mock_stripe_sub = MagicMock(id="sub_123", current_period_end=current_period_end)
        # Mock items structure: items.data[0].price.id
        mock_item = MagicMock()
        mock_item.price.id = "price_old"
        mock_item.quantity = 1
        mock_stripe_sub.__getitem__.side_effect = lambda k: {"data": [mock_item]} if k == "items" else MagicMock()
        mock_stripe.Subscription.retrieve.return_value = mock_stripe_sub

        # Mock Schedule
        mock_schedule = MagicMock(id="sched_123")
        mock_stripe.SubscriptionSchedule.create.return_value = mock_schedule
        mock_stripe.SubscriptionSchedule.retrieve.return_value = mock_schedule

        # Call update
        result = stripe_service.update_subscription(subscription=sub, new_plan="organizer", immediate=False)

        assert result["success"] is True
        assert sub.pending_plan == "organizer"
        assert sub.pending_change_at is not None

        # Verify Schedule Modify
        mock_stripe.SubscriptionSchedule.modify.assert_called_once()
        call_kwargs = mock_stripe.SubscriptionSchedule.modify.call_args[1]
        assert call_kwargs["end_behavior"] == "release"
        phases = call_kwargs["phases"]
        assert len(phases) == 2
        assert phases[1]["items"][0]["price"] == "price_month"

    def test_sync_trial_period_days(self, stripe_service, mock_stripe, django_user_model):
        """Verify bulk trial extension."""
        import uuid

        user = django_user_model.objects.create_user(email=f"test_u_trial_{uuid.uuid4()}@example.com", password="pass")

        # Setup specific trialing subscription
        trial_end = timezone.now() + timedelta(days=5)
        period_start = timezone.now()

        sub = Subscription.objects.get(user=user)
        sub.plan = "organizer"
        sub.status = Subscription.Status.TRIALING
        sub.current_period_start = period_start
        sub.trial_ends_at = trial_end
        sub.stripe_subscription_id = "sub_trial"
        sub.save()

        # Call sync to extend to 14 days
        # New end should be start + 14 days
        result = stripe_service.sync_trial_period_days("organizer", 14)

        assert result["updated"] == 1

        # Verify Stripe Call
        mock_stripe.Subscription.modify.assert_called_once()
        args, kwargs = mock_stripe.Subscription.modify.call_args
        assert args[0] == "sub_trial"

        expected_ts = int((period_start + timedelta(days=14)).timestamp())
        assert kwargs["trial_end"] == expected_ts

        # Verify DB
        sub.refresh_from_db()
        assert sub.trial_ends_at.timestamp() == pytest.approx(expected_ts, 1)

    def test_sync_subscription_local_update(self, stripe_service, mock_stripe, django_user_model, stripe_product):
        """Verify sync_subscription updates local DB from Stripe."""
        import uuid

        user = django_user_model.objects.create_user(email=f"test_u_sync_{uuid.uuid4()}@example.com", password="pass")

        sub = Subscription.objects.get(user=user)
        sub.stripe_subscription_id = "sub_remote"
        sub.plan = "attendee"
        sub.status = "incomplete"
        sub.save()

        # Mock Stripe response
        mock_stripe_sub = MagicMock(
            id="sub_remote",
            status="active",
            current_period_start=1700000000,
            current_period_end=1702592000,
            trial_end=None,
            cancel_at_period_end=False,
            canceled_at=None,
        )
        # Setup items to allow plan mapping
        mock_item = MagicMock()
        mock_item.id = "si_remote"
        mock_item.price.product = "prod_123"
        mock_item.price.recurring.interval = "month"

        # Helper for dictionary access - must return object with .data for items
        items_obj = MagicMock()
        items_obj.data = [mock_item]

        def get_side_effect(key, default=None):
            if key == "items":
                return items_obj
            return getattr(mock_stripe_sub, key, default)

        mock_stripe_sub.__getitem__.side_effect = lambda k: items_obj if k == "items" else MagicMock()
        mock_stripe_sub.get.side_effect = get_side_effect

        mock_stripe.Subscription.retrieve.return_value = mock_stripe_sub

        # Prevent fall-through to Customer.list
        mock_stripe.Customer.list.return_value = MagicMock(data=[])

        user.refresh_from_db()
        result = stripe_service.sync_subscription(user)

        assert result["success"] is True, f"Sync failed: {result.get('error')}"
        sub.refresh_from_db()
        assert sub.status == "active"
        assert sub.plan == "organizer"
        # User has active organizer subscription
        assert sub.user == user
