import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, datetime
from unittest.mock import MagicMock, patch

from billing.models import Subscription, StripeProduct
from billing.admin import SubscriptionAdmin
from billing.services import StripeService
from organizations.models import Organization, OrganizationSubscription
from organizations.admin import OrganizationSubscriptionAdmin

User = get_user_model()

class MockRequest:
    def __init__(self, user=None):
        self.user = user
        self.method = "POST"
        self._messages = []

    def add_message(self, level, message, extra_tags=''):
        self._messages.append(message)


@pytest.mark.django_db
class TestAdminTrialSync:

    @pytest.fixture
    def user(self):
        user = User.objects.create_user(email="test@example.com", password="password", account_type="attendee")
        return user

    @pytest.fixture
    def subscription(self, user):
        # Subscription is auto-created by signal for new users
        sub = Subscription.objects.get(user=user)
        sub.stripe_subscription_id = "sub_test_123"
        sub.trial_ends_at = timezone.now() + timedelta(days=10)
        sub.save()
        return sub

    @pytest.fixture
    def organization(self, user):
        # Organization creation triggers signal for OrganizationSubscription
        return Organization.objects.create(name="Test Org", slug="test-org", created_by=user)

    @pytest.fixture
    def org_subscription(self, organization):
        sub = OrganizationSubscription.objects.get(organization=organization)
        sub.stripe_subscription_id = "sub_org_123"
        sub.trial_ends_at = timezone.now() + timedelta(days=10)
        sub.save()
        return sub

    @pytest.fixture
    def mock_stripe_service(self):
        # Patch the class where it is defined, because it is imported locally in the function
        with patch('billing.services.StripeService') as mock:
            instance = mock.return_value
            instance.update_subscription_trial.return_value = {'success': True}
            yield instance

    @pytest.fixture
    def mock_org_stripe_service(self):
        # Same here
        with patch('billing.services.StripeService') as mock:
            instance = mock.return_value
            instance.update_subscription_trial.return_value = {'success': True}
            yield instance

    @pytest.fixture
    def mock_messages(self):
        with patch('billing.admin.messages') as mock:
            yield mock

    @pytest.fixture
    def mock_org_messages(self):
        with patch('organizations.admin.messages') as mock:
            yield mock

    def test_subscription_admin_save_model_syncs_trial(self, user, subscription, mock_stripe_service, mock_messages):
        site = AdminSite()
        admin = SubscriptionAdmin(Subscription, site)
        request = MockRequest(user=user)
        
        # Simulate form data with changed trial_ends_at
        new_trial_end = timezone.now() + timedelta(days=30)
        subscription.trial_ends_at = new_trial_end
        
        form = MagicMock()
        form.changed_data = ['trial_ends_at']
        
        admin.save_model(request, subscription, form, change=True)
        
        # Verify service was called
        mock_stripe_service.update_subscription_trial.assert_called_once_with(
            "sub_test_123", new_trial_end
        )
        # Verify message added (optional)
        mock_messages.success.assert_called()

    def test_subscription_admin_no_sync_if_not_changed(self, user, subscription, mock_stripe_service):
        site = AdminSite()
        admin = SubscriptionAdmin(Subscription, site)
        request = MockRequest(user=user)
        
        form = MagicMock()
        form.changed_data = [] # Nothing changed
        
        admin.save_model(request, subscription, form, change=True)
        
        mock_stripe_service.update_subscription_trial.assert_not_called()

    def test_org_subscription_admin_save_model_syncs_trial(self, user, org_subscription, mock_org_stripe_service, mock_org_messages):
        site = AdminSite()
        admin = OrganizationSubscriptionAdmin(OrganizationSubscription, site)
        request = MockRequest(user=user)
        
        # Simulate form data with changed trial_ends_at
        new_trial_end = timezone.now() + timedelta(days=45)
        org_subscription.trial_ends_at = new_trial_end
        
        form = MagicMock()
        form.changed_data = ['trial_ends_at']
        
        admin.save_model(request, org_subscription, form, change=True)
        
        # Verify service was called
        mock_org_stripe_service.update_subscription_trial.assert_called_once_with(
            "sub_org_123", new_trial_end
        )
        mock_org_messages.success.assert_called()
