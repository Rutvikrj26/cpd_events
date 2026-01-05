"""
Tests for integrations endpoints.

Endpoints tested:
- Recordings
- Zoom OAuth and meetings
- Email logs
"""

import pytest
from django.utils import timezone
from rest_framework import status
from unittest.mock import patch, MagicMock


# =============================================================================
# Event Recordings Tests
# =============================================================================


@pytest.mark.django_db
class TestEventRecordingViewSet:
    """Tests for organizer recording management."""

    def get_endpoint(self, event):
        return f'/api/v1/events/{event.uuid}/recordings/'

    def test_list_recordings(self, organizer_client, completed_event):
        """Organizer can list recordings for their event."""
        endpoint = self.get_endpoint(completed_event)
        response = organizer_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_update_recording_access(self, organizer_client, completed_event, organizer, db):
        """Organizer can update recording access settings."""
        from integrations.models import ZoomRecording, EmailLog
        # Create a recording
        # Create a recording
        recording = ZoomRecording.objects.create(
            event=completed_event,
            title='Test Recording',
            zoom_recording_id='rec_123', # Adding required fields if any
            zoom_meeting_id='123456789',
            recording_start=completed_event.starts_at,
            recording_end=completed_event.ends_at,
        )
        
        response = organizer_client.patch(
            f'{self.get_endpoint(completed_event)}{recording.uuid}/',
            {'is_public': True}
        )
        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# Attendee Recordings Tests
# =============================================================================


@pytest.mark.django_db  
class TestMyRecordingsViewSet:
    """Tests for attendee recording access."""

    endpoint = '/api/v1/users/me/recordings/'

    def test_list_my_recordings(self, auth_client, registration):
        """User can list recordings they have access to."""
        response = auth_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# Zoom OAuth Tests
# =============================================================================


