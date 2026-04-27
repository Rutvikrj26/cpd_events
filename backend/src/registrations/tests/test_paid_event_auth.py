"""Paid event registration requires login (single-tenant migration).

Phase 1 of the payment redesign. Pins:

- Guest POST to a paid event registration → 401 with code LOGIN_REQUIRED.
- Authenticated POST to the same event → proceeds (status 201, returns
  checkout_url; we don't actually run Stripe, just assert the gate
  doesn't block).
- Free events stay open to guests — the gate only triggers on
  ``event.price > 0``.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from events.models import Event


pytestmark = pytest.mark.django_db


@pytest.fixture
def organizer_user():
    user = User.objects.create_user(email='org@example.com', password='pw', full_name='Org')
    return user


@pytest.fixture
def free_event(organizer_user):
    return Event.objects.create(
        owner=organizer_user,
        title='Free Talk', slug='free-talk',
        starts_at=timezone.now() + timezone.timedelta(days=7),
        ends_at=timezone.now() + timezone.timedelta(days=7, hours=1),
        timezone='UTC', currency='USD', price=Decimal('0'),
        registration_enabled=True, status='published',
    )


@pytest.fixture
def paid_event(organizer_user):
    return Event.objects.create(
        owner=organizer_user,
        title='Paid Workshop', slug='paid-workshop',
        starts_at=timezone.now() + timezone.timedelta(days=7),
        ends_at=timezone.now() + timezone.timedelta(days=7, hours=2),
        timezone='UTC', currency='USD', price=Decimal('100.00'),
        registration_enabled=True, status='published',
    )


def _register(client, event):
    return client.post(
        reverse('public_event_register', kwargs={'event_uuid': event.uuid}),
        {'email': 'guest@example.com', 'full_name': 'Guest User'},
        format='json',
    )


def test_guest_paid_registration_requires_login(paid_event):
    res = _register(APIClient(), paid_event)
    assert res.status_code == status.HTTP_401_UNAUTHORIZED
    assert res.data['error']['code'] == 'LOGIN_REQUIRED'


def test_guest_free_registration_allowed(free_event):
    res = _register(APIClient(), free_event)
    assert res.status_code == status.HTTP_201_CREATED


@patch('billing.checkout.checkout_service.for_event_registration')
def test_authenticated_paid_registration_proceeds(mock_checkout, paid_event):
    """The gate only fires for guests — authenticated paid registration
    still goes through the existing Stripe Checkout path."""
    from billing.checkout import CheckoutResult

    mock_checkout.return_value = CheckoutResult(
        url='https://checkout.stripe.com/test', session_id='cs_test'
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
    assert res.data['checkout_url'] == 'https://checkout.stripe.com/test'
