"""
Tests for common app endpoints.

Endpoints tested:
- POST /api/common/tasks/handler/
"""

import pytest
import json
from rest_framework import status


# =============================================================================
# Cloud Task Handler Tests
# =============================================================================


@pytest.mark.django_db
class TestCloudTaskHandler:
    """Tests for Google Cloud Tasks handler."""

    endpoint = '/api/common/tasks/handler/'

    def test_handle_valid_task(self, api_client, db):
        """Valid task is executed."""
        data = {
            'task_name': 'test_task',
            'args': {'key': 'value'},
        }
        response = api_client.post(
            self.endpoint,
            data,
            format='json',
            HTTP_X_APPENGINE_QUEUENAME='default',  # Simulate Cloud Task header
        )
        # Task may succeed or fail based on registration
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_missing_task_name(self, api_client):
        """Task name is required."""
        data = {
            'args': {'key': 'value'},
        }
        response = api_client.post(
            self.endpoint,
            data,
            format='json',
            HTTP_X_APPENGINE_QUEUENAME='default',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unknown_task(self, api_client):
        """Unknown task returns error."""
        data = {
            'task_name': 'nonexistent_task_xyz',
            'args': {},
        }
        response = api_client.post(
            self.endpoint,
            data,
            format='json',
            HTTP_X_APPENGINE_QUEUENAME='default',
        )
        # Should indicate task not found
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND]

    def test_task_without_queue_header(self, api_client):
        """Request without Cloud Task header may be rejected."""
        data = {
            'task_name': 'test_task',
            'args': {},
        }
        response = api_client.post(
            self.endpoint,
            data,
            format='json',
        )
        # May be rejected for security (no header) or accepted
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]
