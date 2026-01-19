"""
Tests for Course Zoom meeting auto-creation.

Tests cover:
- Signal triggering for hybrid courses
- Task execution and error handling
- ZoomService.create_meeting_for_course method
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from learning.models import Course


@pytest.mark.django_db
class TestCourseZoomSignal:
    """Test signal that triggers Zoom meeting creation for hybrid courses."""

    def test_signal_triggers_on_hybrid_course_with_zoom_enabled(self, organizer, db):
        """Test that creating a hybrid course with Zoom enabled triggers the task."""
        with patch('learning.signals.create_zoom_meeting_for_course') as mock_task:
            course = Course.objects.create(
                title='Hybrid Course',
                owner=organizer,
                format=Course.CourseFormat.HYBRID,
                zoom_settings={'enabled': True},
                live_session_start=timezone.now() + timedelta(days=7),
                live_session_end=timezone.now() + timedelta(days=7, hours=2),
            )

            mock_task.delay.assert_called_once_with(course.id)

    def test_signal_does_not_trigger_for_online_course(self, organizer, db):
        """Test that online (self-paced) courses don't trigger Zoom creation."""
        with patch('learning.signals.create_zoom_meeting_for_course') as mock_task:
            Course.objects.create(
                title='Online Course',
                owner=organizer,
                format=Course.CourseFormat.ONLINE,
                zoom_settings={'enabled': True},
            )

            mock_task.delay.assert_not_called()

    def test_signal_does_not_trigger_if_zoom_disabled(self, organizer, db):
        """Test that signal ignores courses with Zoom disabled."""
        with patch('learning.signals.create_zoom_meeting_for_course') as mock_task:
            Course.objects.create(
                title='Hybrid No Zoom',
                owner=organizer,
                format=Course.CourseFormat.HYBRID,
                zoom_settings={'enabled': False},
                live_session_start=timezone.now() + timedelta(days=7),
            )

            mock_task.delay.assert_not_called()

    def test_signal_does_not_trigger_if_meeting_already_exists(self, organizer, db):
        """Test that signal skips courses that already have a meeting ID."""
        with patch('learning.signals.create_zoom_meeting_for_course') as mock_task:
            Course.objects.create(
                title='Existing Zoom Course',
                owner=organizer,
                format=Course.CourseFormat.HYBRID,
                zoom_settings={'enabled': True},
                zoom_meeting_id='123456789',
                live_session_start=timezone.now() + timedelta(days=7),
            )

            mock_task.delay.assert_not_called()

    def test_signal_does_not_trigger_without_session_start(self, organizer, db):
        """Test that signal skips if no live_session_start is set."""
        with patch('learning.signals.create_zoom_meeting_for_course') as mock_task:
            Course.objects.create(
                title='No Session Time',
                owner=organizer,
                format=Course.CourseFormat.HYBRID,
                zoom_settings={'enabled': True},
                # No live_session_start
            )

            mock_task.delay.assert_not_called()

    def test_signal_triggers_on_update_retry(self, organizer, db):
        """Test that updating a course triggers retry for failed Zoom creation."""
        with patch('learning.signals.create_zoom_meeting_for_course') as mock_task:
            # Create without signal triggering (no zoom_settings)
            course = Course.objects.create(
                title='Retry Course',
                owner=organizer,
                format=Course.CourseFormat.HYBRID,
                live_session_start=timezone.now() + timedelta(days=7),
            )

            mock_task.delay.reset_mock()

            # Enable zoom (simulating retry)
            course.zoom_settings = {'enabled': True}
            course.save()

            mock_task.delay.assert_called_once_with(course.id)

    def test_signal_skips_recursive_zoom_field_updates(self, organizer, db):
        """Test that signal doesn't trigger infinite recursion on zoom field updates."""
        with patch('learning.signals.create_zoom_meeting_for_course') as mock_task:
            course = Course.objects.create(
                title='Recursive Test',
                owner=organizer,
                format=Course.CourseFormat.HYBRID,
                zoom_settings={'enabled': True},
                live_session_start=timezone.now() + timedelta(days=7),
            )

            mock_task.delay.reset_mock()

            # Simulate task updating zoom fields
            course.zoom_meeting_id = '123456789'
            course.save(update_fields=['zoom_meeting_id', 'updated_at'])

            # Should not trigger again
            mock_task.delay.assert_not_called()


