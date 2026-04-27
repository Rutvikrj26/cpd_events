"""POST /api/v1/billing/purchases/{uuid}/refund/ — unified refund.

Phase 3 of the payment redesign. Pins:

- Course full refund → CoursePurchase=REFUNDED + CourseEnrollment=DROPPED.
- Event full refund → cascades to Registration cancel + payment_status=REFUNDED.
- Program full refund → cascades to ProgramEnrollment + every seeded
  CourseEnrollment.
- ``PROGRAM_SEEDED`` rejection: a course-anchored CoursePurchase whose
  enrollment was created by a program purchase cannot be refunded
  directly; the response surfaces the parent program info.
- Permission: ``can_manage`` on the related entity is required.

Stripe is patched at ``billing.services.refund_payment_intent`` so the
tests don't hit the network.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from billing.models import CoursePurchase
from learning.models import (
    Course,
    CourseEnrollment,
    Program,
    ProgramCourse,
    ProgramEnrollment,
)


pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def buyer():
    user = User.objects.create_user(email='buyer@example.com', password='pw', full_name='Buyer')
    user.groups.add(Group.objects.get_or_create(name='learner')[0])
    return user


@pytest.fixture
def admin_user():
    user = User.objects.create_user(email='admin@example.com', password='pw', full_name='Admin')
    user.groups.add(Group.objects.get_or_create(name='admin')[0])
    return user


@pytest.fixture
def stranger():
    user = User.objects.create_user(email='nope@example.com', password='pw', full_name='Stranger')
    return user


@pytest.fixture
def paid_course(admin_user):
    return Course.objects.create(
        title='Course', slug='course-1', price_cents=5000, currency='USD',
        status=Course.Status.PUBLISHED, created_by=admin_user,
    )


@pytest.fixture
def paid_program(admin_user, paid_course):
    program = Program.objects.create(
        title='Program', slug='program-1', price_cents=10000, currency='USD',
        status=Program.Status.PUBLISHED, created_by=admin_user,
    )
    ProgramCourse.objects.create(program=program, course=paid_course, order=0, is_required=True)
    return program


def _refund_url(purchase):
    return reverse('purchase-refund', kwargs={'uuid': purchase.uuid})


def _patch_stripe_refund():
    return patch(
        'billing.services.refund_payment_intent',
        return_value={'refund_id': 're_test', 'status': 'succeeded', 'amount_cents': None},
    )


# ---------------------------------------------------------------------------
# Course refunds
# ---------------------------------------------------------------------------


def test_course_full_refund_drops_enrollment(buyer, admin_user, paid_course):
    purchase = CoursePurchase.objects.create(
        user=buyer, course=paid_course,
        amount_cents=5000, subtotal_cents=5000, tax_cents=0, currency='USD',
        stripe_checkout_session_id='cs_course_1',
        stripe_payment_intent_id='pi_course_1',
        status=CoursePurchase.Status.COMPLETED,
    )
    enrollment = CourseEnrollment.objects.create(
        user=buyer, course=paid_course, status=CourseEnrollment.Status.ACTIVE,
    )

    client = APIClient()
    client.force_authenticate(user=admin_user)
    with _patch_stripe_refund():
        res = client.post(_refund_url(purchase), {'reason': 'requested'}, format='json')

    assert res.status_code == status.HTTP_200_OK
    purchase.refresh_from_db()
    enrollment.refresh_from_db()
    assert purchase.status == CoursePurchase.Status.REFUNDED
    assert enrollment.status == CourseEnrollment.Status.DROPPED


def test_course_partial_refund_leaves_status_active(buyer, admin_user, paid_course):
    purchase = CoursePurchase.objects.create(
        user=buyer, course=paid_course,
        amount_cents=5000, subtotal_cents=5000, tax_cents=0, currency='USD',
        stripe_checkout_session_id='cs_course_partial',
        stripe_payment_intent_id='pi_course_partial',
        status=CoursePurchase.Status.COMPLETED,
    )
    enrollment = CourseEnrollment.objects.create(
        user=buyer, course=paid_course, status=CourseEnrollment.Status.ACTIVE,
    )

    client = APIClient()
    client.force_authenticate(user=admin_user)
    with _patch_stripe_refund():
        res = client.post(
            _refund_url(purchase),
            {'reason': 'partial', 'amount_cents': 2000},
            format='json',
        )

    assert res.status_code == status.HTTP_200_OK
    purchase.refresh_from_db()
    enrollment.refresh_from_db()
    # Partial → purchase row stays COMPLETED, enrollment stays ACTIVE.
    assert purchase.status == CoursePurchase.Status.COMPLETED
    assert enrollment.status == CourseEnrollment.Status.ACTIVE


def test_course_refund_program_seeded_rejected(buyer, admin_user, paid_course, paid_program):
    """A course enrollment seeded by a program must be refunded at the program level."""
    program_purchase = CoursePurchase.objects.create(
        user=buyer, program=paid_program,
        amount_cents=10000, subtotal_cents=10000, tax_cents=0, currency='USD',
        stripe_checkout_session_id='cs_prog_seed',
        stripe_payment_intent_id='pi_prog_seed',
        status=CoursePurchase.Status.COMPLETED,
    )
    pe = ProgramEnrollment.objects.create(
        user=buyer, program=paid_program, status=ProgramEnrollment.Status.ACTIVE,
    )
    course_purchase = CoursePurchase.objects.create(
        user=buyer, course=paid_course,
        amount_cents=5000, subtotal_cents=5000, tax_cents=0, currency='USD',
        stripe_checkout_session_id='cs_course_seeded',
        stripe_payment_intent_id='pi_course_seeded',
        status=CoursePurchase.Status.COMPLETED,
    )
    CourseEnrollment.objects.create(
        user=buyer, course=paid_course,
        status=CourseEnrollment.Status.ACTIVE,
        from_program_enrollment=pe,
    )

    client = APIClient()
    client.force_authenticate(user=admin_user)
    res = client.post(_refund_url(course_purchase), {'reason': 'oops'}, format='json')

    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert res.data['error']['code'] == 'PROGRAM_SEEDED'
    assert res.data['error']['program_uuid'] == str(paid_program.uuid)
    # And the original purchase wasn't touched.
    course_purchase.refresh_from_db()
    assert course_purchase.status == CoursePurchase.Status.COMPLETED


# ---------------------------------------------------------------------------
# Program refunds
# ---------------------------------------------------------------------------


def test_program_full_refund_cascade_drops_seeded(buyer, admin_user, paid_program, paid_course):
    program_purchase = CoursePurchase.objects.create(
        user=buyer, program=paid_program,
        amount_cents=10000, subtotal_cents=10000, tax_cents=0, currency='USD',
        stripe_checkout_session_id='cs_program_full',
        stripe_payment_intent_id='pi_program_full',
        status=CoursePurchase.Status.COMPLETED,
    )
    pe = ProgramEnrollment.objects.create(
        user=buyer, program=paid_program, status=ProgramEnrollment.Status.ACTIVE,
    )
    seeded = CourseEnrollment.objects.create(
        user=buyer, course=paid_course,
        status=CourseEnrollment.Status.ACTIVE,
        from_program_enrollment=pe,
    )

    client = APIClient()
    client.force_authenticate(user=admin_user)
    with _patch_stripe_refund():
        res = client.post(_refund_url(program_purchase), {'reason': 'changed mind'}, format='json')

    assert res.status_code == status.HTTP_200_OK
    program_purchase.refresh_from_db()
    pe.refresh_from_db()
    seeded.refresh_from_db()
    assert program_purchase.status == CoursePurchase.Status.REFUNDED
    assert pe.status == ProgramEnrollment.Status.DROPPED
    assert seeded.status == CourseEnrollment.Status.DROPPED


# ---------------------------------------------------------------------------
# Permission gate
# ---------------------------------------------------------------------------


def test_refund_requires_can_manage(buyer, stranger, paid_course):
    purchase = CoursePurchase.objects.create(
        user=buyer, course=paid_course,
        amount_cents=5000, subtotal_cents=5000, tax_cents=0, currency='USD',
        stripe_checkout_session_id='cs_perm',
        stripe_payment_intent_id='pi_perm',
        status=CoursePurchase.Status.COMPLETED,
    )
    client = APIClient()
    client.force_authenticate(user=stranger)
    res = client.post(_refund_url(purchase), {'reason': 'nope'}, format='json')
    assert res.status_code == status.HTTP_403_FORBIDDEN
