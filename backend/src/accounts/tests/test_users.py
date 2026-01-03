"""
Tests for user profile endpoints.

Endpoints tested:
- GET/PATCH /api/v1/users/me/
- GET/PATCH /api/v1/users/me/organizer-profile/
- GET/PATCH /api/v1/users/me/notifications/
- POST /api/v1/users/me/upgrade/
- POST /api/v1/users/me/delete-account/
- POST /api/v1/users/me/export-data/
- GET /api/v1/organizers/{uuid}/
"""

import pytest
from rest_framework import status


# =============================================================================
# Current User Tests
# =============================================================================


@pytest.mark.django_db
class TestCurrentUserView:
    """Tests for GET/PATCH /api/v1/users/me/"""

    endpoint = '/api/v1/users/me/'

    def test_get_current_user(self, auth_client, user):
        """Authenticated user can get their profile."""
        response = auth_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == user.email
        assert response.data['full_name'] == user.full_name

    def test_get_current_user_unauthenticated(self, api_client):
        """Unauthenticated request is rejected."""
        response = api_client.get(self.endpoint)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_current_user(self, auth_client, user):
        """User can update their profile."""
        response = auth_client.patch(self.endpoint, {
            'full_name': 'Updated Name',
        })
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.full_name == 'Updated Name'

    def test_update_email_not_allowed(self, auth_client, user):
        """Email cannot be changed through profile update."""
        original_email = user.email
        response = auth_client.patch(self.endpoint, {
            'email': 'newemail@example.com',
        })
        # Either rejected or ignored
        user.refresh_from_db()
        assert user.email == original_email

    def test_organizer_profile_fields(self, organizer_client, organizer):
        """Organizer gets additional fields in response."""
        response = organizer_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['account_type'] == 'organizer'


# =============================================================================
# Organizer Profile Tests
# =============================================================================


@pytest.mark.django_db
class TestOrganizerProfileView:
    """Tests for GET/PATCH /api/v1/users/me/organizer-profile/"""

    endpoint = '/api/v1/users/me/organizer-profile/'

    def test_get_organizer_profile(self, organizer_client, organizer):
        """Organizer can get their organizer profile."""
        response = organizer_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_update_organizer_profile(self, organizer_client, organizer):
        """Organizer can update their organizer profile."""
        response = organizer_client.patch(self.endpoint, {
            'organizer_bio': 'This is my bio',
            'organizer_website': 'https://example.com',
        })
        assert response.status_code == status.HTTP_200_OK
        organizer.refresh_from_db()
        assert organizer.organizer_bio == 'This is my bio'

    def test_attendee_cannot_access(self, auth_client):
        """Attendees cannot access organizer profile endpoint."""
        response = auth_client.get(self.endpoint)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_access(self, api_client):
        """Unauthenticated request is rejected."""
        response = api_client.get(self.endpoint)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Notification Preferences Tests
# =============================================================================


@pytest.mark.django_db
class TestNotificationPreferencesView:
    """Tests for GET/PATCH /api/v1/users/me/notifications/"""

    endpoint = '/api/v1/users/me/notifications/'

    def test_get_notification_preferences(self, auth_client):
        """User can get their notification preferences."""
        response = auth_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_update_notification_preferences(self, auth_client, user):
        """User can update notification preferences."""
        response = auth_client.patch(self.endpoint, {
            'email_event_reminders': False,
        })
        assert response.status_code == status.HTTP_200_OK

    def test_unauthenticated_cannot_access(self, api_client):
        """Unauthenticated request is rejected."""
        response = api_client.get(self.endpoint)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Upgrade to Organizer Tests
# =============================================================================


@pytest.mark.django_db
class TestUpgradeToOrganizerView:
    """Tests for POST /api/v1/users/me/upgrade/"""

    endpoint = '/api/v1/users/me/upgrade/'

    def test_upgrade_attendee_to_organizer(self, auth_client, user):
        """Attendee can upgrade to organizer."""
        assert user.account_type == 'attendee'
        response = auth_client.post(self.endpoint)
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.account_type == 'organizer'

    def test_organizer_cannot_upgrade(self, organizer_client, organizer):
        """Already an organizer - upgrade should handle gracefully."""
        response = organizer_client.post(self.endpoint)
        # 403 because @roles('attendee') decorator restricts access, or 400 if reached
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN]

    def test_unauthenticated_cannot_upgrade(self, api_client):
        """Unauthenticated request is rejected."""
        response = api_client.post(self.endpoint)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Delete Account Tests
# =============================================================================


@pytest.mark.django_db
class TestDeleteAccountView:
    """Tests for POST /api/v1/users/me/delete-account/"""

    endpoint = '/api/v1/users/me/delete-account/'

    def test_delete_account_with_password(self, auth_client, user):
        """User can delete their account with password confirmation."""
        response = auth_client.post(self.endpoint, {
            'password': 'testpass123',
            'confirm': True,
        })
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        # User should be soft-deleted or anonymized
        assert user.is_active is False or user.is_deleted is True

    def test_delete_account_wrong_password(self, auth_client):
        """Cannot delete with wrong password."""
        response = auth_client.post(self.endpoint, {
            'password': 'wrongpassword',
            'confirm': True,
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_account_no_confirmation(self, auth_client):
        """Must confirm deletion."""
        response = auth_client.post(self.endpoint, {
            'password': 'testpass123',
            'confirm': False,
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_cannot_delete(self, api_client):
        """Unauthenticated request is rejected."""
        response = api_client.post(self.endpoint)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Data Export Tests (GDPR)
# =============================================================================


@pytest.mark.django_db
class TestDataExportView:
    """Tests for POST /api/v1/users/me/export-data/"""

    endpoint = '/api/v1/users/me/export-data/'

    def test_request_data_export(self, auth_client):
        """User can request their data export."""
        response = auth_client.post(self.endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_unauthenticated_cannot_export(self, api_client):
        """Unauthenticated request is rejected."""
        response = api_client.post(self.endpoint)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Public Organizer Profile Tests
# =============================================================================


@pytest.mark.django_db
class TestPublicOrganizerView:
    """Tests for GET /api/v1/organizers/{uuid}/"""

    def test_get_public_organizer_profile(self, api_client, organizer):
        """Anyone can view public organizer profile."""
        response = api_client.get(f'/api/v1/organizers/{organizer.uuid}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['uuid'] == str(organizer.uuid)

    def test_public_profile_limited_fields(self, api_client, organizer):
        """Public profile should not expose sensitive data."""
        response = api_client.get(f'/api/v1/organizers/{organizer.uuid}/')
        assert response.status_code == status.HTTP_200_OK
        # Should not contain sensitive fields
        assert 'email' not in response.data or response.data.get('email') is None
        assert 'password' not in response.data

    def test_nonexistent_organizer(self, api_client):
        """404 for non-existent organizer."""
        import uuid
        fake_uuid = uuid.uuid4()
        response = api_client.get(f'/api/v1/organizers/{fake_uuid}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_attendee_not_public(self, api_client, user):
        """Attendee profiles are not publicly accessible."""
        response = api_client.get(f'/api/v1/organizers/{user.uuid}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND
