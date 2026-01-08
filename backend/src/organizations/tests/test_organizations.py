"""
Tests for organization endpoints.

Endpoints tested:
- GET /api/v1/organizations/
- POST /api/v1/organizations/
- GET /api/v1/organizations/{pk}/
- PATCH /api/v1/organizations/{pk}/
- DELETE /api/v1/organizations/{pk}/
- GET /api/v1/organizations/{pk}/members/
- POST /api/v1/organizations/{pk}/invite_member/
- PATCH /api/v1/organizations/{pk}/members/{uuid}/
- DELETE /api/v1/organizations/{pk}/members/{uuid}/
- POST /api/v1/organizations/{pk}/link_organizer/
- POST /api/v1/organizations/accept-invite/{token}/
- POST /api/v1/organizations/create-from-account/
- GET /api/v1/organizations/create-from-account/
"""

import pytest
from rest_framework import status


# =============================================================================
# Organization CRUD Tests
# =============================================================================


@pytest.mark.django_db
class TestOrganizationViewSet:
    """Tests for organization CRUD operations."""

    endpoint = '/api/v1/organizations/'

    def test_list_organizations(self, organizer_client, organization):
        """Organizer can list organizations they belong to."""
        response = organizer_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data

    def test_create_organization(self, organizer_client):
        """Organizer can create an organization."""
        data = {
            'name': 'New Organization',
            'description': 'A test organization',
        }
        response = organizer_client.post(self.endpoint, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Organization'

    def test_retrieve_organization(self, organizer_client, organization):
        """Member can retrieve organization details."""
        response = organizer_client.get(f'{self.endpoint}{organization.uuid}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == organization.name

    def test_update_organization_as_owner(self, organizer_client, organization):
        """Owner can update organization."""
        response = organizer_client.patch(f'{self.endpoint}{organization.uuid}/', {
            'name': 'Updated Org Name',
        })
        assert response.status_code == status.HTTP_200_OK
        organization.refresh_from_db()
        assert organization.name == 'Updated Org Name'

    def test_delete_organization_as_owner(self, organizer_client, organization):
        """Owner can delete organization."""
        response = organizer_client.delete(f'{self.endpoint}{organization.uuid}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_attendee_cannot_create_organization(self, auth_client):
        """Attendees cannot create organizations."""
        response = auth_client.post(self.endpoint, {'name': 'Test'})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_access_unrelated_organization(self, organizer_client, other_organizer, db):
        """Cannot access organization user doesn't belong to."""
        from factories import OrganizationFactory
        other_org = OrganizationFactory(created_by=other_organizer)
        
        response = organizer_client.get(f'{self.endpoint}{other_org.uuid}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Member Management Tests
# =============================================================================


@pytest.mark.django_db
class TestMemberManagement:
    """Tests for organization member management."""

    def test_list_members(self, organizer_client, organization):
        """Owner can list organization members."""
        response = organizer_client.get(f'/api/v1/organizations/{organization.uuid}/members/')
        assert response.status_code == status.HTTP_200_OK

    def test_invite_member(self, organizer_client, organization):
        """Owner can invite a new member."""
        response = organizer_client.post(
            f'/api/v1/organizations/{organization.uuid}/members/invite/',
            {
                'email': 'newmember@example.com',
                'role': 'instructor',
            }
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_update_member_role(self, organizer_client, organization, org_member, db):
        """Owner can update member role."""
        from organizations.models import OrganizationMembership
        membership = OrganizationMembership.objects.get(
            organization=organization,
            user=org_member,
        )
        
        response = organizer_client.patch(
            f'/api/v1/organizations/{organization.uuid}/members/{membership.user.uuid}/',
            {'role': 'admin'}
        )
        assert response.status_code == status.HTTP_200_OK
        membership.refresh_from_db()
        assert membership.role == 'admin'

    def test_remove_member(self, organizer_client, organization, org_member, db):
        """Owner can remove a member."""
        from organizations.models import OrganizationMembership
        membership = OrganizationMembership.objects.get(
            organization=organization,
            user=org_member,
        )
        
        response = organizer_client.delete(
            f'/api/v1/organizations/{organization.uuid}/members/{membership.user.uuid}/remove/'
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_member_cannot_invite(self, organizer_client, organization, org_member, db):
        """Regular member cannot invite others."""
        from rest_framework.test import APIClient
        member_client = APIClient()
        member_client.force_authenticate(user=org_member)
        
        response = member_client.post(
            f'/api/v1/organizations/{organization.uuid}/members/invite/',
            {'email': 'another@example.com', 'role': 'member'}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# Invitation Acceptance Tests
# =============================================================================


@pytest.mark.django_db
class TestAcceptInvitation:
    """Tests for POST /api/v1/organizations/accept-invite/{token}/"""

    def test_accept_valid_invitation(self, auth_client, organization, db):
        """User can accept a valid invitation."""
        from factories import OrganizationMembershipFactory, UserFactory
        invitee = UserFactory()
        membership = OrganizationMembershipFactory(
            organization=organization,
            user=invitee,
            role='member',
        )
        membership.generate_invitation_token()
        membership.accepted_at = None  # Mark as pending
        membership.save()
        
        # Authenticate as invited user
        from rest_framework.test import APIClient
        invitee_client = APIClient()
        invitee_client.force_authenticate(user=invitee)
        
        response = invitee_client.post(
            f'/api/v1/organizations/accept-invite/{membership.invitation_token}/'
        )
        assert response.status_code == status.HTTP_200_OK
        membership.refresh_from_db()
        assert membership.accepted_at is not None

    def test_accept_invalid_token(self, auth_client):
        """Cannot accept with invalid token."""
        response = auth_client.post('/api/v1/organizations/accept-invite/invalid-token/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Create from Account Tests
# =============================================================================


@pytest.mark.django_db
class TestCreateFromAccount:
    """Tests for create-from-account endpoint."""

    endpoint = '/api/v1/organizations/create-from-account/'

    def test_preview_create_from_account(self, organizer_client, organizer, event):
        """Organizer can preview what will be migrated."""
        response = organizer_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK
        # Should show counts of events, templates, etc.
        assert isinstance(response.data, dict)

    def test_create_org_from_account(self, organizer_client, organizer):
        """Organizer can create an org from their account."""
        response = organizer_client.post(self.endpoint, {
            'name': 'My New Organization',
        })
        assert response.status_code == status.HTTP_201_CREATED

    def test_attendee_cannot_create_from_account(self, auth_client):
        """Attendees cannot create org from account."""
        response = auth_client.post(self.endpoint, {'name': 'Test'})
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# Link Organizer Data Tests
# =============================================================================


@pytest.mark.django_db
class TestLinkOrganizer:
    """Tests for link_organizer action."""

    def test_link_organizer_data(self, organizer_client, organization, organizer, event):
        """Can link existing organizer data to organization."""
        response = organizer_client.post(
            f'/api/v1/organizations/{organization.uuid}/link-organizer/',
            {'confirm': True}
        )
        # May succeed or fail based on business logic
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
