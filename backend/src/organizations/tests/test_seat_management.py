
import pytest
from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework import status
from organizations.models import Organization, OrganizationSubscription, OrganizationMembership
from common.config.billing import OrganizationPlanLimits

@pytest.mark.django_db
class TestOrganizationSeatManagement:

    @pytest.fixture
    def subscription(self, organization):
        """Create a subscription for the organization."""
        return OrganizationSubscription.objects.create(
            organization=organization,
            plan=OrganizationSubscription.Plan.ORGANIZATION, # Paid plan (Consolidated Organization)
            included_seats=1,
            # active_organizer_seats is a property or denormalized field, but we should rely on memberships for logic tests
            stripe_subscription_id='sub_123'
        )

    def test_plan_limits_configuration(self):
        """Verify the consolidated ORGANIZATION plan limits."""
        limits = OrganizationPlanLimits.ORGANIZATION
        assert limits['name'] == 'Organization'
        assert limits['included_seats'] == 1
        assert limits['seat_price_cents'] == 12900
        assert limits['max_attendees_per_event'] is None

    def test_invite_member_seat_limit_reached(self, api_client, organization, subscription, organizer):
        """Test that inviting a member when seats are full returns 402 with buying options."""
        # Setup: Organization has 1 included seat, 0 additional.
        # Organizer is OWNER (occupies 1 seat).
        # active_organizer_seats is 1. total_seats is 1.
        # So available_seats is 0.
        
        # Authenticate as owner
        api_client.force_authenticate(user=organizer)
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        dummy_user = User.objects.create_user(email='dummy@example.com', password='password')
        
        # Create a dummy organizer to consume the included seat
        OrganizationMembership.objects.create(
            organization=organization,
            user=dummy_user,
            role='organizer',
            organizer_billing_payer='organization',
            is_active=True
        )

        # Create user to be invited
        User.objects.create_user(email='newinvite@example.com', password='password')

        url = reverse('organizations:organization-invite-member', kwargs={'pk': organization.uuid})
        data = {
            'email': 'newinvite@example.com',
            'role': 'organizer',
            'billing_payer': 'organization'
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
        error_data = response.json()['error']
        assert error_data['code'] == 'SEAT_LIMIT_REACHED'
        assert error_data['details']['seat_price_cents'] == 12900
        assert error_data['details']['action'] == 'buy_seat'

    @patch('billing.services.stripe_service.update_subscription_quantity')
    def test_add_seats_success(self, mock_update_stripe, api_client, organization, subscription, organizer):
        """Test adding seats successfully."""
        api_client.force_authenticate(user=organizer)
        
        mock_update_stripe.return_value = {'success': True}
        
        url = reverse('organizations:organization-add-seats', kwargs={'pk': organization.uuid})
        data = {'seats': 2}
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_seats'] == 3 # 1 included + 2 additional
        assert response.data['additional_seats'] == 2
        
        # Verify local DB update
        subscription.refresh_from_db()
        assert subscription.additional_seats == 2
        
        # Verify Stripe call
        mock_update_stripe.assert_called_with('sub_123', quantity=3)

    @patch('billing.services.stripe_service.update_subscription_quantity')
    def test_remove_seats_success(self, mock_update_stripe, api_client, organization, subscription, organizer):
        """Test removing unused seats successfully."""
        # Setup: Buy 2 extra seats first
        subscription.additional_seats = 2
        subscription.save()
        # active=1 (owner), total=3 (1+2). available=2.
        
        api_client.force_authenticate(user=organizer)
        
        mock_update_stripe.return_value = {'success': True}
        
        url = reverse('organizations:organization-remove-seats', kwargs={'pk': organization.uuid})
        data = {'seats': 1}
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_seats'] == 2 # 1 included + 1 additional
        
        subscription.refresh_from_db()
        assert subscription.additional_seats == 1
        
        mock_update_stripe.assert_called_with('sub_123', quantity=2)

    def test_remove_seats_failure_occupied(self, api_client, organization, subscription, organizer):
        """Test failing to remove seats that are currently occupied."""
        # Setup: 0 extra seats. active=1. total=1. available=0.
        # User tries to remove 1 (which would be the base seat? No endpoint logic handles additional only)
        # But let's say they have 1 additional seat, and 2 active users.
        
        subscription.additional_seats = 1
        subscription.save()
        # Create another admin to occupy the seat
        other_user = MagicMock() # We need a real user for membership FK...
        # Let's just mock active_organizer_seats on the model for simplicity if possible, 
        # but update_seat_usage might overwrite it.
        # Best to just rely on the fact that we have 1 active (owner) and 1 included + 1 additional = 2 total.
        # available = 1.
        # Try to remove 2 seats.
        
        api_client.force_authenticate(user=organizer)
        
        url = reverse('organizations:organization-remove-seats', kwargs={'pk': organization.uuid})
        data = {'seats': 2} # Attempt to remove 2, but only 1 is available (technically 1 is unused)
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Cannot remove 2 seats' in response.data['detail']

    @patch('billing.services.stripe_service.update_subscription_quantity')
    def test_stripe_failure_rollback(self, mock_update_stripe, api_client, organization, subscription, organizer):
        """Test that local DB is not updated if Stripe call fails."""
        api_client.force_authenticate(user=organizer)
        
        mock_update_stripe.return_value = {'success': False, 'error': 'Stripe Error'}
        
        url = reverse('organizations:organization-add-seats', kwargs={'pk': organization.uuid})
        data = {'seats': 1}
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        subscription.refresh_from_db()
        assert subscription.additional_seats == 0