@pytest.mark.django_db
class TestCourseZoomTask:
    """Test the create_zoom_meeting_for_course task."""

    def test_task_creates_meeting_successfully(self, organizer, db):
        """Test successful Zoom meeting creation."""
        from learning.tasks import create_zoom_meeting_for_course

        course = Course.objects.create(
            title='Task Test Course',
            owner=organizer,
            format=Course.CourseFormat.HYBRID,
            zoom_settings={'enabled': True},
            live_session_start=timezone.now() + timedelta(days=7),
        )

        mock_result = {
            'success': True,
            'meeting': {
                'id': '987654321',
                'uuid': 'abc123',
                'join_url': 'https://zoom.us/j/987654321',
                'start_url': 'https://zoom.us/s/987654321',
                'password': 'test123',
            },
        }

        with patch('accounts.services.zoom_service.create_meeting_for_course', return_value=mock_result):
            result = create_zoom_meeting_for_course(course.id)

            assert result is True


    def test_task_handles_non_hybrid_course(self, organizer, db):
        """Test that task returns False for non-hybrid courses."""
        from learning.tasks import create_zoom_meeting_for_course

        course = Course.objects.create(
            title='Online Course',
            owner=organizer,
            format=Course.CourseFormat.ONLINE,
        )

        result = create_zoom_meeting_for_course(course.id)
        assert result is False

    def test_task_handles_existing_meeting(self, organizer, db):
        """Test that task returns False if meeting already exists."""
        from learning.tasks import create_zoom_meeting_for_course

        course = Course.objects.create(
            title='Existing Meeting Course',
            owner=organizer,
            format=Course.CourseFormat.HYBRID,
            zoom_meeting_id='existing123',
        )

        result = create_zoom_meeting_for_course(course.id)
        assert result is False

    def test_task_handles_nonexistent_course(self, db):
        """Test that task returns False for non-existent course."""
        from learning.tasks import create_zoom_meeting_for_course

        result = create_zoom_meeting_for_course(99999)
        assert result is False

    def test_task_stores_error_on_failure(self, organizer, db):
        """Test that task stores error when Zoom creation fails."""
        from learning.tasks import create_zoom_meeting_for_course

        course = Course.objects.create(
            title='Error Test Course',
            owner=organizer,
            format=Course.CourseFormat.HYBRID,
            zoom_settings={'enabled': True},
            live_session_start=timezone.now() + timedelta(days=7),
        )

        mock_result = {
            'success': False,
            'error': 'No Zoom connection found',
        }

        with patch('accounts.services.zoom_service.create_meeting_for_course', return_value=mock_result):
            result = create_zoom_meeting_for_course(course.id)

            assert result is False

            course.refresh_from_db()
            assert course.zoom_error == 'No Zoom connection found'
            assert course.zoom_error_at is not None



@pytest.mark.django_db
class TestZoomServiceCourse:
    """Test ZoomService.create_meeting_for_course method."""

    def test_creates_meeting_with_correct_duration(self, organizer, db):
        """Test that duration is calculated from session times."""
        from accounts.models import ZoomConnection
        from accounts.services import zoom_service

        course = Course.objects.create(
            title='Duration Test',
            owner=organizer,
            format=Course.CourseFormat.HYBRID,
            live_session_start=timezone.now() + timedelta(days=7),
            live_session_end=timezone.now() + timedelta(days=7, hours=3),  # 3 hour session
            live_session_timezone='America/New_York',
        )

        mock_connection = MagicMock(spec=ZoomConnection)

        with (
            patch.object(ZoomConnection.objects, 'get', return_value=mock_connection),
            patch.object(zoom_service, 'get_access_token', return_value='fake_token'),
            patch.object(zoom_service, '_make_zoom_request') as mock_request,
        ):
            mock_request.return_value = {
                'success': True,
                'data': {
                    'id': '123',
                    'uuid': 'abc',
                    'join_url': 'https://zoom.us/j/123',
                    'start_url': 'https://zoom.us/s/123',
                    'password': 'pass',
                },
            }

            result = zoom_service.create_meeting_for_course(course)

            assert result['success'] is True
            # Verify duration was calculated (3 hours = 180 minutes)
            call_args = mock_request.call_args
            payload = call_args[0][3]  # 4th positional arg is payload
            assert payload['duration'] == 180

    def test_returns_error_if_no_owner(self, organizer, db):
        """Test that method returns error if course has no creator."""
        from accounts.services import zoom_service

        course = Course.objects.create(
            title='No Owner Test',
            owner=None,
            format=Course.CourseFormat.HYBRID,
            live_session_start=timezone.now() + timedelta(days=7),
        )

        result = zoom_service.create_meeting_for_course(course)

        assert result['success'] is False
        assert 'no creator' in result['error'].lower()

    def test_returns_error_if_no_zoom_connection(self, organizer, db):
        """Test that method returns error if owner has no Zoom connection."""
        from accounts.services import zoom_service

        course = Course.objects.create(
            title='No Zoom Connection',
            owner=organizer,
            format=Course.CourseFormat.HYBRID,
            live_session_start=timezone.now() + timedelta(days=7),
        )

        result = zoom_service.create_meeting_for_course(course)

        assert result['success'] is False
        assert 'zoom account' in result['error'].lower()

    def test_returns_error_if_no_session_start(self, organizer, db):
        """Test that method returns error if no live_session_start."""
        from accounts.models import ZoomConnection
        from accounts.services import zoom_service

        course = Course.objects.create(
            title='No Session Start',
            owner=organizer,
            format=Course.CourseFormat.HYBRID,
            # No live_session_start
        )

        mock_connection = MagicMock(spec=ZoomConnection)

        with (
            patch.object(ZoomConnection.objects, 'get', return_value=mock_connection),
            patch.object(zoom_service, 'get_access_token', return_value='fake_token'),
        ):
            result = zoom_service.create_meeting_for_course(course)

            assert result['success'] is False
            assert 'start time' in result['error'].lower()
