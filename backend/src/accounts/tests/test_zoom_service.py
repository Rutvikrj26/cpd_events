"""
Tests for ZoomService.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from accounts.services import zoom_service


@pytest.mark.django_db
class TestZoomService:
    @pytest.fixture
    def zoom_connection(self, user):
        from accounts.models import ZoomConnection

        return ZoomConnection.objects.create(
            user=user,
            access_token='test_access_token',
            refresh_token='test_refresh_token',
            token_expires_at=timezone.now() + timezone.timedelta(hours=1),
            zoom_user_id='test_zoom_id',
            is_active=True,
        )

    @patch('requests.post')
    def test_create_meeting_success(self, mock_post, zoom_connection, completed_event, user):
        """Test successful meeting creation."""
        # Setup mocks
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'id': 123456789,
            'uuid': 'uuid-123',
            'join_url': 'https://zoom.us/j/123456789',
            'start_url': 'https://zoom.us/s/123456789',
            'password': 'secure-pass',
        }
        mock_post.return_value = mock_response

        # Ensure event owner matches connection
        completed_event.owner = user
        completed_event.save()

        # Call service
        result = zoom_service.create_meeting(completed_event)

        # Verify result
        assert result['success'] is True
        assert result['meeting']['id'] == 123456789

        # Verify API call
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs['json']['topic'] == completed_event.title
        assert 'Authorization' in kwargs['headers']

        # Verify event updated
        completed_event.refresh_from_db()
        assert completed_event.zoom_meeting_id == '123456789'
        assert completed_event.zoom_join_url == 'https://zoom.us/j/123456789'

    def test_create_meeting_no_connection(self, completed_event, user):
        """Test failing when user has no Zoom connection."""
        # User has no connection
        completed_event.owner = user
        completed_event.save()

        result = zoom_service.create_meeting(completed_event)

        assert result['success'] is False
        assert 'User does not have connected Zoom account' in result['error']

    @patch('requests.post')
    def test_create_meeting_api_error(self, mock_post, zoom_connection, completed_event, user):
        """Test handling of Zoom API errors."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = 'Bad Request'
        mock_response.json.return_value = {'message': 'Invalid duration'}
        mock_post.return_value = mock_response

        completed_event.owner = user
        completed_event.save()

        result = zoom_service.create_meeting(completed_event)

        assert result['success'] is False
        assert 'Zoom: Invalid duration' in result['error']

    @patch('requests.post')
    def test_refresh_tokens_success(self, mock_post, zoom_connection):
        """Test successful token refresh."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token',
            'expires_in': 3600,
        }
        mock_post.return_value = mock_response

        # Set connection to expired
        zoom_connection.token_expires_at = timezone.now() - timezone.timedelta(hours=1)
        zoom_connection.save()

        # Call refresh explicitly
        success = zoom_service.refresh_tokens(zoom_connection)

        assert success is True
        zoom_connection.refresh_from_db()
        assert zoom_connection.access_token == 'new_access_token'
        assert zoom_connection.refresh_token == 'new_refresh_token'

    @patch('requests.post')
    def test_refresh_tokens_failure(self, mock_post, zoom_connection):
        """Test handling of token refresh failure."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = 'Invalid Grant'
        mock_post.return_value = mock_response

        success = zoom_service.refresh_tokens(zoom_connection)

        assert success is False
        zoom_connection.refresh_from_db()
        assert 'Token refresh failed' in zoom_connection.last_error

    @patch('requests.post')
    def test_add_registrant_success(self, mock_post, zoom_connection, completed_event, user):
        """Test successful registrant addition."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'id': 'reg-123',
            'join_url': 'https://zoom.us/j/123?tk=abc',
        }
        mock_post.return_value = mock_response

        completed_event.owner = user
        completed_event.zoom_meeting_id = '123456789'
        completed_event.save()

        result = zoom_service.add_meeting_registrant(
            completed_event, 'attendee@example.com', 'John', 'Doe'
        )

        assert result['success'] is True
        assert result['join_url'] == 'https://zoom.us/j/123?tk=abc'

        # Verify payload
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs['json']['email'] == 'attendee@example.com'
        assert kwargs['json']['first_name'] == 'John'
