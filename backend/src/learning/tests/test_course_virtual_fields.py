"""
Tests for Virtual/Live Course fields (Phase 5).
"""

from django.test import TestCase

from accounts.models import User
from billing.models import Subscription
from learning.models import Course


class TestCourseVirtualFields(TestCase):
    """Test the new Zoom and live session fields on Course model."""

    def setUp(self):
        self.user = User.objects.create_user(email="test@example.com", password="password")
        Subscription.objects.update_or_create(
            user=self.user,
            defaults={"plan": Subscription.Plan.LMS, "status": Subscription.Status.ACTIVE},
        )

    def test_zoom_fields_exist(self):
        """Verify Zoom fields are present on Course model."""
        course = Course.objects.create(
            title="Test Course",
            slug="test-course",
            owner=self.user,
            zoom_meeting_id="123456789",
            zoom_meeting_url="https://zoom.us/j/123456789",
            zoom_meeting_password="abc123",
        )

        self.assertEqual(course.zoom_meeting_id, "123456789")
        self.assertEqual(course.zoom_meeting_url, "https://zoom.us/j/123456789")
        self.assertEqual(course.zoom_meeting_password, "abc123")

    def test_live_session_fields_exist(self):
        """Verify live session scheduling fields are present."""
        from django.utils import timezone

        start_time = timezone.now()
        end_time = start_time + timezone.timedelta(hours=2)

        course = Course.objects.create(
            title="Hybrid Course",
            slug="hybrid-course",
            owner=self.user,
            format=Course.CourseFormat.HYBRID,
            live_session_start=start_time,
            live_session_end=end_time,
            live_session_timezone="America/New_York",
        )

        self.assertEqual(course.format, "hybrid")
        self.assertEqual(course.live_session_start, start_time)
        self.assertEqual(course.live_session_end, end_time)
        self.assertEqual(course.live_session_timezone, "America/New_York")

    def test_zoom_fields_optional(self):
        """Zoom fields should be optional (blank=True)."""
        course = Course.objects.create(
            title="Self-Paced Course",
            slug="self-paced-course",
            owner=self.user,
        )

        # All zoom fields should default to empty
        self.assertEqual(course.zoom_meeting_id, "")
        self.assertEqual(course.zoom_meeting_url, "")
        self.assertEqual(course.zoom_meeting_password, "")
        self.assertIsNone(course.live_session_start)
        self.assertIsNone(course.live_session_end)
        self.assertEqual(course.live_session_timezone, "UTC")  # Default
