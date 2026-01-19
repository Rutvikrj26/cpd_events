import pytest
from rest_framework import status

from billing.models import Subscription
from factories import UserFactory


@pytest.mark.django_db
class TestEventPermissions:
    def test_course_manager_can_list_events(self, api_client):
        """Course Manager should list events (empty or owned), not get 403."""
        user = UserFactory()
        Subscription.objects.update_or_create(
            user=user,
            defaults={"plan": Subscription.Plan.LMS, "status": Subscription.Status.ACTIVE},
        )
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/v1/events/")
        assert response.status_code == status.HTTP_200_OK

    def test_organizer_can_list_events(self, api_client):
        user = UserFactory()
        Subscription.objects.update_or_create(
            user=user,
            defaults={"plan": Subscription.Plan.ORGANIZER, "status": Subscription.Status.ACTIVE},
        )
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/v1/events/")
        assert response.status_code == status.HTTP_200_OK

    def test_attendee_cannot_list_events(self, api_client):
        user = UserFactory()
        Subscription.objects.update_or_create(
            user=user,
            defaults={"plan": Subscription.Plan.ATTENDEE, "status": Subscription.Status.ACTIVE},
        )
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/v1/events/")
        assert response.status_code == status.HTTP_403_FORBIDDEN
