"""
Tests for learning tasks - critical paths.
"""

from unittest.mock import patch

import pytest
from django.utils import timezone

from learning.models import Course, CourseEnrollment
from learning.tasks import (
    create_zoom_meeting_for_course,
    create_zoom_meeting_for_session,
    send_course_enrollment_confirmation,
    sync_session_attendance,
)


@pytest.mark.django_db
class TestSendCourseEnrollmentConfirmation:
    """Tests for send_course_enrollment_confirmation task."""

    @patch("learning.tasks.send_mail")
    def test_send_confirmation_success(self, mock_send_mail, organizer, user):
        """Test sending enrollment confirmation email."""
        course = Course.objects.create(
            owner=organizer,
            title="Test Course",
            status="published",
        )

        enrollment = CourseEnrollment.objects.create(
            course=course,
            user=user,
            status="active",
        )

        send_course_enrollment_confirmation(enrollment.id)

        mock_send_mail.assert_called_once()
        call_args = mock_send_mail.call_args
        assert call_args[1]["recipient_list"] == [user.email]
        assert "Test Course" in call_args[1]["subject"]

    @patch("learning.tasks.send_mail")
    def test_send_confirmation_nonexistent_enrollment(self, mock_send_mail):
        """Test handling of nonexistent enrollment."""
        send_course_enrollment_confirmation(99999)

        mock_send_mail.assert_not_called()

    @patch("learning.tasks.send_mail")
    def test_send_confirmation_handles_email_failure(self, mock_send_mail, organizer, user):
        """Test handling of email sending failure."""
        course = Course.objects.create(
            owner=organizer,
            title="Test Course",
            status="published",
        )

        enrollment = CourseEnrollment.objects.create(
            course=course,
            user=user,
            status="active",
        )

        mock_send_mail.side_effect = Exception("SMTP Error")

        # Should not raise, just log
        send_course_enrollment_confirmation(enrollment.id)


@pytest.mark.django_db
class TestCreateZoomMeetingForCourse:
    """Tests for create_zoom_meeting_for_course task."""

    @patch("accounts.services.zoom_service")
    def test_create_zoom_for_hybrid_course(self, mock_zoom_service, organizer):
        """Test creating Zoom meeting for hybrid course."""
        course = Course.objects.create(
            owner=organizer,
            title="Hybrid Course",
            status="published",
            format=Course.CourseFormat.HYBRID,
        )

        mock_zoom_service.create_meeting_for_course.return_value = {
            "success": True,
            "meeting_id": "123456789",
        }

        result = create_zoom_meeting_for_course(course.id)

        assert result is True
        mock_zoom_service.create_meeting_for_course.assert_called_once_with(course)

    @patch("accounts.services.zoom_service")
    def test_skip_non_hybrid_course(self, mock_zoom_service, organizer):
        """Test that non-hybrid courses are skipped."""
        course = Course.objects.create(
            owner=organizer,
            title="Online Course",
            status="published",
            format=Course.CourseFormat.ONLINE,
        )

        result = create_zoom_meeting_for_course(course.id)

        assert result is False
        mock_zoom_service.create_meeting_for_course.assert_not_called()

    @patch("accounts.services.zoom_service")
    def test_skip_course_with_existing_meeting(self, mock_zoom_service, organizer):
        """Test that courses with existing Zoom meetings are skipped."""
        course = Course.objects.create(
            owner=organizer,
            title="Hybrid Course",
            status="published",
            format=Course.CourseFormat.HYBRID,
            zoom_meeting_id="existing123",
        )

        result = create_zoom_meeting_for_course(course.id)

        assert result is False
        mock_zoom_service.create_meeting_for_course.assert_not_called()

    @patch("accounts.services.zoom_service")
    def test_handle_zoom_error(self, mock_zoom_service, organizer):
        """Test handling of Zoom API error."""
        course = Course.objects.create(
            owner=organizer,
            title="Hybrid Course",
            status="published",
            format=Course.CourseFormat.HYBRID,
        )

        mock_zoom_service.create_meeting_for_course.return_value = {
            "success": False,
            "error": "Zoom API Error",
        }

        result = create_zoom_meeting_for_course(course.id)

        assert result is False
        course.refresh_from_db()
        assert course.zoom_error == "Zoom API Error"
        assert course.zoom_error_at is not None

    @patch("accounts.services.zoom_service")
    def test_clear_error_on_success(self, mock_zoom_service, organizer):
        """Test that previous errors are cleared on success."""
        course = Course.objects.create(
            owner=organizer,
            title="Hybrid Course",
            status="published",
            format=Course.CourseFormat.HYBRID,
            zoom_error="Previous error",
            zoom_error_at=timezone.now(),
        )

        mock_zoom_service.create_meeting_for_course.return_value = {
            "success": True,
            "meeting_id": "123456789",
        }

        result = create_zoom_meeting_for_course(course.id)

        assert result is True
        course.refresh_from_db()
        assert course.zoom_error == ""
        assert course.zoom_error_at is None

    def test_handle_nonexistent_course(self):
        """Test handling of nonexistent course."""
        result = create_zoom_meeting_for_course(99999)
        assert result is False


