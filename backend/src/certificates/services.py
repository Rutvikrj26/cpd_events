"""
Certificate services for PDF generation and delivery.
"""

import logging
from typing import Any

from django.utils import timezone

logger = logging.getLogger(__name__)


class CertificateService:
    """
    Service for certificate operations.

    Handles:
    - PDF generation
    - File upload
    - Email delivery
    - Bulk issuance
    """

    def generate_pdf(self, certificate) -> bytes | None:
        """
        Generate PDF for a certificate.

        Args:
            certificate: Certificate to generate PDF for

        Returns:
            PDF bytes or None if failed
        """
        try:
            # Build certificate data
            data = certificate.build_certificate_data()
            if not data:
                return None

            # Get template
            template = certificate.template
            if not template:
                logger.error("No template associated with certificate")
                return None

            # Generate PDF using reportlab or weasyprint
            pdf_bytes = self._render_pdf(template, data)

            return pdf_bytes

        except Exception as e:
            logger.error(f"Certificate PDF generation failed: {e}")
            return None

    def _render_pdf(self, template, data: dict) -> bytes:
        """
        Render certificate as PDF.

        Uses reportlab for PDF generation.
        """
        try:
            from io import BytesIO

            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas

            buffer = BytesIO()

            # Use A4 or letter based on template settings
            page_size = A4
            c = canvas.Canvas(buffer, pagesize=page_size)
            width, height = page_size

            # Draw background if template has one
            if template.background_image_url:
                try:
                    # In production, download and cache the image
                    pass
                except Exception:
                    pass

            # Get field positions from template
            positions = template.field_positions or {}

            # Draw text fields
            for field_name, field_data in positions.items():
                text = data.get(field_name, '')
                if not text:
                    continue

                x = field_data.get('x', 100)
                y = height - field_data.get('y', 100)  # Convert to PDF coords
                font_size = field_data.get('font_size', 12)
                font = field_data.get('font', 'Helvetica')

                c.setFont(font, font_size)
                c.drawString(x, y, str(text))

            c.save()

            return buffer.getvalue()

        except ImportError:
            logger.error("reportlab not installed")
            return b''
        except Exception as e:
            logger.error(f"PDF rendering failed: {e}")
            return b''

    def upload_pdf(self, certificate, pdf_bytes: bytes) -> str | None:
        """
        Upload PDF to cloud storage.

        Args:
            certificate: Certificate to upload PDF for
            pdf_bytes: PDF file content

        Returns:
            URL of uploaded PDF or None
        """
        from django.utils import timezone

        from common.storage import gcs_storage

        try:
            # Generate path
            path = f"certificates/{certificate.uuid}.pdf"

            # Upload with metadata
            url = gcs_storage.upload(
                content=pdf_bytes,
                path=path,
                content_type='application/pdf',
                public=False,  # Use signed URLs for access
                metadata={
                    'certificate_id': str(certificate.uuid),
                    'registration_id': str(certificate.registration.uuid),
                    'event_id': str(certificate.registration.event.uuid),
                    'issued_at': timezone.now().isoformat(),
                },
            )

            if url:
                certificate.file_url = url
                certificate.file_generated_at = timezone.now()
                certificate.save(update_fields=['file_url', 'file_generated_at', 'updated_at'])
                logger.info(f"Certificate PDF uploaded: {path}")

            return url

        except Exception as e:
            logger.error(f"Certificate PDF upload failed: {e}")
            return None

    def get_pdf_url(self, certificate, expiration_minutes: int = 60) -> str | None:
        """
        Get a signed URL for downloading a certificate PDF.

        Args:
            certificate: Certificate to get URL for
            expiration_minutes: How long the URL is valid

        Returns:
            Signed download URL
        """
        from common.storage import gcs_storage

        if not certificate.file_url:
            return None

        # Extract path from gs:// URI or return as-is if already a URL
        file_url = certificate.file_url
        if file_url.startswith('gs://'):
            # Extract path from gs://bucket/path
            path = '/'.join(file_url.split('/')[3:])
            return gcs_storage.get_signed_url(path, expiration_minutes)

        # Already a public URL or local path
        return file_url

    def issue_certificate(self, registration, template=None, issued_by=None) -> dict[str, Any]:
        """
        Issue a certificate for a registration.

        Args:
            registration: Registration to issue certificate for
            template: Template to use (optional, uses event default)
            issued_by: User issuing the certificate

        Returns:
            Dict with success status and certificate
        """
        from certificates.models import Certificate

        try:
            event = registration.event

            # Use event's template if not specified
            if not template:
                template = event.certificate_template

            if not template:
                return {'success': False, 'error': 'No certificate template configured'}

            # Check if certificate already exists
            existing = Certificate.objects.filter(registration=registration, status='issued').first()

            if existing:
                return {'success': True, 'certificate': existing, 'already_issued': True}

            # Create certificate
            certificate = Certificate.objects.create(
                registration=registration,
                template=template,
                status='pending',
                cpd_type=event.cpd_type,
                cpd_credits=event.cpd_credits,
            )

            # Build and save certificate data snapshot
            cert_data = certificate.build_certificate_data()
            certificate.certificate_data = cert_data
            certificate.save()

            # Generate PDF
            pdf_bytes = self.generate_pdf(certificate)
            if pdf_bytes:
                self.upload_pdf(certificate, pdf_bytes)

            # Mark as issued
            certificate.status = 'issued'
            certificate.issued_at = timezone.now()
            certificate.issued_by = issued_by
            certificate.save()

            # Update registration
            registration.certificate_issued = True
            registration.certificate_issued_at = timezone.now()
            registration.save(update_fields=['certificate_issued', 'certificate_issued_at', 'updated_at'])

            return {'success': True, 'certificate': certificate}

        except Exception as e:
            logger.error(f"Certificate issuance failed: {e}")
            return {'success': False, 'error': str(e)}

    def issue_bulk(self, event, registrations: list | None = None, issued_by=None) -> dict[str, Any]:
        """
        Issue certificates in bulk for an event.

        Args:
            event: Event to issue certificates for
            registrations: Specific registrations (or all eligible)
            issued_by: User issuing certificates

        Returns:
            Dict with success count and errors
        """
        from registrations.models import Registration

        if registrations is None:
            # Get all eligible registrations
            registrations = Registration.objects.filter(
                event=event, status='attended', attendance_eligible=True, certificate_issued=False
            )

        results = {'total': len(registrations), 'success': 0, 'failed': 0, 'errors': []}

        for reg in registrations:
            result = self.issue_certificate(reg, issued_by=issued_by)
            if result['success']:
                results['success'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({'registration_id': str(reg.uuid), 'error': result.get('error', 'Unknown error')})

        return results

    def send_certificate_email(self, certificate) -> bool:
        """
        Send certificate email to attendee.

        Args:
            certificate: Certificate to send

        Returns:
            True if successful
        """
        try:
            from integrations.services import email_service

            user = certificate.registration.user
            event = certificate.registration.event

            return email_service.send_email(
                template='certificate_issued',
                recipient=user.email,
                context={
                    'user_name': user.full_name,
                    'event_title': event.title,
                    'certificate_url': certificate.pdf_url,
                    'verification_url': certificate.verification_url,
                    'cpd_credits': str(certificate.cpd_credits),
                    'cpd_type': certificate.cpd_type,
                },
            )

        except Exception as e:
            logger.error(f"Certificate email failed: {e}")
            return False


# Singleton instance
certificate_service = CertificateService()
