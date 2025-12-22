"""
Certificates app models - CertificateTemplate, Certificate, CertificateStatusHistory.
"""

import secrets

from django.db import models
from django.utils import timezone

from common.models import BaseModel, SoftDeleteModel
from common.validators import validate_field_positions_schema


def generate_verification_code():
    """Generate unique verification code."""
    return secrets.token_urlsafe(16)  # 22 characters


def generate_short_code():
    """Generate short code for display on certificate."""
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # No ambiguous chars
    return ''.join(secrets.choice(alphabet) for _ in range(8))


class CertificateTemplate(SoftDeleteModel):
    """
    A certificate template for generating certificates.

    Templates are immutable after certificates are issued.
    To "edit" a template, create a new version.

    Versioning:
    - When template is modified, create new template with incremented version
    - Old version preserved for historical certificates
    - Link via original_template FK
    """

    # =========================================
    # Ownership
    # =========================================
    owner = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='certificate_templates',
        help_text="Organizer who owns this template",
    )
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='certificate_templates',
        help_text="Organization that owns this template (null for individual organizers)",
    )

    # =========================================
    # Basic Info
    # =========================================
    name = models.CharField(max_length=100, help_text="Template name (for organizer reference)")
    description = models.TextField(blank=True, max_length=500, help_text="Template description")

    # =========================================
    # Template File
    # =========================================
    file_url = models.URLField(blank=True, help_text="URL to template file in cloud storage")
    file_type = models.CharField(max_length=10, default='pdf', help_text="File type (pdf, png, jpg)")
    file_size_bytes = models.PositiveIntegerField(default=0, help_text="File size in bytes")

    # Dimensions
    width_px = models.PositiveIntegerField(default=1056, help_text="Template width in pixels (default: 11in @ 96dpi)")
    height_px = models.PositiveIntegerField(default=816, help_text="Template height in pixels (default: 8.5in @ 96dpi)")
    orientation = models.CharField(
        max_length=20,
        default='landscape',
        choices=[('landscape', 'Landscape'), ('portrait', 'Portrait')],
        help_text="Template orientation",
    )

    # =========================================
    # Field Positions
    # =========================================
    field_positions = models.JSONField(
        default=dict,
        validators=[validate_field_positions_schema],
        blank=True,
        help_text="Positions and styling for dynamic fields",
    )

    # =========================================
    # Versioning
    # =========================================
    version = models.PositiveIntegerField(default=1, help_text="Template version number")
    original_template = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='versions',
        help_text="Original template this is a version of",
    )
    is_latest_version = models.BooleanField(default=True, help_text="Is this the latest version")

    # =========================================
    # Settings
    # =========================================
    is_default = models.BooleanField(default=False, help_text="Default template for new events")
    is_active = models.BooleanField(default=True, help_text="Available for selection (not archived)")
    is_shared = models.BooleanField(
        default=False,
        help_text="If True, this org template is available to all org members for their events"
    )

    # =========================================
    # Stats (denormalized)
    # =========================================
    usage_count = models.PositiveIntegerField(default=0, help_text="Number of certificates issued with this template")
    last_used_at = models.DateTimeField(null=True, blank=True, help_text="When last used to issue a certificate")

    class Meta:
        db_table = 'certificate_templates'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner']),
            models.Index(fields=['owner', 'is_active']),
            models.Index(fields=['organization', 'is_shared']),
            models.Index(fields=['uuid']),
        ]
        verbose_name = 'Certificate Template'
        verbose_name_plural = 'Certificate Templates'

    def __str__(self):
        return f"{self.name} (v{self.version})"

    @property
    def can_be_deleted(self):
        """Check if template can be deleted (no certificates)."""
        return not self.certificates.exists()

    @property
    def can_be_edited(self):
        """Check if template can be edited (no certificates)."""
        return not self.certificates.exists()

    def set_as_default(self):
        """Set this template as the default for the owner."""
        CertificateTemplate.objects.filter(owner=self.owner, is_default=True).exclude(pk=self.pk).update(is_default=False)

        self.is_default = True
        self.save(update_fields=['is_default', 'updated_at'])

    def create_new_version(self, **changes):
        """Create a new version of this template."""
        self.is_latest_version = False
        self.save(update_fields=['is_latest_version', 'updated_at'])

        new_template = CertificateTemplate.objects.create(
            owner=self.owner,
            name=changes.get('name', self.name),
            description=changes.get('description', self.description),
            file_url=changes.get('file_url', self.file_url),
            file_type=changes.get('file_type', self.file_type),
            file_size_bytes=changes.get('file_size_bytes', self.file_size_bytes),
            width_px=changes.get('width_px', self.width_px),
            height_px=changes.get('height_px', self.height_px),
            orientation=changes.get('orientation', self.orientation),
            field_positions=changes.get('field_positions', self.field_positions),
            version=self.version + 1,
            original_template=self.original_template or self,
            is_latest_version=True,
            is_default=self.is_default,
        )

        if self.is_default:
            self.is_default = False
            self.save(update_fields=['is_default', 'updated_at'])

        return new_template

    def duplicate(self, new_name=None):
        """Create a copy of this template."""
        return CertificateTemplate.objects.create(
            owner=self.owner,
            name=new_name or f"{self.name} (Copy)",
            description=self.description,
            file_url=self.file_url,
            file_type=self.file_type,
            file_size_bytes=self.file_size_bytes,
            width_px=self.width_px,
            height_px=self.height_px,
            orientation=self.orientation,
            field_positions=self.field_positions,
            version=1,
            original_template=None,
            is_latest_version=True,
            is_default=False,
        )

    def increment_usage(self):
        """Increment usage count."""
        from django.db.models import F

        CertificateTemplate.objects.filter(pk=self.pk).update(usage_count=F('usage_count') + 1, last_used_at=timezone.now())


