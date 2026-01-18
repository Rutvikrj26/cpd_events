import pytest
from rest_framework import status
from factories import UserFactory

@pytest.mark.django_db
class TestEventPermissions:
    def test_course_manager_can_list_events(self, api_client):
        """Course Manager should list events (empty or owned), not get 403."""
        user = UserFactory(account_type='course_manager')
        api_client.force_authenticate(user=user)
        response = api_client.get('/api/v1/events/')
        assert response.status_code == status.HTTP_200_OK

    def test_organizer_can_list_events(self, api_client):
        user = UserFactory(account_type='organizer')
        api_client.force_authenticate(user=user)
        response = api_client.get('/api/v1/events/')
        assert response.status_code == status.HTTP_200_OK

    def test_attendee_cannot_list_events(self, api_client):
        user = UserFactory(account_type='attendee')
        api_client.force_authenticate(user=user)
        response = api_client.get('/api/v1/events/')
        assert response.status_code == status.HTTP_403_FORBIDDEN
