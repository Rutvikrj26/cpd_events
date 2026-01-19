"""
Tests for authentication endpoints.

Endpoints tested:
- POST /api/v1/auth/signup/
- POST /api/v1/auth/token/
- POST /api/v1/auth/token/refresh/
- POST /api/v1/auth/verify-email/
- POST /api/v1/auth/password-reset/
- POST /api/v1/auth/password-reset/confirm/
- POST /api/v1/auth/password-change/
- GET /api/v1/auth/manifest/
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

User = get_user_model()


# =============================================================================
# Signup Tests
# =============================================================================


@pytest.mark.django_db
class TestSignupView:
    """Tests for POST /api/v1/auth/signup/"""

    endpoint = "/api/v1/auth/signup/"

    def test_signup_attendee_success(self, api_client):
        """Successfully create an attendee account."""
        data = {
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!",
            "full_name": "New User",
        }
        response = api_client.post(self.endpoint, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert "access" not in response.data
        assert "refresh" not in response.data
        assert "message" in response.data
        assert User.objects.filter(email="newuser@example.com").exists()

    def test_signup_organizer_success(self, api_client):
        """Successfully create an organizer account."""
        data = {
            "email": "neworganizer@example.com",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!",
            "full_name": "New Organizer",
        }
        response = api_client.post(self.endpoint, data)
        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email="neworganizer@example.com")
        assert user.email == "neworganizer@example.com"

    def test_signup_duplicate_email(self, api_client, user):
        """Cannot create account with existing email."""
        data = {
            "email": user.email,  # Already exists
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!",
            "full_name": "Duplicate User",
        }
        response = api_client.post(self.endpoint, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Handle nested error format
        error_data = response.data.get("error", {}).get("details", response.data)
        assert "email" in error_data

    def test_signup_password_mismatch(self, api_client):
        """Password confirmation must match."""
        data = {
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "password_confirm": "DifferentPass123!",
            "full_name": "New User",
        }
        response = api_client.post(self.endpoint, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_signup_weak_password(self, api_client):
        """Password must meet strength requirements."""
        data = {
            "email": "newuser@example.com",
            "password": "123",  # Too weak
            "password_confirm": "123",
            "full_name": "New User",
        }
        response = api_client.post(self.endpoint, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_signup_missing_required_fields(self, api_client):
        """Required fields must be provided."""
        data = {
            "email": "newuser@example.com",
            # Missing password, full_name
        }
        response = api_client.post(self.endpoint, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_signup_invalid_email(self, api_client):
        """Email must be valid format."""
        data = {
            "email": "not-an-email",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!",
            "full_name": "New User",
        }
        response = api_client.post(self.endpoint, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Handle nested error format
        error_data = response.data.get("error", {}).get("details", response.data)
        assert "email" in error_data


# =============================================================================
# Token (Login) Tests
# =============================================================================


@pytest.mark.django_db
class TestTokenObtainView:
    """Tests for POST /api/v1/auth/token/"""

    endpoint = "/api/v1/auth/token/"

    def test_login_success(self, api_client, user):
        """Successfully obtain tokens with valid credentials."""
        data = {
            "email": user.email,
            "password": "testpass123",  # Set by factory
        }
        response = api_client.post(self.endpoint, data)
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_wrong_password(self, api_client, user):
        """Cannot login with wrong password."""
        data = {
            "email": user.email,
            "password": "wrongpassword",
        }
        response = api_client.post(self.endpoint, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, api_client):
        """Cannot login with non-existent email."""
        data = {
            "email": "nonexistent@example.com",
            "password": "somepassword",
        }
        response = api_client.post(self.endpoint, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_inactive_user(self, api_client, db):
        """Cannot login with inactive account."""
        from factories import UserFactory

        inactive_user = UserFactory(is_active=False)
        data = {
            "email": inactive_user.email,
            "password": "testpass123",
        }
        response = api_client.post(self.endpoint, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_case_insensitive_email(self, api_client, user):
        """Email lookup is case-insensitive."""
        data = {
            "email": user.email.upper(),
            "password": "testpass123",
        }
        response = api_client.post(self.endpoint, data)
        assert response.status_code == status.HTTP_200_OK

    def test_login_unverified_user_blocked(self, api_client, unverified_user):
        """Unverified users cannot log in."""
        data = {
            "email": unverified_user.email,
            "password": "testpass123",
        }
        response = api_client.post(self.endpoint, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Check error message is present
        error_data = response.data.get("error", {}).get("details", response.data)
        assert "non_field_errors" in error_data or "email" in error_data


# =============================================================================
# Token Refresh Tests
# =============================================================================


@pytest.mark.django_db
class TestTokenRefreshView:
    """Tests for POST /api/v1/auth/token/refresh/"""

    endpoint = "/api/v1/auth/token/refresh/"
    token_endpoint = "/api/v1/auth/token/"

    def test_refresh_token_success(self, api_client, user):
        """Successfully refresh access token."""
        # First, get tokens
        login_response = api_client.post(
            self.token_endpoint,
            {
                "email": user.email,
                "password": "testpass123",
            },
        )
        refresh_token = login_response.data["refresh"]

        # Now refresh
        response = api_client.post(self.endpoint, {"refresh": refresh_token})
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_refresh_invalid_token(self, api_client):
        """Cannot refresh with invalid token."""
        response = api_client.post(self.endpoint, {"refresh": "invalid-token"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_missing_token(self, api_client):
        """Must provide refresh token."""
        response = api_client.post(self.endpoint, {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Email Verification Tests
# =============================================================================


@pytest.mark.django_db
class TestEmailVerificationView:
    """Tests for POST /api/v1/auth/verify-email/"""

    endpoint = "/api/v1/auth/verify-email/"

    def test_verify_email_success(self, api_client, unverified_user):
        """Successfully verify email with valid token."""
        token = unverified_user.generate_email_verification_token()
        unverified_user.save()

        response = api_client.post(self.endpoint, {"token": token})
        assert response.status_code == status.HTTP_200_OK

        unverified_user.refresh_from_db()
        assert unverified_user.email_verified is True

    def test_verify_email_invalid_token(self, api_client):
        """Cannot verify with invalid token."""
        response = api_client.post(self.endpoint, {"token": "invalid-token"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_verify_email_already_verified(self, api_client, user):
        """Already verified users get appropriate response."""
        token = user.generate_email_verification_token()
        user.save()

        response = api_client.post(self.endpoint, {"token": token})
        # Should still succeed or indicate already verified
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]


# =============================================================================
# Password Reset Request Tests
# =============================================================================


@pytest.mark.django_db
class TestPasswordResetRequestView:
    """Tests for POST /api/v1/auth/password-reset/"""

    endpoint = "/api/v1/auth/password-reset/"

    def test_request_reset_existing_user(self, api_client, user, mock_email):
        """Request password reset for existing user."""
        response = api_client.post(self.endpoint, {"email": user.email})
        # Always returns success to prevent email enumeration
        assert response.status_code == status.HTTP_200_OK

    def test_request_reset_nonexistent_user(self, api_client, mock_email):
        """Request for non-existent user still returns success (security)."""
        response = api_client.post(self.endpoint, {"email": "nonexistent@example.com"})
        # Should not reveal whether email exists
        assert response.status_code == status.HTTP_200_OK

    def test_request_reset_invalid_email(self, api_client):
        """Invalid email format is rejected."""
        response = api_client.post(self.endpoint, {"email": "not-an-email"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Password Reset Confirm Tests
# =============================================================================


@pytest.mark.django_db
class TestPasswordResetConfirmView:
    """Tests for POST /api/v1/auth/password-reset/confirm/"""

    endpoint = "/api/v1/auth/password-reset/confirm/"

    def test_reset_password_success(self, api_client, user):
        """Successfully reset password with valid token."""
        token = user.generate_password_reset_token()
        user.save()

        response = api_client.post(
            self.endpoint,
            {
                "token": token,
                "new_password": "NewSecurePass123!",
                "new_password_confirm": "NewSecurePass123!",
            },
        )
        assert response.status_code == status.HTTP_200_OK

        # Verify new password works
        login_response = api_client.post(
            "/api/v1/auth/token/",
            {
                "email": user.email,
                "password": "NewSecurePass123!",
            },
        )
        assert login_response.status_code == status.HTTP_200_OK

    def test_reset_password_invalid_token(self, api_client):
        """Cannot reset with invalid token."""
        response = api_client.post(
            self.endpoint,
            {
                "token": "invalid-token",
                "new_password": "NewSecurePass123!",
                "new_password_confirm": "NewSecurePass123!",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_reset_password_mismatch(self, api_client, user):
        """Password confirmation must match."""
        token = user.generate_password_reset_token()
        user.save()

        response = api_client.post(
            self.endpoint,
            {
                "token": token,
                "new_password": "NewSecurePass123!",
                "new_password_confirm": "DifferentPass123!",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Password Change Tests
# =============================================================================


@pytest.mark.django_db
class TestPasswordChangeView:
    """Tests for POST /api/v1/auth/password-change/"""

    endpoint = "/api/v1/auth/password-change/"

    def test_change_password_success(self, auth_client, user):
        """Successfully change password with correct old password."""
        response = auth_client.post(
            self.endpoint,
            {
                "current_password": "testpass123",
                "new_password": "NewSecurePass123!",
                "new_password_confirm": "NewSecurePass123!",
            },
        )
        assert response.status_code == status.HTTP_200_OK

    def test_change_password_wrong_old_password(self, auth_client):
        """Cannot change with incorrect old password."""
        response = auth_client.post(
            self.endpoint,
            {
                "current_password": "wrongpassword",
                "new_password": "NewSecurePass123!",
                "new_password_confirm": "NewSecurePass123!",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_unauthenticated(self, api_client):
        """Must be authenticated to change password."""
        response = api_client.post(
            self.endpoint,
            {
                "current_password": "testpass123",
                "new_password": "NewSecurePass123!",
                "new_password_confirm": "NewSecurePass123!",
            },
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_change_password_mismatch(self, auth_client):
        """New password confirmation must match."""
        response = auth_client.post(
            self.endpoint,
            {
                "current_password": "testpass123",
                "new_password": "NewSecurePass123!",
                "new_password_confirm": "DifferentPass123!",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Manifest Tests
# =============================================================================


@pytest.mark.django_db
class TestManifestView:
    """Tests for GET /api/v1/auth/manifest/"""

    endpoint = "/api/v1/auth/manifest/"

    def test_manifest_authenticated(self, auth_client):
        """Authenticated user gets their manifest."""
        response = auth_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK
        # Manifest should contain route/permission info
        assert isinstance(response.data, dict)

    def test_manifest_organizer(self, organizer_client):
        """Organizer gets appropriate permissions."""
        response = organizer_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_manifest_unauthenticated(self, api_client):
        """Unauthenticated request is rejected."""
        response = api_client.get(self.endpoint)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Onboarding Completion Tests
# =============================================================================


@pytest.mark.django_db
class TestCompleteOnboardingView:
    """Tests for POST /api/v1/users/me/onboarding/complete/"""

    endpoint = "/api/v1/users/me/onboarding/complete/"

    def test_complete_onboarding_success(self, auth_client, user):
        """Successfully complete onboarding for authenticated user."""
        assert user.onboarding_completed is False

        response = auth_client.post(self.endpoint)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["onboarding_completed"] is True

        user.refresh_from_db()
        assert user.onboarding_completed is True

    def test_complete_onboarding_idempotent(self, auth_client, user):
        """Completing onboarding multiple times is idempotent."""
        user.onboarding_completed = True
        user.save()

        response = auth_client.post(self.endpoint)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["onboarding_completed"] is True

    def test_complete_onboarding_unauthenticated(self, api_client):
        """Unauthenticated request is rejected."""
        response = api_client.post(self.endpoint)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
