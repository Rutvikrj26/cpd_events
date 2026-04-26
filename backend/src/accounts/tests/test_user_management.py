"""
Tests for Phase 1 user management hardening.

Covers:
- AdminBulkInviteView response shape (invited / errors)
- Last-admin guard on AdminUserUpdateSerializer
- Last-admin guard on AdminUserDeactivateView
- Duplicate pending invitation rejection on AdminInviteUserView
"""

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import AuditLog, UserInvitation, UserRoleChange
from factories import UserFactory


ADMIN_USERS_URL = '/api/v1/admin/users/'
INVITE_URL = '/api/v1/admin/users/invite/'
BULK_INVITE_URL = '/api/v1/admin/users/bulk-invite/'
INVITATIONS_URL = '/api/v1/admin/users/invitations/'
EMAIL_CHANGE_REQUEST_URL = '/api/v1/users/me/email-change/request/'
EMAIL_CHANGE_CONFIRM_URL = '/api/v1/auth/email-change/confirm/'


@pytest.fixture
def institution_admin(db):
    """An admin-group user (the institution admin, not Django superuser)."""
    return UserFactory(
        email='institution-admin@example.com',
        full_name='Institution Admin',
        groups=['admin'],
    )


@pytest.fixture
def admin_api_client(institution_admin):
    client = APIClient()
    client.force_authenticate(user=institution_admin)
    return client


