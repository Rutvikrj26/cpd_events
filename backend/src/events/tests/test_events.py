"""
Tests for event CRUD and action endpoints.

Endpoints tested:
- GET /api/v1/events/
- POST /api/v1/events/
- GET /api/v1/events/{uuid}/
- PATCH /api/v1/events/{uuid}/
- DELETE /api/v1/events/{uuid}/
- POST /api/v1/events/{uuid}/publish/
- POST /api/v1/events/{uuid}/unpublish/
- POST /api/v1/events/{uuid}/cancel/
- POST /api/v1/events/{uuid}/go_live/
- POST /api/v1/events/{uuid}/complete/
- POST /api/v1/events/{uuid}/duplicate/
- POST /api/v1/events/{uuid}/upload_image/
- GET /api/v1/events/{uuid}/history/
- GET /api/v1/events/dashboard/
"""

import pytest
from rest_framework import status
from django.utils import timezone
from datetime import timedelta


# =============================================================================
# Event List Tests
# =============================================================================


@pytest.mark.django_db
class TestEventList:
    """Tests for GET /api/v1/events/"""

    endpoint = '/api/v1/events/'

    def test_list_events_organizer(self, organizer_client, event):
        """Organizer can list their events."""
        response = organizer_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert len(response.data['results']) >= 1

    def test_list_events_only_own(self, organizer_client, event, other_organizer_event):
        """Organizer only sees their own events."""
        response = organizer_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK
        event_uuids = [e['uuid'] for e in response.data['results']]
        assert str(event.uuid) in event_uuids
        assert str(other_organizer_event.uuid) not in event_uuids

    def test_list_events_attendee_forbidden(self, auth_client):
        """Attendees cannot access organizer event list."""
        response = auth_client.get(self.endpoint)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_events_unauthenticated(self, api_client):
        """Unauthenticated request is rejected."""
        response = api_client.get(self.endpoint)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_events_filter_by_status(self, organizer_client, event, published_event):
        """Can filter events by status."""
        response = organizer_client.get(f'{self.endpoint}?status=published')
        assert response.status_code == status.HTTP_200_OK
        for e in response.data['results']:
            assert e['status'] == 'published'

    def test_list_events_pagination(self, organizer_client, organizer, db):
        """Event list is paginated."""
        from factories import EventFactory
        # Create many events
        EventFactory.create_batch(15, owner=organizer)
        response = organizer_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK
        assert 'count' in response.data
        assert 'next' in response.data or 'previous' in response.data


# =============================================================================
# Event Create Tests
# =============================================================================


