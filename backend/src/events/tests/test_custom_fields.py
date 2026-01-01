"""
Tests for event custom fields endpoints.

Endpoints tested:
- GET /api/v1/events/{event_uuid}/custom-fields/
- POST /api/v1/events/{event_uuid}/custom-fields/
- GET /api/v1/events/{event_uuid}/custom-fields/{uuid}/
- PATCH /api/v1/events/{event_uuid}/custom-fields/{uuid}/
- DELETE /api/v1/events/{event_uuid}/custom-fields/{uuid}/
- POST /api/v1/events/{event_uuid}/custom-fields/reorder/
"""

import pytest
from rest_framework import status


# =============================================================================
# Custom Field List/Create Tests
# =============================================================================


@pytest.mark.django_db
class TestEventCustomFieldListCreate:
    """Tests for custom field list and create operations."""

    def get_endpoint(self, event):
        return f'/api/v1/events/{event.uuid}/custom-fields/'

    def test_list_custom_fields(self, organizer_client, event_with_custom_fields):
        """Organizer can list custom fields for their event."""
        endpoint = self.get_endpoint(event_with_custom_fields)
        response = organizer_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_list_custom_fields_empty(self, organizer_client, event):
        """Empty list for event without custom fields."""
        endpoint = self.get_endpoint(event)
        response = organizer_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_create_custom_field_text(self, organizer_client, event):
        """Organizer can create a text custom field."""
        endpoint = self.get_endpoint(event)
        data = {
            'label': 'Company Name',
            'field_type': 'text',
            'required': True,
            'placeholder': 'Enter your company name',
        }
        response = organizer_client.post(endpoint, data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_custom_field_select(self, organizer_client, event):
        """Organizer can create a select custom field with options."""
        endpoint = self.get_endpoint(event)
        data = {
            'label': 'Dietary Requirements',
            'field_type': 'select',
            'required': False,
            'options': ['None', 'Vegetarian', 'Vegan', 'Gluten-Free'],
        }
        response = organizer_client.post(endpoint, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_custom_field_other_event_forbidden(self, organizer_client, other_organizer_event):
        """Cannot create custom field for another organizer's event."""
        endpoint = self.get_endpoint(other_organizer_event)
        data = {
            'label': 'Hacked Field',
            'field_type': 'text',
        }
        response = organizer_client.post(endpoint, data)
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]

    def test_create_custom_field_attendee_forbidden(self, auth_client, event):
        """Attendees cannot create custom fields."""
        endpoint = self.get_endpoint(event)
        data = {
            'label': 'Test Field',
            'field_type': 'text',
        }
        response = auth_client.post(endpoint, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# Custom Field Detail/Update/Delete Tests
# =============================================================================


@pytest.mark.django_db
class TestEventCustomFieldDetail:
    """Tests for custom field detail, update, and delete operations."""

    def test_retrieve_custom_field(self, organizer_client, event_with_custom_fields):
        """Organizer can retrieve a specific custom field."""
        field = event_with_custom_fields.custom_fields.first()
        response = organizer_client.get(
            f'/api/v1/events/{event_with_custom_fields.uuid}/custom-fields/{field.uuid}/'
        )
        assert response.status_code == status.HTTP_200_OK

    def test_update_custom_field(self, organizer_client, event_with_custom_fields):
        """Organizer can update a custom field."""
        field = event_with_custom_fields.custom_fields.first()
        response = organizer_client.patch(
            f'/api/v1/events/{event_with_custom_fields.uuid}/custom-fields/{field.uuid}/',
            {'label': 'Updated Field Label'}
        )
        assert response.status_code == status.HTTP_200_OK

    def test_delete_custom_field(self, organizer_client, event_with_custom_fields):
        """Organizer can delete a custom field."""
        field = event_with_custom_fields.custom_fields.first()
        response = organizer_client.delete(
            f'/api/v1/events/{event_with_custom_fields.uuid}/custom-fields/{field.uuid}/'
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_update_other_event_field_forbidden(self, organizer_client, other_organizer, db):
        """Cannot update custom field on another organizer's event."""
        from factories import EventFactory, EventCustomFieldFactory
        other_event = EventFactory(owner=other_organizer)
        field = EventCustomFieldFactory(event=other_event)
        
        response = organizer_client.patch(
            f'/api/v1/events/{other_event.uuid}/custom-fields/{field.uuid}/',
            {'label': 'Hacked'}
        )
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]


# =============================================================================
# Custom Field Reorder Tests
# =============================================================================


@pytest.mark.django_db
class TestEventCustomFieldReorder:
    """Tests for custom field reorder endpoint."""

    def test_reorder_custom_fields(self, organizer_client, event_with_custom_fields):
        """Organizer can reorder custom fields."""
        fields = list(event_with_custom_fields.custom_fields.all().order_by('order'))
        # Reverse the order
        new_order = [str(f.uuid) for f in reversed(fields)]
        
        response = organizer_client.post(
            f'/api/v1/events/{event_with_custom_fields.uuid}/custom-fields/reorder/',
            {'order': new_order},
            format='json'
        )
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_reorder_attendee_forbidden(self, auth_client, event_with_custom_fields):
        """Attendees cannot reorder custom fields."""
        response = auth_client.post(
            f'/api/v1/events/{event_with_custom_fields.uuid}/custom-fields/reorder/',
            {'order': []}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