@pytest.mark.django_db
class TestZoomOAuth:
    """Tests for Zoom OAuth endpoints."""

    def test_initiate_zoom_oauth(self, organizer_client):
        """Organizer can initiate Zoom OAuth."""
        response = organizer_client.get('/api/v1/integrations/zoom/initiate/')
        assert response.status_code == status.HTTP_200_OK
        # Should return auth URL
        assert 'url' in response.data or 'auth_url' in response.data

    @patch('accounts.services.zoom_service.complete_oauth')
    def test_zoom_callback(self, mock_complete_oauth, organizer_client, organizer, db):
        """Zoom OAuth callback is handled."""
        mock_complete_oauth.return_value = {'success': True}
        
        # Callback with authorization code
        response = organizer_client.get('/api/v1/integrations/zoom/callback/', {
            'code': 'test_auth_code',
            'state': 'test_state',
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'connected'

    def test_get_zoom_status(self, organizer_client, organizer):
        """Organizer can check Zoom connection status."""
        response = organizer_client.get('/api/v1/integrations/zoom/status/')
        assert response.status_code == status.HTTP_200_OK
        assert 'is_connected' in response.data

    def test_disconnect_zoom(self, organizer_client, mock_zoom, organizer, db):
        """Organizer can disconnect Zoom."""
        # Create a Zoom connection
        from accounts.models import ZoomConnection
        from django.utils import timezone
        ZoomConnection.objects.create(
            user=organizer,
            access_token='test_token',
            refresh_token='test_refresh',
            token_expires_at=timezone.now() + timezone.timedelta(hours=1),
            zoom_user_id='test_user_id',
        )
        
        response = organizer_client.post('/api/v1/integrations/zoom/disconnect/')
        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# Zoom Meetings Tests
# =============================================================================


@pytest.mark.django_db
class TestZoomMeetingsList:
    """Tests for Zoom meetings list."""

    endpoint = '/api/v1/integrations/zoom/meetings/'

    def test_list_zoom_meetings(self, organizer_client, organizer, db):
        """Organizer can list their Zoom meetings."""
        from accounts.models import ZoomConnection
        from django.utils import timezone
        ZoomConnection.objects.create(
            user=organizer,
            access_token='test_token',
            refresh_token='test_refresh',
            token_expires_at=timezone.now() + timezone.timedelta(hours=1),
            zoom_user_id='test_user_id',
        )
        
        response = organizer_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_attendee_cannot_list_meetings(self, auth_client):
        """Attendees cannot access Zoom meetings."""
        response = auth_client.get(self.endpoint)
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# Zoom Webhook Tests
# =============================================================================


@pytest.mark.django_db
class TestZoomWebhook:
    """Tests for Zoom webhook handling."""

    endpoint = '/api/v1/integrations/webhooks/zoom/'

    def test_url_validation(self, api_client):
        """Zoom URL validation challenge is handled."""
        data = {
            'event': 'endpoint.url_validation',
            'payload': {
                'plainToken': 'test_token',
            }
        }
        response = api_client.post(
            self.endpoint,
            data,
            format='json',
        )
        # URL validation should return the token hash
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    @patch('integrations.views.ZoomWebhookView._verify_signature')
    def test_recording_completed_event(self, mock_verify, api_client, completed_event, organizer, db):
        """Handle recording.completed event."""
        mock_verify.return_value = True
        completed_event.zoom_meeting_id = '123456789'
        completed_event.save()
        
        data = {
            'event': 'recording.completed',
            'payload': {
                'object': {
                    'id': 123456789,
                    'recording_files': [
                        {
                            'id': 'rec_123',
                            'recording_type': 'shared_screen_with_speaker_view',
                            'download_url': 'https://zoom.us/rec/download/123',
                        }
                    ]
                }
            }
        }
        response = api_client.post(
            self.endpoint,
            data,
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK

    def test_join_leave_updates_attendance_and_eligibility(self, organizer, db):
        """Join + leave webhooks update attendance and certificate eligibility."""
        from factories import EventFactory, RegistrationFactory
        from integrations.models import ZoomWebhookLog
        from integrations.tasks import process_zoom_webhook

        event = EventFactory(
            owner=organizer,
            status='published',
            zoom_meeting_id='999999',
            minimum_attendance_minutes=30,
            duration_minutes=60,
        )
        registration = RegistrationFactory(
            event=event,
            status='confirmed',
            user=None,
            email='attendee@example.com',
            full_name='Attendee Example',
        )

        join_time = timezone.now()
        leave_time = join_time + timezone.timedelta(minutes=45)

        join_log = ZoomWebhookLog.objects.create(
            webhook_id='join_1',
            event_type='meeting.participant_joined',
            event_timestamp=join_time,
            zoom_meeting_id='999999',
            zoom_meeting_uuid='uuid-1',
            payload={
                'payload': {
                    'object': {
                        'id': 999999,
                        'participant': {
                            'id': 'participant-1',
                            'user_id': 'zoom-user-1',
                            'user_name': 'Attendee Example',
                            'email': registration.email,
                            'join_time': join_time.isoformat(),
                        }
                    }
                }
            },
        )
        process_zoom_webhook(join_log.id)

        leave_log = ZoomWebhookLog.objects.create(
            webhook_id='leave_1',
            event_type='meeting.participant_left',
            event_timestamp=leave_time,
            zoom_meeting_id='999999',
            zoom_meeting_uuid='uuid-1',
            payload={
                'payload': {
                    'object': {
                        'id': 999999,
                        'participant': {
                            'id': 'participant-1',
                            'leave_time': leave_time.isoformat(),
                        }
                    }
                }
            },
        )
        process_zoom_webhook(leave_log.id)

        registration.refresh_from_db()
        assert registration.total_attendance_minutes >= 45
        assert registration.attendance_eligible is True
        assert registration.can_receive_certificate is True


# =============================================================================
# Email Log Tests
# =============================================================================


@pytest.mark.django_db
class TestEmailLogViewSet:
    """Tests for email log viewing."""

    def get_endpoint(self, event):
        return f'/api/v1/events/{event.uuid}/emails/'

    def test_list_email_logs(self, organizer_client, completed_event):
        """Organizer can view email logs for their event."""
        endpoint = self.get_endpoint(completed_event)
        response = organizer_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_attendee_cannot_view_email_logs(self, auth_client, completed_event):
        """Attendees cannot view email logs."""
        endpoint = self.get_endpoint(completed_event)
        response = auth_client.get(endpoint)
        assert response.status_code == status.HTTP_403_FORBIDDEN
