"""Tests for the unified /users/me/accreditations/ endpoint."""

import pytest
from django.utils import timezone
from rest_framework import status

from certificates.models import Certificate
from badges.models import IssuedBadge


@pytest.mark.django_db
class TestMyAccreditations:
    """The learner's unified accreditations feed."""

    URL = '/api/v1/users/me/accreditations/'

    def test_empty_for_new_user(self, auth_client):
        response = auth_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == {'count': 0, 'results': []}

    def test_returns_certificate_for_registration(
        self, auth_client, user, event, organizer, certificate_template
    ):
        from factories import RegistrationFactory

        registration = RegistrationFactory(event=event, user=user, status='attended')
        Certificate.objects.create(
            registration=registration,
            template=certificate_template,
            issued_by=organizer,
        )

        response = auth_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        item = response.data['results'][0]
        assert item['kind'] == 'certificate'
        assert item['source_kind'] == 'event'
        assert item['source_title'] == event.title
        assert 'verification_code' in item
        assert 'issued_at' in item

    def test_merges_certificates_and_badges_ordered_desc(
        self, auth_client, user, event, organizer, certificate_template
    ):
        from factories import RegistrationFactory
        from badges.models import BadgeTemplate

        reg = RegistrationFactory(event=event, user=user, status='attended')

        # Older certificate
        cert = Certificate.objects.create(
            registration=reg,
            template=certificate_template,
            issued_by=organizer,
        )
        old_ts = timezone.now() - timezone.timedelta(days=10)
        Certificate.objects.filter(pk=cert.pk).update(created_at=old_ts)

        # Newer badge
        badge_template = BadgeTemplate.objects.create(
            name='Attendance Badge',
            owner=organizer,
        )
        IssuedBadge.objects.create(
            registration=reg,
            recipient=user,
            template=badge_template,
            issued_by=organizer,
        )

        response = auth_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2
        kinds = [r['kind'] for r in response.data['results']]
        assert kinds[0] == 'badge', 'newer item should be first'
        assert kinds[1] == 'certificate'

    def test_excludes_revoked_items(
        self, auth_client, user, event, organizer, certificate_template
    ):
        from factories import RegistrationFactory

        reg = RegistrationFactory(event=event, user=user, status='attended')
        Certificate.objects.create(
            registration=reg,
            template=certificate_template,
            issued_by=organizer,
            status=Certificate.Status.REVOKED,
        )
        response = auth_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0

    def test_excludes_other_users_accreditations(
        self, auth_client, user, other_organizer_event, organizer, certificate_template
    ):
        from factories import RegistrationFactory, UserFactory

        other = UserFactory()
        reg = RegistrationFactory(event=other_organizer_event, user=other, status='attended')
        Certificate.objects.create(
            registration=reg,
            template=certificate_template,
            issued_by=organizer,
        )
        response = auth_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0

    def test_requires_authentication(self, api_client):
        response = api_client.get(self.URL)
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )
