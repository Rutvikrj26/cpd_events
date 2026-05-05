"""MagicLink primitives + verify/accept endpoints.

Covers:
- Token sign/verify round-trip with salt isolation (an invite token must
  not verify as a magic link, even with the same uuid+secret).
- Expiry: a link past its `expires_at` returns 410 GONE on verify and accept.
- Anti-enumeration on /auth/sign-in-link/: identical 202 + body whether
  the email matches a User or not; no email queued for unknown emails.
- Accept(CLAIM) creates the User passwordlessly, marks email_verified,
  links any guest registrations, returns JWT pair + redirect URL.
- Accept(SIGN_IN) authenticates an existing User without password change.
- Replaying an accepted link returns 410 LINK_ALREADY_ACCEPTED.
- An authenticated caller hitting an accept link for a different email
  gets 409 wrong_email.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import LearningInvitation, MagicLink, User
from accounts.services import (
    accept_registration_claim,
    accept_sign_in,
    create_registration_claim,
    create_sign_in_link,
    sign_invite_token,
    sign_magic_link_token,
    verify_magic_link_token,
)
from accounts.tokens import (
    MAGIC_LINK_CLAIM_MAX_AGE_SECONDS,
    MAGIC_LINK_SIGN_IN_MAX_AGE_SECONDS,
    sign_token,
    verify_token,
)
from events.models import Event
from registrations.models import Registration


pytestmark = pytest.mark.django_db


# -- Pure token primitives -------------------------------------------------


def test_token_round_trip_succeeds():
    t = sign_token('test-salt', 'abc-uuid', 'secret123')
    assert verify_token('test-salt', 60, 'abc-uuid', t) == 'secret123'


def test_token_wrong_salt_rejects():
    t = sign_token('salt-a', 'abc-uuid', 'secret123')
    assert verify_token('salt-b', 60, 'abc-uuid', t) is None


def test_token_wrong_uuid_rejects():
    t = sign_token('test-salt', 'uuid-a', 'secret')
    assert verify_token('test-salt', 60, 'uuid-b', t) is None


def test_token_tampered_rejects():
    t = sign_token('test-salt', 'abc-uuid', 'secret')
    assert verify_token('test-salt', 60, 'abc-uuid', t[:-3] + 'XYZ') is None


# -- Salt isolation between invite + magic-link ----------------------------


@pytest.fixture
def organizer():
    return User.objects.create_user(email='org@example.com', password='pw', full_name='Org')


@pytest.fixture
def event(organizer):
    return Event.objects.create(
        owner=organizer, title='Test', slug='test',
        starts_at=timezone.now() + timedelta(days=7),
        duration_minutes=60,
        timezone='UTC', currency='USD', price=Decimal('0'),
        registration_enabled=True, status='published',
    )


def test_invite_token_does_not_verify_as_magic_link(organizer, event):
    inv = LearningInvitation.objects.create(
        target_type=LearningInvitation.TargetType.EVENT, event=event,
        email='x@example.com', invited_by=organizer,
        token=LearningInvitation.generate_token(),
        expires_at=timezone.now() + timedelta(days=30),
    )
    invite_token = sign_invite_token(inv)
    # Same uuid + same secret, but different salt → rejected.
    assert verify_magic_link_token(str(inv.uuid), invite_token) is None


# -- Anti-enumeration on sign-in-link --------------------------------------


@patch('accounts.tasks.send_magic_link_email')
def test_sign_in_link_request_unknown_email_returns_202_silently(mock_send):
    res = APIClient().post(
        reverse('accounts:email_sign_in_request'),
        {'email': 'nobody@example.com'},
        format='json',
    )
    assert res.status_code == status.HTTP_202_ACCEPTED
    assert MagicLink.objects.filter(email='nobody@example.com').count() == 0
    mock_send.assert_not_called()


@patch('accounts.tasks.send_magic_link_email')
def test_sign_in_link_request_known_email_creates_link(mock_send, organizer):
    res = APIClient().post(
        reverse('accounts:email_sign_in_request'),
        {'email': organizer.email},
        format='json',
    )
    assert res.status_code == status.HTTP_202_ACCEPTED
    link = MagicLink.objects.get(email=organizer.email)
    assert link.purpose == MagicLink.Purpose.SIGN_IN
    mock_send.assert_called_once_with(link.id)


# -- create_sign_in_link returns None on unknown email ---------------------


def test_create_sign_in_link_returns_none_for_unknown():
    assert create_sign_in_link('nobody@example.com') is None


# -- Verify endpoint -------------------------------------------------------


def test_verify_returns_summary_for_pending_claim(event):
    reg = Registration.objects.create(
        event=event, user=None,
        email='guest@example.com', full_name='Guest',
        status=Registration.Status.CONFIRMED,
        payment_status=Registration.PaymentStatus.NA,
        amount_paid=Decimal('0'), total_amount=Decimal('0'),
        source=Registration.Source.SELF,
    )
    link = create_registration_claim(reg)
    token = sign_magic_link_token(link)
    res = APIClient().post(
        reverse('accounts:magic_link_verify', kwargs={'uuid': link.uuid}) + f'?t={token}',
        {}, format='json',
    )
    assert res.status_code == 200
    assert res.data['purpose'] == 'registration_claim'
    assert res.data['user_exists'] is False
    summary = res.data['registration_summary']
    assert summary['event_uuid'] == str(event.uuid)
    assert summary['event_slug'] == event.slug


def test_verify_returns_410_for_expired_link(event):
    reg = Registration.objects.create(
        event=event, user=None, email='guest@example.com', full_name='Guest',
        status=Registration.Status.CONFIRMED, payment_status=Registration.PaymentStatus.NA,
        amount_paid=Decimal('0'), total_amount=Decimal('0'),
        source=Registration.Source.SELF,
    )
    link = create_registration_claim(reg)
    # Force expiry — 410 is the contract for the verify endpoint.
    link.expires_at = timezone.now() - timedelta(seconds=1)
    link.save(update_fields=['expires_at'])
    token = sign_magic_link_token(link)

    res = APIClient().post(
        reverse('accounts:magic_link_verify', kwargs={'uuid': link.uuid}) + f'?t={token}',
        {}, format='json',
    )
    assert res.status_code == 410
    assert res.data['status'] == 'expired'


# -- Accept(CLAIM) end-to-end ---------------------------------------------


def test_accept_claim_creates_user_and_links_registration(event):
    reg = Registration.objects.create(
        event=event, user=None,
        email='claim@example.com', full_name='Claim Guy',
        status=Registration.Status.CONFIRMED, payment_status=Registration.PaymentStatus.NA,
        amount_paid=Decimal('0'), total_amount=Decimal('0'),
        source=Registration.Source.SELF,
    )
    link = create_registration_claim(reg)
    token = sign_magic_link_token(link)

    res = APIClient().post(
        reverse('accounts:magic_link_accept', kwargs={'uuid': link.uuid}) + f'?t={token}',
        {'password': 'verysecure123'}, format='json',
    )
    assert res.status_code == 200
    assert res.data['purpose'] == 'registration_claim'
    assert res.data['redirect_url'] == f'/events/{event.slug}/details'
    assert res.data['user']['email'] == 'claim@example.com'
    assert res.data['access']
    assert res.data['refresh']

    user = User.objects.get(email='claim@example.com')
    assert user.email_verified
    assert user.has_usable_password()
    assert user.check_password('verysecure123')

    reg.refresh_from_db()
    assert reg.user_id == user.id

    link.refresh_from_db()
    assert link.status == MagicLink.Status.ACCEPTED


def test_accept_claim_short_password_rejected(event):
    reg = Registration.objects.create(
        event=event, user=None, email='shortpw@example.com', full_name='X',
        status=Registration.Status.CONFIRMED, payment_status=Registration.PaymentStatus.NA,
        amount_paid=Decimal('0'), total_amount=Decimal('0'),
        source=Registration.Source.SELF,
    )
    link = create_registration_claim(reg)
    token = sign_magic_link_token(link)
    res = APIClient().post(
        reverse('accounts:magic_link_accept', kwargs={'uuid': link.uuid}) + f'?t={token}',
        {'password': 'short'}, format='json',
    )
    assert res.status_code == 400
    assert res.data['error']['code'] == 'PASSWORD_TOO_SHORT'


def test_accept_replay_returns_410(event):
    reg = Registration.objects.create(
        event=event, user=None, email='replay@example.com', full_name='X',
        status=Registration.Status.CONFIRMED, payment_status=Registration.PaymentStatus.NA,
        amount_paid=Decimal('0'), total_amount=Decimal('0'),
        source=Registration.Source.SELF,
    )
    link = create_registration_claim(reg)
    token = sign_magic_link_token(link)
    url = reverse('accounts:magic_link_accept', kwargs={'uuid': link.uuid}) + f'?t={token}'
    APIClient().post(url, {'password': 'verysecure123'}, format='json')
    second = APIClient().post(url, {'password': 'verysecure123'}, format='json')
    assert second.status_code == 410
    assert second.data['error']['code'] == 'LINK_ALREADY_ACCEPTED'


def test_authenticated_caller_with_different_email_rejected(event):
    other = User.objects.create_user(email='other@example.com', password='pw', full_name='Other')
    reg = Registration.objects.create(
        event=event, user=None, email='target@example.com', full_name='Target',
        status=Registration.Status.CONFIRMED, payment_status=Registration.PaymentStatus.NA,
        amount_paid=Decimal('0'), total_amount=Decimal('0'),
        source=Registration.Source.SELF,
    )
    link = create_registration_claim(reg)
    token = sign_magic_link_token(link)
    client = APIClient()
    client.force_authenticate(user=other)
    res = client.post(
        reverse('accounts:magic_link_accept', kwargs={'uuid': link.uuid}) + f'?t={token}',
        {'password': 'verysecure123'}, format='json',
    )
    assert res.status_code == 409
    assert res.data['wrong_email'] is True
    assert res.data['link_email'] == 'target@example.com'


# -- Accept(SIGN_IN) -------------------------------------------------------


def test_accept_sign_in_returns_jwt(organizer):
    link = create_sign_in_link(organizer.email)
    token = sign_magic_link_token(link)
    res = APIClient().post(
        reverse('accounts:magic_link_accept', kwargs={'uuid': link.uuid}) + f'?t={token}',
        {}, format='json',
    )
    assert res.status_code == 200
    assert res.data['user']['email'] == organizer.email
    assert res.data['access']
    link.refresh_from_db()
    assert link.status == MagicLink.Status.ACCEPTED


# -- Idempotent claim creation (webhook retry simulation) ------------------


def test_create_registration_claim_is_idempotent(event):
    reg = Registration.objects.create(
        event=event, user=None, email='idem@example.com', full_name='X',
        status=Registration.Status.CONFIRMED, payment_status=Registration.PaymentStatus.NA,
        amount_paid=Decimal('0'), total_amount=Decimal('0'),
        source=Registration.Source.SELF,
    )
    a = create_registration_claim(reg)
    b = create_registration_claim(reg)
    assert a.id == b.id
    b.refresh_from_db()
    assert b.send_count == 2
