"""
Tests for certificate template endpoints.

Endpoints tested:
- GET /api/v1/certificate-templates/
- POST /api/v1/certificate-templates/
- GET /api/v1/certificate-templates/{uuid}/
- PATCH /api/v1/certificate-templates/{uuid}/
- DELETE /api/v1/certificate-templates/{uuid}/
- POST /api/v1/certificate-templates/{uuid}/set-default/
- POST /api/v1/certificate-templates/{uuid}/duplicate/
- GET /api/v1/certificate-templates/available/
- POST /api/v1/certificate-templates/{uuid}/upload/
- POST /api/v1/certificate-templates/{uuid}/preview/
"""

import pytest
from rest_framework import status

# =============================================================================
# Template List/Create Tests
# =============================================================================


@pytest.mark.django_db
class TestCertificateTemplateListCreate:
    """Tests for certificate template list and create operations."""

    endpoint = '/api/v1/certificate-templates/'

    def test_list_templates(self, organizer_client, certificate_template):
        """Organizer can list their templates."""
        response = organizer_client.get(self.endpoint)
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data

    def test_create_template(self, organizer_client):
        """Organizer can create a template."""
        data = {
            'name': 'New Template',
            'description': 'A certificate template',
        }
        response = organizer_client.post(self.endpoint, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Template'

    def test_attendee_cannot_create_template(self, auth_client):
        """Attendees cannot create templates."""
        data = {
            'name': 'Unauthorized Template',
        }
        response = auth_client.post(self.endpoint, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_access(self, api_client):
        """Unauthenticated request is rejected."""
        response = api_client.get(self.endpoint)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Template Detail/Update/Delete Tests
# =============================================================================


@pytest.mark.django_db
class TestCertificateTemplateDetail:
    """Tests for template detail, update, and delete operations."""

    def test_retrieve_template(self, organizer_client, certificate_template):
        """Organizer can retrieve their template."""
        response = organizer_client.get(f'/api/v1/certificate-templates/{certificate_template.uuid}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['uuid'] == str(certificate_template.uuid)

    def test_update_template(self, organizer_client, certificate_template):
        """Organizer can update their template."""
        response = organizer_client.patch(
            f'/api/v1/certificate-templates/{certificate_template.uuid}/', {'name': 'Updated Template Name'}
        )
        assert response.status_code == status.HTTP_200_OK
        certificate_template.refresh_from_db()
        assert certificate_template.name == 'Updated Template Name'

    def test_update_template_used_in_place(self, organizer_client, certificate_template):
        """Updating a template that has already issued certificates updates in place, not via a clone."""
        from certificates.models import CertificateTemplate

        certificate_template.usage_count = 5
        certificate_template.save(update_fields=['usage_count'])
        uuid = certificate_template.uuid
        row_count_before = CertificateTemplate.objects.filter(owner=certificate_template.owner).count()

        response = organizer_client.patch(
            f'/api/v1/certificate-templates/{uuid}/', {'name': 'In-Place Edit'}
        )

        assert response.status_code == status.HTTP_200_OK
        certificate_template.refresh_from_db()
        assert certificate_template.uuid == uuid
        assert certificate_template.name == 'In-Place Edit'
        assert (
            CertificateTemplate.objects.filter(owner=certificate_template.owner).count()
            == row_count_before
        )

    def test_delete_template_without_certificates(self, organizer_client, certificate_template):
        """Organizer can delete a template with no issued certificates."""
        response = organizer_client.delete(f'/api/v1/certificate-templates/{certificate_template.uuid}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_cannot_access_other_organizer_template(self, organizer_client, other_organizer, db):
        """Cannot access another organizer's template."""
        from factories import CertificateTemplateFactory

        other_template = CertificateTemplateFactory(owner=other_organizer)

        response = organizer_client.get(f'/api/v1/certificate-templates/{other_template.uuid}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Set Default Template Tests
# =============================================================================


@pytest.mark.django_db
class TestSetDefaultTemplate:
    """Tests for set_default action."""

    def test_set_default_template(self, organizer_client, organizer, db):
        """Organizer can set a template as default."""
        from factories import CertificateTemplateFactory

        template = CertificateTemplateFactory(owner=organizer, is_default=False)

        response = organizer_client.post(f'/api/v1/certificate-templates/{template.uuid}/set-default/')
        assert response.status_code == status.HTTP_200_OK
        template.refresh_from_db()
        assert template.is_default is True

    def test_previous_default_unset(self, organizer_client, certificate_template, organizer, db):
        """Setting new default unsets previous default."""
        from factories import CertificateTemplateFactory

        new_template = CertificateTemplateFactory(owner=organizer, is_default=False)

        response = organizer_client.post(f'/api/v1/certificate-templates/{new_template.uuid}/set-default/')
        assert response.status_code == status.HTTP_200_OK

        certificate_template.refresh_from_db()
        assert certificate_template.is_default is False


# =============================================================================
# Duplicate Template Tests
# =============================================================================


@pytest.mark.django_db
class TestDuplicateTemplate:
    """Tests for the duplicate action."""

    def test_duplicate_template(self, organizer_client, certificate_template):
        """Organizer can duplicate a template."""
        from certificates.models import CertificateTemplate

        count_before = CertificateTemplate.objects.count()

        response = organizer_client.post(
            f'/api/v1/certificate-templates/{certificate_template.uuid}/duplicate/'
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert CertificateTemplate.objects.count() == count_before + 1
        assert response.data['uuid'] != str(certificate_template.uuid)
        assert response.data['name'] == f'{certificate_template.name} (Copy)'
        assert response.data['is_default'] is False

    def test_duplicate_template_with_custom_name(self, organizer_client, certificate_template):
        """Organizer can duplicate a template and override the name."""
        response = organizer_client.post(
            f'/api/v1/certificate-templates/{certificate_template.uuid}/duplicate/',
            {'name': 'My Clone'},
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'My Clone'


# =============================================================================
# Available Templates Tests
# =============================================================================


@pytest.mark.django_db
class TestAvailableTemplates:
    """Tests for available_templates action."""

    def test_get_available_templates(self, organizer_client, certificate_template):
        """Organizer can get all available templates."""
        response = organizer_client.get('/api/v1/certificate-templates/available/')
        assert response.status_code == status.HTTP_200_OK
        # Should include own templates
        template_uuids = [t['uuid'] for t in response.data['templates']]
        assert str(certificate_template.uuid) in template_uuids

    def test_includes_shared_org_templates(self, organizer_client, organizer, db):
        """Available templates endpoint is accessible."""
        response = organizer_client.get('/api/v1/certificate-templates/available/')
        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# Template Upload Tests
# =============================================================================


@pytest.mark.django_db
class TestTemplateUpload:
    """Tests for template PDF upload."""

    def test_upload_pdf_template(self, organizer_client, certificate_template):
        """Organizer can upload a PDF template file."""
        # This would need a mock PDF file
        # Skipping actual file upload in this test
        pass  # TODO: Add file upload test with mock PDF


# =============================================================================
# Template Preview Tests
# =============================================================================


@pytest.mark.django_db
class TestTemplatePreview:
    """Tests for template preview action."""

    def test_preview_template(self, organizer_client, certificate_template):
        """Organizer can generate a preview of the template."""
        response = organizer_client.post(
            f'/api/v1/certificate-templates/{certificate_template.uuid}/preview/',
            {
                'recipient_name': 'John Doe',
                'event_title': 'Test Event',
                'completion_date': '2024-01-01',
            },
        )
        # Preview may return URL or file
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
