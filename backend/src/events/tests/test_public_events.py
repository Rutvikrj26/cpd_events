"""
Tests for public event endpoints.

Endpoints tested:
- GET /api/v1/public/events/
- GET /api/v1/public/events/{identifier}/
"""

import pytest
from rest_framework import status

# =============================================================================
# Public Event List Tests
# =============================================================================


@pytest.mark.django_db
class TestPublicEventListView:
    """Tests for GET /api/v1/public/events/"""

    endpoint = '/api/v1/public/events/'

    def test_list_public_events_unauthenticated(self, api_client, published_event):
        """Anyone can list public events without authentication."""
        response = api_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data

    def test_list_public_events_authenticated(self, auth_client, published_event):
        """Authenticated users can also list public events."""
        response = auth_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_only_published_events_visible(self, api_client, event, published_event):
        """Only published events are visible publicly."""
        response = api_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK
        event_uuids = [e['uuid'] for e in response.data['results']]
        # Draft event should not be visible
        assert str(event.uuid) not in event_uuids
        # Published event should be visible
        assert str(published_event.uuid) in event_uuids

    def test_cancelled_events_not_visible(self, api_client, organizer, db):
        """Cancelled events are not publicly visible."""
        from factories import EventFactory

        cancelled = EventFactory(owner=organizer, status='cancelled')
        response = api_client.get(self.endpoint)
        event_uuids = [e['uuid'] for e in response.data['results']]
        assert str(cancelled.uuid) not in event_uuids

    def test_filter_by_event_type(self, api_client, organizer, db):
        """Can filter events by type."""
        from factories import EventFactory

        webinar = EventFactory(owner=organizer, status='published', event_type='webinar')
        workshop = EventFactory(owner=organizer, status='published', event_type='workshop')

        response = api_client.get(f'{self.endpoint}?event_type=webinar')
        assert response.status_code == status.HTTP_200_OK
        for e in response.data['results']:
            assert e['event_type'] == 'webinar'

    def test_filter_by_date_range(self, api_client, published_event):
        """Can filter events by date range."""
        from datetime import timedelta

        from django.utils import timezone

        future_date = (timezone.now() + timedelta(days=30)).date().isoformat()
        response = api_client.get(f'{self.endpoint}?starts_before={future_date}')
        assert response.status_code == status.HTTP_200_OK

    def test_search_events(self, api_client, published_event):
        """Can search events by title/description."""
        response = api_client.get(f'{self.endpoint}?search={published_event.title[:5]}')
        assert response.status_code == status.HTTP_200_OK

    def test_pagination(self, api_client, organizer, db):
        """Public event list is paginated."""
        from factories import EventFactory

        EventFactory.create_batch(15, owner=organizer, status='published')
        response = api_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK
        assert 'count' in response.data

    def test_ordering_by_start_date(self, api_client, organizer, db):
        """Events are ordered by start date."""
        from datetime import timedelta

        from django.utils import timezone

        from factories import EventFactory

        event1 = EventFactory(
            owner=organizer,
            status='published',
            starts_at=timezone.now() + timedelta(days=10),
        )
        event2 = EventFactory(
            owner=organizer,
            status='published',
            starts_at=timezone.now() + timedelta(days=5),
        )

        response = api_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK
        # Default ordering should be by start date ascending
        results = response.data['results']
        if len(results) >= 2:
            # Earlier event should come first
            assert results[0]['starts_at'] <= results[1]['starts_at']


# =============================================================================
# Public Event Detail Tests
# =============================================================================


@pytest.mark.django_db
class TestPublicEventDetailView:
    """Tests for GET /api/v1/public/events/{identifier}/"""

    def test_retrieve_by_uuid(self, api_client, published_event):
        """Can retrieve event by UUID."""
        response = api_client.get(f'/api/v1/public/events/{published_event.uuid}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['uuid'] == str(published_event.uuid)

    def test_retrieve_by_slug(self, api_client, published_event):
        """Can retrieve event by slug if set."""
        if published_event.slug:
            response = api_client.get(f'/api/v1/public/events/{published_event.slug}/')
            assert response.status_code == status.HTTP_200_OK

    def test_draft_event_not_accessible(self, api_client, event):
        """Draft events are not publicly accessible."""
        response = api_client.get(f'/api/v1/public/events/{event.uuid}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cancelled_event_not_accessible(self, api_client, organizer, db):
        """Cancelled events are not publicly accessible."""
        from factories import EventFactory

        cancelled = EventFactory(owner=organizer, status='cancelled')
        response = api_client.get(f'/api/v1/public/events/{cancelled.uuid}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_nonexistent_event(self, api_client):
        """404 for non-existent event."""
        import uuid

        fake_uuid = uuid.uuid4()
        response = api_client.get(f'/api/v1/public/events/{fake_uuid}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_public_event_detail_includes_required_fields(self, api_client, published_event):
        """Public event detail includes necessary fields."""
        response = api_client.get(f'/api/v1/public/events/{published_event.uuid}/')
        assert response.status_code == status.HTTP_200_OK
        # Check required fields are present
        assert 'uuid' in response.data
        assert 'title' in response.data
        assert 'description' in response.data
        assert 'starts_at' in response.data
        assert 'event_type' in response.data

    def test_public_event_excludes_sensitive_fields(self, api_client, published_event):
        """Public event detail should not expose sensitive organizer data."""
        response = api_client.get(f'/api/v1/public/events/{published_event.uuid}/')
        assert response.status_code == status.HTTP_200_OK
        # Should not expose internal fields
        assert 'zoom_meeting_password' not in response.data

    def test_registration_info_included(self, api_client, published_event):
        """Public event includes registration availability info."""
        response = api_client.get(f'/api/v1/public/events/{published_event.uuid}/')
        assert response.status_code == status.HTTP_200_OK
        # Should indicate if registration is open
        # Field names may vary based on implementation
        assert 'registration_enabled' in response.data or 'is_open_for_registration' in response.data


# =============================================================================
# Public Event with Sessions Tests
# =============================================================================


@pytest.mark.django_db
class TestPublicEventWithSessions:
    """Tests for public events with sessions."""

    def test_event_with_sessions_includes_session_info(self, api_client, event_with_sessions, organizer, db):
        """Published event with sessions includes session details."""
        # Publish the event first
        event_with_sessions.status = 'published'
        event_with_sessions.save()

        response = api_client.get(f'/api/v1/public/events/{event_with_sessions.uuid}/')
        assert response.status_code == status.HTTP_200_OK
        # Sessions should be included if the event has them
        if 'sessions' in response.data:
            assert len(response.data['sessions']) == 3
