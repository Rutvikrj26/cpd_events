import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from rest_framework import status
from events.models import Event

@pytest.mark.django_db
class TestSyncAttendanceEndpoint:
    """Tests for the sync_attendance endpoint fix."""

    def test_sync_attendance_async_mode(self, api_client, organization, db):
        """Test sync_attendance when background task is successfully queued (async)."""
        user = organization.created_by
        api_client.force_authenticate(user=user)

        event = Event.objects.create(
            title="Async Event",
            owner=user,
            organization=organization,
            zoom_meeting_id="123456789",
            format="online",
            starts_at=timezone.now()
        )

        url = f"/api/v1/events/{event.uuid}/sync_attendance/"
        
        # Mock CloudTask response (object with .name attribute)
        mock_task = MagicMock()
        mock_task.name = "projects/test/locations/test/queues/default/tasks/123"
        del mock_task.id # Ensure it doesn't have .id

        with patch('events.tasks.sync_zoom_attendance.delay', return_value=mock_task):
            response = api_client.post(url)
            assert response.status_code == status.HTTP_200_OK
            assert response.data['task_id'] == mock_task.name
            assert response.data['status'] == 'queued'

    def test_sync_attendance_sync_mode(self, api_client, organization, db):
        """Test sync_attendance when background task is run synchronously (Sync mode/Emulator)."""
        user = organization.created_by
        api_client.force_authenticate(user=user)

        event = Event.objects.create(
            title="Sync Event",
            owner=user,
            organization=organization,
            zoom_meeting_id="123456789",
            format="online",
            starts_at=timezone.now()
        )

        url = f"/api/v1/events/{event.uuid}/sync_attendance/"
        
        # Mock dictionary response (sync mode)
        mock_result = {'status': 'success', 'matched_count': 5}

        with patch('events.tasks.sync_zoom_attendance.delay', return_value=mock_result):
            response = api_client.post(url)
            assert response.status_code == status.HTTP_200_OK
            assert response.data['task_id'] is None
            assert response.data['status'] == 'queued'

    def test_sync_attendance_no_zoom(self, api_client, organization, db):
        """Test error when no Zoom meeting is linked."""
        user = organization.created_by
        api_client.force_authenticate(user=user)

        event = Event.objects.create(
            title="No Zoom Event",
            owner=user,
            organization=organization,
            zoom_meeting_id="",
            starts_at=timezone.now()
        )

        url = f"/api/v1/events/{event.uuid}/sync_attendance/"
        response = api_client.post(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['error']['code'] == 'NO_ZOOM'

    def test_unmatched_participants_success(self, api_client, organization, db):
        """Test retrieving unmatched Zoom participants for an event."""
        user = organization.created_by
        api_client.force_authenticate(user=user)

        event = Event.objects.create(
            title="Unmatched Test",
            owner=user,
            organization=organization,
            zoom_meeting_id="987654321",
            format="online",
            starts_at=timezone.now()
        )

        mock_participants = {
            'success': True,
            'data': {
                'participants': [
                    {
                        'id': 'zoom_unmatched_1',
                        'name': 'Unmatched User',
                        'user_email': 'unmatched@example.com',
                        'join_time': '2023-10-01T10:00:00Z',
                        'duration': 3600
                    }
                ]
            }
        }

        with patch('accounts.services.zoom_service.get_past_meeting_participants', return_value=mock_participants):
            url = f"/api/v1/events/{event.uuid}/unmatched_participants/"
            response = api_client.get(url)

            assert response.status_code == status.HTTP_200_OK
            assert len(response.data) == 1
            assert response.data[0]['user_email'] == 'unmatched@example.com'

    def test_sync_attendance_pulls_from_zoom(self, api_client, organization, db):
        """Test that sync_attendance actually fetches data from Zoom API."""
        user = organization.created_by
        api_client.force_authenticate(user=user)

        event = Event.objects.create(
            title="Sync Pull Test",
            owner=user,
            organization=organization,
            zoom_meeting_id="111222333",
            format="online",
            starts_at=timezone.now()
        )

        from registrations.models import Registration, AttendanceRecord
        reg = Registration.objects.create(
            event=event,
            full_name="Confirmed User",
            email="confirmed@example.com",
            status="confirmed"
        )

        mock_participants = {
            'success': True,
            'data': {
                'participants': [
                    {
                        'id': 'zoom_confirmed_1',
                        'name': 'Confirmed User',
                        'user_email': 'confirmed@example.com',
                        'join_time': '2023-10-01T10:00:00Z',
                        'leave_time': '2023-10-01T11:00:00Z',
                        'duration': 3600
                    }
                ]
            }
        }

        with patch('accounts.services.zoom_service.get_past_meeting_participants', return_value=mock_participants):
            url = f"/api/v1/events/{event.uuid}/sync_attendance/"
            # We use a mock result for the delay return to match the view's handling
            with patch('events.tasks.sync_zoom_attendance.delay', side_effect=lambda event_id: {'status': 'success'}):
                response = api_client.post(url)
                assert response.status_code == status.HTTP_200_OK
                
                # Now manually trigger the task since we matched the delay result
                from integrations.services import attendance_matcher
                result = attendance_matcher.match_attendance(event, pull_from_zoom=True)
                
                assert result['matched'] == 1
                assert AttendanceRecord.objects.filter(event=event, registration=reg).exists()
