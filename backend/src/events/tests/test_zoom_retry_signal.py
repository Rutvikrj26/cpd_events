from unittest.mock import patch

import pytest

from events.models import Event


@pytest.mark.django_db
class TestZoomRetrySignal:
    def test_signal_triggers_task_on_update(self, organizer, db):
        """Test that updating an event with zoom settings triggers the creation task."""
        # Mock the celery task where it's used (in signals module, not tasks module)
        with patch('events.signals.create_zoom_meeting') as mock_task:
            # Create event without meeting ID but with settings (simulating failed creation)
            event = Event.objects.create(
                owner=organizer,
                title="Test Zoom Retry",
                starts_at="2024-01-01T12:00:00Z",
                zoom_settings={'enabled': True},
                zoom_meeting_id="",
            )

            # Reset mock to not count the creation call
            mock_task.delay.reset_mock()

            # Update the event (simulating what the frontend retry button will do)
            # We just need to save() it to trigger the signal
            event.save()

            # Verify task was called
            mock_task.delay.assert_called_once_with(event.id)

    def test_signal_does_not_trigger_if_meeting_exists(self, organizer, db):
        """Test that signal ignores events that already have a meeting ID."""
        with patch('events.signals.create_zoom_meeting') as mock_task:
            event = Event.objects.create(
                owner=organizer,
                title="Test Existing Zoom",
                starts_at="2024-01-01T12:00:00Z",
                zoom_settings={'enabled': True},
                zoom_meeting_id="123456789",
            )

            mock_task.delay.assert_not_called()

    def test_signal_does_not_trigger_if_zoom_disabled(self, organizer, db):
        """Test that signal ignores events with zoom disabled."""
        with patch('events.signals.create_zoom_meeting') as mock_task:
            event = Event.objects.create(
                owner=organizer,
                title="Test No Zoom",
                starts_at="2024-01-01T12:00:00Z",
                zoom_settings={'enabled': False},
                zoom_meeting_id="",
            )

            mock_task.delay.assert_not_called()

