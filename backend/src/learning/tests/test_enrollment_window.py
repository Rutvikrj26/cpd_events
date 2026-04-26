"""Tests for Course.enrollment_opens_at / enrollment_closes_at window."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from learning.models import Course


@pytest.fixture
def learner(db):
    return User.objects.create_user(email='l@ex.com', password='pw')


@pytest.fixture
def client(learner):
    c = APIClient()
    c.force_authenticate(learner)
    return c


def _make_course(**kwargs):
    defaults = dict(
        title='Window Course',
        slug='window-course',
        price_cents=1000,  # paid so checkout view doesn't short-circuit
        stripe_price_id='price_test',
        status=Course.Status.PUBLISHED,
    )
    defaults.update(kwargs)
    return Course.objects.create(**defaults)


@pytest.mark.django_db
class TestEnrollmentWindowState:
    def test_unbounded_when_no_dates(self):
        course = _make_course()
        assert course.enrollment_window_state == 'unbounded'
        assert course.is_enrollable

    def test_upcoming_before_open(self):
        course = _make_course(enrollment_opens_at=timezone.now() + timedelta(hours=1))
        assert course.enrollment_window_state == 'upcoming'
        assert not course.is_enrollable

    def test_closed_after_close(self):
        course = _make_course(enrollment_closes_at=timezone.now() - timedelta(hours=1))
        assert course.enrollment_window_state == 'closed'
        assert not course.is_enrollable

    def test_open_inside_window(self):
        now = timezone.now()
        course = _make_course(
            enrollment_opens_at=now - timedelta(hours=1),
            enrollment_closes_at=now + timedelta(hours=1),
        )
        assert course.enrollment_window_state == 'open'
        assert course.is_enrollable

    def test_closed_ignores_enrollment_open_toggle(self):
        course = _make_course(
            enrollment_open=False,
            enrollment_closes_at=timezone.now() + timedelta(hours=1),
        )
        assert not course.is_enrollable


@pytest.mark.django_db
class TestCheckoutRespectsWindow:
    def _post(self, client, course):
        return client.post(
            reverse('learning:course-checkout', kwargs={'uuid': str(course.uuid)}),
            {'success_url': 'http://s', 'cancel_url': 'http://c'},
            format='json',
        )

    def test_rejects_when_upcoming(self, client):
        course = _make_course(enrollment_opens_at=timezone.now() + timedelta(hours=1))
        response = self._post(client, course)
        assert response.status_code == 400
        assert 'opens' in str(response.data).lower()

    def test_rejects_when_closed(self, client):
        course = _make_course(enrollment_closes_at=timezone.now() - timedelta(hours=1))
        response = self._post(client, course)
        assert response.status_code == 400
        assert 'closed' in str(response.data).lower()


@pytest.mark.django_db
class TestCheckEnrollableCodes:
    """Single source of truth: every enrollment entry point calls check_enrollable()."""

    def test_upcoming_returns_code(self):
        course = _make_course(enrollment_opens_at=timezone.now() + timedelta(hours=1))
        ok, code, _ = course.check_enrollable()
        assert not ok and code == 'ENROLLMENT_UPCOMING'

    def test_closed_window_returns_code(self):
        course = _make_course(enrollment_closes_at=timezone.now() - timedelta(hours=1))
        ok, code, _ = course.check_enrollable()
        assert not ok and code == 'ENROLLMENT_CLOSED'

    def test_toggle_off_returns_code(self):
        course = _make_course(enrollment_open=False)
        ok, code, _ = course.check_enrollable()
        assert not ok and code == 'ENROLLMENT_CLOSED'

    def test_full_returns_code(self):
        course = _make_course(max_enrollments=0)
        course.enrollment_count = 0
        ok, _, _ = course.check_enrollable()
        # max=0 → is_full returns False (0 >= 0 is True though...)
        # Verify capacity path separately:
        course.max_enrollments = 1
        course.enrollment_count = 1
        course.save()
        ok, code, _ = course.check_enrollable()
        assert not ok and code == 'COURSE_FULL'

    def test_ok_when_unbounded(self):
        course = _make_course()
        ok, code, _ = course.check_enrollable()
        assert ok and code == ''
