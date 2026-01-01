import pytest
from unittest.mock import patch, MagicMock
from organizations.models import Organization, OrganizationMembership, OrganizationSubscription
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def organization(organizer):
    # Create user subscription (required for OrganizationViewSet access)
    from billing.models import Subscription
    Subscription.objects.update_or_create(
        user=organizer,
        defaults={
            'plan': 'organization',
            'status': 'active'
        }
    )

    org = Organization.objects.create(
        name="Test Org",
        slug="test-org",
        created_by=organizer
    )
    
    # Create owner membership (required for permission checks)
    # The import is already at the top, but following the instruction to include it here.
    from organizations.models import OrganizationMembership 
    OrganizationMembership.objects.create(
        user=organizer,
        organization=org,
        role='owner',
        is_active=True
    )
    
    # Create subscription
    OrganizationSubscription.objects.create(
        organization=org,
        included_seats=3,
        seat_price_cents=1500,
        status='active'
    )
    
    # Refresh organizer to ensure subscription is updated in memory
    organizer.refresh_from_db()
    
    return org

@pytest.mark.django_db
class TestOrganizationPlansAndBilling:
    def test_get_plans(self, organizer_client):
        response = organizer_client.get('/api/v1/organizations/plans/')
        assert response.status_code == 200
        assert 'free' in response.data
        assert 'team' in response.data
        assert response.data['team']['name'] == 'Team'

    @patch('organizations.views.stripe_service')
    def test_upgrade_subscription(self, mock_stripe, organizer_client, organization):
        mock_stripe.create_checkout_session.return_value = {'success': True, 'url': 'https://stripe.com/checkout'}
        
        url = f'/api/v1/organizations/{organization.uuid}/subscription/upgrade/'
        data = {'plan': 'team'}
        
    
        response = organizer_client.post(url, data)
        assert response.status_code == 200
        assert response.data['url'] == 'https://stripe.com/checkout'
        mock_stripe.create_checkout_session.assert_called_once()
        
    @patch('organizations.views.email_service')
    def test_invite_organizer_external(self, mock_email, organizer_client, organization):
        # Ensure invitee exists
        invitee = User.objects.create_user(email='invitee@example.com', password='pw', full_name='Invitee')

        url = f'/api/v1/organizations/{organization.uuid}/link-organizer/'
        data = {'organizer_email': 'invitee@example.com', 'role': 'member'}
        
        response = organizer_client.post(url, data)
        assert response.status_code == 201
        mock_email.send_email.assert_called_once()
        
        # Check membership created
        assert OrganizationMembership.objects.filter(user=invitee, organization=organization, is_active=False).exists()

    @patch('organizations.views.email_service')
    def test_invite_organizer_non_existent(self, mock_email, organizer_client, organization):
        url = f'/api/v1/organizations/{organization.uuid}/link-organizer/'
        data = {'organizer_email': 'nobody@example.com', 'role': 'member'}
        
        response = organizer_client.post(url, data)
        assert response.status_code == 400
        assert 'does not exist' in response.data['detail']
        mock_email.send_email.assert_not_called()
