"""
Tests for Virtual/Live Course fields (Phase 5).
"""

from django.test import TestCase

from accounts.models import User
from learning.models import Course


class TestCourseVirtualFields(TestCase):
    """Test live session fields on Course model."""

    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='password')

    def test_live_session_fields_exist(self):
        """Verify live session scheduling fields are present."""
        from django.utils import timezone

        start_time = timezone.now()
        end_time = start_time + timezone.timedelta(hours=2)

        course = Course.objects.create(
            title='Hybrid Course',
            slug='hybrid-course',
            created_by=self.user,
            format=Course.CourseFormat.HYBRID,
            live_session_start=start_time,
            live_session_end=end_time,
            live_session_timezone='America/New_York',
        )

        self.assertEqual(course.format, 'hybrid')
        self.assertEqual(course.live_session_start, start_time)
        self.assertEqual(course.live_session_end, end_time)
        self.assertEqual(course.live_session_timezone, 'America/New_York')

    def test_live_session_fields_optional(self):
        """Live session fields should be optional (blank=True)."""
        course = Course.objects.create(
            title='Self-Paced Course',
            slug='self-paced-course',
            created_by=self.user,
        )

        self.assertIsNone(course.live_session_start)
        self.assertIsNone(course.live_session_end)
        self.assertEqual(course.live_session_timezone, 'UTC')  # Default
