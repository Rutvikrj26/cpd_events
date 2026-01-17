"""
Badge services for Image generation and delivery.
"""

import logging
from typing import Any
from io import BytesIO
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont
import requests

logger = logging.getLogger(__name__)


class BadgeService:
    """
    Service for badge operations.
    
    Handles:
    - Image generation (Pillow)
    - File upload
    - Issuance
    """

    def generate_badge_image(self, badge) -> bytes | None:
        """
        Generate image for a badge.
        """
        try:
            # Build snapshot data
            data = badge.badge_data or self._build_badge_data(badge)
            if not badge.badge_data:
                badge.badge_data = data
                badge.save(update_fields=['badge_data'])

            template = badge.template
            if not template:
                logger.error("No template associated with badge")
                return None

            return self._render_image(template, data)

        except Exception as e:
            logger.error(f"Badge image generation failed: {e}")
            return None

    def _render_image(self, template, data: dict) -> bytes:
        """
        Render badge as Image by overlaying text on the template.
        """
        try:
            # Download template image
            template_bytes = self._download_template_image(template)
            if not template_bytes:
                logger.error("Could not download template image")
                return b''

            # Open image
            with Image.open(BytesIO(template_bytes)) as base_img:
                # Convert to RGBA to ensure alpha channel support
                img = base_img.convert("RGBA")
                draw = ImageDraw.Draw(img)

                # Get field positions
                positions = template.field_positions or {}

                # Draw text fields
                for field_name, field_data in positions.items():
                    text = data.get(field_name, '')
                    if not text:
                        continue

                    x = field_data.get('x', 100)
                    y = field_data.get('y', 100)
                    font_size = field_data.get('fontSize', field_data.get('font_size', 24))
                    color = field_data.get('color', '#000000')
                    
                    # Try to load font (default to basic compatible font if custom not found)
                    try:
                        # In a real app, you'd load custom fonts from files
                        font = ImageFont.truetype("DejaVuSans.ttf", font_size)
                    except OSError:
                        font = ImageFont.load_default()

                    draw.text((x, y), str(text), font=font, fill=color)

                # Save to buffer
                output = BytesIO()
                img.save(output, format="PNG")
                return output.getvalue()

        except Exception as e:
            logger.error(f"Badge rendering failed: {e}")
            return b''

    def _download_template_image(self, template) -> bytes | None:
        """Download template image from storage."""
        if not template.start_image:
            return None

        try:
            from common.storage import gcs_storage
            
            # If it's a field file, we can read it directly usually
            # But let's stick to the pattern used in certificates if possible
            # Or use standard django storage API
            
            with template.start_image.open('rb') as f:
                return f.read()

        except Exception as e:
            logger.error(f"Template image download failed: {e}")
            return None

    def _build_badge_data(self, badge) -> dict:
        """Build data snapshot for badge."""
        if badge.registration:
            reg = badge.registration
            return {
                'attendee_name': reg.full_name,
                'event_title': reg.event.title,
                'issued_date': timezone.now().date().isoformat(),
            }
        elif badge.course_enrollment:
            enroll = badge.course_enrollment
            return {
                'attendee_name': enroll.user.display_name,
                'course_title': enroll.course.title,
                'issued_date': timezone.now().date().isoformat(),
            }
        return {}

    def upload_badge_image(self, badge, image_bytes: bytes) -> str | None:
        """Upload generated badge image."""
        try:
            from common.storage import gcs_storage
            
            path = f"badges/issued/{badge.uuid}.png"
            
            url = gcs_storage.upload(
                content=image_bytes,
                path=path,
                content_type='image/png',
                public=True, # Badges are usually public
                metadata={'badge_id': str(badge.uuid)}
            )
            
            if url:
                badge.image_url = url
                badge.image_generated_at = timezone.now()
                badge.save(update_fields=['image_url', 'image_generated_at'])
                return url
                
        except Exception as e:
            logger.error(f"Badge upload failed: {e}")
            return None

    def issue_badge(self, template, issued_by=None, registration=None, course_enrollment=None) -> dict[str, Any]:
        """
        Issue a badge for a registration or course enrollment.
        
        Args:
            template: BadgeTemplate to use
            issued_by: User who is issuing the badge
            registration: Optional Registration (for events)
            course_enrollment: Optional CourseEnrollment (for courses)
        """
        from badges.models import IssuedBadge
        
        if not registration and not course_enrollment:
            return {'success': False, 'error': 'Must provide registration or course_enrollment'}
        
        if registration and course_enrollment:
            return {'success': False, 'error': 'Cannot provide both registration and course_enrollment'}
        
        try:
            # Determine recipient and context
            if registration:
                recipient = registration.user
                existing_filter = {'registration': registration, 'template': template, 'status': 'active'}
                owner = registration.event.owner
            else:
                recipient = course_enrollment.user
                existing_filter = {'course_enrollment': course_enrollment, 'template': template, 'status': 'active'}
                owner = course_enrollment.course.created_by
            
            # Check existing
            existing = IssuedBadge.objects.filter(**existing_filter).first()
            
            if existing:
                 return {'success': True, 'badge': existing, 'already_issued': True}

            # Check subscription limits
            subscription = None
            try:
                subscription = owner.subscription
            except Exception:
                # RelatedObjectDoesNotExist or similar
                pass
            
            if subscription:
                # We reuse the certificate limit for now as "Credentials Limit"
                if not subscription.check_certificate_limit():
                    limit = subscription.limits.get('certificates_per_month')
                    return {
                        'success': False,
                        'error': f"Issuance limit reached ({limit} per month). Please upgrade your plan.",
                        'limit_exceeded': True,
                    }

            # Create badge
            badge = IssuedBadge.objects.create(
                registration=registration,
                course_enrollment=course_enrollment,
                template=template,
                recipient=recipient,
                issued_by=issued_by,
                status='active'
            )
            
            # Generate Image
            image_bytes = self.generate_badge_image(badge)
            if image_bytes:
                self.upload_badge_image(badge, image_bytes)

            # Increment subscription counter
            if subscription:
                subscription.increment_certificates()
                
            # Send Email
            self.send_badge_email(badge)
                
            return {'success': True, 'badge': badge}

        except Exception as e:
            logger.error(f"Badge issuance failed: {e}")
            return {'success': False, 'error': str(e)}

    def issue_bulk(self, event, registrations: list | None = None, issued_by=None) -> dict[str, Any]:
        """
        Issue badges in bulk for an event.
        """
        from registrations.models import Registration
        from badges.models import BadgeTemplate

        # Determine template (logic: use first active template for this event/org)
        # Since we don't have explicit event-template link yet, we search for a template owned by event owner
        # matching the event name or just the default one.
        # This is a heuristic. Ideally passed in.
        template = BadgeTemplate.objects.filter(owner=event.owner, is_active=True).first()
        
        if not template:
            return {'total': 0, 'success': 0, 'failed': 0, 'errors': ['No suitable badge template found for event owner']}

        if registrations is None:
            # Get all eligible registrations
            qs = Registration.objects.filter(
                event=event, 
                status='attended',
            )
            registrations = list(qs)

        results = {'total': len(registrations), 'success': 0, 'failed': 0, 'errors': []}

        for reg in registrations:
             res = self.issue_badge(template=template, registration=reg, issued_by=issued_by)
             if res['success']:
                 results['success'] += 1
             else:
                 results['failed'] += 1
                 results['errors'].append({'registration': str(reg.uuid), 'error': res.get('error')})
             
        return results

    def _generate_qr_code(self, url: str):
        """Generate QR code image as PIL Image."""
        import qrcode
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Ensure it's a PIL Image by saving/loading if needed, or just return
        # The safest way to handle potential 'PyPNGImage' or other types is to buffer it
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return Image.open(buffer).convert('RGB')

    def send_badge_email(self, badge) -> bool:
        """
        Send badge issued email.
        """
        try:
            from integrations.services import email_service

            user = badge.recipient
            # Use event info if available, else course
            title = badge.registration.event.title if badge.registration else (badge.course_enrollment.course.title if badge.course_enrollment else "Training")
            
            # Using existing certificate template as fallback or a new one
            # Ideally we register 'badge_issued' template
            
            return email_service.send_email(
                template='badge_issued', # Need to ensure this exists or use generic
                recipient=user.email,
                context={
                    'user_name': user.full_name,
                    'event_title': title,
                    'badge_url': badge.image_url,
                    'verification_url': badge.get_verification_url(), # Need to add this method to model
                    'badge_name': badge.template.name,
                },
            )

        except Exception as e:
            logger.error(f"Badge email failed: {e}")
            return False

badge_service = BadgeService()
