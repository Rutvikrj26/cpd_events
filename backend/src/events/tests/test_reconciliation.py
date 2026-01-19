from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework import status

from billing.models import Subscription
from events.models import Event
from factories import UserFactory
from registrations.models import AttendanceRecord, Registration


@pytest.mark.django_db
class TestEventReconciliation:
    """Tests for event attendance reconciliation endpoints."""

    def test_unmatched_participants_success(self, api_client, db):
        """Test retrieving unmatched Zoom participants for an event."""
        user = UserFactory()
        Subscription.objects.update_or_create(
            user=user,
            defaults={"plan": Subscription.Plan.ORGANIZER, "status": Subscription.Status.ACTIVE},
        )
        api_client.force_authenticate(user=user)

        event = Event.objects.create(
            title="Test Event", owner=user, zoom_meeting_id="123456789", format="online", starts_at=timezone.now()
        )

        # Create one matched registration
        reg1 = Registration.objects.create(
            event=event, user=user, full_name="Matched User", email="matched@example.com", status="confirmed"
        )
        AttendanceRecord.objects.create(
            event=event, registration=reg1, zoom_user_email="matched@example.com", is_matched=True, join_time=timezone.now()
        )

        # Mock Zoom API response
        mock_participants = {
            "success": True,
            "data": {
                "participants": [
                    {
                        "id": "zoom_1",
                        "name": "Matched User",
                        "user_email": "matched@example.com",
                        "join_time": "2023-10-01T10:00:00Z",
                        "duration": 3600,
                    },
                    {
                        "id": "zoom_2",
                        "name": "Unmatched User",
                        "user_email": "unmatched@example.com",
                        "join_time": "2023-10-01T10:05:00Z",
                        "duration": 1800,
                    },
                ]
            },
        }

        with patch("accounts.services.zoom_service.get_past_meeting_participants", return_value=mock_participants):
            url = f"/api/v1/events/{event.uuid}/unmatched_participants/"
            response = api_client.get(url)

            assert response.status_code == status.HTTP_200_OK
            data = response.data
            assert len(data) == 1
            assert data[0]["user_email"] == "unmatched@example.com"
            assert data[0]["user_name"] == "Unmatched User"

    def test_match_participant_manual(self, api_client, db):
        """Test manually matching a Zoom participant to a registration."""
        user = UserFactory()
        Subscription.objects.update_or_create(
            user=user,
            defaults={"plan": Subscription.Plan.ORGANIZER, "status": Subscription.Status.ACTIVE},
        )
        api_client.force_authenticate(user=user)

        event = Event.objects.create(title="Test Event", owner=user, zoom_meeting_id="123456789", starts_at=timezone.now())

        reg = Registration.objects.create(
            event=event, user=user, full_name="Target User", email="target@example.com", status="confirmed"
        )

        url = f"/api/v1/events/{event.uuid}/match_participant/"
        payload = {
            "registration_uuid": str(reg.uuid),
            "zoom_user_email": "zoom_user@example.com",
            "zoom_user_name": "Zoom User",
            "zoom_join_time": "2023-10-01T10:00:00Z",
            "attendance_minutes": 45,
        }

        response = api_client.post(url, payload)

        assert response.status_code == status.HTTP_200_OK

        # Verify AttendanceRecord was created
        record = AttendanceRecord.objects.get(event=event, registration=reg)
        assert record.zoom_user_email == "zoom_user@example.com"
        assert record.is_matched is True
        assert record.matched_manually is True
        assert record.duration_minutes == 45

    def test_unmatched_participants_no_zoom(self, api_client, db):
        """Test that 400 is returned if no Zoom meeting is linked."""
        user = UserFactory()
        Subscription.objects.update_or_create(
            user=user,
            defaults={"plan": Subscription.Plan.ORGANIZER, "status": Subscription.Status.ACTIVE},
        )
        api_client.force_authenticate(user=user)

        event = Event.objects.create(title="No Zoom Event", owner=user, zoom_meeting_id="", starts_at=timezone.now())

        url = f"/api/v1/events/{event.uuid}/unmatched_participants/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "NO_ZOOM"
