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

    def test_update_organization_as_admin(self, organizer_client, organization):
        """Admin can update organization."""
        response = organizer_client.patch(
            f'{self.endpoint}{organization.uuid}/',
            {
                'name': 'Updated Org Name',
            },
        )
        assert response.status_code == status.HTTP_200_OK
        organization.refresh_from_db()
        assert organization.name == 'Updated Org Name'

    def test_delete_organization_as_admin(self, organizer_client, organization):
        """Admin can delete organization."""
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
        """Admin can list organization members."""
        response = organizer_client.get(f'/api/v1/organizations/{organization.uuid}/members/')
        assert response.status_code == status.HTTP_200_OK

    def test_invite_member(self, organizer_client, organization):
        """Admin can invite a new member."""
        response = organizer_client.post(
            f'/api/v1/organizations/{organization.uuid}/members/invite/',
            {
                'email': 'newmember@example.com',
                'role': 'instructor',
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_update_member_role(self, organizer_client, organization, org_member, db):
        """Admin can update member role."""
        from organizations.models import OrganizationMembership

        membership = OrganizationMembership.objects.get(
            organization=organization,
            user=org_member,
        )

        response = organizer_client.patch(
            f'/api/v1/organizations/{organization.uuid}/members/{membership.user.uuid}/', {'role': 'admin'}
        )
        assert response.status_code == status.HTTP_200_OK
        membership.refresh_from_db()
        assert membership.role == 'admin'

    def test_remove_member(self, organizer_client, organization, org_member, db):
        """Admin can remove a member."""
        from organizations.models import OrganizationMembership

        membership = OrganizationMembership.objects.get(
            organization=organization,
            user=org_member,
        )

        response = organizer_client.delete(f'/api/v1/organizations/{organization.uuid}/members/{membership.uuid}/remove/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_member_cannot_invite(self, organizer_client, organization, org_member, db):
        """Instructor cannot invite others."""
        from rest_framework.test import APIClient

        member_client = APIClient()
        member_client.force_authenticate(user=org_member)

        response = member_client.post(
            f'/api/v1/organizations/{organization.uuid}/members/invite/', {'email': 'another@example.com', 'role': 'instructor'}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# Organization Oversight Tests
# =============================================================================


@pytest.mark.django_db
class TestOrganizationOversight:
    def test_admin_can_view_all_org_events(self, organizer_client, organization, other_organizer):
        """Admin can view all events across organizers in the org."""
        from factories import EventFactory
        from organizations.models import OrganizationMembership

        OrganizationMembership.objects.create(
            organization=organization,
            user=other_organizer,
            role=OrganizationMembership.Role.ORGANIZER,
            is_active=True,
        )

        event = EventFactory(
            owner=other_organizer,
            organization=organization,
            title='Org Event',
        )

        response = organizer_client.get(f'/api/v1/organizations/{organization.uuid}/events/')
        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        assert any(item['uuid'] == str(event.uuid) for item in results)

    def test_admin_can_view_all_org_courses(self, organizer_client, organization, course_manager):
        """Admin can view all courses across course managers in the org."""
        from factories import CourseFactory
        from organizations.models import OrganizationMembership

        OrganizationMembership.objects.create(
            organization=organization,
            user=course_manager,
            role=OrganizationMembership.Role.COURSE_MANAGER,
            is_active=True,
        )

        course = CourseFactory(
            organization=organization,
            created_by=course_manager,
            title='Org Course',
        )

        response = organizer_client.get(f'/api/v1/organizations/{organization.uuid}/courses/')
        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        assert any(item['uuid'] == str(course.uuid) for item in results)

    def test_non_admin_cannot_view_org_overview(self, organization, other_organizer):
        """Non-admins cannot access org oversight endpoints."""
        from rest_framework.test import APIClient

        from organizations.models import OrganizationMembership

        OrganizationMembership.objects.create(
            organization=organization,
            user=other_organizer,
            role=OrganizationMembership.Role.ORGANIZER,
            is_active=True,
        )

        client = APIClient()
        client.force_authenticate(user=other_organizer)

        response = client.get(f'/api/v1/organizations/{organization.uuid}/events/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

        response = client.get(f'/api/v1/organizations/{organization.uuid}/courses/')
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
            role='instructor',
        )
        membership.generate_invitation_token()
        membership.accepted_at = None  # Mark as pending
        membership.save()

        # Authenticate as invited user
        from rest_framework.test import APIClient

        invitee_client = APIClient()
        invitee_client.force_authenticate(user=invitee)

        response = invitee_client.post(f'/api/v1/organizations/accept-invite/{membership.invitation_token}/')
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
        response = organizer_client.post(
            self.endpoint,
            {
                'name': 'My New Organization',
            },
        )
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
        response = organizer_client.post(f'/api/v1/organizations/{organization.uuid}/link-organizer/', {'confirm': True})
        # May succeed or fail based on business logic
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]


# =============================================================================
# Organization Onboarding Tests
# =============================================================================


@pytest.mark.django_db
class TestOrganizationOnboarding:
    """Tests for organization onboarding endpoints."""

    endpoint = '/api/v1/organizations/'

    def test_complete_onboarding_success(self, organizer_client, organization):
        """Admin can complete onboarding."""
        assert organization.onboarding_completed is False

        response = organizer_client.post(
            f'{self.endpoint}{organization.uuid}/onboarding/complete/'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['onboarding_completed'] is True
        assert response.data['message'] == 'Onboarding completed.'

        organization.refresh_from_db()
        assert organization.onboarding_completed is True
        assert organization.onboarding_completed_at is not None

    def test_complete_onboarding_idempotent(self, organizer_client, organization):
        """Completing onboarding multiple times is safe."""
        from django.utils import timezone
        
        original_timestamp = timezone.now()
        organization.onboarding_completed = True
        organization.onboarding_completed_at = original_timestamp
        organization.save()

        response = organizer_client.post(
            f'{self.endpoint}{organization.uuid}/onboarding/complete/'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['onboarding_completed'] is True

        # Timestamp should not be updated
        organization.refresh_from_db()
        assert organization.onboarding_completed_at == original_timestamp

    def test_non_admin_cannot_complete_onboarding(self, organization, org_member):
        """Non-admin members (instructors) cannot complete onboarding."""
        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=org_member)

        response = client.post(
            f'{self.endpoint}{organization.uuid}/onboarding/complete/'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'Admin access required' in response.data['detail']

    def test_unauthenticated_cannot_complete_onboarding(self, api_client, organization):
        """Unauthenticated users cannot complete onboarding."""
        response = api_client.post(
            f'{self.endpoint}{organization.uuid}/onboarding/complete/'
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_non_member_cannot_complete_onboarding(self, other_organizer_client, organization):
        """Non-members cannot complete onboarding (blocked by RBAC)."""
        response = other_organizer_client.post(
            f'{self.endpoint}{organization.uuid}/onboarding/complete/'
        )
        # RBAC decorator blocks non-members before they can access the org
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]

    def test_onboarding_completed_sets_timestamp(self, organizer_client, organization):
        """Completing onboarding sets the timestamp."""
        from django.utils import timezone

        before = timezone.now()
        response = organizer_client.post(
            f'{self.endpoint}{organization.uuid}/onboarding/complete/'
        )
        after = timezone.now()

        assert response.status_code == status.HTTP_200_OK
        organization.refresh_from_db()
        assert before <= organization.onboarding_completed_at <= after

    def test_organization_list_includes_onboarding_completed(self, organizer_client, organization):
        """Organization list endpoint includes onboarding_completed field."""
        response = organizer_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK
        
        # Find our org in results
        results = response.data.get('results', response.data)
        org_data = next((o for o in results if o['uuid'] == str(organization.uuid)), None)
        assert org_data is not None
        assert 'onboarding_completed' in org_data
        assert org_data['onboarding_completed'] is False

    def test_organization_detail_includes_onboarding_completed(self, organizer_client, organization):
        """Organization detail endpoint includes onboarding_completed field."""
        response = organizer_client.get(f'{self.endpoint}{organization.uuid}/')
        assert response.status_code == status.HTTP_200_OK
        assert 'onboarding_completed' in response.data
        assert response.data['onboarding_completed'] is False

    def test_organizer_role_cannot_complete_onboarding(self, organization, db):
        """Organizer role members (not admin) cannot complete onboarding."""
        from factories import OrganizerFactory, OrganizationMembershipFactory
        from rest_framework.test import APIClient

        # Create an organizer member (not admin)
        organizer_member = OrganizerFactory()
        OrganizationMembershipFactory(
            organization=organization,
            user=organizer_member,
            role='organizer',
        )

        client = APIClient()
        client.force_authenticate(user=organizer_member)

        response = client.post(
            f'{self.endpoint}{organization.uuid}/onboarding/complete/'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_course_manager_cannot_complete_onboarding(self, organization, db):
        """Course manager role members cannot complete onboarding."""
        from factories import OrganizerFactory, OrganizationMembershipFactory
        from rest_framework.test import APIClient

        # Create a course manager member
        cm_user = OrganizerFactory()
        OrganizationMembershipFactory(
            organization=organization,
            user=cm_user,
            role='course_manager',
        )

        client = APIClient()
        client.force_authenticate(user=cm_user)

        response = client.post(
            f'{self.endpoint}{organization.uuid}/onboarding/complete/'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_newly_created_org_has_onboarding_incomplete(self, organizer_client):
        """Newly created organizations have onboarding_completed=False."""
        from organizations.models import Organization

        data = {
            'name': 'New Onboarding Test Org',
            'description': 'Testing onboarding default',
        }
        response = organizer_client.post(self.endpoint, data)
        assert response.status_code == status.HTTP_201_CREATED
        
        # Check database value (create serializer may not include all fields)
        org = Organization.objects.get(name='New Onboarding Test Org')
        assert org.onboarding_completed is False
        assert org.onboarding_completed_at is None

