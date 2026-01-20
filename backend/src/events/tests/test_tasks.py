"""
Comprehensive tests for event background tasks.
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from events.models import Event
from events.tasks import (
    auto_complete_events,
    create_zoom_meeting,
    notify_event_cancelled,
    send_event_reminders,
    sync_zoom_attendance,
    update_event_counts,
)
from integrations.models import EmailLog
from registrations.models import Registration


@pytest.mark.django_db
class TestSendEventReminders:
    """Tests for send_event_reminders task."""

    @patch('integrations.services.email_service')
    def test_send_reminders_for_upcoming_events(self, mock_email_service, organizer):
        """Test sending reminders for events starting in 24 hours."""
        # Create event starting in 24 hours
        event = Event.objects.create(
            owner=organizer,
            title="Upcoming Event",
            status="published",
            starts_at=timezone.now() + timedelta(hours=24),
        )

        # Create confirmed registrations
        user1 = pytest.helpers.create_user(email="user1@test.com", full_name="User One")
        user2 = pytest.helpers.create_user(email="user2@test.com", full_name="User Two")

        Registration.objects.create(event=event, user=user1, email=user1.email, status="confirmed", full_name=user1.full_name)
        Registration.objects.create(event=event, user=user2, email=user2.email, status="confirmed", full_name=user2.full_name)

        # Run task
        count = send_event_reminders(hours_before=24)

        assert count == 2
        assert mock_email_service.send_email.call_count == 2

    @patch('integrations.services.email_service')
    def test_no_reminders_for_past_events(self, mock_email_service, organizer):
        """Test that no reminders are sent for past events."""
        # Create past event
        Event.objects.create(
            owner=organizer,
            title="Past Event",
            status="completed",
            starts_at=timezone.now() - timedelta(days=1),
        )

        count = send_event_reminders(hours_before=24)

        assert count == 0
        mock_email_service.send_email.assert_not_called()

    @patch('integrations.services.email_service')
    def test_no_reminders_for_draft_events(self, mock_email_service, organizer, user):
        """Test that no reminders are sent for draft events."""
        # Create draft event
        event = Event.objects.create(
            owner=organizer,
            title="Draft Event",
            status="draft",
            starts_at=timezone.now() + timedelta(hours=24),
        )

        Registration.objects.create(event=event, user=user, email=user.email, status="confirmed", full_name=user.full_name)

        count = send_event_reminders(hours_before=24)

        assert count == 0
        mock_email_service.send_email.assert_not_called()

    @patch('integrations.services.email_service')
    def test_no_reminders_for_cancelled_registrations(self, mock_email_service, organizer, user):
        """Test that no reminders are sent to cancelled registrations."""
        event = Event.objects.create(
            owner=organizer,
            title="Event",
            status="published",
            starts_at=timezone.now() + timedelta(hours=24),
        )

        Registration.objects.create(event=event, user=user, email=user.email, status="cancelled", full_name=user.full_name)

        count = send_event_reminders(hours_before=24)

        assert count == 0
        mock_email_service.send_email.assert_not_called()

    @patch('integrations.services.email_service')
    def test_reminders_with_custom_hours_before(self, mock_email_service, organizer, user):
        """Test sending reminders with custom hours_before parameter."""
        event = Event.objects.create(
            owner=organizer,
            title="Event",
            status="published",
            starts_at=timezone.now() + timedelta(hours=2),
        )

        Registration.objects.create(event=event, user=user, email=user.email, status="confirmed", full_name=user.full_name)

        count = send_event_reminders(hours_before=2)

        assert count == 1
        mock_email_service.send_email.assert_called_once()


@pytest.mark.django_db
class TestAutoCompleteEvents:
    """Tests for auto_complete_events task."""

    def test_auto_complete_live_events_that_ended(self, organizer):
        """Test that live events are completed after they end."""
        # Create event that ended 1 hour ago
        event = Event.objects.create(
            owner=organizer,
            title="Live Event",
            status="live",
            starts_at=timezone.now() - timedelta(hours=3),
            duration_minutes=60,
        )

        count = auto_complete_events()

        assert count == 1
        event.refresh_from_db()
        assert event.status == Event.Status.COMPLETED

    def test_no_completion_for_ongoing_events(self, organizer):
        """Test that ongoing events are not completed."""
        # Create event that is currently happening
        Event.objects.create(
            owner=organizer,
            title="Ongoing Event",
            status="live",
            starts_at=timezone.now() - timedelta(minutes=30),
            duration_minutes=120,
        )

        count = auto_complete_events()

        assert count == 0

    def test_no_completion_for_events_just_ended(self, organizer):
        """Test that events just ended (less than 30 min ago) are not completed."""
        # Create event that ended 10 minutes ago
        Event.objects.create(
            owner=organizer,
            title="Recently Ended Event",
            status="live",
            starts_at=timezone.now() - timedelta(hours=2),
            duration_minutes=110,
        )

        count = auto_complete_events()

        assert count == 0

    def test_no_completion_for_already_completed_events(self, organizer):
        """Test that already completed events are not processed again."""
        Event.objects.create(
            owner=organizer,
            title="Completed Event",
            status="completed",
            starts_at=timezone.now() - timedelta(days=1),
        )

        count = auto_complete_events()

        assert count == 0


@pytest.mark.django_db
class TestCreateZoomMeeting:
    """Tests for create_zoom_meeting task."""

    @patch('accounts.services.zoom_service')
    def test_create_zoom_meeting_success(self, mock_zoom_service, organizer):
        """Test successful Zoom meeting creation."""
        event = Event.objects.create(
            owner=organizer,
            title="Test Event",
            status="published",
            starts_at=timezone.now() + timedelta(days=1),
        )

        mock_zoom_service.create_meeting.return_value = {
            'success': True,
            'meeting_id': '123456789',
            'join_url': 'https://zoom.us/j/123456789',
        }

        result = create_zoom_meeting(event.id)

        assert result is True
        mock_zoom_service.create_meeting.assert_called_once_with(event)

    @patch('accounts.services.zoom_service')
    def test_create_zoom_meeting_failure(self, mock_zoom_service, organizer):
        """Test Zoom meeting creation failure."""
        event = Event.objects.create(
            owner=organizer,
            title="Test Event",
            status="published",
            starts_at=timezone.now() + timedelta(days=1),
        )

        mock_zoom_service.create_meeting.return_value = {
            'success': False,
            'error': 'Zoom API error',
        }

        result = create_zoom_meeting(event.id)

        assert result is False
        event.refresh_from_db()
        assert event.zoom_error == 'Zoom API error'
        assert event.zoom_error_at is not None

    @patch('accounts.services.zoom_service')
    def test_create_zoom_meeting_clears_previous_error(self, mock_zoom_service, organizer):
        """Test that successful creation clears previous errors."""
        event = Event.objects.create(
            owner=organizer,
            title="Test Event",
            status="published",
            starts_at=timezone.now() + timedelta(days=1),
            zoom_error="Previous error",
            zoom_error_at=timezone.now(),
        )

        mock_zoom_service.create_meeting.return_value = {'success': True}

        result = create_zoom_meeting(event.id)

        assert result is True
        event.refresh_from_db()
        assert event.zoom_error == ''
        assert event.zoom_error_at is None

    def test_create_zoom_meeting_nonexistent_event(self):
        """Test handling of nonexistent event."""
        result = create_zoom_meeting(99999)
        assert result is False


@pytest.mark.django_db
class TestSyncZoomAttendance:
    """Tests for sync_zoom_attendance task."""

    @patch('integrations.services.attendance_matcher')
    def test_sync_attendance_success(self, mock_attendance_matcher, organizer):
        """Test successful attendance sync."""
        event = Event.objects.create(
            owner=organizer,
            title="Test Event",
            status="live",
            starts_at=timezone.now(),
        )

        mock_attendance_matcher.match_attendance.return_value = {
            'matched': 10,
            'unmatched': 2,
        }

        result = sync_zoom_attendance(event.id)

        assert result == {'matched': 10, 'unmatched': 2}
        mock_attendance_matcher.match_attendance.assert_called_once_with(event)

    def test_sync_attendance_nonexistent_event(self):
        """Test handling of nonexistent event."""
        result = sync_zoom_attendance(99999)
        assert result == {}


@pytest.mark.django_db
class TestUpdateEventCounts:
    """Tests for update_event_counts task."""

    def test_update_counts_success(self, organizer, user):
        """Test successful count update."""
        event = Event.objects.create(
            owner=organizer,
            title="Test Event",
            status="published",
            starts_at=timezone.now() + timedelta(days=1),
            max_attendees=100,
        )

        # Create some registrations
        Registration.objects.create(event=event, user=user, email=user.email, status="confirmed", full_name=user.full_name)

        result = update_event_counts(event.id)

        assert result is True
        event.refresh_from_db()
        assert event.registration_count > 0

    def test_update_counts_nonexistent_event(self):
        """Test handling of nonexistent event."""
        result = update_event_counts(99999)
        assert result is False


@pytest.mark.django_db
class TestNotifyEventCancelled:
    """Tests for notify_event_cancelled task."""

    @patch('integrations.tasks.send_email')
    def test_notify_cancelled_event(self, mock_send_email, organizer, user):
        """Test notifying registrants of event cancellation."""
        event = Event.objects.create(
            owner=organizer,
            title="Cancelled Event",
            status="cancelled",
            starts_at=timezone.now() + timedelta(days=1),
        )

        # Create confirmed registrations
        reg1 = Registration.objects.create(
            event=event,
            user=user,
            email=user.email,
            status="confirmed",
            full_name=user.full_name,
        )

        user2 = pytest.helpers.create_user(email="user2@test.com", full_name="User Two")
        reg2 = Registration.objects.create(
            event=event,
            user=user2,
            email=user2.email,
            status="confirmed",
            full_name=user2.full_name,
        )

        count = notify_event_cancelled(event.id)

        assert count == 2
        assert EmailLog.objects.count() == 2
        assert mock_send_email.delay.call_count == 2

    @patch('integrations.tasks.send_email')
    def test_no_notification_for_non_cancelled_event(self, mock_send_email, organizer, user):
        """Test that notifications are not sent for non-cancelled events."""
        event = Event.objects.create(
            owner=organizer,
            title="Published Event",
            status="published",
            starts_at=timezone.now() + timedelta(days=1),
        )

        Registration.objects.create(event=event, user=user, email=user.email, status="confirmed", full_name=user.full_name)

        count = notify_event_cancelled(event.id)

        assert count == 0
        mock_send_email.delay.assert_not_called()

    @patch('integrations.tasks.send_email')
    def test_only_confirmed_registrations_notified(self, mock_send_email, organizer, user):
        """Test that only confirmed registrations are notified."""
        event = Event.objects.create(
            owner=organizer,
            title="Cancelled Event",
            status="cancelled",
            starts_at=timezone.now() + timedelta(days=1),
        )

        Registration.objects.create(event=event, user=user, email=user.email, status="confirmed", full_name=user.full_name)

        user2 = pytest.helpers.create_user(email="user2@test.com", full_name="User Two")
        Registration.objects.create(event=event, user=user2, email=user2.email, status="waitlisted", full_name=user2.full_name)

        count = notify_event_cancelled(event.id)

        assert count == 1
        assert mock_send_email.delay.call_count == 1

    def test_notify_cancelled_nonexistent_event(self):
        """Test handling of nonexistent event."""
        count = notify_event_cancelled(99999)
        assert count == 0


@pytest.mark.django_db
@pytest.mark.skip(reason="EventInvitation model does not exist - likely planned feature")
class TestSendInvitations:
    """Tests for send_invitations task - SKIPPED (EventInvitation model not implemented)."""

    def test_placeholder(self):
        """Placeholder test."""
        pass


# Add helper for creating users if not already available
@pytest.fixture(autouse=True)
def setup_helpers():
    """Setup pytest helpers."""
    if not hasattr(pytest, 'helpers'):
        pytest.helpers = type('Helpers', (), {})()

    def create_user(email, full_name, password="testpass123"):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.create_user(email=email, password=password, full_name=full_name)

    pytest.helpers.create_user = create_user
