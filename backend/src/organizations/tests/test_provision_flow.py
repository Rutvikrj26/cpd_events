import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core import mail
from django.test import Client
from rest_framework import status
from rest_framework.test import APIClient

from organizations.models import Organization

User = get_user_model()


@pytest.mark.django_db
class TestProvisionOrganizationFlow:
    """Test the full flow of provisioning an organization via admin."""

    def test_provision_flow(self, client, admin_user):
        """
        Test provisioning flow:
        1. Admin provisions organization
        2. User and Organization created
        3. Email sent with verification link
        4. User verifies email
        """
        # Login as admin
        client.force_login(admin_user)

        # 1. Admin provisions organization
        url = reverse("admin:organizations_organization_provision")
        data = {
            "organization_name": "Test Provisioned Org",
            "admin_name": "Provisioned Admin",
            "admin_email": "provisioned@example.com",
        }

        response = client.post(url, data, follow=True)
        assert response.status_code == 200

        # Check messages
        messages = list(response.context["messages"])
        assert len(messages) == 1
        assert "Organization 'Test Provisioned Org' provisioned successfully" in str(messages[0])

        # 2. Verify User and Organization created
        user = User.objects.get(email="provisioned@example.com")
        org = Organization.objects.get(name="Test Provisioned Org")

        assert user.full_name == "Provisioned Admin"
        assert user.account_type == "organizer"
        assert user.email_verified is False
        assert user.email_verification_token != ""
        assert user.password_reset_token != ""

        assert org.created_by == user
        assert org.slug == "test-provisioned-org"

        # 3. Verify Email Sent
        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.to == ["provisioned@example.com"]
        assert "Welcome to Test Provisioned Org" in email.subject

        # Extract verification URL from email
        # The email body contains: setup_url
        # setup_url = f"{settings.FRONTEND_URL}/auth/verify-email?token={verification_token}&password_token={password_token}"
        message_body = email.body
        assert "auth/verify-email" in message_body
        assert f"token={user.email_verification_token}" in message_body
        assert f"password_token={user.password_reset_token}" in message_body

        # 4. Simulate User Clicking Link and Frontend calling Verify Email API

        # We need an unauthenticated client for verification
        client = APIClient()

        verify_url = "/api/v1/auth/verify-email/"
        verify_data = {"token": user.email_verification_token}

        response = client.post(verify_url, verify_data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Email verified successfully."
        assert "access" in response.data
        assert "refresh" in response.data

        # Verify user state updated
        user.refresh_from_db()
        assert user.email_verified is True
        assert user.email_verification_token == ""  # Should be cleared

        # 5. Simulate User Setting Password (Password Reset Confirm)
        # Frontend would use the password_token extracted from URL
        reset_url = "/api/v1/auth/password-reset/confirm/"
        reset_data = {
            "token": user.password_reset_token,
            "new_password": "newSafePassword123!",
            "new_password_confirm": "newSafePassword123!",
        }

        response = client.post(reset_url, reset_data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Password reset successfully."

        user.refresh_from_db()
        assert user.check_password("newSafePassword123!")
        assert user.password_reset_token == ""  # Should be cleared
