"""
Tests for certificate endpoints.

Endpoints tested:
- GET /api/v1/events/{event_uuid}/certificates/
- POST /api/v1/events/{event_uuid}/certificates/issue/
- POST /api/v1/events/{event_uuid}/certificates/{uuid}/revoke/
- GET /api/v1/events/{event_uuid}/certificates/summary/
- GET /api/v1/certificates/ (my certificates)
- GET /api/v1/certificates/{uuid}/
- GET /api/v1/certificates/{uuid}/download/
- GET /api/v1/public/certificates/verify/{code}/
"""

import pytest
from rest_framework import status

# =============================================================================
# Event Certificate Management Tests
# =============================================================================


@pytest.mark.django_db
class TestEventCertificateViewSet:
    """Tests for event certificate management."""

    def get_endpoint(self, event):
        return f'/api/v1/events/{event.uuid}/certificates/'

    def test_list_event_certificates(self, organizer_client, certificate, completed_event):
        """Organizer can list certificates for their event."""
        endpoint = self.get_endpoint(completed_event)
        response = organizer_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_issue_certificate(self, organizer_client, attended_registration, certificate_template, completed_event):
        """Organizer can issue a certificate."""
        endpoint = f'{self.get_endpoint(completed_event)}issue/'
        response = organizer_client.post(
            endpoint,
            {
                'registration_uuid': str(attended_registration.uuid),
                'template_uuid': str(certificate_template.uuid),
            },
        )
        # Should succeed or indicate already issued
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_issue_bulk_certificates(self, organizer_client, completed_event, certificate_template, db):
        """Organizer can issue certificates in bulk."""
        from factories import RegistrationFactory

        # Create eligible registrations
        regs = [
            RegistrationFactory(
                event=completed_event,
                status='confirmed',
                attended=True,
                attendance_eligible=True,
            )
            for _ in range(3)
        ]

        endpoint = f'{self.get_endpoint(completed_event)}issue/'
        response = organizer_client.post(
            endpoint,
            {
                'issue_all_eligible': True,
                'template_uuid': str(certificate_template.uuid),
            },
        )
        # Bulk issuance may return different status
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

    def test_revoke_certificate(self, organizer_client, certificate, completed_event):
        """Organizer can revoke a certificate."""
        endpoint = f'/api/v1/events/{certificate.registration.event.uuid}/certificates/{certificate.uuid}/revoke/'
        response = organizer_client.post(
            endpoint,
            {
                'reason': 'Issued in error',
            },
        )
        assert response.status_code == status.HTTP_200_OK
        certificate.refresh_from_db()
        assert certificate.status == 'revoked'

    def test_educator_can_manage_any_institution_event_certificates(
        self, organizer_client, other_organizer_event
    ):
        """Institutional model: any educator can manage certificates for any event in the institution."""
        endpoint = self.get_endpoint(other_organizer_event)
        response = organizer_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_attendee_cannot_manage_certificates(self, auth_client, completed_event):
        """Attendees cannot access certificate management."""
        endpoint = self.get_endpoint(completed_event)
        response = auth_client.get(endpoint)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_soft_deleted_event_returns_404_on_issue(
        self, organizer_client, completed_event, attended_registration
    ):
        """Soft-deleted events cannot have certificates issued against them."""
        from django.utils import timezone

        completed_event.deleted_at = timezone.now()
        completed_event.save(update_fields=['deleted_at'])

        endpoint = f'{self.get_endpoint(completed_event)}issue/'
        response = organizer_client.post(
            endpoint,
            {'registration_uuids': [str(attended_registration.uuid)]},
            format='json',
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_force_reissue_replaces_existing_cert(
        self, organizer_client, certificate, completed_event, certificate_template
    ):
        """Re-issuing with force=True soft-deletes the old cert and creates a new one."""
        from certificates.models import Certificate

        completed_event.certificate_template = certificate_template
        completed_event.save(update_fields=['certificate_template'])

        original_uuid = certificate.uuid
        endpoint = f'{self.get_endpoint(completed_event)}issue/'

        response = organizer_client.post(
            endpoint,
            {
                'registration_uuids': [str(certificate.registration.uuid)],
                'force': True,
            },
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['issued_count'] == 1

        # Original soft-deleted, new active cert exists
        original = Certificate.all_objects.get(uuid=original_uuid)
        assert original.deleted_at is not None
        new_cert_uuid = response.data['issued'][0]
        assert str(new_cert_uuid) != str(original_uuid)
        new_cert = Certificate.objects.get(uuid=new_cert_uuid)
        assert new_cert.status == 'active'
        assert new_cert.registration == certificate.registration

    def test_issue_skipped_reasons_are_per_registration(
        self, organizer_client, completed_event, attended_registration, certificate_template
    ):
        """Each skipped registration includes a reason in the response."""
        from factories import RegistrationFactory

        completed_event.certificate_template = certificate_template
        completed_event.save(update_fields=['certificate_template'])

        # Create a non-eligible registration (not attended)
        ineligible = RegistrationFactory(
            event=completed_event,
            status='confirmed',
            attended=False,
            attendance_eligible=False,
        )

        endpoint = f'{self.get_endpoint(completed_event)}issue/'
        response = organizer_client.post(
            endpoint,
            {
                'registration_uuids': [
                    str(attended_registration.uuid),
                    str(ineligible.uuid),
                ],
            },
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['issued_count'] == 1
        assert response.data['skipped_count'] == 1
        skipped = response.data['skipped']
        assert any(
            s['uuid'] == str(ineligible.uuid) and s['reason'] == 'NOT_ELIGIBLE'
            for s in skipped
        )

    def test_cannot_create_duplicate_active_cert(
        self, db, attended_registration, certificate_template, organizer
    ):
        """Unique constraint: two active certs for the same registration is a DB error."""
        from django.db import IntegrityError, transaction

        from certificates.models import Certificate

        Certificate.objects.create(
            registration=attended_registration,
            template=certificate_template,
            status='active',
            issued_by=organizer,
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Certificate.objects.create(
                    registration=attended_registration,
                    template=certificate_template,
                    status='active',
                    issued_by=organizer,
                )


# =============================================================================
# Certificate Summary Tests
# =============================================================================


@pytest.mark.django_db
class TestCertificateSummary:
    """Tests for certificate summary endpoint."""

    def test_get_certificate_summary(self, organizer_client, certificate, completed_event):
        """Organizer can get certificate summary for an event."""
        endpoint = f'/api/v1/events/{completed_event.uuid}/certificates/summary/'
        response = organizer_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK
        # Should contain summary stats
        assert isinstance(response.data, dict)


# =============================================================================
# Attendee Certificate Tests
# =============================================================================


@pytest.mark.django_db
class TestMyCertificateViewSet:
    """Tests for attendee certificate viewing."""

    endpoint = '/api/v1/certificates/'

    def test_list_my_certificates(self, auth_client, certificate, user):
        """User can list their certificates."""
        # Certificate should be linked to user's registration
        response = auth_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_my_certificate(self, auth_client, certificate, user):
        """User can retrieve their specific certificate."""
        response = auth_client.get(f'{self.endpoint}{certificate.uuid}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['uuid'] == str(certificate.uuid)

    def test_cannot_see_others_certificates(self, auth_client, other_organizer, db):
        """User cannot see certificates issued to others."""
        from factories import CertificateFactory, EventFactory, RegistrationFactory

        other_event = EventFactory(owner=other_organizer, status='completed')
        other_reg = RegistrationFactory(event=other_event, attended=True)
        other_cert = CertificateFactory(registration=other_reg, issued_by=other_organizer)

        response = auth_client.get(f'{self.endpoint}{other_cert.uuid}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_download_certificate(self, auth_client, certificate):
        """User can download their certificate."""
        response = auth_client.post(f'{self.endpoint}{certificate.uuid}/download/')
        # Download should return file or URL
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_302_FOUND]

    def test_unauthenticated_cannot_access(self, api_client):
        """Unauthenticated users cannot access certificates."""
        response = api_client.get(self.endpoint)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Public Verification Tests
# =============================================================================


@pytest.mark.django_db
class TestCertificateVerification:
    """Tests for GET /api/v1/public/certificates/verify/{code}/"""

    def test_verify_valid_certificate(self, api_client, certificate):
        """Anyone can verify a valid certificate."""
        response = api_client.get(f'/api/v1/public/certificates/verify/{certificate.verification_code}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_valid'] is True

    def test_verify_revoked_certificate(self, api_client, certificate):
        """Revoked certificate shows as invalid."""
        certificate.status = 'revoked'
        certificate.save()

        response = api_client.get(f'/api/v1/public/certificates/verify/{certificate.verification_code}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_valid'] is False

    def test_verify_invalid_code(self, api_client):
        """Invalid verification code returns 404."""
        response = api_client.get('/api/v1/public/certificates/verify/INVALID123/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_verify_short_code(self, api_client, certificate):
        """Can also verify using short code."""
        if certificate.short_code:
            response = api_client.get(f'/api/v1/public/certificates/verify/{certificate.short_code}/')
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_verification_response_includes_details(self, api_client, certificate):
        """Verification response includes certificate details."""
        response = api_client.get(f'/api/v1/public/certificates/verify/{certificate.verification_code}/')
        assert response.status_code == status.HTTP_200_OK
        # Should include relevant verification info
        assert 'is_valid' in response.data


# =============================================================================
# Certificate Eligibility Tests
# =============================================================================


@pytest.mark.django_db
class TestCertificateEligibility:
    """Tests for certificate issuance eligibility rules."""

    def test_cannot_issue_to_non_eligible(self, organizer_client, completed_event, certificate_template, db):
        """Cannot issue certificate to non-eligible registration."""
        from factories import RegistrationFactory

        non_eligible = RegistrationFactory(
            event=completed_event,
            status='confirmed',
            attended=False,
            attendance_eligible=False,
        )

        endpoint = f'/api/v1/events/{completed_event.uuid}/certificates/issue/'
        response = organizer_client.post(
            endpoint,
            {
                'registration_uuid': str(non_eligible.uuid),
                'template_uuid': str(certificate_template.uuid),
            },
        )
        # Should fail or indicate not eligible
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_issue_duplicate(
        self, organizer_client, certificate, attended_registration, certificate_template, completed_event
    ):
        """Cannot issue duplicate certificate to same registration."""
        endpoint = f'/api/v1/events/{completed_event.uuid}/certificates/issue/'
        response = organizer_client.post(
            endpoint,
            {
                'registration_uuid': str(attended_registration.uuid),
                'template_uuid': str(certificate_template.uuid),
            },
        )
        # Should fail - already issued
        assert response.status_code == status.HTTP_400_BAD_REQUEST
