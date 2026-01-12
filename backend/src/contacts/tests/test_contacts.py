"""
Tests for contacts endpoints (Single List Architecture).

Endpoints tested:
- GET /api/v1/tags/
- POST /api/v1/tags/
- PATCH /api/v1/tags/{uuid}/
- DELETE /api/v1/tags/{uuid}/
- GET /api/v1/contact-lists/
- GET /api/v1/contacts/
- POST /api/v1/contacts/
- PATCH /api/v1/contacts/{uuid}/
- DELETE /api/v1/contacts/{uuid}/
- POST /api/v1/contacts/bulk_create/
- GET /api/v1/contacts/export/
"""

import pytest
from rest_framework import status

from contacts.models import Contact, ContactList

# =============================================================================
# Tag Tests
# =============================================================================


@pytest.mark.django_db
class TestTagViewSet:
    """Tests for tag CRUD operations."""

    endpoint = '/api/v1/tags/'

    def test_list_tags(self, organizer_client, tag):
        """Organizer can list their tags."""
        response = organizer_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data

    def test_create_tag(self, organizer_client):
        """Organizer can create a tag."""
        data = {
            'name': 'New Tag',
            'color': '#FF5733',
        }
        response = organizer_client.post(self.endpoint, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Tag'

    def test_update_tag(self, organizer_client, tag):
        """Organizer can update a tag."""
        response = organizer_client.patch(
            f'{self.endpoint}{tag.uuid}/',
            {
                'name': 'Updated Tag',
                'color': '#00FF00',
            },
        )
        assert response.status_code == status.HTTP_200_OK
        tag.refresh_from_db()
        assert tag.name == 'Updated Tag'

    def test_delete_tag(self, organizer_client, tag):
        """Organizer can delete a tag."""
        response = organizer_client.delete(f'{self.endpoint}{tag.uuid}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_attendee_cannot_access_tags(self, auth_client):
        """Attendees cannot access tags."""
        response = auth_client.get(self.endpoint)
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# Contact List Tests
# =============================================================================


@pytest.mark.django_db
class TestContactList:
    """Tests for contact list behavior (auto-creation)."""

    endpoint = '/api/v1/contact-lists/'

    def test_list_auto_created(self, organizer_client, organizer):
        """List is auto-created on first access."""
        assert ContactList.objects.filter(owner=organizer).count() == 0

        # Access contacts endpoint should trigger creation
        response = organizer_client.get('/api/v1/contacts/')
        assert response.status_code == status.HTTP_200_OK

        assert ContactList.objects.filter(owner=organizer).count() == 1
        contact_list = ContactList.objects.get(owner=organizer)
        assert contact_list.name == 'My Contacts'

    def test_get_contact_lists(self, organizer_client, organizer):
        """Organizer can see their list in the lists endpoint."""
        ContactList.get_or_create_for_user(organizer)

        response = organizer_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
        assert response.data['results'][0]['name'] == 'My Contacts'


# =============================================================================
# Contact Tests
# =============================================================================


@pytest.mark.django_db
class TestContactViewSet:
    """Tests for contact CRUD."""

    endpoint = '/api/v1/contacts/'

    def test_list_contacts(self, organizer_client, contact):
        """Organizer can list their contacts."""
        # Contact factory should set owner correctly
        response = organizer_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) > 0

    def test_create_contact(self, organizer_client):
        """Organizer can create a contact."""
        data = {
            'email': 'new@example.com',
            'full_name': 'New Contact',
            'phone': '1234567890',
        }
        response = organizer_client.post(self.endpoint, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['email'] == 'new@example.com'

    def test_update_contact(self, organizer_client, contact):
        """Organizer can update a contact."""
        response = organizer_client.patch(
            f'{self.endpoint}{contact.uuid}/',
            {
                'full_name': 'Updated Name',
            },
        )
        assert response.status_code == status.HTTP_200_OK
        contact.refresh_from_db()
        assert contact.full_name == 'Updated Name'

    def test_delete_contact(self, organizer_client, contact):
        """Organizer can delete a contact."""
        response = organizer_client.delete(f'{self.endpoint}{contact.uuid}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Contact.objects.filter(uuid=contact.uuid).exists()

    def test_bulk_create(self, organizer_client):
        """Organizer can bulk create contacts."""
        data = {
            'contacts': [
                {'email': 'bulk1@example.com', 'full_name': 'Bulk One'},
                {'email': 'bulk2@example.com', 'full_name': 'Bulk Two'},
            ]
        }
        response = organizer_client.post(f'{self.endpoint}bulk_create/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['created'] == 2

    def test_export_contacts(self, organizer_client, contact):
        """Organizer can export contacts."""
        response = organizer_client.get(f'{self.endpoint}export/')
        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'text/csv'

        content = response.content.decode('utf-8')
        assert 'Email,Full Name' in content
        assert contact.email in content

    def test_duplicate_email_prevention(self, organizer_client, contact):
        """Cannot add duplicate email."""
        data = {
            'email': contact.email,
            'full_name': 'Duplicate',
        }
        response = organizer_client.post(self.endpoint, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_filter_by_tag(self, organizer_client, contact, tag):
        """Can filter contacts by tag."""
        contact.tags.add(tag)
        response = organizer_client.get(f'{self.endpoint}?tag={tag.uuid}')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['uuid'] == str(contact.uuid)

    def test_search(self, organizer_client, contact):
        """Can search contacts."""
        response = organizer_client.get(f'{self.endpoint}?search={contact.email}')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
