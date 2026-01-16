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
        Render certificate as PDF by overlaying text on the template.

        Uses PyPDF2 to merge text overlay onto the template PDF.
        """
        try:
            from io import BytesIO

            from reportlab.lib.colors import black
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas

            # Try to get template PDF for overlay
            template_bytes = self._download_template(template)

            if template_bytes:
                # Use PyPDF2 to overlay text on template
                from pypdf import PdfReader, PdfWriter

                template_reader = PdfReader(BytesIO(template_bytes))
                if len(template_reader.pages) == 0:
                    logger.error("Template PDF has no pages")
                    return b''

                template_page = template_reader.pages[0]
                page_width = float(template_page.mediabox.width)
                page_height = float(template_page.mediabox.height)
            else:
                # Fallback to blank A4 page
                logger.warning("No template PDF, generating on blank canvas")
                page_width, page_height = A4
                template_page = None

            # Create overlay with text
            overlay_buffer = BytesIO()
            c = canvas.Canvas(overlay_buffer, pagesize=(page_width, page_height))

            # Get field positions from template
            positions = template.field_positions or {}

            # Draw text fields
            for field_name, field_data in positions.items():
                text = data.get(field_name, '')
                if not text:
                    continue

                x = field_data.get('x', 100)
                y = page_height - field_data.get('y', 100)  # Convert from top-left to PDF coords
                font_size = field_data.get('fontSize', field_data.get('font_size', 12))
                font_family = field_data.get('fontFamily', field_data.get('font', 'Helvetica'))

                try:
                    c.setFont(font_family, font_size)
                except KeyError:
                    c.setFont('Helvetica', font_size)

                c.setFillColor(black)
                c.drawString(x, y, str(text))

            c.save()
            overlay_buffer.seek(0)

            if template_page:
                # Merge template with overlay
                overlay_reader = PdfReader(overlay_buffer)
                overlay_page = overlay_reader.pages[0]
                template_page.merge_page(overlay_page)

                # Write result
                writer = PdfWriter()
                writer.add_page(template_page)

                output = BytesIO()
                writer.write(output)
                return output.getvalue()
            else:
                # Return blank canvas with text
                return overlay_buffer.getvalue()

        except ImportError as e:
            logger.error(f"PDF library not installed: {e}")
            return b''
        except Exception as e:
            logger.error(f"PDF rendering failed: {e}")
            return b''

    def generate_template_preview(self, template, field_positions: dict, sample_data: dict) -> bytes | None:
        """
        Generate a preview PDF with sample data overlaid on the template.

        Args:
            template: CertificateTemplate with file_url
            field_positions: Dict of {field_name: {x, y, fontSize, fontFamily}}
            sample_data: Dict of {field_name: value}

        Returns:
            PDF bytes with text overlaid
        """
        try:
            from io import BytesIO

            from pypdf import PdfReader, PdfWriter
            from reportlab.lib.colors import black
            from reportlab.lib.pagesizes import A4, letter
            from reportlab.pdfgen import canvas

            # Get template PDF
            template_bytes = self._download_template(template)
            if not template_bytes:
                logger.warning("No template PDF, generating blank preview")
                return self._generate_blank_preview(field_positions, sample_data)

            # Read template PDF
            template_reader = PdfReader(BytesIO(template_bytes))
            if len(template_reader.pages) == 0:
                logger.error("Template PDF has no pages")
                return None

            template_page = template_reader.pages[0]
            page_width = float(template_page.mediabox.width)
            page_height = float(template_page.mediabox.height)

            # Create overlay with text
            overlay_buffer = BytesIO()
            c = canvas.Canvas(overlay_buffer, pagesize=(page_width, page_height))

            # Draw text at field positions
            for field_name, position in (field_positions or {}).items():
                text = sample_data.get(field_name, '')
                if not text:
                    continue

                x = position.get('x', 100)
                y = page_height - position.get('y', 100)  # Convert from top-left to PDF coords
                font_size = position.get('fontSize', 24)
                font_family = position.get('fontFamily', 'Helvetica')

                try:
                    c.setFont(font_family, font_size)
                except KeyError:
                    c.setFont('Helvetica', font_size)

                c.setFillColor(black)
                c.drawString(x, y, str(text))

            c.save()
            overlay_buffer.seek(0)

            # Merge template with overlay
            overlay_reader = PdfReader(overlay_buffer)
            overlay_page = overlay_reader.pages[0]

            template_page.merge_page(overlay_page)

            # Write result
            writer = PdfWriter()
            writer.add_page(template_page)

            output = BytesIO()
            writer.write(output)
            return output.getvalue()

        except ImportError as e:
            logger.error(f"PDF library not installed: {e}")
            return None
        except Exception as e:
            logger.error(f"Preview generation failed: {e}")
            return None

    def _download_template(self, template) -> bytes | None:
        """Download template PDF from storage."""
        if not template.file_url:
            return None

        try:
            from common.storage import gcs_storage

            file_url = template.file_url
            if file_url.startswith('gs://'):
                path = '/'.join(file_url.split('/')[3:])
                return gcs_storage.download(path)
            elif file_url.startswith('/media/'):
                # Local file
                import os

                from django.conf import settings

                local_path = os.path.join(settings.MEDIA_ROOT, file_url.replace('/media/', ''))
                with open(local_path, 'rb') as f:
                    return f.read()
            else:
                logger.warning(f"Unknown file URL format: {file_url}")
                return None
        except Exception as e:
            logger.error(f"Template download failed: {e}")
            return None

    def _generate_blank_preview(self, field_positions: dict, sample_data: dict) -> bytes:
        """Generate a blank preview with just the text fields visible."""
        from io import BytesIO

        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Light gray background to show it's a preview
        c.setFillColorRGB(0.95, 0.95, 0.95)
        c.rect(0, 0, width, height, fill=True)

        # Draw text at field positions
        for field_name, position in (field_positions or {}).items():
            text = sample_data.get(field_name, field_name)
            x = position.get('x', 100)
            y = height - position.get('y', 100)
            font_size = position.get('fontSize', 24)

            c.setFillColorRGB(0, 0, 0)
            c.setFont('Helvetica', font_size)
            c.drawString(x, y, str(text))

        c.save()
        return buffer.getvalue()

    def upload_pdf(self, certificate, pdf_bytes: bytes) -> str | None:
        """
        Upload PDF to cloud storage or local media storage as fallback.

        Args:
            certificate: Certificate to upload PDF for
            pdf_bytes: PDF file content

        Returns:
            URL of uploaded PDF or None
        """
        import os

        from django.conf import settings
        from django.utils import timezone

        try:
            # Try GCS first if configured
            from common.storage import gcs_storage

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
                logger.info(f"Certificate PDF uploaded to GCS: {path}")
                return url

        except Exception as e:
            logger.warning(f"GCS upload failed, falling back to local storage: {e}")

        # Fallback to local media storage
        try:
            # Create certificates directory if it doesn't exist
            cert_dir = os.path.join(settings.MEDIA_ROOT, 'certificates')
            os.makedirs(cert_dir, exist_ok=True)

            # Save file locally
            filename = f"{certificate.uuid}.pdf"
            filepath = os.path.join(cert_dir, filename)

            with open(filepath, 'wb') as f:
                f.write(pdf_bytes)

            # Build URL using MEDIA_URL
            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            url = f"{media_url}certificates/{filename}"

            certificate.file_url = url
            certificate.file_generated_at = timezone.now()
            certificate.save(update_fields=['file_url', 'file_generated_at', 'updated_at'])
            logger.info(f"Certificate PDF saved locally: {filepath}")
            return url

        except Exception as e:
            logger.error(f"Certificate PDF local save failed: {e}")
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

        # For local paths, construct absolute URL
        if file_url.startswith('/'):
            from django.conf import settings

            base_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
            return f"{base_url.rstrip('/')}{file_url}"

        # Already a public URL
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
            owner = event.owner

            # Check subscription certificate limit
            subscription = getattr(owner, 'subscription', None)
            if subscription:
                if not subscription.check_certificate_limit():
                    limit = subscription.limits.get('certificates_per_month')
                    return {
                        'success': False,
                        'error': f"Certificate limit reached ({limit} per month). Please upgrade your plan to issue more certificates.",
                        'limit_exceeded': True,
                    }

            # Use event's template if not specified
            if not template:
                template = event.certificate_template

            if not template:
                return {'success': False, 'error': 'No certificate template configured'}

            # Check if certificate already exists
            existing = Certificate.objects.filter(registration=registration, status='active').first()

            if existing:
                return {'success': True, 'certificate': existing, 'already_issued': True}

            # Create certificate
            certificate = Certificate.objects.create(
                registration=registration,
                template=template,
                status='pending',
                issued_by=issued_by,
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
            certificate.status = 'active'
            certificate.issued_at = timezone.now()
            certificate.issued_by = issued_by
            certificate.save()

            # Update registration
            registration.certificate_issued = True
            registration.certificate_issued_at = timezone.now()
            registration.save(update_fields=['certificate_issued', 'certificate_issued_at', 'updated_at'])

            # Increment certificate counter in subscription
            if subscription:
                subscription.increment_certificates()

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
