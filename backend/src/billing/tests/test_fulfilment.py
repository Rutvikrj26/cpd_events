"""Unified webhook fulfilment — every paid surface writes a CoursePurchase.

Phase 2 of the payment redesign. The contract this file pins:

- ``_fulfil_event_registration``, ``_fulfil_course_enrollment``, and
  ``_fulfil_program_enrollment`` all upsert a single CoursePurchase row
  keyed on ``stripe_checkout_session_id``.
- The row carries ``amount_cents``, ``subtotal_cents``, ``tax_cents``,
  ``stripe_payment_intent_id``, and ``currency`` straight off the
  session payload.
- Replays produce no duplicate rows (partial unique on session id).
- Tax flows through even when the webhook payload doesn't carry
  ``total_details`` — the helper re-fetches with ``expand`` and the
  ``CoursePurchase.tax_cents`` ends up populated.

These tests avoid hitting Stripe by stubbing ``billing.client.get_stripe``
and the ``Session.retrieve`` re-fetch path.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import Group
from django.utils import timezone

from accounts.models import User
from billing.handlers import (
    _fulfil_course_enrollment,
    _fulfil_event_registration,
    _fulfil_program_enrollment,
)
from billing.models import CoursePurchase
from events.models import Event
from learning.models import (
    Course,
    CourseEnrollment,
    Program,
    ProgramCourse,
    ProgramEnrollment,
)
from registrations.models import Registration


pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures (kept inline so the file is self-describing)
# ---------------------------------------------------------------------------


@pytest.fixture
def buyer():
    user = User.objects.create_user(email='buyer@example.com', password='pw', full_name='Buyer')
    user.groups.add(Group.objects.get_or_create(name='learner')[0])
    return user


@pytest.fixture
def paid_event(buyer):
    return Event.objects.create(
        owner=buyer,
        title='Paid Workshop',
        slug='paid-workshop',
        starts_at=timezone.now() + timezone.timedelta(days=7),
        ends_at=timezone.now() + timezone.timedelta(days=7, hours=2),
        timezone='UTC',
        currency='USD',
        price=Decimal('100.00'),
        registration_enabled=True,
    )


@pytest.fixture
def pending_registration(buyer, paid_event):
    return Registration.objects.create(
        event=paid_event,
        user=buyer,
        email=buyer.email,
        full_name=buyer.full_name,
        status=Registration.Status.PENDING,
        payment_status=Registration.PaymentStatus.PENDING,
        amount_paid=Decimal('100.00'),
        total_amount=Decimal('100.00'),
        stripe_checkout_session_id='cs_event_1',
    )


@pytest.fixture
def paid_course():
    return Course.objects.create(
        title='Paid Course', slug='paid-course', price_cents=5000, currency='USD',
        status=Course.Status.PUBLISHED,
    )


@pytest.fixture
def paid_program(paid_course):
    program = Program.objects.create(
        title='Paid Program', slug='paid-program', price_cents=10000, currency='USD',
        status=Program.Status.PUBLISHED,
    )
    ProgramCourse.objects.create(program=program, course=paid_course, order=0, is_required=True)
    return program


def _session(*, kind, session_id, amount_total=10000, tax=800, **metadata):
    """Build a minimal Stripe-shaped session dict with total_details populated.

    Mirrors the shape the webhook delivers when ``expand=['total_details']``
    was set on session creation (which we do in ``billing.checkout``).
    """
    md = {"kind": kind, "env": "dev"} | metadata
    return {
        "id": session_id,
        "amount_total": amount_total,
        "amount_subtotal": amount_total - tax,
        "currency": "usd",
        "payment_intent": f"pi_{session_id}",
        "metadata": md,
        "client_reference_id": metadata.get("registration_uuid", ""),
        "total_details": {"amount_tax": tax, "breakdown": {"discounts": []}},
    }


# ---------------------------------------------------------------------------
# Event registration fulfilment
# ---------------------------------------------------------------------------


def test_event_fulfilment_writes_course_purchase(buyer, paid_event, pending_registration):
    session = _session(
        kind="event_registration",
        session_id=pending_registration.stripe_checkout_session_id,
        registration_uuid=str(pending_registration.uuid),
        event_uuid=str(paid_event.uuid),
        user_id=str(buyer.pk),
    )
    _fulfil_event_registration(session)

    purchase = CoursePurchase.objects.get(stripe_checkout_session_id=session["id"])
    assert purchase.event_id == paid_event.id
    assert purchase.user_id == buyer.id
    assert purchase.amount_cents == 10000
    assert purchase.tax_cents == 800
    assert purchase.subtotal_cents == 9200
    assert purchase.stripe_payment_intent_id == "pi_cs_event_1"
    assert purchase.status == CoursePurchase.Status.COMPLETED

    pending_registration.refresh_from_db()
    assert pending_registration.purchase_id == purchase.pk
    assert pending_registration.payment_status == Registration.PaymentStatus.PAID
    assert pending_registration.status == Registration.Status.CONFIRMED


def test_event_fulfilment_idempotent_on_replay(buyer, paid_event, pending_registration):
    session = _session(
        kind="event_registration",
        session_id=pending_registration.stripe_checkout_session_id,
        registration_uuid=str(pending_registration.uuid),
        event_uuid=str(paid_event.uuid),
        user_id=str(buyer.pk),
    )
    _fulfil_event_registration(session)
    _fulfil_event_registration(session)

    assert CoursePurchase.objects.filter(stripe_checkout_session_id=session["id"]).count() == 1


# ---------------------------------------------------------------------------
# Course enrollment fulfilment
# ---------------------------------------------------------------------------


def test_course_fulfilment_writes_course_purchase(buyer, paid_course):
    session = _session(
        kind="course_enrollment",
        session_id="cs_course_1",
        course_uuid=str(paid_course.uuid),
        user_id=str(buyer.pk),
        amount_total=5500,
        tax=500,
    )
    _fulfil_course_enrollment(session)

    purchase = CoursePurchase.objects.get(stripe_checkout_session_id="cs_course_1")
    assert purchase.course_id == paid_course.id
    assert purchase.user_id == buyer.id
    assert purchase.amount_cents == 5500
    assert purchase.tax_cents == 500
    assert purchase.stripe_payment_intent_id == "pi_cs_course_1"

    enrollment = CourseEnrollment.objects.get(user=buyer, course=paid_course)
    assert enrollment.status == CourseEnrollment.Status.ACTIVE
    assert enrollment.stripe_checkout_session_id == "cs_course_1"


def test_course_fulfilment_idempotent_on_replay(buyer, paid_course):
    session = _session(
        kind="course_enrollment",
        session_id="cs_course_2",
        course_uuid=str(paid_course.uuid),
        user_id=str(buyer.pk),
    )
    _fulfil_course_enrollment(session)
    _fulfil_course_enrollment(session)

    assert CoursePurchase.objects.filter(stripe_checkout_session_id="cs_course_2").count() == 1
    assert CourseEnrollment.objects.filter(user=buyer, course=paid_course).count() == 1


# ---------------------------------------------------------------------------
# Program enrollment fulfilment
# ---------------------------------------------------------------------------


def test_program_fulfilment_writes_course_purchase(buyer, paid_program, paid_course):
    session = _session(
        kind="program_enrollment",
        session_id="cs_program_1",
        program_uuid=str(paid_program.uuid),
        user_id=str(buyer.pk),
        amount_total=11000,
        tax=1000,
    )
    _fulfil_program_enrollment(session)

    purchase = CoursePurchase.objects.get(stripe_checkout_session_id="cs_program_1")
    assert purchase.program_id == paid_program.id
    assert purchase.amount_cents == 11000
    assert purchase.tax_cents == 1000

    pe = ProgramEnrollment.objects.get(user=buyer, program=paid_program)
    assert pe.status == ProgramEnrollment.Status.ACTIVE
    assert pe.stripe_checkout_session_id == "cs_program_1"

    # activate() seeds a CourseEnrollment for every member course.
    seeded = CourseEnrollment.objects.get(user=buyer, course=paid_course)
    assert seeded.from_program_enrollment_id == pe.pk


# ---------------------------------------------------------------------------
# Tax re-fetch fallback (Phase 2 fix)
# ---------------------------------------------------------------------------


def test_fulfilment_refetches_session_when_total_details_missing(buyer, paid_course):
    """If the webhook payload omits total_details, the helper re-retrieves."""
    session_no_total = {
        "id": "cs_course_3",
        "amount_total": 6000,
        "amount_subtotal": 5500,
        "currency": "usd",
        "payment_intent": "pi_cs_course_3",
        "metadata": {
            "kind": "course_enrollment",
            "course_uuid": str(paid_course.uuid),
            "user_id": str(buyer.pk),
        },
        # NO total_details key — simulates the legacy payload.
    }
    refetched = dict(session_no_total)
    refetched["total_details"] = {"amount_tax": 500, "breakdown": {"discounts": []}}

    fake_stripe = MagicMock()
    fake_stripe.checkout.Session.retrieve.return_value = MagicMock(to_dict=lambda: refetched)

    with patch("billing.client.get_stripe", return_value=fake_stripe):
        _fulfil_course_enrollment(session_no_total)

    purchase = CoursePurchase.objects.get(stripe_checkout_session_id="cs_course_3")
    assert purchase.tax_cents == 500
    fake_stripe.checkout.Session.retrieve.assert_called_once()