class Certificate(SoftDeleteModel):
    """
    An issued certificate.

    Immutable after creation — certificate data is snapshotted at issuance
    to preserve historical accuracy even if source data changes.

    Verification:
    - Public verification via verification_code
    - Short code displayed on certificate itself
    """

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        REVOKED = 'revoked', 'Revoked'

    # =========================================
    # Relationships
    # =========================================
    registration = models.OneToOneField(
        'registrations.Registration',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='certificate',
        help_text="Registration this certificate was issued for",
    )
    course_enrollment = models.OneToOneField(
        'learning.CourseEnrollment',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='certificate',
        help_text="Course enrollment this certificate was issued for",
    )
    template = models.ForeignKey(
        CertificateTemplate,
        on_delete=models.PROTECT,
        related_name='certificates',
        help_text="Template used to generate certificate",
    )
    issued_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='certificates_issued',
        help_text="User who issued the certificate",
    )

    # =========================================
    # Verification Codes
    # =========================================
    verification_code = models.CharField(
        max_length=30,
        unique=True,
        default=generate_verification_code,
        db_index=True,
        help_text="Full verification code for URL",
    )
    short_code = models.CharField(
        max_length=10, unique=True, default=generate_short_code, help_text="Short code displayed on certificate"
    )
    qrcode = models.ImageField(upload_to='certificates/qrcodes/', blank=True, null=True, help_text="QR code image")

    # =========================================
    # Status
    # =========================================
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    # Revocation
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='certificates_revoked'
    )
    revocation_reason = models.TextField(blank=True)

    # =========================================
    # Generated File
    # =========================================
    file_url = models.URLField(blank=True, help_text="URL to generated PDF in cloud storage")
    file_generated_at = models.DateTimeField(null=True, blank=True, help_text="When PDF was generated")

    # =========================================
    # Certificate Data Snapshot
    # =========================================
    certificate_data = models.JSONField(default=dict, help_text="Snapshot of data at time of issuance")

    # =========================================
    # Delivery
    # =========================================
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)

    # =========================================
    # Engagement (denormalized)
    # =========================================
    first_viewed_at = models.DateTimeField(null=True, blank=True, help_text="First time certificate was viewed")
    view_count = models.PositiveIntegerField(default=0)
    first_downloaded_at = models.DateTimeField(null=True, blank=True, help_text="First time PDF was downloaded")
    download_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'certificates'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['verification_code']),
            models.Index(fields=['short_code']),
            models.Index(fields=['status']),
            models.Index(fields=['uuid']),
            models.Index(fields=['issued_by', '-created_at']),
        ]
        verbose_name = 'Certificate'
        verbose_name_plural = 'Certificates'

    def __str__(self):
        if self.registration:
            return f"Certificate: {self.registration.full_name}"
        if self.course_enrollment:
            return f"Certificate: {self.course_enrollment.user.display_name} (Course)"
        return f"Certificate: {self.pk}"

    @property
    def recipient_name(self):
        """Get recipient name."""
        if self.registration:
            return self.registration.full_name
        if self.course_enrollment:
            return self.course_enrollment.user.display_name
        return "Unknown"

    @property
    def context_title(self):
        """Get event or course title."""
        if self.registration:
            return self.registration.event.title
        if self.course_enrollment:
            return self.course_enrollment.course.title
        return "Unknown"

    @property
    def event(self):
        """Shortcut to event (for legacy compatibility)."""
        if self.registration:
            return self.registration.event
        return None

    @property
    def attendee_name(self):
        """Get attendee name from snapshot."""
        if self.registration:
            return self.certificate_data.get('attendee_name', self.registration.full_name)
        if self.course_enrollment:
            return self.certificate_data.get('attendee_name', self.course_enrollment.user.display_name)
        return self.certificate_data.get('attendee_name', '')

    @property
    def is_valid(self):
        """Check if certificate is valid."""
        return self.status == self.Status.ACTIVE and not self.is_deleted

    @property
    def verification_url(self):
        """Get full verification URL."""
        from django.conf import settings

        base = getattr(settings, 'SITE_URL', 'https://example.com')
        return f"{base}/verify/{self.verification_code}"

    @property
    def can_be_revoked(self):
        """Check if certificate can be revoked."""
        return self.status == self.Status.ACTIVE

    def revoke(self, user, reason=''):
        """Revoke the certificate."""
        if not self.can_be_revoked:
            raise ValueError("Certificate cannot be revoked")

        old_status = self.status
        self.status = self.Status.REVOKED
        self.revoked_at = timezone.now()
        self.revoked_by = user
        self.revocation_reason = reason
        self.save(update_fields=['status', 'revoked_at', 'revoked_by', 'revocation_reason', 'updated_at'])

        CertificateStatusHistory.objects.create(
            certificate=self, from_status=old_status, to_status=self.status, changed_by=user, reason=reason
        )

    def record_view(self):
        """Record a certificate view."""
        from django.db.models import F

        updates = {'view_count': F('view_count') + 1}
        if not self.first_viewed_at:
            updates['first_viewed_at'] = timezone.now()

        Certificate.objects.filter(pk=self.pk).update(**updates)

    def record_download(self):
        """Record a certificate download."""
        from django.db.models import F

        updates = {'download_count': F('download_count') + 1}
        if not self.first_downloaded_at:
            updates['first_downloaded_at'] = timezone.now()

        Certificate.objects.filter(pk=self.pk).update(**updates)

    def build_certificate_data(self):
        """Build certificate data snapshot."""
        if self.registration:
            reg = self.registration
            event = reg.event
            self.certificate_data = {
                'attendee_name': reg.full_name,
                'attendee_email': reg.email,
                'attendee_title': reg.professional_title,
                'attendee_organization': reg.organization_name,
                'event_title': event.title,
                'event_date': event.starts_at.date().isoformat() if event.starts_at else '',
                'event_datetime': event.starts_at.isoformat() if event.starts_at else '',
                'event_duration_minutes': event.duration_minutes,
                'cpd_type': event.cpd_credit_type if event.cpd_enabled else '',
                'cpd_credits': str(event.cpd_credit_value) if event.cpd_enabled else '',
                'cpd_accreditation': event.cpd_accreditation_note,
                'organizer_name': event.owner.display_name,
                'organizer_email': event.owner.email,
                'attendance_minutes': reg.total_attendance_minutes,
                'attendance_percent': reg.attendance_percent,
                'issued_date': timezone.now().date().isoformat(),
                'issued_datetime': timezone.now().isoformat(),
                'type': 'event',
            }
        elif self.course_enrollment:
            enrollment = self.course_enrollment
            course = enrollment.course
            user = enrollment.user
            self.certificate_data = {
                'attendee_name': user.display_name,
                'attendee_email': user.email,
                # 'attendee_title': user.profile.professional_title, # Assuming profile exists or similar
                'event_title': course.title, # Using event_title key for template compatibility
                'course_title': course.title,
                'event_date': enrollment.completed_at.date().isoformat() if enrollment.completed_at else timezone.now().date().isoformat(),
                'completion_date': enrollment.completed_at.date().isoformat() if enrollment.completed_at else timezone.now().date().isoformat(),
                'cpd_type': course.cpd_type,
                'cpd_credits': str(course.cpd_credits),
                'organizer_name': course.organization.name, # Course is owned by org
                'issued_date': timezone.now().date().isoformat(),
                'issued_datetime': timezone.now().isoformat(),
                'type': 'course',
            }

        return self.certificate_data


class CertificateStatusHistory(BaseModel):
    """
    Audit log of certificate status changes.
    """

    certificate = models.ForeignKey(Certificate, on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.TextField(blank=True)

    class Meta:
        db_table = 'certificate_status_history'
        ordering = ['-created_at']
        verbose_name = 'Certificate Status History'
        verbose_name_plural = 'Certificate Status Histories'

    def __str__(self):
        return f"{self.certificate}: {self.from_status} → {self.to_status}"
