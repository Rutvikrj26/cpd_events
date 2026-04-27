"""GET /api/v1/billing/verify-session/ — frontend post-checkout polling.

Phase 5 of the payment redesign. Pins:
- 200 + ``fulfilled=true`` once the CoursePurchase exists for the
  requesting user.
- 202 ``fulfilled=false`` while the webhook hasn't yet fulfilled OR when
  the session belongs to a different user (deliberately the same shape
  to avoid leaking existence).
- 400 INVALID_SESSION for anything that doesn't look like ``cs_...``.
- The ``redirect_url`` matches the kind so CheckoutReturn can route the
  learner without a second round-trip.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from billing.models import CoursePurchase
from learning.models import Course


pytestmark = pytest.mark.django_db


@pytest.fixture
def buyer():
    user = User.objects.create_user(email='buyer@example.com', password='pw', full_name='Buyer')
    user.groups.add(Group.objects.get_or_create(name='learner')[0])
    return user


@pytest.fixture
def other_user():
    user = User.objects.create_user(email='other@example.com', password='pw', full_name='Other')
    user.groups.add(Group.objects.get_or_create(name='learner')[0])
    return user


@pytest.fixture
def paid_course():
    return Course.objects.create(
        title='Paid Course', slug='paid-course', price_cents=5000, currency='USD',
        status=Course.Status.PUBLISHED,
    )


def _verify(client, session_id):
    return client.get(reverse('billing-verify-session'), {'session_id': session_id})


def test_returns_fulfilled_when_purchase_exists(buyer, paid_course):
    CoursePurchase.objects.create(
        user=buyer, course=paid_course,
        amount_cents=5000, subtotal_cents=5000, tax_cents=0, currency='USD',
        stripe_checkout_session_id='cs_test_1',
        stripe_payment_intent_id='pi_test_1',
        status=CoursePurchase.Status.COMPLETED,
    )
    client = APIClient()
    client.force_authenticate(user=buyer)

    res = _verify(client, 'cs_test_1')
    assert res.status_code == status.HTTP_200_OK
    assert res.data['fulfilled'] is True
    assert res.data['kind'] == 'course'
    assert res.data['payment_status'] == CoursePurchase.Status.COMPLETED
    assert res.data['redirect_url'] == '/dashboard'


def test_returns_202_when_webhook_pending(buyer):
    """No CoursePurchase row → webhook still in flight → 202 (caller polls)."""
    client = APIClient()
    client.force_authenticate(user=buyer)
    res = _verify(client, 'cs_pending_xyz')
    assert res.status_code == status.HTTP_202_ACCEPTED
    assert res.data['fulfilled'] is False


def test_rejects_other_users_session(buyer, other_user, paid_course):
    """A leaked session id can't be probed by another logged-in user."""
    CoursePurchase.objects.create(
        user=other_user, course=paid_course,
        amount_cents=5000, subtotal_cents=5000, tax_cents=0, currency='USD',
        stripe_checkout_session_id='cs_owned_by_other',
        stripe_payment_intent_id='pi_owned_by_other',
        status=CoursePurchase.Status.COMPLETED,
    )
    client = APIClient()
    client.force_authenticate(user=buyer)
    res = _verify(client, 'cs_owned_by_other')
    # Same shape as the pending case — no existence oracle.
    assert res.status_code == status.HTTP_202_ACCEPTED


def test_rejects_invalid_session_id(buyer):
    client = APIClient()
    client.force_authenticate(user=buyer)
    res = _verify(client, 'not-a-stripe-session')
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert res.data['error']['code'] == 'INVALID_SESSION'


def test_requires_authentication(paid_course):
    res = APIClient().get(reverse('billing-verify-session'), {'session_id': 'cs_x'})
    assert res.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
