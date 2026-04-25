"""
Tests for host-role resolution on the join-video endpoints.

Covers the expanded host model:
- Event host: owner, listed Speaker, platform admin
- Course-session host: course creator, CourseStaff member, platform admin
- Admin override: admins can join without registration/enrollment

Backed by helpers in `conferencing.views`:
- is_event_host
- is_course_session_host
- is_platform_admin
"""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.contenttypes.models import ContentType
from rest_framework import status

from conferencing.models import VideoRoom


@pytest.fixture
def mock_video_provider():
    provider = MagicMock()
    provider.generate_join_token.return_value = 'mock-token'
    with patch('conferencing.views.get_video_provider', return_value=provider):
        yield provider


@pytest.fixture
def event_room(db, event):
    ct = ContentType.objects.get_for_model(event)
    return VideoRoom.objects.create(
        content_type=ct,
        object_id=event.id,
        room_id='RM_event',
        room_name=f'event-{event.uuid}',
        provider='livekit',
        status=VideoRoom.Status.ACTIVE,
    )


@pytest.fixture
def course(db, instructor):
    from learning.models import Course

    return Course.objects.create(
        title='Test Course',
        description='x',
        created_by=instructor,
    )


@pytest.fixture
def course_session(db, course):
    from datetime import timedelta

    from django.utils import timezone

    from learning.models import CourseSession

    return CourseSession.objects.create(
        course=course,
        title='Live Session',
        starts_at=timezone.now() + timedelta(minutes=30),
        duration_minutes=60,
    )


@pytest.fixture
def session_room(db, course_session):
    ct = ContentType.objects.get_for_model(course_session)
    return VideoRoom.objects.create(
        content_type=ct,
        object_id=course_session.id,
        room_id='RM_session',
        room_name=f'session-{course_session.uuid}',
        provider='livekit',
        status=VideoRoom.Status.ACTIVE,
    )


def event_url(event):
    return f'/api/v1/events/{event.uuid}/join-video/'


def session_url(course, course_session):
    return f'/api/v1/courses/{course.uuid}/sessions/{course_session.uuid}/join-video/'


@pytest.mark.django_db
class TestEventHostResolution:
    def test_owner_is_host(self, organizer_client, event, event_room, mock_video_provider):
        response = organizer_client.post(event_url(event))
        assert response.status_code == status.HTTP_200_OK
        assert response.json()['is_host'] is True

    def test_speaker_is_host_without_registration(
        self, auth_client, user, event, event_room, mock_video_provider
    ):
        from events.models import Speaker

        speaker = Speaker.objects.create(
            owner=user, name='Dr Speaker', bio='x', qualifications='x',
        )
        event.speakers.add(speaker)

        response = auth_client.post(event_url(event))
        assert response.status_code == status.HTTP_200_OK, response.data
        body = response.json()
        assert body['is_host'] is True

    def test_admin_is_host_without_registration(
        self, admin_client, event, event_room, mock_video_provider
    ):
        response = admin_client.post(event_url(event))
        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.json()['is_host'] is True

    def test_registered_attendee_is_not_host(
        self, auth_client, user, event, event_room, mock_video_provider
    ):
        from factories import RegistrationFactory

        RegistrationFactory(event=event, user=user, status='confirmed')
        response = auth_client.post(event_url(event))
        assert response.status_code == status.HTTP_200_OK
        assert response.json()['is_host'] is False

    def test_unregistered_non_host_user_forbidden(
        self, auth_client, event, event_room, mock_video_provider
    ):
        response = auth_client.post(event_url(event))
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestCourseSessionHostResolution:
    def test_course_creator_is_host(
        self, instructor_client, course, course_session, session_room, mock_video_provider
    ):
        response = instructor_client.post(session_url(course, course_session))
        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.json()['is_host'] is True

    def test_course_staff_is_host_without_enrollment(
        self, auth_client, user, course, course_session, session_room, mock_video_provider
    ):
        from learning.models import CourseStaff

        CourseStaff.objects.create(course=course, user=user, role='instructor')

        response = auth_client.post(session_url(course, course_session))
        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.json()['is_host'] is True

    def test_admin_is_host_without_enrollment(
        self, admin_client, course, course_session, session_room, mock_video_provider
    ):
        response = admin_client.post(session_url(course, course_session))
        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.json()['is_host'] is True

    def test_enrolled_learner_is_not_host(
        self, auth_client, user, course, course_session, session_room, mock_video_provider
    ):
        from learning.models import CourseEnrollment

        CourseEnrollment.objects.create(course=course, user=user, status='active')

        response = auth_client.post(session_url(course, course_session))
        assert response.status_code == status.HTTP_200_OK
        assert response.json()['is_host'] is False

    def test_non_enrolled_non_host_forbidden(
        self, auth_client, course, course_session, session_room, mock_video_provider
    ):
        response = auth_client.post(session_url(course, course_session))
        assert response.status_code == status.HTTP_403_FORBIDDEN