@pytest.mark.django_db
class TestAdminBulkInvite:
    """POST /admin/users/bulk-invite/ response shape."""

    def test_returns_invited_and_errors_keys(self, admin_api_client):
        existing = UserFactory(email='taken@example.com', groups=['learner'])

        payload = {
            'invitations': [
                {'email': 'new1@example.com', 'full_name': 'New One', 'role': 'learner'},
                {'email': 'new2@example.com', 'full_name': 'New Two', 'role': 'learner'},
                {'email': existing.email, 'full_name': 'Dupe', 'role': 'learner'},
            ]
        }
        response = admin_api_client.post(BULK_INVITE_URL, payload, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert 'invited' in response.data
        assert 'errors' in response.data
        assert response.data['invited'] == 2
        assert len(response.data['errors']) == 1
        err = response.data['errors'][0]
        assert err['email'] == existing.email
        assert 'error' in err

    def test_pending_invitation_treated_as_error(self, admin_api_client, institution_admin):
        UserInvitation.create_invitation(
            email='pending@example.com',
            full_name='Pending',
            role='learner',
            invited_by=institution_admin,
        )
        response = admin_api_client.post(
            BULK_INVITE_URL,
            {'invitations': [{'email': 'pending@example.com', 'full_name': 'Pending', 'role': 'learner'}]},
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['invited'] == 0
        assert len(response.data['errors']) == 1


@pytest.mark.django_db
class TestLastAdminGuardOnRoleUpdate:
    """AdminUserUpdateSerializer should refuse to drop the last admin."""

    def test_cannot_remove_last_admin_role(self, institution_admin):
        client = APIClient()
        client.force_authenticate(user=institution_admin)
        url = f'{ADMIN_USERS_URL}{institution_admin.uuid}/'

        response = client.patch(url, {'roles': ['learner']}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        institution_admin.refresh_from_db()
        assert institution_admin.groups.filter(name='admin').exists()

    def test_can_remove_admin_role_when_other_admin_exists(self, institution_admin, admin_api_client):
        other_admin = UserFactory(
            email='other-admin@example.com',
            full_name='Other Admin',
            groups=['admin'],
        )
        url = f'{ADMIN_USERS_URL}{other_admin.uuid}/'

        response = admin_api_client.patch(url, {'roles': ['learner']}, format='json')

        assert response.status_code == status.HTTP_200_OK
        other_admin.refresh_from_db()
        assert not other_admin.groups.filter(name='admin').exists()

    def test_cannot_deactivate_via_patch_last_admin(self, institution_admin):
        client = APIClient()
        client.force_authenticate(user=institution_admin)
        url = f'{ADMIN_USERS_URL}{institution_admin.uuid}/'

        response = client.patch(url, {'is_active': False}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        institution_admin.refresh_from_db()
        assert institution_admin.is_active is True


@pytest.mark.django_db
class TestLastAdminGuardOnDeactivateEndpoint:
    """POST /admin/users/{uuid}/deactivate/ should refuse to drop last admin."""

    def test_can_deactivate_when_other_admin_exists(self, admin_api_client):
        second_admin = UserFactory(
            email='second-admin@example.com',
            full_name='Second Admin',
            groups=['admin'],
        )
        url = f'{ADMIN_USERS_URL}{second_admin.uuid}/deactivate/'
        response = admin_api_client.post(url)
        assert response.status_code == status.HTTP_200_OK
        second_admin.refresh_from_db()
        assert second_admin.is_active is False

    def test_cannot_deactivate_last_admin_via_dedicated_endpoint(self, institution_admin):
        # Create a second admin who will be the caller; deactivate them so
        # institution_admin is the only *active* admin. Then force-authenticate
        # as the now-inactive second admin (force_authenticate bypasses the
        # is_active check in the authentication backend) and attempt to
        # deactivate institution_admin. The guard must block it.
        inactive_caller = UserFactory(
            email='inactive-caller@example.com',
            full_name='Inactive Caller',
            groups=['admin'],
        )
        inactive_caller.is_active = False
        inactive_caller.save(update_fields=['is_active'])

        client = APIClient()
        client.force_authenticate(user=inactive_caller)

        response = client.post(f'{ADMIN_USERS_URL}{institution_admin.uuid}/deactivate/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['error']['code'] == 'LAST_ADMIN'
        institution_admin.refresh_from_db()
        assert institution_admin.is_active is True


@pytest.mark.django_db
class TestDuplicatePendingInvitation:
    """AdminInviteUserView rejects re-invitation when one is already pending."""

    def test_duplicate_pending_invitation_rejected(self, admin_api_client):
        payload = {'email': 'invited@example.com', 'full_name': 'Invited', 'role': 'learner'}

        r1 = admin_api_client.post(INVITE_URL, payload, format='json')
        assert r1.status_code == status.HTTP_201_CREATED

        r2 = admin_api_client.post(INVITE_URL, payload, format='json')
        assert r2.status_code == status.HTTP_400_BAD_REQUEST
        assert r2.data['error']['code'] == 'INVITATION_PENDING'

    def test_expired_invitation_does_not_block(self, admin_api_client, institution_admin):
        inv = UserInvitation.create_invitation(
            email='stale@example.com',
            full_name='Stale',
            role='learner',
            invited_by=institution_admin,
        )
        inv.expires_at = timezone.now() - timezone.timedelta(days=1)
        inv.save(update_fields=['expires_at'])

        response = admin_api_client.post(
            INVITE_URL,
            {'email': 'stale@example.com', 'full_name': 'Stale', 'role': 'learner'},
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED


# =============================================================================
# Phase 2 — Unified invitation flow
# =============================================================================


@pytest.mark.django_db
class TestCreateUserEndpointGone:
    """POST /admin/users/ must return 405 — invitation is the only path."""

    def test_post_returns_405(self, admin_api_client):
        response = admin_api_client.post(
            ADMIN_USERS_URL,
            {'email': 'direct@example.com', 'full_name': 'Direct', 'password': 'testpass123', 'roles': ['learner']},
            format='json',
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.django_db
class TestInvitationExpiryFromSettings:
    """create_invitation() should honour INVITATION_EXPIRY_DAYS."""

    def test_default_30_day_expiry(self, settings, institution_admin):
        settings.INVITATION_EXPIRY_DAYS = 30
        before = timezone.now()
        inv = UserInvitation.create_invitation(
            email='a@example.com',
            full_name='A',
            role='learner',
            invited_by=institution_admin,
        )
        delta_days = (inv.expires_at - before).days
        assert 29 <= delta_days <= 30

    def test_override_expiry_via_setting(self, settings, institution_admin):
        settings.INVITATION_EXPIRY_DAYS = 14
        before = timezone.now()
        inv = UserInvitation.create_invitation(
            email='b@example.com',
            full_name='B',
            role='learner',
            invited_by=institution_admin,
        )
        delta_days = (inv.expires_at - before).days
        assert 13 <= delta_days <= 14


@pytest.mark.django_db
class TestInvitationResend:
    """POST /admin/users/invitations/{uuid}/resend/"""

    def test_resend_bumps_counters_and_extends_expiry(self, admin_api_client, institution_admin, settings):
        settings.INVITATION_EXPIRY_DAYS = 30
        inv = UserInvitation.create_invitation(
            email='resend@example.com',
            full_name='Resend',
            role='learner',
            invited_by=institution_admin,
        )
        inv.expires_at = timezone.now() + timezone.timedelta(days=1)
        inv.save(update_fields=['expires_at'])

        url = f'{INVITATIONS_URL}{inv.uuid}/resend/'
        response = admin_api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        inv.refresh_from_db()
        assert inv.resent_count == 1
        # Expiry pushed forward to ~30 days from now
        delta_days = (inv.expires_at - timezone.now()).days
        assert delta_days >= 28

    def test_cannot_resend_accepted_invitation(self, admin_api_client, institution_admin):
        inv = UserInvitation.create_invitation(
            email='accepted@example.com',
            full_name='Accepted',
            role='learner',
            invited_by=institution_admin,
        )
        inv.is_used = True
        inv.accepted_at = timezone.now()
        inv.save(update_fields=['is_used', 'accepted_at'])

        url = f'{INVITATIONS_URL}{inv.uuid}/resend/'
        response = admin_api_client.post(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['error']['code'] == 'INVITATION_ALREADY_ACCEPTED'

    def test_cannot_resend_revoked_invitation(self, admin_api_client, institution_admin):
        inv = UserInvitation.create_invitation(
            email='revoked@example.com',
            full_name='Revoked',
            role='learner',
            invited_by=institution_admin,
        )
        inv.revoke()

        url = f'{INVITATIONS_URL}{inv.uuid}/resend/'
        response = admin_api_client.post(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['error']['code'] == 'INVITATION_REVOKED'


@pytest.mark.django_db
class TestInvitationRevoke:
    """POST /admin/users/invitations/{uuid}/revoke/"""

    def test_revoke_makes_invitation_unusable(self, admin_api_client, institution_admin, api_client):
        inv = UserInvitation.create_invitation(
            email='to-revoke@example.com',
            full_name='Revoke Me',
            role='learner',
            invited_by=institution_admin,
        )
        url = f'{INVITATIONS_URL}{inv.uuid}/revoke/'
        response = admin_api_client.post(url)
        assert response.status_code == status.HTTP_200_OK
        inv.refresh_from_db()
        assert inv.revoked_at is not None
        assert inv.status == 'revoked'

        # Attempting to accept the revoked token must fail.
        accept_response = api_client.post(
            '/api/v1/auth/accept-invitation/',
            {'token': inv.token, 'password': 'NewPass123!', 'password_confirm': 'NewPass123!'},
            format='json',
        )
        assert accept_response.status_code == status.HTTP_400_BAD_REQUEST
        assert accept_response.data['error']['code'] == 'INVITATION_REVOKED'

    def test_revoke_is_idempotent(self, admin_api_client, institution_admin):
        inv = UserInvitation.create_invitation(
            email='idem@example.com',
            full_name='Idempotent',
            role='learner',
            invited_by=institution_admin,
        )
        url = f'{INVITATIONS_URL}{inv.uuid}/revoke/'
        r1 = admin_api_client.post(url)
        inv.refresh_from_db()
        first_revoked_at = inv.revoked_at

        r2 = admin_api_client.post(url)
        inv.refresh_from_db()

        assert r1.status_code == status.HTTP_200_OK
        assert r2.status_code == status.HTTP_200_OK
        assert inv.revoked_at == first_revoked_at


@pytest.mark.django_db
class TestInvitationListFilters:
    """GET /admin/users/invitations/?status=..."""

    def test_pending_filter_excludes_accepted_and_revoked_and_expired(self, admin_api_client, institution_admin):
        pending = UserInvitation.create_invitation(
            email='pending@example.com',
            full_name='Pending',
            role='learner',
            invited_by=institution_admin,
        )
        accepted = UserInvitation.create_invitation(
            email='accepted@example.com',
            full_name='Accepted',
            role='learner',
            invited_by=institution_admin,
        )
        accepted.is_used = True
        accepted.accepted_at = timezone.now()
        accepted.save(update_fields=['is_used', 'accepted_at'])

        revoked = UserInvitation.create_invitation(
            email='revoked@example.com',
            full_name='Revoked',
            role='learner',
            invited_by=institution_admin,
        )
        revoked.revoke()

        expired = UserInvitation.create_invitation(
            email='expired@example.com',
            full_name='Expired',
            role='learner',
            invited_by=institution_admin,
        )
        expired.expires_at = timezone.now() - timezone.timedelta(days=1)
        expired.save(update_fields=['expires_at'])

        response = admin_api_client.get(f'{INVITATIONS_URL}?status=pending')
        assert response.status_code == status.HTTP_200_OK
        uuids = {row['uuid'] for row in response.data['results']}
        assert str(pending.uuid) in uuids
        assert str(accepted.uuid) not in uuids
        assert str(revoked.uuid) not in uuids
        assert str(expired.uuid) not in uuids

    def test_default_list_hides_revoked(self, admin_api_client, institution_admin):
        keep = UserInvitation.create_invitation(
            email='keep@example.com',
            full_name='Keep',
            role='learner',
            invited_by=institution_admin,
        )
        hide = UserInvitation.create_invitation(
            email='hide@example.com',
            full_name='Hide',
            role='learner',
            invited_by=institution_admin,
        )
        hide.revoke()

        response = admin_api_client.get(INVITATIONS_URL)
        assert response.status_code == status.HTTP_200_OK
        uuids = {row['uuid'] for row in response.data['results']}
        assert str(keep.uuid) in uuids
        assert str(hide.uuid) not in uuids


# =============================================================================
# Phase 3 — Role governance & audit log
# =============================================================================


@pytest.mark.django_db
class TestRoleChangeAudit:
    """User.set_roles writes a UserRoleChange row when roles actually change."""

    def test_role_change_via_patch_writes_audit_row(self, admin_api_client, institution_admin):
        target = UserFactory(email='target@example.com', groups=['learner'])
        url = f'{ADMIN_USERS_URL}{target.uuid}/'

        response = admin_api_client.patch(url, {'roles': ['learner', 'organizer']}, format='json')
        assert response.status_code == status.HTTP_200_OK

        rows = UserRoleChange.objects.filter(user=target)
        assert rows.count() == 1
        row = rows.first()
        assert set(row.from_roles) == {'learner'}
        assert set(row.to_roles) == {'learner', 'organizer'}
        assert row.changed_by == institution_admin

    def test_no_audit_row_when_roles_unchanged(self, admin_api_client):
        target = UserFactory(email='static@example.com', groups=['learner'])
        url = f'{ADMIN_USERS_URL}{target.uuid}/'

        response = admin_api_client.patch(url, {'roles': ['learner']}, format='json')
        assert response.status_code == status.HTTP_200_OK

        assert UserRoleChange.objects.filter(user=target).count() == 0


@pytest.mark.django_db
class TestRoleValidation:
    """AdminUserUpdateSerializer.validate_roles rejects empty and unknown."""

    def test_empty_roles_list_rejected(self, admin_api_client):
        target = UserFactory(email='victim@example.com', groups=['learner'])
        url = f'{ADMIN_USERS_URL}{target.uuid}/'

        response = admin_api_client.patch(url, {'roles': []}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unknown_role_rejected(self, admin_api_client):
        target = UserFactory(email='victim@example.com', groups=['learner'])
        url = f'{ADMIN_USERS_URL}{target.uuid}/'

        response = admin_api_client.patch(url, {'roles': ['ceo']}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_duplicate_roles_are_collapsed(self, admin_api_client):
        target = UserFactory(email='dupe@example.com', groups=['learner'])
        url = f'{ADMIN_USERS_URL}{target.uuid}/'

        response = admin_api_client.patch(url, {'roles': ['organizer', 'organizer', 'learner']}, format='json')
        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert set(target.role_names) == {'organizer', 'learner'}


@pytest.mark.django_db
class TestDeactivateWritesAuditLog:
    """POST /admin/users/{uuid}/deactivate/ writes an AuditLog row."""

    def test_deactivation_writes_audit_row(self, admin_api_client):
        target = UserFactory(email='to-deactivate@example.com', groups=['learner'])
        url = f'{ADMIN_USERS_URL}{target.uuid}/deactivate/'

        response = admin_api_client.post(url)
        assert response.status_code == status.HTTP_200_OK

        rows = AuditLog.objects.filter(action='user_deactivated', object_uuid=str(target.uuid))
        assert rows.count() == 1
        assert rows.first().metadata.get('target_email') == 'to-deactivate@example.com'


@pytest.mark.django_db
class TestInvitationAcceptWritesAudit:
    """Accepting an invitation writes both UserRoleChange and AuditLog rows."""

    def test_accept_writes_role_and_audit(self, api_client, institution_admin):
        inv = UserInvitation.create_invitation(
            email='new@example.com',
            full_name='New Person',
            role='organizer',
            invited_by=institution_admin,
        )
        response = api_client.post(
            '/api/v1/auth/accept-invitation/',
            {'token': inv.token, 'password': 'StrongPass123!', 'password_confirm': 'StrongPass123!'},
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED

        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(email='new@example.com')

        role_changes = UserRoleChange.objects.filter(user=user)
        assert role_changes.count() == 1
        row = role_changes.first()
        assert set(row.to_roles) == {'organizer'}
        assert row.changed_by == institution_admin

        assert AuditLog.objects.filter(
            action='invitation_accepted',
            object_uuid=str(user.uuid),
        ).exists()


@pytest.mark.django_db
class TestRolePropertiesNoIsStaffShortCircuit:
    """is_staff should NOT grant institution-admin privileges in app code."""

    def test_is_staff_user_without_admin_group_is_not_institution_admin(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(
            email='django-super@example.com',
            password='x',
            full_name='Django Super',
        )
        user.is_staff = True
        user.save(update_fields=['is_staff'])

        assert user.is_institution_admin is False
        assert user.is_admin is False

    def test_admin_group_grants_institution_admin(self, institution_admin):
        assert institution_admin.is_institution_admin is True
        assert institution_admin.is_admin is True


# =============================================================================
# Phase 4 — Self-service email change
# =============================================================================


@pytest.mark.django_db
class TestEmailChangeRequest:

    def _client_for(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def test_happy_path_stores_pending_email(self, db):
        user = UserFactory(email='old@example.com', groups=['learner'], password='OldPass123!')
        client = self._client_for(user)

        response = client.post(
            EMAIL_CHANGE_REQUEST_URL,
            {'current_password': 'OldPass123!', 'new_email': 'new@example.com'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.pending_email == 'new@example.com'
        assert user.email_change_token != ''
        assert user.email_change_requested_at is not None
        # Email still the old value until confirm
        assert user.email == 'old@example.com'

    def test_wrong_password_rejected(self, db):
        user = UserFactory(email='wp@example.com', groups=['learner'], password='RightPass1!')
        client = self._client_for(user)

        response = client.post(
            EMAIL_CHANGE_REQUEST_URL,
            {'current_password': 'WrongPass1!', 'new_email': 'new@example.com'},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        user.refresh_from_db()
        assert user.pending_email == ''

    def test_duplicate_email_rejected(self, db):
        UserFactory(email='taken@example.com', groups=['learner'])
        user = UserFactory(email='orig@example.com', groups=['learner'], password='Pass1234!')
        client = self._client_for(user)

        response = client.post(
            EMAIL_CHANGE_REQUEST_URL,
            {'current_password': 'Pass1234!', 'new_email': 'taken@example.com'},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_same_email_rejected(self, db):
        user = UserFactory(email='self@example.com', groups=['learner'], password='Pass1234!')
        client = self._client_for(user)

        response = client.post(
            EMAIL_CHANGE_REQUEST_URL,
            {'current_password': 'Pass1234!', 'new_email': 'self@example.com'},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestEmailChangeConfirm:

    def test_confirm_swaps_email(self, api_client, db):
        user = UserFactory(email='old@example.com', groups=['learner'], password='Pass1234!')
        # Kick off request through the serializer-driven flow
        req_client = APIClient()
        req_client.force_authenticate(user=user)
        req = req_client.post(
            EMAIL_CHANGE_REQUEST_URL,
            {'current_password': 'Pass1234!', 'new_email': 'new@example.com'},
            format='json',
        )
        assert req.status_code == status.HTTP_200_OK

        user.refresh_from_db()
        token = user.email_change_token
        assert token

        response = api_client.post(EMAIL_CHANGE_CONFIRM_URL, {'token': token}, format='json')
        assert response.status_code == status.HTTP_200_OK

        user.refresh_from_db()
        assert user.email == 'new@example.com'
        assert user.pending_email == ''
        assert user.email_change_token == ''
        assert user.email_change_requested_at is None

    def test_confirm_links_guest_registrations(self, api_client, db, published_event):
        from registrations.models import Registration

        user = UserFactory(email='old@example.com', groups=['learner'], password='Pass1234!')
        # Create a guest registration with the future email address.
        guest_reg = Registration.objects.create(
            event=published_event,
            email='new@example.com',
            full_name='Guest',
            status='confirmed',
        )
        assert guest_reg.user is None

        req_client = APIClient()
        req_client.force_authenticate(user=user)
        req_client.post(
            EMAIL_CHANGE_REQUEST_URL,
            {'current_password': 'Pass1234!', 'new_email': 'new@example.com'},
            format='json',
        )
        user.refresh_from_db()

        api_client.post(EMAIL_CHANGE_CONFIRM_URL, {'token': user.email_change_token}, format='json')

        guest_reg.refresh_from_db()
        assert guest_reg.user == user

    def test_confirm_expired_token_rejected(self, api_client, db):
        user = UserFactory(email='old@example.com', groups=['learner'], password='Pass1234!')
        user.pending_email = 'new@example.com'
        user.email_change_token = 'test-token-123'
        user.email_change_requested_at = timezone.now() - timezone.timedelta(hours=25)
        user.save(update_fields=[
            'pending_email', 'email_change_token', 'email_change_requested_at', 'updated_at'
        ])

        response = api_client.post(
            EMAIL_CHANGE_CONFIRM_URL,
            {'token': 'test-token-123'},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['error']['code'] == 'TOKEN_EXPIRED'
        user.refresh_from_db()
        assert user.email == 'old@example.com'  # unchanged

    def test_confirm_invalid_token_rejected(self, api_client, db):
        response = api_client.post(
            EMAIL_CHANGE_CONFIRM_URL,
            {'token': 'nope-not-a-real-token'},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['error']['code'] == 'INVALID_TOKEN'

    def test_confirm_blacklists_outstanding_refresh_tokens(self, api_client, db):
        """Security: all existing refresh tokens must be invalidated on confirm."""
        from rest_framework_simplejwt.tokens import RefreshToken
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken,
            OutstandingToken,
        )

        user = UserFactory(email='old@example.com', groups=['learner'], password='Pass1234!')

        # Mint two refresh tokens (simulating two logged-in devices)
        RefreshToken.for_user(user)
        RefreshToken.for_user(user)
        outstanding_before = OutstandingToken.objects.filter(user=user).count()
        assert outstanding_before >= 2

        req_client = APIClient()
        req_client.force_authenticate(user=user)
        req_client.post(
            EMAIL_CHANGE_REQUEST_URL,
            {'current_password': 'Pass1234!', 'new_email': 'new@example.com'},
            format='json',
        )
        user.refresh_from_db()

        api_client.post(EMAIL_CHANGE_CONFIRM_URL, {'token': user.email_change_token}, format='json')

        # Every outstanding token for this user must now be blacklisted.
        outstanding = OutstandingToken.objects.filter(user=user)
        assert outstanding.count() == outstanding_before
        blacklisted = BlacklistedToken.objects.filter(token__in=outstanding).count()
        assert blacklisted == outstanding_before


# =============================================================================
# Phase 5 — Admin user detail view
# =============================================================================


@pytest.mark.django_db
class TestAdminUserDetailView:

    def test_permission_denied_for_non_admin(self, db):
        user = UserFactory(email='learner@example.com', groups=['learner'])
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(f'{ADMIN_USERS_URL}{user.uuid}/detail/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_detail_includes_all_sections(self, admin_api_client, institution_admin):
        target = UserFactory(email='subject@example.com', groups=['learner'])

        response = admin_api_client.get(f'{ADMIN_USERS_URL}{target.uuid}/detail/')
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        for key in (
            'profile',
            'groups',
            'course_staff',
            'owned_events',
            'owned_courses',
            'certificates',
            'recent_activity',
            'pending_invitation',
        ):
            assert key in data

        assert data['profile']['email'] == target.email
        assert data['groups'] == ['learner']
        assert data['course_staff'] == []
        assert data['owned_events'] == []
        assert data['owned_courses'] == []
        assert data['certificates'] == []
        assert data['pending_invitation'] is None

    def test_role_change_appears_in_recent_activity(self, admin_api_client, institution_admin):
        target = UserFactory(email='patch@example.com', groups=['learner'])

        patch = admin_api_client.patch(
            f'{ADMIN_USERS_URL}{target.uuid}/',
            {'roles': ['learner', 'organizer']},
            format='json',
        )
        assert patch.status_code == status.HTTP_200_OK

        detail = admin_api_client.get(f'{ADMIN_USERS_URL}{target.uuid}/detail/')
        activity_types = [row['type'] for row in detail.data['recent_activity']]
        assert 'role_change' in activity_types
        assert 'organizer' in detail.data['groups']

    def test_pending_invitation_surfaced(self, admin_api_client, institution_admin):
        # Issue an invitation for an email not yet claimed, then create the
        # user at that email. The detail endpoint looks up pending invitations
        # by email, so we expect the invitation to surface on the user detail.
        inv = UserInvitation.create_invitation(
            email='pending@example.com',
            full_name='Pending',
            role='learner',
            invited_by=institution_admin,
        )
        target = UserFactory(email='pending@example.com', groups=['learner'])

        detail = admin_api_client.get(f'{ADMIN_USERS_URL}{target.uuid}/detail/')
        assert detail.status_code == status.HTTP_200_OK
        assert detail.data['pending_invitation'] is not None
        assert detail.data['pending_invitation']['uuid'] == str(inv.uuid)
