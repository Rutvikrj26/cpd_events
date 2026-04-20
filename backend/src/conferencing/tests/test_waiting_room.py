"""
Tests for the waiting-room flow.

Covers:
- POST /api/v1/events/{event_uuid}/join-video/        (attendee vs owner vs unregistered)
- POST /api/v1/video/rooms/{uuid}/admit_participant/  (owner vs foreign-organizer)
- POST /api/v1/video/rooms/{uuid}/deny_participant/   (owner vs foreign-organizer)
- Ensures cross-organizer admit/deny is rejected (404 via queryset filter).
"""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.contenttypes.models import ContentType
from rest_framework import status

from conferencing.models import VideoRoom


@pytest.fixture
def mock_video_provider():
    """Replace the LiveKit provider with a MagicMock so tests don't hit network."""
    provider = MagicMock()
    provider.generate_join_token.return_value = 'mock-token'
    provider.update_participant.return_value = True
    with patch('conferencing.views.get_video_provider', return_value=provider):
        yield provider


@pytest.fixture
def video_room(db, event):
    """A VideoRoom attached to the organizer-owned event."""
    ct = ContentType.objects.get_for_model(event)
    event.video_settings = {'waiting_room_enabled': True}
    event.save(update_fields=['video_settings', 'updated_at'])
    return VideoRoom.objects.create(
        content_type=ct,
        object_id=event.id,
        room_id='RM_test',
        room_name=f'event-{event.uuid}',
        provider='livekit',
        status=VideoRoom.Status.ACTIVE,
    )


@pytest.fixture
def other_organizer_video_room(db, other_organizer_event):
    """A VideoRoom attached to another organizer's event — used for cross-tenant checks."""
    ct = ContentType.objects.get_for_model(other_organizer_event)
    other_organizer_event.video_settings = {'waiting_room_enabled': True}
    other_organizer_event.save(update_fields=['video_settings', 'updated_at'])
    return VideoRoom.objects.create(
        content_type=ct,
        object_id=other_organizer_event.id,
        room_id='RM_other',
        room_name=f'event-{other_organizer_event.uuid}',
        provider='livekit',
        status=VideoRoom.Status.ACTIVE,
    )


@pytest.mark.django_db
class TestJoinVideoWaiting:
    """POST /events/:uuid/join-video/ — waiting flag and registration gating."""

    def url(self, event):
        return f'/api/v1/events/{event.uuid}/join-video/'

    def test_owner_bypasses_waiting(self, organizer_client, event, video_room, mock_video_provider):
        response = organizer_client.post(self.url(event))
        assert response.status_code == status.HTTP_200_OK, response.data
        body = response.json()
        assert body['is_host'] is True
        assert body['waiting'] is False
        assert body['waiting_room_enabled'] is True
        mock_video_provider.generate_join_token.assert_called_once()
        _, kwargs = mock_video_provider.generate_join_token.call_args
        assert kwargs['is_host'] is True
        assert kwargs['waiting'] is False

    def test_registered_attendee_enters_waiting(
        self, auth_client, user, event, video_room, mock_video_provider
    ):
        from factories import RegistrationFactory

        RegistrationFactory(event=event, user=user, status='confirmed')
        response = auth_client.post(self.url(event))
        assert response.status_code == status.HTTP_200_OK, response.data
        body = response.json()
        assert body['is_host'] is False
        assert body['waiting'] is True
        _, kwargs = mock_video_provider.generate_join_token.call_args
        assert kwargs['waiting'] is True

    def test_unregistered_user_forbidden(self, auth_client, event, video_room, mock_video_provider):
        response = auth_client.post(self.url(event))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_waiting_room_disabled_means_no_wait(
        self, auth_client, user, event, video_room, mock_video_provider
    ):
        from factories import RegistrationFactory

        RegistrationFactory(event=event, user=user, status='confirmed')
        event.video_settings = {'waiting_room_enabled': False}
        event.save(update_fields=['video_settings', 'updated_at'])

        response = auth_client.post(self.url(event))
        assert response.status_code == status.HTTP_200_OK
        assert response.json()['waiting'] is False


@pytest.mark.django_db
class TestAdmitDenyParticipant:
    """POST /video/rooms/:uuid/admit_participant/ and deny_participant/"""

    def admit_url(self, room):
        return f'/api/v1/video/rooms/{room.uuid}/admit_participant/'

    def deny_url(self, room):
        return f'/api/v1/video/rooms/{room.uuid}/deny_participant/'

    def test_owner_can_admit(self, organizer_client, video_room, mock_video_provider):
        response = organizer_client.post(
            self.admit_url(video_room), {'identity': 'attendee-1'}, format='json'
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.json()['status'] == 'admitted'
        mock_video_provider.update_participant.assert_called_once()
        _, kwargs = mock_video_provider.update_participant.call_args
        assert kwargs['can_publish'] is True
        assert kwargs['can_subscribe'] is True

    def test_owner_can_deny(self, organizer_client, video_room, mock_video_provider):
        response = organizer_client.post(
            self.deny_url(video_room), {'identity': 'attendee-1'}, format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()['status'] == 'denied'
        _, kwargs = mock_video_provider.update_participant.call_args
        assert kwargs['can_publish'] is False
        assert kwargs['can_subscribe'] is False

    def test_identity_required(self, organizer_client, video_room, mock_video_provider):
        response = organizer_client.post(self.admit_url(video_room), {}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_foreign_organizer_cannot_admit(
        self, other_organizer_client, video_room, mock_video_provider
    ):
        """Regression: a different organizer must not be able to admit into someone else's room.

        Ownership is enforced by VideoRoomViewSet.get_queryset filtering by
        event owner / course staff — cross-tenant access resolves to 404.
        """
        response = other_organizer_client.post(
            self.admit_url(video_room), {'identity': 'attendee-1'}, format='json'
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        mock_video_provider.update_participant.assert_not_called()

    def test_foreign_organizer_cannot_deny(
        self, other_organizer_client, video_room, mock_video_provider
    ):
        response = other_organizer_client.post(
            self.deny_url(video_room), {'identity': 'attendee-1'}, format='json'
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        mock_video_provider.update_participant.assert_not_called()

    def test_attendee_cannot_admit(
        self, auth_client, user, event, video_room, mock_video_provider
    ):
        """A registered attendee (learner role) must not reach admit/deny at all."""
        from factories import RegistrationFactory

        RegistrationFactory(event=event, user=user, status='confirmed')
        response = auth_client.post(
            self.admit_url(video_room), {'identity': 'attendee-1'}, format='json'
        )
        # Role decorator (educator/admin) rejects learners.
        assert response.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )
        mock_video_provider.update_participant.assert_not_called()
