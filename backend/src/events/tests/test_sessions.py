"""
Tests for event sessions endpoints (multi-session events).

Endpoints tested:
- GET /api/v1/events/{event_uuid}/sessions/
- POST /api/v1/events/{event_uuid}/sessions/
- GET /api/v1/events/{event_uuid}/sessions/{uuid}/
- PATCH /api/v1/events/{event_uuid}/sessions/{uuid}/
- DELETE /api/v1/events/{event_uuid}/sessions/{uuid}/
- POST /api/v1/events/{event_uuid}/sessions/reorder/
"""

import pytest
from rest_framework import status
from django.utils import timezone
from datetime import timedelta


# =============================================================================
# Session List/Create Tests
# =============================================================================


@pytest.mark.django_db
class TestEventSessionListCreate:
    """Tests for session list and create operations."""

    def get_endpoint(self, event):
        return f'/api/v1/events/{event.uuid}/sessions/'

    def test_list_sessions(self, organizer_client, event_with_sessions):
        """Organizer can list sessions for their event."""
        endpoint = self.get_endpoint(event_with_sessions)
        response = organizer_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 3

    def test_list_sessions_empty(self, organizer_client, event):
        """Empty list for event without sessions."""
        endpoint = self.get_endpoint(event)
        response = organizer_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 0

    def test_create_session(self, organizer_client, event):
        """Organizer can create a session."""
        endpoint = self.get_endpoint(event)
        data = {
            'title': 'Opening Keynote',
            'description': 'Welcome and introduction',
            'starts_at': (timezone.now() + timedelta(days=7)).isoformat(),
            'duration_minutes': 60,
        }
        response = organizer_client.post(endpoint, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'Opening Keynote'

    def test_create_session_with_speaker(self, organizer_client, event):
        """Can create session with speaker information."""
        endpoint = self.get_endpoint(event)
        data = {
            'title': 'Expert Panel',
            'starts_at': (timezone.now() + timedelta(days=7)).isoformat(),
            'duration_minutes': 90,
            'speaker_name': 'Dr. Jane Smith',
            'speaker_bio': 'Expert in the field',
        }
        response = organizer_client.post(endpoint, data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_session_other_event_forbidden(self, organizer_client, other_organizer_event):
        """Cannot create session for another organizer's event."""
        endpoint = self.get_endpoint(other_organizer_event)
        data = {
            'title': 'Hacked Session',
            'starts_at': (timezone.now() + timedelta(days=7)).isoformat(),
            'duration_minutes': 60,
        }
        response = organizer_client.post(endpoint, data)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_session_attendee_forbidden(self, auth_client, event):
        """Attendees cannot create sessions."""
        endpoint = self.get_endpoint(event)
        data = {
            'title': 'Session',
            'starts_at': (timezone.now() + timedelta(days=7)).isoformat(),
            'duration_minutes': 60,
        }
        response = auth_client.post(endpoint, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_session_missing_title(self, organizer_client, event):
        """Title is required."""
        endpoint = self.get_endpoint(event)
        data = {
            'starts_at': (timezone.now() + timedelta(days=7)).isoformat(),
            'duration_minutes': 60,
        }
        response = organizer_client.post(endpoint, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Session Detail/Update/Delete Tests
# =============================================================================


@pytest.mark.django_db
class TestEventSessionDetail:
    """Tests for session detail, update, and delete operations."""

    def test_retrieve_session(self, organizer_client, event_with_sessions):
        """Organizer can retrieve a specific session."""
        session = event_with_sessions.sessions.first()
        response = organizer_client.get(
            f'/api/v1/events/{event_with_sessions.uuid}/sessions/{session.uuid}/'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['uuid'] == str(session.uuid)

    def test_update_session(self, organizer_client, event_with_sessions):
        """Organizer can update a session."""
        session = event_with_sessions.sessions.first()
        response = organizer_client.patch(
            f'/api/v1/events/{event_with_sessions.uuid}/sessions/{session.uuid}/',
            {'title': 'Updated Session Title', 'description': 'New description'}
        )
        assert response.status_code == status.HTTP_200_OK
        session.refresh_from_db()
        assert session.title == 'Updated Session Title'

    def test_delete_session(self, organizer_client, event_with_sessions):
        """Organizer can delete a session."""
        session = event_with_sessions.sessions.first()
        session_uuid = session.uuid
        response = organizer_client.delete(
            f'/api/v1/events/{event_with_sessions.uuid}/sessions/{session.uuid}/'
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        from events.models import EventSession
        assert not EventSession.objects.filter(uuid=session_uuid).exists()

    def test_update_other_event_session_forbidden(self, organizer_client, other_organizer, db):
        """Cannot update session on another organizer's event."""
        from factories import EventFactory, EventSessionFactory
        other_event = EventFactory(owner=other_organizer)
        session = EventSessionFactory(event=other_event)
        
        response = organizer_client.patch(
            f'/api/v1/events/{other_event.uuid}/sessions/{session.uuid}/',
            {'title': 'Hacked'}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Session Reorder Tests
# =============================================================================


@pytest.mark.django_db
class TestEventSessionReorder:
    """Tests for session reorder endpoint."""

    def test_reorder_sessions(self, organizer_client, event_with_sessions):
        """Organizer can reorder sessions."""
        sessions = list(event_with_sessions.sessions.all().order_by('order'))
        # Reverse the order
        new_order = [str(s.uuid) for s in reversed(sessions)]
        
        response = organizer_client.post(
            f'/api/v1/events/{event_with_sessions.uuid}/sessions/reorder/',
            {'order': new_order}
        )
        assert response.status_code == status.HTTP_200_OK

    def test_reorder_other_event_forbidden(self, organizer_client, other_organizer, db):
        """Cannot reorder sessions on another organizer's event."""
        from factories import EventFactory, EventSessionFactory
        other_event = EventFactory(owner=other_organizer)
        session = EventSessionFactory(event=other_event)
        
        response = organizer_client.post(
            f'/api/v1/events/{other_event.uuid}/sessions/reorder/',
            {'order': [str(session.uuid)]}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Session Ordering Tests
# =============================================================================


@pytest.mark.django_db
class TestSessionOrdering:
    """Tests for session ordering behavior."""

    def test_sessions_returned_in_order(self, organizer_client, event_with_sessions):
        """Sessions are returned in order."""
        endpoint = f'/api/v1/events/{event_with_sessions.uuid}/sessions/'
        response = organizer_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK
        
        results = response.data['results']
        # Check ordering
        for i in range(len(results) - 1):
            assert results[i]['order'] <= results[i + 1]['order']

    def test_new_session_gets_next_order(self, organizer_client, event_with_sessions):
        """New session is added at the end with correct order."""
        # Get current max order
        max_order = event_with_sessions.sessions.count()
        
        endpoint = f'/api/v1/events/{event_with_sessions.uuid}/sessions/'
        data = {
            'title': 'New Session',
            'starts_at': (timezone.now() + timedelta(days=7, hours=2)).isoformat(),
            'duration_minutes': 30,
        }
        response = organizer_client.post(endpoint, data)
        assert response.status_code == status.HTTP_201_CREATED
        # New session should have order >= max_order
        assert response.data['order'] >= max_order