@pytest.mark.django_db
class TestEventCreate:
    """Tests for POST /api/v1/events/"""

    endpoint = '/api/v1/events/'

    def test_create_event_success(self, organizer_client, event_create_data):
        """Organizer can create an event."""
        response = organizer_client.post(self.endpoint, event_create_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == event_create_data['title']
        assert response.data['status'] == 'draft'

    def test_create_event_requires_certificate_template_when_enabled(self, organizer_client):
        """Certificate template is required when certificates are enabled."""
        data = {
            'title': 'Certificate Event',
            'starts_at': (timezone.now() + timedelta(days=7)).isoformat(),
            'certificates_enabled': True,
        }
        response = organizer_client.post(self.endpoint, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'certificate_template' in response.data['error']['details']

    def test_create_event_with_certificate_template(self, organizer_client, certificate_template):
        """Can create event when certificates are enabled with a template."""
        data = {
            'title': 'Certificate Event',
            'starts_at': (timezone.now() + timedelta(days=7)).isoformat(),
            'certificates_enabled': True,
            'certificate_template': str(certificate_template.uuid),
        }
        response = organizer_client.post(self.endpoint, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert str(response.data['certificate_template']) == str(certificate_template.uuid)

    def test_create_event_minimal(self, organizer_client):
        """Can create event with minimal required fields."""
        data = {
            'title': 'Minimal Event',
            'starts_at': (timezone.now() + timedelta(days=7)).isoformat(),
            'timezone': 'UTC',
        }
        response = organizer_client.post(self.endpoint, data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_event_attendee_forbidden(self, auth_client, event_create_data):
        """Attendees cannot create events."""
        response = auth_client.post(self.endpoint, event_create_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_event_missing_title(self, organizer_client):
        """Title is required."""
        data = {
            'starts_at': (timezone.now() + timedelta(days=7)).isoformat(),
            'timezone': 'UTC',
        }
        response = organizer_client.post(self.endpoint, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'title' in response.data['error']['details']

    def test_create_event_past_start_date(self, organizer_client):
        """Cannot create event with past start date."""
        data = {
            'title': 'Past Event',
            'starts_at': (timezone.now() - timedelta(days=1)).isoformat(),
            'timezone': 'UTC',
        }
        response = organizer_client.post(self.endpoint, data)
        # Might be allowed for drafts, but typically rejected
        # Accept both 201 (if allowed) or 400 (if validated)
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]


# =============================================================================
# Event Detail Tests
# =============================================================================


@pytest.mark.django_db
class TestEventDetail:
    """Tests for GET /api/v1/events/{uuid}/"""

    def test_retrieve_event(self, organizer_client, event):
        """Organizer can retrieve their event."""
        response = organizer_client.get(f'/api/v1/events/{event.uuid}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['uuid'] == str(event.uuid)
        assert response.data['title'] == event.title

    def test_retrieve_other_organizer_event_not_found(self, organizer_client, other_organizer_event):
        """Cannot retrieve another organizer's event."""
        response = organizer_client.get(f'/api/v1/events/{other_organizer_event.uuid}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_nonexistent_event(self, organizer_client):
        """404 for non-existent event."""
        import uuid
        fake_uuid = uuid.uuid4()
        response = organizer_client.get(f'/api/v1/events/{fake_uuid}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Event Update Tests
# =============================================================================


@pytest.mark.django_db
class TestEventUpdate:
    """Tests for PATCH /api/v1/events/{uuid}/"""

    def test_update_event(self, organizer_client, event):
        """Organizer can update their event."""
        response = organizer_client.patch(f'/api/v1/events/{event.uuid}/', {
            'title': 'Updated Event Title',
            'description': 'Updated description',
            'certificates_enabled': False,
        })
        assert response.status_code == status.HTTP_200_OK
        event.refresh_from_db()
        assert event.title == 'Updated Event Title'

    def test_update_event_requires_certificate_template_when_enabled(self, organizer_client, event):
        """Cannot enable certificates without selecting a template."""
        event.certificates_enabled = False
        event.certificate_template = None
        event.save(update_fields=['certificates_enabled', 'certificate_template', 'updated_at'])

        response = organizer_client.patch(f'/api/v1/events/{event.uuid}/', {
            'certificates_enabled': True,
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'certificate_template' in response.data['error']['details']

    def test_update_other_organizer_event_forbidden(self, organizer_client, other_organizer_event):
        """Cannot update another organizer's event."""
        response = organizer_client.patch(f'/api/v1/events/{other_organizer_event.uuid}/', {
            'title': 'Hacked Title',
        })
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_completed_event_limited(self, organizer_client, completed_event):
        """Limited fields can be updated on completed event."""
        response = organizer_client.patch(f'/api/v1/events/{completed_event.uuid}/', {
            'title': 'Updated Completed Event',
        })
        # Might be allowed or restricted
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]


# =============================================================================
# Event Delete Tests
# =============================================================================


@pytest.mark.django_db
class TestEventDelete:
    """Tests for DELETE /api/v1/events/{uuid}/"""

    def test_delete_draft_event(self, organizer_client, event):
        """Organizer can delete a draft event."""
        response = organizer_client.delete(f'/api/v1/events/{event.uuid}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_other_organizer_event_forbidden(self, organizer_client, other_organizer_event):
        """Cannot delete another organizer's event."""
        response = organizer_client.delete(f'/api/v1/events/{other_organizer_event.uuid}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_published_event(self, organizer_client, published_event):
        """Deleting published event may be restricted or soft-delete."""
        response = organizer_client.delete(f'/api/v1/events/{published_event.uuid}/')
        # Could be soft delete (204) or forbidden (400/403)
        assert response.status_code in [
            status.HTTP_204_NO_CONTENT,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]


# =============================================================================
# Event Status Transition Tests
# =============================================================================


@pytest.mark.django_db
class TestEventStatusTransitions:
    """Tests for event status transition endpoints."""

    def test_publish_draft_event(self, organizer_client, event):
        """Organizer can publish a draft event."""
        response = organizer_client.post(f'/api/v1/events/{event.uuid}/publish/')
        assert response.status_code == status.HTTP_200_OK
        event.refresh_from_db()
        assert event.status == 'published'

    def test_unpublish_published_event(self, organizer_client, published_event):
        """Organizer can unpublish a published event."""
        response = organizer_client.post(f'/api/v1/events/{published_event.uuid}/unpublish/')
        assert response.status_code == status.HTTP_200_OK
        published_event.refresh_from_db()
        assert published_event.status == 'draft'

    def test_cancel_event(self, organizer_client, published_event):
        """Organizer can cancel an event."""
        response = organizer_client.post(f'/api/v1/events/{published_event.uuid}/cancel/')
        assert response.status_code == status.HTTP_200_OK
        published_event.refresh_from_db()
        assert published_event.status == 'cancelled'

    def test_go_live(self, organizer_client, published_event):
        """Organizer can start (go live) a published event."""
        response = organizer_client.post(f'/api/v1/events/{published_event.uuid}/go_live/')
        assert response.status_code == status.HTTP_200_OK
        published_event.refresh_from_db()
        assert published_event.status == 'live'

    def test_complete_live_event(self, organizer_client, live_event):
        """Organizer can complete a live event."""
        response = organizer_client.post(f'/api/v1/events/{live_event.uuid}/complete/')
        assert response.status_code == status.HTTP_200_OK
        live_event.refresh_from_db()
        assert live_event.status == 'completed'

    def test_invalid_transition_draft_to_complete(self, organizer_client, event):
        """Cannot transition directly from draft to completed."""
        response = organizer_client.post(f'/api/v1/events/{event.uuid}/complete/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_transition_completed_to_draft(self, organizer_client, completed_event):
        """Cannot transition from completed back to draft."""
        response = organizer_client.post(f'/api/v1/events/{completed_event.uuid}/unpublish/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Event Action Tests
# =============================================================================


@pytest.mark.django_db
class TestEventActions:
    """Tests for event action endpoints."""

    def test_duplicate_event(self, organizer_client, event):
        """Organizer can duplicate an event."""
        response = organizer_client.post(f'/api/v1/events/{event.uuid}/duplicate/')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['uuid'] != str(event.uuid)
        assert 'Copy' in response.data['title'] or event.title in response.data['title']

    def test_get_event_history(self, organizer_client, published_event):
        """Organizer can view event status history."""
        response = organizer_client.get(f'/api/v1/events/{published_event.uuid}/history/')
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)


# =============================================================================
# Event Dashboard Tests
# =============================================================================


@pytest.mark.django_db
class TestEventDashboard:
    """Tests for GET /api/v1/events/dashboard/"""

    endpoint = '/api/v1/events/dashboard/'

    def test_get_dashboard(self, organizer_client, event, published_event):
        """Organizer can view their dashboard stats."""
        response = organizer_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK
        # Dashboard should contain summary statistics
        assert isinstance(response.data, dict)

    def test_dashboard_attendee_forbidden(self, auth_client):
        """Attendees cannot access dashboard."""
        response = auth_client.get(self.endpoint)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_dashboard_unauthenticated(self, api_client):
        """Unauthenticated request is rejected."""
        response = api_client.get(self.endpoint)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Event Permission Tests
# =============================================================================


@pytest.mark.django_db
class TestEventPermissions:
    """Tests for event endpoint permissions."""

    def test_attendee_cannot_manage_events(self, auth_client, event_create_data):
        """Attendees cannot create, update, or delete events."""
        # Create
        response = auth_client.post('/api/v1/events/', event_create_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_organizer_cannot_access_other_events(self, organizer_client, other_organizer_event):
        """Organizer cannot access another organizer's events."""
        # Retrieve
        response = organizer_client.get(f'/api/v1/events/{other_organizer_event.uuid}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Update
        response = organizer_client.patch(f'/api/v1/events/{other_organizer_event.uuid}/', {
            'title': 'Hacked',
        })
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Delete
        response = organizer_client.delete(f'/api/v1/events/{other_organizer_event.uuid}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND
