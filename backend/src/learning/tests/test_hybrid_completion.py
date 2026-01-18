import pytest
from django.utils import timezone

from accounts.models import User
from learning.models import (
    Course,
    CourseEnrollment,
    CourseSession,
    CourseSessionAttendance,
)
from organizations.models import Organization


@pytest.mark.django_db
class TestHybridCompletion:

    def setup_method(self):
        self.user = User.objects.create(email='test@example.com', password='password')
        self.org = Organization.objects.create(name="Test Org", slug="test-org")

    def test_completion_modules_only(self):
        """Test completion when only modules are required."""
        course = Course.objects.create(
            title="Modules Only Course",
            slug="modules-only",
            organization=self.org,
            format='hybrid',
            hybrid_completion_criteria='modules_only'
        )
        enrollment = CourseEnrollment.objects.create(course=course, user=self.user, progress_percent=100)

        # Should be complete even without session attendance
        assert enrollment._are_all_requirements_passed() is True

    def test_completion_sessions_only(self):
        """Test completion when only sessions are required."""
        course = Course.objects.create(
            title="Sessions Only Course",
            slug="sessions-only",
            organization=self.org,
            format='hybrid',
            hybrid_completion_criteria='sessions_only'
        )
        session = CourseSession.objects.create(
            course=course,
            title="Session 1",
            starts_at=timezone.now(),
            is_mandatory=True,
            is_published=True
        )
        enrollment = CourseEnrollment.objects.create(course=course, user=self.user, progress_percent=0)

        # Not complete initially
        assert enrollment._are_all_requirements_passed() is False

        # Attend session
        CourseSessionAttendance.objects.create(session=session, enrollment=enrollment, is_eligible=True)

        # Should be complete
        assert enrollment._are_all_requirements_passed() is True

    def test_completion_both(self):
        """Test completion when both modules and sessions are required."""
        course = Course.objects.create(
            title="Both Course",
            slug="both-course",
            organization=self.org,
            format='hybrid',
            hybrid_completion_criteria='both'
        )
        session = CourseSession.objects.create(
            course=course,
            title="Session 1",
            starts_at=timezone.now(),
            is_mandatory=True,
            is_published=True
        )
        enrollment = CourseEnrollment.objects.create(course=course, user=self.user, progress_percent=100)

        # Modules done, but session not attended -> False
        assert enrollment._are_all_requirements_passed() is False

        # Attend session
        CourseSessionAttendance.objects.create(session=session, enrollment=enrollment, is_eligible=True)

        # Now both done -> True
        assert enrollment._are_all_requirements_passed() is True

    def test_completion_min_sessions(self):
        """Test completion with minimum number of sessions."""
        course = Course.objects.create(
            title="Min Sessions Course",
            slug="min-sessions",
            organization=self.org,
            format='hybrid',
            hybrid_completion_criteria='min_sessions',
            min_sessions_required=2
        )

        # 3 sessions available, none mandatory
        item1 = CourseSession.objects.create(course=course, title="S1", starts_at=timezone.now(), is_mandatory=False, is_published=True)
        item2 = CourseSession.objects.create(course=course, title="S2", starts_at=timezone.now(), is_mandatory=False, is_published=True)
        item3 = CourseSession.objects.create(course=course, title="S3", starts_at=timezone.now(), is_mandatory=False, is_published=True)
        sessions = [item1, item2, item3]

        enrollment = CourseEnrollment.objects.create(course=course, user=self.user, progress_percent=100)

        # 0 sessions attended -> False
        assert enrollment._are_all_requirements_passed() is False

        # 1 session attended -> False
        CourseSessionAttendance.objects.create(session=sessions[0], enrollment=enrollment, is_eligible=True)
        assert enrollment._are_all_requirements_passed() is False

        # 2 sessions attended -> True
        CourseSessionAttendance.objects.create(session=sessions[1], enrollment=enrollment, is_eligible=True)
        assert enrollment._are_all_requirements_passed() is True

    def test_min_sessions_overrides_mandatory(self):
        """Test that min_sessions criteria overrides individual session mandatory flags."""
        course = Course.objects.create(
            title="Min Sessions Override",
            slug="min-sessions-override",
            organization=self.org,
            format='hybrid',
            hybrid_completion_criteria='min_sessions',
            min_sessions_required=1
        )

        # 2 sessions, BOTH MANDATORY (default is usually mandatory)
        s1 = CourseSession.objects.create(course=course, title="S1", starts_at=timezone.now(), is_mandatory=True, is_published=True)
        s2 = CourseSession.objects.create(course=course, title="S2", starts_at=timezone.now(), is_mandatory=True, is_published=True)

        enrollment = CourseEnrollment.objects.create(course=course, user=self.user, progress_percent=100)

        # Attend S1 only
        CourseSessionAttendance.objects.create(session=s1, enrollment=enrollment, is_eligible=True)

        # Should be TRUE because we met min_sessions=1, ignoring that S2 is mandatory/missing
        assert enrollment._are_all_requirements_passed() is True
