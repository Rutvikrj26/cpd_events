"""
Tests for CertificateService.
"""

from unittest.mock import MagicMock, patch

import pytest

from certificates.services import certificate_service


@pytest.mark.django_db
class TestCertificateService:
    def test_issue_certificate_success(
        self, certificate_template, attended_registration, organizer
    ):
        """Test successful certificate issuance."""
        # Ensure eligible
        attended_registration.attendance_eligible = True
        attended_registration.save()

        # Mock PDF generation to avoid library dependency in this test
        # Define side effect for upload_pdf to simulate state change
        def mock_upload(cert, content):
            cert.file_url = 'http://example.com/cert.pdf'
            cert.save()
            return 'http://example.com/cert.pdf'

        with patch.object(certificate_service, 'generate_pdf', return_value=b'pdf-content'), patch.object(
            certificate_service, 'upload_pdf', side_effect=mock_upload
        ):
            result = certificate_service.issue_certificate(
                attended_registration, template=certificate_template, issued_by=organizer
            )

        assert result['success'] is True
        certificate = result['certificate']
        assert certificate.status == 'active'
        assert certificate.file_url == 'http://example.com/cert.pdf'
        assert certificate.issued_by == organizer

        # Verify registration updated
        attended_registration.refresh_from_db()
        assert attended_registration.certificate_issued is True

    def test_issue_duplicate(self, certificate, organizer):
        """Test preventing duplicate issuance."""
        # certificate fixture already creates an issued certificate
        result = certificate_service.issue_certificate(
            certificate.registration, template=certificate.template, issued_by=organizer
        )

        assert result['success'] is True
        assert result.get('already_issued') is True
        assert result['certificate'].uuid == certificate.uuid

    def test_issue_certificate_limit_reached(
        self, certificate_template, attended_registration, organizer
    ):
        """Test subscription limit enforcement."""
        # Mock subscription on owner
        mock_sub = MagicMock()
        mock_sub.check_certificate_limit.return_value = False
        mock_sub.limits = {'certificates_per_month': 10}

        # We need to attach this mock to the owner
        # Since owner is a model instance, we can just patch 'subscription' property if it existed
        # But it's likely a related object. Let's just mock getattr or the attribute.
        # Assuming the code uses getattr(owner, 'subscription', None)

        # Depending on how subscription is implemented (OneToOne usually),
        # let's try to mock the attribute on the user instance provided by the fixture
        with patch.object(type(organizer), 'subscription', mock_sub, create=True):
             result = certificate_service.issue_certificate(
                attended_registration, template=certificate_template, issued_by=organizer
            )

        assert result['success'] is False
        assert 'Certificate limit reached' in result['error']

    def test_issue_no_template(self, attended_registration, organizer):
        """Test failure when no template is available."""
        # Ensure event has no default template
        attended_registration.event.certificate_template = None
        attended_registration.event.save()

        result = certificate_service.issue_certificate(
            attended_registration, template=None, issued_by=organizer
        )

        assert result['success'] is False
        assert 'No certificate template' in result['error']

    @patch('certificates.services.CertificateService._render_pdf')
    def test_generate_pdf_flow(self, mock_render, certificate):
        """Test generate_pdf calls render correctly."""
        mock_render.return_value = b'pdf-bytes'

        result = certificate_service.generate_pdf(certificate)

        assert result == b'pdf-bytes'
        mock_render.assert_called_once()

    def test_generate_pdf_no_template(self, certificate):
        """Test generate_pdf fails if certificate has no template."""
        certificate.template = None

        # Check that it handles it gracefully
        result = certificate_service.generate_pdf(certificate)
        assert result is None

    @patch('common.storage.gcs_storage.upload')
    def test_upload_pdf_gcs_success(self, mock_upload, certificate):
        """Test uploading to GCS."""
        mock_upload.return_value = 'gs://bucket/cert.pdf'

        result = certificate_service.upload_pdf(certificate, b'content')

        assert result == 'gs://bucket/cert.pdf'
        certificate.refresh_from_db()
        assert certificate.file_url == 'gs://bucket/cert.pdf'

    @patch('common.storage.gcs_storage.upload')
    def test_upload_pdf_fallback(self, mock_upload, certificate):
        """Test fallback to local storage if GCS fails."""
        mock_upload.side_effect = Exception("GCS Error")

        with patch('builtins.open', new_callable=MagicMock) as mock_open, patch('os.makedirs'):
            result = certificate_service.upload_pdf(certificate, b'content')

        # Should return a local URL
        assert result.startswith('/media/certificates/')
        assert result.endswith('.pdf')
