"""
Tests for contacts endpoints.

Endpoints tested:
- GET /api/v1/tags/
- POST /api/v1/tags/
- PATCH /api/v1/tags/{uuid}/
- DELETE /api/v1/tags/{uuid}/
- POST /api/v1/tags/{uuid}/merge/
- GET /api/v1/contact-lists/
- POST /api/v1/contact-lists/
- PATCH /api/v1/contact-lists/{uuid}/
- DELETE /api/v1/contact-lists/{uuid}/
- POST /api/v1/contact-lists/{uuid}/set_default/
- POST /api/v1/contact-lists/{uuid}/duplicate/
- POST /api/v1/contact-lists/{uuid}/merge/
- GET /api/v1/contact-lists/{uuid}/contacts/
- POST /api/v1/contact-lists/{uuid}/contacts/
- PATCH /api/v1/contact-lists/{uuid}/contacts/{uuid}/
- DELETE /api/v1/contact-lists/{uuid}/contacts/{uuid}/
- POST /api/v1/contact-lists/{uuid}/contacts/bulk_create/
- POST /api/v1/contact-lists/{uuid}/contacts/{uuid}/move/
"""

import pytest
from rest_framework import status


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
        response = organizer_client.patch(f'{self.endpoint}{tag.uuid}/', {
            'name': 'Updated Tag',
            'color': '#00FF00',
        })
        assert response.status_code == status.HTTP_200_OK
        tag.refresh_from_db()
        assert tag.name == 'Updated Tag'

    def test_delete_tag(self, organizer_client, tag):
        """Organizer can delete a tag."""
        response = organizer_client.delete(f'{self.endpoint}{tag.uuid}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_merge_tags(self, organizer_client, organizer, db):
        """Organizer can merge tags."""
        from factories import TagFactory
        tag1 = TagFactory(owner=organizer, name='Tag 1')
        tag2 = TagFactory(owner=organizer, name='Tag 2')
        
        response = organizer_client.post(f'{self.endpoint}{tag1.uuid}/merge/', {
            'target_tag_uuid': str(tag2.uuid),
        })
        assert response.status_code == status.HTTP_200_OK

    def test_attendee_cannot_access_tags(self, auth_client):
        """Attendees cannot access tags."""
        response = auth_client.get(self.endpoint)
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# Contact List Tests
# =============================================================================


@pytest.mark.django_db
class TestContactListViewSet:
    """Tests for contact list CRUD operations."""

    endpoint = '/api/v1/contact-lists/'

    def test_list_contact_lists(self, organizer_client, contact_list):
        """Organizer can list their contact lists."""
        response = organizer_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data

    def test_create_contact_list(self, organizer_client):
        """Organizer can create a contact list."""
        data = {
            'name': 'New Contact List',
            'description': 'A test list',
        }
        response = organizer_client.post(self.endpoint, data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_retrieve_contact_list(self, organizer_client, contact_list):
        """Organizer can retrieve a contact list."""
        response = organizer_client.get(f'{self.endpoint}{contact_list.uuid}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == contact_list.name

    def test_update_contact_list(self, organizer_client, contact_list):
        """Organizer can update a contact list."""
        response = organizer_client.patch(f'{self.endpoint}{contact_list.uuid}/', {
            'name': 'Updated List',
        })
        assert response.status_code == status.HTTP_200_OK
        contact_list.refresh_from_db()
        assert contact_list.name == 'Updated List'

    def test_delete_contact_list(self, organizer_client, contact_list):
        """Organizer can delete a contact list."""
        response = organizer_client.delete(f'{self.endpoint}{contact_list.uuid}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_set_default_list(self, organizer_client, contact_list):
        """Organizer can set a list as default."""
        response = organizer_client.post(f'{self.endpoint}{contact_list.uuid}/set_default/')
        assert response.status_code == status.HTTP_200_OK
        contact_list.refresh_from_db()
        assert contact_list.is_default is True

    def test_duplicate_list(self, organizer_client, contact_list, contact):
        """Organizer can duplicate a contact list."""
        response = organizer_client.post(f'{self.endpoint}{contact_list.uuid}/duplicate/')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['uuid'] != str(contact_list.uuid)

    def test_merge_lists(self, organizer_client, organizer, db):
        """Organizer can merge contact lists."""
        from factories import ContactListFactory
        list1 = ContactListFactory(owner=organizer, name='List 1')
        list2 = ContactListFactory(owner=organizer, name='List 2')
        
        response = organizer_client.post(f'{self.endpoint}{list1.uuid}/merge/', {
            'target_list_uuid': str(list2.uuid),
        })
        assert response.status_code == status.HTTP_200_OK

    def test_cannot_access_other_organizer_list(self, organizer_client, other_organizer, db):
        """Cannot access another organizer's list."""
        from factories import ContactListFactory
        other_list = ContactListFactory(owner=other_organizer)
        
        response = organizer_client.get(f'{self.endpoint}{other_list.uuid}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Contact (Nested) Tests
# =============================================================================


@pytest.mark.django_db
class TestListContactViewSet:
    """Tests for contacts within a list."""

    def get_endpoint(self, contact_list):
        return f'/api/v1/contact-lists/{contact_list.uuid}/contacts/'

    def test_list_contacts(self, organizer_client, contact_list, contact):
        """Organizer can list contacts in their list."""
        endpoint = self.get_endpoint(contact_list)
        response = organizer_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data

    def test_create_contact(self, organizer_client, contact_list):
        """Organizer can add a contact."""
        endpoint = self.get_endpoint(contact_list)
        data = {
            'email': 'newcontact@example.com',
            'full_name': 'New Contact',
        }
        response = organizer_client.post(endpoint, data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_update_contact(self, organizer_client, contact_list, contact):
        """Organizer can update a contact."""
        response = organizer_client.patch(
            f'{self.get_endpoint(contact_list)}{contact.uuid}/',
            {'full_name': 'Updated Name'}
        )
        assert response.status_code == status.HTTP_200_OK
        contact.refresh_from_db()
        assert contact.full_name == 'Updated Name'

    def test_delete_contact(self, organizer_client, contact_list, contact):
        """Organizer can delete a contact."""
        response = organizer_client.delete(
            f'{self.get_endpoint(contact_list)}{contact.uuid}/'
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_bulk_create_contacts(self, organizer_client, contact_list):
        """Organizer can bulk add contacts."""
        endpoint = f'{self.get_endpoint(contact_list)}bulk_create/'
        data = {
            'contacts': [
                {'email': 'bulk1@example.com', 'full_name': 'Bulk One'},
                {'email': 'bulk2@example.com', 'full_name': 'Bulk Two'},
            ]
        }
        response = organizer_client.post(endpoint, data, format='json')
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_move_contact(self, organizer_client, contact_list, contact, organizer, db):
        """Organizer can move contact to another list."""
        from factories import ContactListFactory
        target_list = ContactListFactory(owner=organizer)
        
        response = organizer_client.post(
            f'{self.get_endpoint(contact_list)}{contact.uuid}/move/',
            {'target_list_uuid': str(target_list.uuid)}
        )
        assert response.status_code == status.HTTP_200_OK
        contact.refresh_from_db()
        assert contact.contact_list == target_list

    def test_filter_contacts_by_tag(self, organizer_client, contact_list, contact, tag, db):
        """Can filter contacts by tag."""
        contact.tags.add(tag)
        endpoint = f'{self.get_endpoint(contact_list)}?tags={tag.uuid}'
        response = organizer_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_search_contacts(self, organizer_client, contact_list, contact):
        """Can search contacts by name or email."""
        endpoint = f'{self.get_endpoint(contact_list)}?search={contact.full_name[:5]}'
        response = organizer_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# Contact Validation Tests
# =============================================================================


@pytest.mark.django_db
class TestContactValidation:
    """Tests for contact validation rules."""

    def test_duplicate_email_in_list(self, organizer_client, contact_list, contact):
        """Cannot add duplicate email to same list."""
        endpoint = f'/api/v1/contact-lists/{contact_list.uuid}/contacts/'
        data = {
            'email': contact.email,  # Already exists
            'full_name': 'Duplicate',
        }
        response = organizer_client.post(endpoint, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_email_format(self, organizer_client, contact_list):
        """Invalid email is rejected."""
        endpoint = f'/api/v1/contact-lists/{contact_list.uuid}/contacts/'
        data = {
            'email': 'not-an-email',
            'full_name': 'Test',
        }
        response = organizer_client.post(endpoint, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
