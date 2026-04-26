import pytest
from rest_framework import status

from factories import UserFactory


@pytest.mark.django_db
class TestEventPermissions:
    def test_instructor_cannot_list_events(self, api_client):
        """Instructors are course-only and must NOT see the top-level events list."""
        user = UserFactory(groups=['instructor'])
        api_client.force_authenticate(user=user)
        response = api_client.get('/api/v1/events/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_organizer_can_list_events(self, api_client):
        user = UserFactory(groups=['organizer'])
        api_client.force_authenticate(user=user)
        response = api_client.get('/api/v1/events/')
        assert response.status_code == status.HTTP_200_OK

    def test_attendee_cannot_list_events(self, api_client):
        user = UserFactory(groups=['learner'])
        api_client.force_authenticate(user=user)
        response = api_client.get('/api/v1/events/')
        assert response.status_code == status.HTTP_403_FORBIDDEN
