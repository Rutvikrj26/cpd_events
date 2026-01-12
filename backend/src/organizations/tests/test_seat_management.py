from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status

from organizations.models import OrganizationMembership


@pytest.mark.django_db
class TestOrganizationSeatManagement:

    @patch('billing.services.stripe_service.update_subscription_quantity')
    def test_auto_provisioning_on_invite(self, mock_update_stripe, api_client, organization, organizer):
        """Test that inviting a member auto-provisions a seat."""

        # Setup: Organization has 1 included seat (Admin), 0 additional.
        subscription = organization.subscription
        subscription.stripe_subscription_id = 'sub_123'
        subscription.save()

        # Ensure admin membership exists (free, but has permissions)
        admin_membership = organization.memberships.get(user=organizer)
        admin_membership.role = OrganizationMembership.Role.ADMIN
        admin_membership.save()

        # Create a dummy billable member (Organizer) to consume the included seat
        from django.contrib.auth import get_user_model

        User = get_user_model()
        dummy_user = User.objects.create_user(email='dummy@example.com', password='password')
        OrganizationMembership.objects.create(
            organization=organization, user=dummy_user, role=OrganizationMembership.Role.ORGANIZER, is_active=True
        )

        api_client.force_authenticate(user=organizer)
        mock_update_stripe.return_value = {'success': True}

        url = reverse('organizations:organization-invite-member', kwargs={'pk': organization.uuid})

        # Create user beforehand
        User.objects.create_user(email='new_member@example.com', password='password')

        data = {'email': 'new_member@example.com', 'role': 'organizer', 'billing_payer': 'organization'}

        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED

        # Check seat count
        subscription.refresh_from_db()
        assert subscription.additional_seats == 1  # 1 admin + 1 new = 2 total. 1 included. 1 additional.

        # Verify Stripe call
        # total = included(1) + additional(1) = 2
        mock_update_stripe.assert_called_with('sub_123', quantity=2)

    @patch('billing.services.stripe_service.update_subscription_quantity')
    def test_invite_new_user_auto_provisions_seat(self, mock_update_stripe, api_client, organization, organizer):
        """Test that inviting a NEW user (no account) auto-provisions a seat."""
        subscription = organization.subscription
        subscription.stripe_subscription_id = 'sub_123'
        subscription.save()

        # Ensure admin membership exists (free, but has permissions)
        admin_membership = organization.memberships.get(user=organizer)
        admin_membership.role = OrganizationMembership.Role.ADMIN
        admin_membership.save()

        # Create a dummy billable member (Organizer) to consume the included seat
        from django.contrib.auth import get_user_model

        User = get_user_model()
        dummy_user = User.objects.create_user(email='dummy_new@example.com', password='password')
        OrganizationMembership.objects.create(
            organization=organization, user=dummy_user, role=OrganizationMembership.Role.ORGANIZER, is_active=True
        )

        api_client.force_authenticate(user=organizer)
        mock_update_stripe.return_value = {'success': True}

        url = reverse('organizations:organization-invite-member', kwargs={'pk': organization.uuid})
        data = {
            'email': 'brand_new_user@example.com',  # No user created in DB
            'role': 'organizer',
            'billing_payer': 'organization',
        }

        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED

        # Check membership created with user=None
        membership = OrganizationMembership.objects.get(invitation_email='brand_new_user@example.com')
        assert membership.user is None
        assert not membership.is_active

        # Check seat count
        subscription.refresh_from_db()
        # Admin (1 - FREE) + Dummy (1 - BILLABLE) + Pending (1 - BILLABLE) = 2 Billable Total
        # Included = 1. Additional = 1.
        assert subscription.org_paid_organizers_count == 2
        assert subscription.additional_seats == 1

        # Verify Stripe call
        mock_update_stripe.assert_called_with('sub_123', quantity=2)

        # Verify list endpoint returns user_email for pending member
        list_url = reverse('organizations:organization-members', kwargs={'pk': organization.uuid})
        list_response = api_client.get(list_url)
        assert list_response.status_code == status.HTTP_200_OK
        # Find the pending member
        pending = next(m for m in list_response.data if m['user_email'] == 'brand_new_user@example.com')
        assert pending['user_email'] == 'brand_new_user@example.com'
        assert pending['user_name'] is None

    @patch('billing.services.stripe_service.update_subscription_quantity')
    def test_auto_deprovisioning_on_remove(self, mock_update_stripe, api_client, organization, organizer):
        """Test that removing an organizer automatically releases the seat (removes additional)."""
        # Setup: 2 organizers (1 admin + 1 extra). 1 additional seat. active=2.
        subscription = organization.subscription
        subscription.stripe_subscription_id = 'sub_123'
        subscription.additional_seats = 1
        subscription.save()

        # Ensure admin membership exists (free, but has permissions)
        admin_membership = organization.memberships.get(user=organizer)
        admin_membership.role = OrganizationMembership.Role.ADMIN
        admin_membership.save()

        from django.contrib.auth import get_user_model

        User = get_user_model()

        # User 1: Dummy Organizer (Billable)
        dummy_user = User.objects.create_user(email='dummy_remove@example.com', password='password')
        OrganizationMembership.objects.create(
            organization=organization, user=dummy_user, role=OrganizationMembership.Role.ORGANIZER, is_active=True
        )

        # User 2: The one we will remove (Billable)
        user2 = User.objects.create_user(email='user2@example.com', password='password')

        m = OrganizationMembership.objects.create(
            organization=organization, user=user2, role='organizer', organizer_billing_payer='organization', is_active=True
        )

        # Verify setup
        organization.update_counts()  # ensure counts are fresh
        subscription.refresh_from_db()
        assert subscription.org_paid_organizers_count == 2
        assert subscription.additional_seats == 1

        # Now remove user2
        api_client.force_authenticate(user=organizer)
        mock_update_stripe.return_value = {'success': True}

        # Using API to remove member
        # Note: 'remove_member' action url is .../members/{uuid}/remove
        url = reverse('organizations:organization-remove-member', kwargs={'pk': organization.uuid, 'member_uuid': m.uuid})
        # Wait, the action url_path is 'members/(?P<member_uuid>[^/.]+)/remove'
        # verify URL: organizations/{pk}/members/{member_uuid}/remove/

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify local DB update
        subscription.refresh_from_db()
        assert subscription.org_paid_organizers_count == 1
        assert subscription.additional_seats == 0

        # Verify Stripe call
        # total = included(1) + additional(0) = 1
        mock_update_stripe.assert_called_with('sub_123', quantity=1)

    @patch('billing.services.stripe_service.update_subscription_quantity')
    def test_admin_plus_pending_organizer_count(self, mock_update_stripe, api_client, organization, organizer):
        """
        Test the user's scenario: 1 active Admin + 1 pending Organizer.
        Should result in 2 org-paid seats and 1 additional seat.
        """
        subscription = organization.subscription
        subscription.stripe_subscription_id = 'sub_123'
        subscription.save()

        # 1. The 'organizer' (creator) is already a member, likely an admin.
        # Let's ensure they are an 'admin' (FREE).
        membership = OrganizationMembership.objects.get(organization=organization, user=organizer)
        membership.role = OrganizationMembership.Role.ADMIN
        membership.is_active = True
        membership.organizer_billing_payer = None
        membership.save()

        # Create a dummy billable member (Organizer) to consume the included seat
        from django.contrib.auth import get_user_model

        User = get_user_model()
        dummy_user = User.objects.create_user(email='dummy_pending@example.com', password='password')
        OrganizationMembership.objects.create(
            organization=organization, user=dummy_user, role=OrganizationMembership.Role.ORGANIZER, is_active=True
        )

        api_client.force_authenticate(user=organizer)
        mock_update_stripe.return_value = {'success': True}

        # 2. Invite a pending organizer
        url = reverse('organizations:organization-invite-member', kwargs={'pk': organization.uuid})
        data = {'email': 'pending_org@example.com', 'role': 'organizer', 'billing_payer': 'organization'}

        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED

        # 3. Verify total seats
        subscription.refresh_from_db()
        # Admin (1 - FREE) + Dummy Organizer (1 - BILLABLE) + Pending Organizer (1 - BILLABLE) = 2 Billable Total
        # Included = 1. Additional = 1.
        assert subscription.org_paid_organizers_count == 2
        assert subscription.additional_seats == 1

        # Verify Stripe call
        mock_update_stripe.assert_called_with('sub_123', quantity=2)

    def test_invite_course_manager_requires_available_seat(self, api_client, organization, organizer):
        """Course manager invites should respect org-paid seat limits."""
        from django.contrib.auth import get_user_model

        User = get_user_model()

        subscription = organization.subscription
        subscription.included_seats = 1
        subscription.additional_seats = 0
        subscription.save(update_fields=['included_seats', 'additional_seats', 'updated_at'])

        # Ensure admin membership exists (free, but has permissions)
        admin_membership = organization.memberships.get(user=organizer)
        admin_membership.role = OrganizationMembership.Role.ADMIN
        admin_membership.save()

        # Consume the single included seat with an org-paid organizer
        dummy_user = User.objects.create_user(email='seat_owner@example.com', password='password')
        OrganizationMembership.objects.create(
            organization=organization,
            user=dummy_user,
            role=OrganizationMembership.Role.ORGANIZER,
            organizer_billing_payer='organization',
            is_active=True,
        )

        api_client.force_authenticate(user=organizer)

        url = reverse('organizations:organization-invite-member', kwargs={'pk': organization.uuid})
        data = {
            'email': 'course_manager@example.com',
            'role': 'course_manager',
        }

        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert response.data['error']['code'] == 'SEAT_LIMIT_REACHED'
