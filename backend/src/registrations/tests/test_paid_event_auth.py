"""Anonymous registration → magic-link claim flow.

Replaces the prior "paid event requires login" test contract — that gate
is gone. The new contract:

- Guest POST to a paid event → 201 + checkout_url (Stripe-mocked).
- Guest POST to a free event → 201 + claim email queued.
- Guest POST with an email matching an existing User → 409 EMAIL_HAS_ACCOUNT.
- Authenticated paid registration → unchanged (no claim, normal flow).
- Stripe webhook fulfilment for an anonymous paid registration creates
  a CLAIM `MagicLink` and queues the email.
- Webhook retries are idempotent: replay creates no duplicate link.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import MagicLink, User
from events.models import Event
from registrations.models import Registration


pytestmark = pytest.mark.django_db


@pytest.fixture
def organizer_user():
    return User.objects.create_user(email='org@example.com', password='pw', full_name='Org')


@pytest.fixture
def free_event(organizer_user):
    return Event.objects.create(
        owner=organizer_user,
        title='Free Talk', slug='free-talk',
        starts_at=timezone.now() + timezone.timedelta(days=7),
        duration_minutes=60,
        timezone='UTC', currency='USD', price=Decimal('0'),
        registration_enabled=True, status='published',
    )


@pytest.fixture
def paid_event(organizer_user):
    return Event.objects.create(
        owner=organizer_user,
        title='Paid Workshop', slug='paid-workshop',
        starts_at=timezone.now() + timezone.timedelta(days=7),
        duration_minutes=120,
        timezone='UTC', currency='USD', price=Decimal('100.00'),
        registration_enabled=True, status='published',
    )


def _make_purchase(reg, *, amount_cents=10000, tax_cents=0):
    """Build a real CoursePurchase row to satisfy the FK on Registration.purchase.

    `user` is intentionally pulled from the registration (may be None for
    anonymous flows — the model now allows it).
    """
    from billing.models import CoursePurchase

    return CoursePurchase.objects.create(
        user=reg.user,
        event=reg.event,
        amount_cents=amount_cents,
        subtotal_cents=amount_cents - tax_cents,
        tax_cents=tax_cents,
        currency=reg.event.currency,
        stripe_payment_intent_id='pi_test',
        stripe_checkout_session_id=f'cs_test_{reg.uuid}',
        status=CoursePurchase.Status.COMPLETED,
    )


def _register(client, event, email='guest@example.com', full_name='Guest User'):
    return client.post(
        reverse('public_event_register', kwargs={'event_uuid': event.uuid}),
        {'email': email, 'full_name': full_name},
        format='json',
    )


# -- Guest paid: now allowed (formerly LOGIN_REQUIRED) --------------------


@patch('accounts.tasks.send_magic_link_email')
@patch('billing.checkout.checkout_service.for_event_registration')
def test_guest_paid_registration_returns_checkout_url(mock_checkout, _send_email, paid_event):
    from billing.checkout import CheckoutResult
    mock_checkout.return_value = CheckoutResult(
        url='https://checkout.stripe.com/test', session_id='cs_test',
    )

    res = _register(APIClient(), paid_event)
    assert res.status_code == status.HTTP_201_CREATED
    assert res.data['requires_payment'] is True
    assert res.data['anonymous'] is True
    assert res.data['checkout_url'] == 'https://checkout.stripe.com/test'
    # No claim link yet — paid claims are issued in the webhook handler.
    assert MagicLink.objects.filter(email='guest@example.com').count() == 0


# -- Guest free: claim email issued immediately ----------------------------


@patch('accounts.tasks.send_magic_link_email')
def test_guest_free_registration_issues_claim(mock_send, free_event):
    res = _register(APIClient(), free_event)
    assert res.status_code == status.HTTP_201_CREATED
    assert res.data['anonymous'] is True

    link = MagicLink.objects.get(email='guest@example.com')
    assert link.purpose == MagicLink.Purpose.REGISTRATION_CLAIM
    assert link.status == MagicLink.Status.PENDING
    assert link.registration_id == Registration.objects.get(email='guest@example.com').id
    mock_send.assert_called_once_with(link.id)


# -- Guest with existing-email collision: 409 inline auth challenge --------


def test_guest_register_blocked_when_email_has_account(free_event):
    User.objects.create_user(email='owner@example.com', password='pw', full_name='Owner')
    res = _register(APIClient(), free_event, email='owner@example.com')
    assert res.status_code == status.HTTP_409_CONFLICT
    assert res.data['error']['code'] == 'EMAIL_HAS_ACCOUNT'
    # No registration row written.
    assert not Registration.objects.filter(email='owner@example.com').exists()
    assert not MagicLink.objects.filter(email='owner@example.com').exists()


# -- Authenticated paid: unchanged path -------------------------------------


@patch('billing.checkout.checkout_service.for_event_registration')
def test_authenticated_paid_registration_proceeds(mock_checkout, paid_event):
    from billing.checkout import CheckoutResult
    mock_checkout.return_value = CheckoutResult(
        url='https://checkout.stripe.com/test', session_id='cs_test',
    )
    user = User.objects.create_user(email='learner@example.com', password='pw', full_name='Learner')
    client = APIClient()
    client.force_authenticate(user=user)

    res = client.post(
        reverse('public_event_register', kwargs={'event_uuid': paid_event.uuid}),
        {'full_name': user.full_name},
        format='json',
    )
    assert res.status_code == status.HTTP_201_CREATED
    assert res.data['requires_payment'] is True
    assert res.data['anonymous'] is False
    assert res.data['checkout_url'] == 'https://checkout.stripe.com/test'
    # Authenticated path doesn't create a claim link.
    assert not MagicLink.objects.filter(email='learner@example.com').exists()


# -- Webhook fulfilment issues claim for anonymous paid --------------------


@patch('accounts.tasks.send_magic_link_email')
@patch('billing.handlers._upsert_purchase_from_session')
def test_webhook_fulfilment_creates_claim_for_anonymous(mock_upsert, mock_send, paid_event):
    """When a Stripe webhook fulfils a guest paid registration, a CLAIM
    MagicLink is created and the email task is queued."""
    from billing.handlers import _fulfil_event_registration

    reg = Registration.objects.create(
        event=paid_event, user=None,
        email='paidguest@example.com', full_name='Paid Guest',
        status=Registration.Status.PENDING,
        payment_status=Registration.PaymentStatus.PENDING,
        amount_paid=Decimal('100.00'),
        total_amount=Decimal('100.00'),
        source=Registration.Source.SELF,
    )

    purchase = _make_purchase(reg)
    mock_upsert.return_value = (purchase, {'metadata': {}})

    _fulfil_event_registration({
        'metadata': {'kind': 'event_registration', 'registration_uuid': str(reg.uuid)},
        'client_reference_id': str(reg.uuid),
        'id': 'cs_test',
    })

    reg.refresh_from_db()
    assert reg.payment_status == Registration.PaymentStatus.PAID

    link = MagicLink.objects.get(email='paidguest@example.com')
    assert link.purpose == MagicLink.Purpose.REGISTRATION_CLAIM
    assert link.registration_id == reg.id
    mock_send.assert_called_with(link.id)


# -- Multi-attendee single-buyer ------------------------------------------


@patch('accounts.tasks.send_magic_link_email')
def test_multi_attendee_free_creates_n_registrations_and_n_claims(mock_send, free_event):
    payload = {
        'attendees': [
            {'email': 'a@example.com', 'full_name': 'Alpha User'},
            {'email': 'b@example.com', 'full_name': 'Beta User'},
            {'email': 'c@example.com', 'full_name': 'Gamma User'},
        ],
    }
    res = APIClient().post(
        reverse('public_event_register', kwargs={'event_uuid': free_event.uuid}),
        payload, format='json',
    )
    assert res.status_code == status.HTTP_201_CREATED
    assert res.data['attendee_count'] == 3
    assert res.data['anonymous'] is True
    assert len(res.data['registration_uuids']) == 3

    assert Registration.objects.filter(event=free_event).count() == 3
    assert MagicLink.objects.filter(
        purpose=MagicLink.Purpose.REGISTRATION_CLAIM,
        email__in=['a@example.com', 'b@example.com', 'c@example.com'],
    ).count() == 3


def test_multi_attendee_duplicate_email_in_batch_rejected(free_event):
    res = APIClient().post(
        reverse('public_event_register', kwargs={'event_uuid': free_event.uuid}),
        {
            'attendees': [
                {'email': 'dup@example.com', 'full_name': 'A'},
                {'email': 'dup@example.com', 'full_name': 'B'},
            ],
        },
        format='json',
    )
    assert res.status_code == 400
    assert res.data['error']['code'] == 'DUPLICATE_EMAIL_IN_BATCH'
    assert not Registration.objects.filter(email='dup@example.com').exists()


def test_multi_attendee_existing_account_blocks_whole_batch(free_event):
    User.objects.create_user(email='existing@example.com', password='pw', full_name='X')
    res = APIClient().post(
        reverse('public_event_register', kwargs={'event_uuid': free_event.uuid}),
        {
            'attendees': [
                {'email': 'fresh@example.com', 'full_name': 'Fresh'},
                {'email': 'existing@example.com', 'full_name': 'Collide'},
            ],
        },
        format='json',
    )
    assert res.status_code == 409
    assert res.data['error']['code'] == 'EMAIL_HAS_ACCOUNT'
    # Whole batch rolled back: no registration written even for the
    # non-colliding email.
    assert not Registration.objects.filter(email__in=['fresh@example.com', 'existing@example.com']).exists()


@patch('accounts.tasks.send_magic_link_email')
@patch('billing.handlers._upsert_purchase_from_session')
def test_webhook_replay_idempotent_for_claim(mock_upsert, mock_send, paid_event):
    """Stripe webhook redelivery must not duplicate claim links."""
    from billing.handlers import _fulfil_event_registration

    reg = Registration.objects.create(
        event=paid_event, user=None,
        email='retryguest@example.com', full_name='Retry Guest',
        status=Registration.Status.PENDING,
        payment_status=Registration.PaymentStatus.PENDING,
        amount_paid=Decimal('100.00'),
        total_amount=Decimal('100.00'),
        source=Registration.Source.SELF,
    )

    purchase = _make_purchase(reg)
    mock_upsert.return_value = (purchase, {'metadata': {}})

    payload = {
        'metadata': {'kind': 'event_registration', 'registration_uuid': str(reg.uuid)},
        'client_reference_id': str(reg.uuid),
        'id': 'cs_test',
    }
    _fulfil_event_registration(payload)
    _fulfil_event_registration(payload)  # replay

    assert MagicLink.objects.filter(email='retryguest@example.com').count() == 1
