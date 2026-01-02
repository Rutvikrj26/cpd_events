import pytest
from unittest.mock import patch, MagicMock
from events.models import Event
from events.signals import trigger_zoom_creation

@pytest.mark.django_db
class TestZoomRetrySignal:
    def test_signal_triggers_task_on_update(self, organizer, db):
        """Test that updating an event with zoom settings triggers the creation task."""
        
        # Create event without meeting ID but with settings (simulating failed creation)
        event = Event.objects.create(
            owner=organizer,
            title="Test Zoom Retry",
            starts_at="2024-01-01T12:00:00Z",
            zoom_settings={'enabled': True},
            zoom_meeting_id=""
        )
        
        # Mock the celery task
        with patch('events.tasks.create_zoom_meeting.delay') as mock_task:
            # Update the event (simulating what the frontend retry button will do)
            # We just need to save() it to trigger the signal
            event.save()
            
            # Verify task was called
            mock_task.assert_called_once_with(event.id)

    def test_signal_does_not_trigger_if_meeting_exists(self, organizer, db):
        """Test that signal ignores events that already have a meeting ID."""
        
        event = Event.objects.create(
            owner=organizer,
            title="Test Existing Zoom",
            starts_at="2024-01-01T12:00:00Z",
            zoom_settings={'enabled': True},
            zoom_meeting_id="123456789"
        )
        
        with patch('events.tasks.create_zoom_meeting.delay') as mock_task:
            event.save()
            mock_task.assert_not_called()

    def test_signal_does_not_trigger_if_zoom_disabled(self, organizer, db):
        """Test that signal ignores events with zoom disabled."""
        
        event = Event.objects.create(
            owner=organizer,
            title="Test No Zoom",
            starts_at="2024-01-01T12:00:00Z",
            zoom_settings={'enabled': False},
            zoom_meeting_id=""
        )
        
        with patch('events.tasks.create_zoom_meeting.delay') as mock_task:
            event.save()
            mock_task.assert_not_called()
