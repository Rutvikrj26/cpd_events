"""Tests for the per-course discussion board."""

from unittest.mock import patch

import pytest
from rest_framework import status

from factories import (
    CourseEnrollmentFactory,
    CourseFactory,
    DiscussionFlagFactory,
    DiscussionReplyFactory,
    DiscussionThreadFactory,
    UserFactory,
)


def _url(course, path=''):
    return f'/api/v1/courses/{course.uuid}/discussions/{path}'


def _enroll(user, course):
    return CourseEnrollmentFactory(user=user, course=course, status='active')


@pytest.fixture
def enrolled_learner(db, user, course):
    _enroll(user, course)
    return user


@pytest.fixture
def enrolled_learner_client(auth_client, enrolled_learner):
    return auth_client


@pytest.mark.django_db
class TestDiscussionThreadPermissions:
    def test_non_enrolled_learner_cannot_list(self, auth_client, course):
        response = auth_client.get(_url(course))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_enrolled_learner_can_list(self, enrolled_learner_client, course):
        DiscussionThreadFactory(course=course)
        response = enrolled_learner_client.get(_url(course))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_enrolled_learner_can_create(self, enrolled_learner_client, course):
        response = enrolled_learner_client.post(
            _url(course),
            {'title': 'Hello', 'body_html': '<p>My first thread</p>'},
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_empty_body_rejected(self, enrolled_learner_client, course):
        response = enrolled_learner_client.post(
            _url(course),
            {'title': 'x', 'body_html': '   '},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_sanitization_strips_scripts(self, enrolled_learner_client, course):
        response = enrolled_learner_client.post(
            _url(course),
            {'title': 'x', 'body_html': '<p>hi<script>alert(1)</script></p>'},
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        from learning.models import DiscussionThread

        thread = DiscussionThread.objects.latest('created_at')
        assert '<script' not in thread.body_html
        assert 'alert(1)' in thread.body_plain  # text survives, script tag doesn't


@pytest.mark.django_db
class TestModerationActions:
    def test_staff_can_pin(self, instructor_client, course):
        thread = DiscussionThreadFactory(course=course)
        response = instructor_client.post(_url(course, f'{thread.uuid}/pin/'))
        assert response.status_code == status.HTTP_200_OK
        thread.refresh_from_db()
        assert thread.is_pinned is True

    def test_learner_cannot_pin(self, enrolled_learner_client, course):
        thread = DiscussionThreadFactory(course=course)
        response = enrolled_learner_client.post(_url(course, f'{thread.uuid}/pin/'))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_staff_can_lock(self, instructor_client, course):
        thread = DiscussionThreadFactory(course=course)
        response = instructor_client.post(_url(course, f'{thread.uuid}/lock/'))
        assert response.status_code == status.HTTP_200_OK
        thread.refresh_from_db()
        assert thread.is_locked is True

    def test_locked_thread_rejects_learner_reply(self, enrolled_learner_client, enrolled_learner, course):
        thread = DiscussionThreadFactory(course=course, is_locked=True)
        response = enrolled_learner_client.post(
            _url(course, f'{thread.uuid}/replies/'),
            {'body_html': '<p>hi</p>'},
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_hidden_thread_invisible_to_learner(self, enrolled_learner_client, course):
        DiscussionThreadFactory(course=course, is_hidden=True)
        response = enrolled_learner_client.get(_url(course))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0

    def test_hidden_thread_visible_to_staff(self, instructor_client, course):
        DiscussionThreadFactory(course=course, is_hidden=True)
        response = instructor_client.get(_url(course))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1


@pytest.mark.django_db
class TestReplyFlow:
    def test_creating_reply_increments_count(self, enrolled_learner_client, enrolled_learner, course):
        thread = DiscussionThreadFactory(course=course)
        with patch('learning.discussions_service._send_email'):
            response = enrolled_learner_client.post(
                _url(course, f'{thread.uuid}/replies/'),
                {'body_html': '<p>reply body</p>'},
                format='json',
            )
        assert response.status_code == status.HTTP_201_CREATED
        thread.refresh_from_db()
        assert thread.reply_count == 1

    def test_reply_notifies_thread_author(self, enrolled_learner_client, enrolled_learner, course):
        author = UserFactory(email='author@example.com', groups=['learner'])
        _enroll(author, course)
        thread = DiscussionThreadFactory(course=course, author=author)
        with patch('learning.discussions_service._send_email'):
            response = enrolled_learner_client.post(
                _url(course, f'{thread.uuid}/replies/'),
                {'body_html': '<p>reply body</p>'},
                format='json',
            )
        assert response.status_code == status.HTTP_201_CREATED
        from accounts.models import Notification

        assert Notification.objects.filter(
            user=author,
            notification_type=Notification.Type.DISCUSSION_REPLY,
        ).exists()


@pytest.mark.django_db
class TestFlags:
    def test_learner_can_flag(self, enrolled_learner_client, course):
        thread = DiscussionThreadFactory(course=course)
        response = enrolled_learner_client.post(
            _url(course, f'{thread.uuid}/flag/'),
            {'reason': 'off_topic', 'note': 'no'},
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        from learning.models import DiscussionFlag

        assert DiscussionFlag.objects.filter(thread=thread, status='open').count() == 1

    def test_learner_cannot_see_flag_queue(self, enrolled_learner_client, course):
        response = enrolled_learner_client.get(f'/api/v1/courses/{course.uuid}/discussions/flags/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_staff_can_see_flag_queue(self, instructor_client, course):
        thread = DiscussionThreadFactory(course=course)
        DiscussionFlagFactory(thread=thread, reporter=UserFactory())
        response = instructor_client.get(f'/api/v1/courses/{course.uuid}/discussions/flags/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_resolve_hide_marks_content_hidden(self, instructor_client, course):
        thread = DiscussionThreadFactory(course=course)
        flag = DiscussionFlagFactory(thread=thread, reporter=UserFactory())
        response = instructor_client.post(
            f'/api/v1/courses/{course.uuid}/discussions/flags/{flag.uuid}/resolve/',
            {'action': 'hide'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        thread.refresh_from_db()
        assert thread.is_hidden is True
        flag.refresh_from_db()
        assert flag.status == 'resolved_hidden'

    def test_resolve_keep_leaves_content(self, instructor_client, course):
        thread = DiscussionThreadFactory(course=course, is_hidden=False)
        flag = DiscussionFlagFactory(thread=thread, reporter=UserFactory())
        response = instructor_client.post(
            f'/api/v1/courses/{course.uuid}/discussions/flags/{flag.uuid}/resolve/',
            {'action': 'keep'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        thread.refresh_from_db()
        assert thread.is_hidden is False
        flag.refresh_from_db()
        assert flag.status == 'resolved_kept'


@pytest.mark.django_db
class TestMemberSearch:
    def test_search_requires_access(self, auth_client, course):
        response = auth_client.get(f'/api/v1/courses/{course.uuid}/members/search/?q=x')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_search_returns_enrolled_users(self, enrolled_learner_client, enrolled_learner, course):
        other = UserFactory(email='other@example.com', full_name='Alice Smith', groups=['learner'])
        _enroll(other, course)
        response = enrolled_learner_client.get(f'/api/v1/courses/{course.uuid}/members/search/?q=alice')
        assert response.status_code == status.HTTP_200_OK
        emails = [m['email'] for m in response.data]
        assert 'other@example.com' in emails

    def test_search_excludes_non_enrollees(self, enrolled_learner_client, course):
        stranger = UserFactory(email='stranger@example.com', full_name='Bob')
        response = enrolled_learner_client.get(f'/api/v1/courses/{course.uuid}/members/search/?q=stranger')
        assert response.status_code == status.HTTP_200_OK
        emails = [m['email'] for m in response.data]
        assert 'stranger@example.com' not in emails


@pytest.mark.django_db
class TestMentionsExtraction:
    def test_mention_triggers_m2m_and_notification(self, enrolled_learner_client, enrolled_learner, course):
        target = UserFactory(email='target@example.com', full_name='Target', groups=['learner'])
        _enroll(target, course)
        body = (
            '<p>hi '
            f'<span class="mention" data-user-uuid="{target.uuid}">@Target</span>'
            '</p>'
        )
        with patch('learning.discussions_service._send_email'):
            response = enrolled_learner_client.post(
                _url(course),
                {'title': 'm', 'body_html': body},
                format='json',
            )
        assert response.status_code == status.HTTP_201_CREATED
        from learning.models import DiscussionThread

        thread = DiscussionThread.objects.latest('created_at')
        assert target in thread.mentions.all()
        from accounts.models import Notification

        assert Notification.objects.filter(
            user=target,
            notification_type=Notification.Type.DISCUSSION_MENTION,
        ).exists()

    def test_mention_to_non_member_is_ignored(self, enrolled_learner_client, course):
        stranger = UserFactory(email='stranger2@example.com', full_name='Stranger')
        body = (
            f'<p><span class="mention" data-user-uuid="{stranger.uuid}">@Stranger</span></p>'
        )
        with patch('learning.discussions_service._send_email'):
            response = enrolled_learner_client.post(
                _url(course),
                {'title': 'm', 'body_html': body},
                format='json',
            )
        assert response.status_code == status.HTTP_201_CREATED
        from learning.models import DiscussionThread

        thread = DiscussionThread.objects.latest('created_at')
        assert stranger not in thread.mentions.all()