@pytest.mark.django_db
class TestCreateZoomMeetingForSession:
    """Tests for create_zoom_meeting_for_session task."""

    @patch("accounts.services.zoom_service")
    def test_create_zoom_for_session(self, mock_zoom_service, organizer):
        """Test creating Zoom meeting for course session."""
        from learning.models import CourseSession

        course = Course.objects.create(
            owner=organizer,
            title="Course",
            status="published",
        )

        session = CourseSession.objects.create(
            course=course,
            title="Session 1",
            scheduled_at=timezone.now(),
            zoom_settings={"enabled": True},
        )

        mock_zoom_service.create_meeting_for_session.return_value = {
            "success": True,
            "meeting_id": "987654321",
        }

        result = create_zoom_meeting_for_session(session.id)

        assert result is True
        mock_zoom_service.create_meeting_for_session.assert_called_once_with(session)

    @patch("accounts.services.zoom_service")
    def test_skip_session_without_zoom_enabled(self, mock_zoom_service, organizer):
        """Test that sessions without Zoom enabled are skipped."""
        from learning.models import CourseSession

        course = Course.objects.create(
            owner=organizer,
            title="Course",
            status="published",
        )

        session = CourseSession.objects.create(
            course=course,
            title="Session 1",
            scheduled_at=timezone.now(),
            zoom_settings={"enabled": False},
        )

        result = create_zoom_meeting_for_session(session.id)

        assert result is False
        mock_zoom_service.create_meeting_for_session.assert_not_called()

    @patch("accounts.services.zoom_service")
    def test_skip_session_with_existing_meeting(self, mock_zoom_service, organizer):
        """Test that sessions with existing meetings are skipped."""
        from learning.models import CourseSession

        course = Course.objects.create(
            owner=organizer,
            title="Course",
            status="published",
        )

        session = CourseSession.objects.create(
            course=course,
            title="Session 1",
            scheduled_at=timezone.now(),
            zoom_meeting_id="existing789",
            zoom_settings={"enabled": True},
        )

        result = create_zoom_meeting_for_session(session.id)

        assert result is False
        mock_zoom_service.create_meeting_for_session.assert_not_called()

    @patch("accounts.services.zoom_service")
    def test_handle_zoom_error_for_session(self, mock_zoom_service, organizer):
        """Test handling of Zoom error for session."""
        from learning.models import CourseSession

        course = Course.objects.create(
            owner=organizer,
            title="Course",
            status="published",
        )

        session = CourseSession.objects.create(
            course=course,
            title="Session 1",
            scheduled_at=timezone.now(),
            zoom_settings={"enabled": True},
        )

        mock_zoom_service.create_meeting_for_session.return_value = {
            "success": False,
            "error": "Session API Error",
        }

        result = create_zoom_meeting_for_session(session.id)

        assert result is False
        session.refresh_from_db()
        assert session.zoom_error == "Session API Error"

    def test_handle_nonexistent_session(self):
        """Test handling of nonexistent session."""
        result = create_zoom_meeting_for_session(99999)
        assert result is False


@pytest.mark.django_db
class TestSyncSessionAttendance:
    """Tests for sync_session_attendance task."""

    @patch("integrations.services.attendance_matcher")
    def test_sync_attendance_success(self, mock_attendance_matcher, organizer):
        """Test successful attendance sync."""
        from learning.models import CourseSession

        course = Course.objects.create(
            owner=organizer,
            title="Course",
            status="published",
        )

        session = CourseSession.objects.create(
            course=course,
            title="Session 1",
            scheduled_at=timezone.now(),
        )

        mock_attendance_matcher.match_session_attendance.return_value = {
            "matched": 15,
            "unmatched": 2,
        }

        result = sync_session_attendance(session.id)

        assert result == {"matched": 15, "unmatched": 2}
        mock_attendance_matcher.match_session_attendance.assert_called_once_with(session)

    def test_sync_attendance_nonexistent_session(self):
        """Test handling of nonexistent session."""
        result = sync_session_attendance(99999)
        assert result == {}
