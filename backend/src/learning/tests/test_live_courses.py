"""
Regression tests for the LIVE course format and CourseSession lifecycle.
"""
import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.models import User
from learning.models import (
    Course,
    CourseEnrollment,
    CourseSession,
    CourseSessionAttendance,
)
from learning.services import build_session_ics


@pytest.fixture
def user(db):
    return User.objects.create(email='live-tester@example.com', password='password')


@pytest.fixture
def live_course(db, user):
    return Course.objects.create(
        title='Live Course',
        slug='live-course',
        format=Course.CourseFormat.LIVE,
        hybrid_completion_criteria=Course.HybridCompletionCriteria.SESSIONS_ONLY,
        created_by=user,
    )


@pytest.mark.django_db
class TestLiveCourseFormat:

    def test_live_format_choice_exists(self):
        assert ('live', 'Live (Lectures)') in Course.CourseFormat.choices

    def test_publish_live_course_without_sessions_fails(self, live_course):
        with pytest.raises(ValidationError) as excinfo:
            live_course.publish()
        assert 'sessions' in excinfo.value.message_dict

    def test_publish_live_course_with_sessions_succeeds(self, live_course):
        CourseSession.objects.create(
            course=live_course,
            title='Lecture 1',
            starts_at=timezone.now() + timezone.timedelta(days=1),
            is_published=True,
        )
        live_course.publish()
        live_course.refresh_from_db()
        assert live_course.status == Course.Status.PUBLISHED

    def test_publish_online_course_without_modules_fails(self, user):
        course = Course.objects.create(title='Empty', slug='empty', created_by=user)
        with pytest.raises(ValidationError) as excinfo:
            course.publish()
        assert 'modules' in excinfo.value.message_dict


@pytest.mark.django_db
class TestSessionsOnlyCompletionDoesNotAutoComplete:
    """Regression: live-only course with no published mandatory sessions
    used to return True from _check_session_requirements()."""

    def test_no_sessions_means_not_passed(self, user, live_course):
        enrollment = CourseEnrollment.objects.create(
            course=live_course, user=user, status=CourseEnrollment.Status.ACTIVE,
        )
        assert enrollment._check_session_requirements() is False
        assert enrollment._are_all_requirements_passed() is False

    def test_min_sessions_short_circuits_when_count_too_low(self, user):
        course = Course.objects.create(
            title='Min',
            slug='min',
            format=Course.CourseFormat.LIVE,
            hybrid_completion_criteria=Course.HybridCompletionCriteria.MIN_SESSIONS,
            min_sessions_required=3,
            created_by=user,
        )
        # Only 1 published session — required is 3
        CourseSession.objects.create(
            course=course,
            title='S1',
            starts_at=timezone.now() + timezone.timedelta(days=1),
            is_published=True,
        )
        enrollment = CourseEnrollment.objects.create(
            course=course, user=user, status=CourseEnrollment.Status.ACTIVE,
        )
        assert enrollment._check_session_requirements() is False


@pytest.mark.django_db
class TestCourseSessionLifecycle:

    def _make_session(self, live_course):
        return CourseSession.objects.create(
            course=live_course,
            title='Lecture',
            starts_at=timezone.now() + timezone.timedelta(hours=1),
            is_published=True,
        )

    def test_default_status_is_scheduled(self, live_course):
        s = self._make_session(live_course)
        assert s.status == CourseSession.Status.SCHEDULED

    def test_cancel_records_reason_and_timestamp(self, live_course):
        s = self._make_session(live_course)
        s.cancel(reason='snowstorm')
        s.refresh_from_db()
        assert s.status == CourseSession.Status.CANCELLED
        assert s.cancelled_reason == 'snowstorm'
        assert s.cancelled_at is not None

    def test_cannot_cancel_after_completed(self, live_course):
        s = self._make_session(live_course)
        s.status = CourseSession.Status.COMPLETED
        s.save()
        with pytest.raises(ValueError):
            s.cancel(reason='nope')

    def test_reschedule_resets_to_scheduled(self, live_course):
        s = self._make_session(live_course)
        new_start = timezone.now() + timezone.timedelta(days=2)
        s.reschedule(new_starts_at=new_start, new_duration_minutes=90)
        s.refresh_from_db()
        assert s.starts_at == new_start
        assert s.duration_minutes == 90
        assert s.status == CourseSession.Status.SCHEDULED

    def test_cannot_reschedule_cancelled(self, live_course):
        s = self._make_session(live_course)
        s.cancel(reason='x')
        with pytest.raises(ValueError):
            s.reschedule(new_starts_at=timezone.now())


@pytest.mark.django_db
class TestIcsBuilder:

    def test_published_session_emits_publish_method(self, live_course, user):
        s = CourseSession.objects.create(
            course=live_course,
            title='Lecture',
            starts_at=timezone.now() + timezone.timedelta(hours=1),
            is_published=True,
        )
        ics = build_session_ics(s, user=user)
        assert 'METHOD:PUBLISH' in ics
        assert 'STATUS:CONFIRMED' in ics
        assert f'UID:course-session-{s.uuid}' in ics

    def test_cancelled_session_emits_cancel_method(self, live_course, user):
        s = CourseSession.objects.create(
            course=live_course,
            title='Lecture',
            starts_at=timezone.now() + timezone.timedelta(hours=1),
            is_published=True,
        )
        s.cancel(reason='moved')
        ics = build_session_ics(s, user=user)
        assert 'METHOD:CANCEL' in ics
        assert 'STATUS:CANCELLED' in ics


@pytest.mark.django_db
class TestParticipantFieldRename:
    """The old fields (zoom_*) were renamed to participant_* on
    CourseSessionAttendance. Make sure the rename took effect and the
    eligibility helper still works."""

    def test_fields_renamed(self):
        names = {f.name for f in CourseSessionAttendance._meta.get_fields()}
        assert 'participant_id' in names
        assert 'participant_email' in names
        assert 'join_time' in names
        assert 'leave_time' in names
        assert 'zoom_user_email' not in names
        assert 'zoom_participant_id' not in names

    def test_calculate_eligibility(self, user, live_course):
        s = CourseSession.objects.create(
            course=live_course,
            title='Lecture',
            starts_at=timezone.now() + timezone.timedelta(hours=1),
            duration_minutes=60,
            minimum_attendance_percent=80,
            is_published=True,
        )
        enrollment = CourseEnrollment.objects.create(course=live_course, user=user)
        att = CourseSessionAttendance.objects.create(
            session=s, enrollment=enrollment, attendance_minutes=50,
        )
        att.calculate_eligibility()
        assert att.is_eligible is True  # 50/60 = 83% >= 80% threshold

        att.attendance_minutes = 30
        att.calculate_eligibility()
        assert att.is_eligible is False  # 30/60 = 50% < 80%
