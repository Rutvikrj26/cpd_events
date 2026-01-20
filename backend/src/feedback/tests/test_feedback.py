"""
Comprehensive tests for EventFeedback API.
"""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework import status

from feedback.models import EventFeedback


@pytest.mark.django_db
class TestEventFeedbackViewSet:
    """Tests for EventFeedback ViewSet."""

    def test_create_feedback_authenticated_user(self, auth_client, completed_event, attended_registration):
        """Test creating feedback as an authenticated attendee."""
        url = "/api/v1/feedback/"
        data = {
            "event": str(completed_event.uuid),
            "registration": str(attended_registration.uuid),
            "rating": 5,
            "content_quality_rating": 4,
            "speaker_rating": 5,
            "comments": "Excellent event!",
            "is_anonymous": False,
        }

        response = auth_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["rating"] == 5
        assert response.data["content_quality_rating"] == 4
        assert response.data["speaker_rating"] == 5
        assert response.data["comments"] == "Excellent event!"
        assert response.data["is_anonymous"] is False
        assert "attendee_name" in response.data

        # Verify database
        feedback = EventFeedback.objects.get(uuid=response.data["uuid"])
        assert feedback.event == completed_event
        assert feedback.registration == attended_registration

    def test_create_feedback_unauthenticated(self, api_client, completed_event, attended_registration):
        """Test that unauthenticated users cannot create feedback."""
        url = "/api/v1/feedback/"
        data = {
            "event": str(completed_event.uuid),
            "registration": str(attended_registration.uuid),
            "rating": 5,
            "content_quality_rating": 4,
            "speaker_rating": 5,
        }

        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_feedback_for_other_users_registration(self, auth_client, completed_event, guest_registration):
        """Test that users cannot submit feedback for someone else's registration."""
        url = "/api/v1/feedback/"
        data = {
            "event": str(completed_event.uuid),
            "registration": str(guest_registration.uuid),
            "rating": 5,
            "content_quality_rating": 4,
            "speaker_rating": 5,
        }

        response = auth_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_anonymous_feedback(self, auth_client, completed_event, attended_registration):
        """Test creating anonymous feedback."""
        url = "/api/v1/feedback/"
        data = {
            "event": str(completed_event.uuid),
            "registration": str(attended_registration.uuid),
            "rating": 4,
            "content_quality_rating": 3,
            "speaker_rating": 4,
            "comments": "Good but could be better",
            "is_anonymous": True,
        }

        response = auth_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["is_anonymous"] is True
        assert response.data["attendee_name"] == "Anonymous"

    def test_create_feedback_with_minimum_rating(self, auth_client, completed_event, attended_registration):
        """Test creating feedback with minimum valid ratings (1)."""
        url = "/api/v1/feedback/"
        data = {
            "event": str(completed_event.uuid),
            "registration": str(attended_registration.uuid),
            "rating": 1,
            "content_quality_rating": 1,
            "speaker_rating": 1,
            "comments": "Not satisfied",
        }

        response = auth_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_feedback_with_maximum_rating(self, auth_client, completed_event, attended_registration):
        """Test creating feedback with maximum valid ratings (5)."""
        url = "/api/v1/feedback/"
        data = {
            "event": str(completed_event.uuid),
            "registration": str(attended_registration.uuid),
            "rating": 5,
            "content_quality_rating": 5,
            "speaker_rating": 5,
        }

        response = auth_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_feedback_with_invalid_rating_too_low(self, auth_client, completed_event, attended_registration):
        """Test that ratings below 1 are rejected."""
        url = "/api/v1/feedback/"
        data = {
            "event": str(completed_event.uuid),
            "registration": str(attended_registration.uuid),
            "rating": 0,
            "content_quality_rating": 3,
            "speaker_rating": 3,
        }

        response = auth_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_feedback_with_invalid_rating_too_high(self, auth_client, completed_event, attended_registration):
        """Test that ratings above 5 are rejected."""
        url = "/api/v1/feedback/"
        data = {
            "event": str(completed_event.uuid),
            "registration": str(attended_registration.uuid),
            "rating": 6,
            "content_quality_rating": 3,
            "speaker_rating": 3,
        }

        response = auth_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_feedback_missing_required_fields(self, auth_client, completed_event, attended_registration):
        """Test that missing required fields are rejected."""
        url = "/api/v1/feedback/"
        data = {
            "event": str(completed_event.uuid),
            "registration": str(attended_registration.uuid),
            # Missing rating fields
        }

        response = auth_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_feedback_as_organizer(self, organizer_client, completed_event, attended_registration):
        """Test that organizers can list feedback for their events."""
        # Create some feedback first
        EventFeedback.objects.create(
            event=completed_event,
            registration=attended_registration,
            rating=5,
            content_quality_rating=4,
            speaker_rating=5,
        )

        url = "/api/v1/feedback/"
        response = organizer_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) > 0

    def test_list_feedback_filtered_by_event(self, organizer_client, completed_event, attended_registration):
        """Test filtering feedback by event UUID."""
        # Create feedback
        feedback = EventFeedback.objects.create(
            event=completed_event,
            registration=attended_registration,
            rating=5,
            content_quality_rating=4,
            speaker_rating=5,
        )

        url = f"/api/v1/feedback/?event={completed_event.uuid}"
        response = organizer_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["uuid"] == str(feedback.uuid)

    def test_list_feedback_as_attendee(self, auth_client, completed_event, attended_registration):
        """Test that attendees can list their own feedback."""
        # Create feedback
        feedback = EventFeedback.objects.create(
            event=completed_event,
            registration=attended_registration,
            rating=5,
            content_quality_rating=4,
            speaker_rating=5,
        )

        url = "/api/v1/feedback/"
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) > 0

    def test_retrieve_feedback(self, organizer_client, completed_event, attended_registration):
        """Test retrieving specific feedback by UUID."""
        feedback = EventFeedback.objects.create(
            event=completed_event,
            registration=attended_registration,
            rating=5,
            content_quality_rating=4,
            speaker_rating=5,
            comments="Great session!",
        )

        url = f"/api/v1/feedback/{feedback.uuid}/"
        response = organizer_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["uuid"] == str(feedback.uuid)
        assert response.data["rating"] == 5
        assert response.data["comments"] == "Great session!"

    def test_update_feedback(self, auth_client, completed_event, attended_registration):
        """Test updating feedback."""
        feedback = EventFeedback.objects.create(
            event=completed_event,
            registration=attended_registration,
            rating=3,
            content_quality_rating=3,
            speaker_rating=3,
        )

        url = f"/api/v1/feedback/{feedback.uuid}/"
        data = {
            "event": str(completed_event.uuid),
            "registration": str(attended_registration.uuid),
            "rating": 5,
            "content_quality_rating": 5,
            "speaker_rating": 5,
            "comments": "Actually, it was excellent!",
        }

        response = auth_client.put(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["rating"] == 5
        assert response.data["comments"] == "Actually, it was excellent!"

    def test_delete_feedback(self, auth_client, completed_event, attended_registration):
        """Test deleting feedback."""
        feedback = EventFeedback.objects.create(
            event=completed_event,
            registration=attended_registration,
            rating=3,
            content_quality_rating=3,
            speaker_rating=3,
        )

        url = f"/api/v1/feedback/{feedback.uuid}/"
        response = auth_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not EventFeedback.objects.filter(uuid=feedback.uuid).exists()

    def test_duplicate_feedback_prevention(self, auth_client, completed_event, attended_registration):
        """Test that duplicate feedback for same registration is prevented."""
        # Create first feedback
        EventFeedback.objects.create(
            event=completed_event,
            registration=attended_registration,
            rating=5,
            content_quality_rating=4,
            speaker_rating=5,
        )

        # Try to create duplicate
        url = "/api/v1/feedback/"
        data = {
            "event": str(completed_event.uuid),
            "registration": str(attended_registration.uuid),
            "rating": 4,
            "content_quality_rating": 4,
            "speaker_rating": 4,
        }

        response = auth_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_feedback_creates_successfully_without_certificate_issuance(
        self,
        auth_client,
        completed_event,
        attended_registration,
    ):
        """Test that feedback submission works even when certificate conditions aren't met."""
        # Submit feedback without certificate template
        url = "/api/v1/feedback/"
        data = {
            "event": str(completed_event.uuid),
            "registration": str(attended_registration.uuid),
            "rating": 5,
            "content_quality_rating": 5,
            "speaker_rating": 5,
        }

        response = auth_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert EventFeedback.objects.count() == 1

    def test_feedback_without_comments(self, auth_client, completed_event, attended_registration):
        """Test that feedback can be submitted without comments."""
        url = "/api/v1/feedback/"
        data = {
            "event": str(completed_event.uuid),
            "registration": str(attended_registration.uuid),
            "rating": 4,
            "content_quality_rating": 4,
            "speaker_rating": 4,
        }

        response = auth_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["comments"] == ""

    def test_list_feedback_unauthenticated(self, api_client):
        """Test that unauthenticated users cannot list feedback."""
        url = "/api/v1/feedback/"
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_attendee_cannot_see_other_attendees_feedback(self, auth_client, other_organizer_client, completed_event):
        """Test that attendees cannot see feedback from other attendees unless they're the organizer."""
        from factories import RegistrationFactory

        # Create another user's registration and feedback
        other_registration = RegistrationFactory(event=completed_event, status="attended")
        other_feedback = EventFeedback.objects.create(
            event=completed_event,
            registration=other_registration,
            rating=3,
            content_quality_rating=3,
            speaker_rating=3,
        )

        url = "/api/v1/feedback/"
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Should not see other user's feedback
        feedback_uuids = [f["uuid"] for f in response.data["results"]]
        assert str(other_feedback.uuid) not in feedback_uuids
