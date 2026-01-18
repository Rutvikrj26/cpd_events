# Certificates App: Certificate Management

## Overview

The `certificates` app handles:
- Certificate template management
- Certificate issuance and PDF generation
- Certificate verification (public)
- Certificate audit trail

---

## Models

### CertificateTemplate

A reusable certificate design owned by an organizer.

```python
# certificates/models.py

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from common.models import SoftDeleteModel
from common.validators import validate_field_positions_schema


class CertificateTemplate(SoftDeleteModel):
    """
    A certificate template for generating certificates.
    
    Templates are immutable after certificates are issued.
    To "edit" a template, create a new version.
    
    Soft Delete Behavior:
    - Cannot delete if certificates reference this template (PROTECTED)
    - Soft delete hides from selection but certificates remain valid
    
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
        help_text="Organizer who owns this template"
    )
    
    # Phase 2: Organization ownership
    # organization = models.ForeignKey(
    #     'organizations.Organization',
    #     on_delete=models.SET_NULL,
    #     null=True, blank=True,
    #     related_name='certificate_templates'
    # )
    
    # =========================================
    # Basic Info
    # =========================================
    name = models.CharField(
        max_length=100,
        help_text="Template name (for organizer reference)"
    )
    description = models.TextField(
        blank=True,
        max_length=500,
        help_text="Template description"
    )
    
    # =========================================
    # Template File
    # =========================================
    file_url = models.URLField(
        help_text="URL to template file in cloud storage"
    )
    file_type = models.CharField(
        max_length=10,
        help_text="File type (pdf, png, jpg)"
    )
    file_size_bytes = models.PositiveIntegerField(
        default=0,
        help_text="File size in bytes"
    )
    
    # Dimensions
    width_px = models.PositiveIntegerField(
        default=1056,
        help_text="Template width in pixels (default: 11in @ 96dpi)"
    )
    height_px = models.PositiveIntegerField(
        default=816,
        help_text="Template height in pixels (default: 8.5in @ 96dpi)"
    )
    orientation = models.CharField(
        max_length=20,
        default='landscape',
        choices=[('landscape', 'Landscape'), ('portrait', 'Portrait')],
        help_text="Template orientation"
    )
    
    # =========================================
    # Field Positions
    # =========================================
    field_positions = models.JSONField(
        default=dict,
        validators=[validate_field_positions_schema],
        help_text="Positions and styling for dynamic fields"
    )
    """
    Schema:
    {
        "attendee_name": {
            "x": 528,              # X position (pixels from left)
            "y": 300,              # Y position (pixels from top)
            "font_size": 24,       # Font size in points
            "font": "Helvetica",   # Font family
            "font_weight": "bold", # normal, bold
            "color": "#000000",    # Hex color
            "align": "center"      # left, center, right
        },
        "event_title": {...},
        "event_date": {...},
        "cpd_credits": {...},
        "cpd_type": {...},
        "certificate_id": {...},
        "organizer_name": {...},
        "issue_date": {...},
        "signature": {
            "x": 528,
            "y": 500,
            "image_url": "https://...",  # Signature image
            "width": 150                  # Display width
        },
        "qr_code": {
            "x": 50,
            "y": 700,
            "size": 80                    # QR code size
        }
    }
    """
    
    # =========================================
    # Versioning
    # =========================================
    version = models.PositiveIntegerField(
        default=1,
        help_text="Template version number"
    )
    original_template = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='versions',
        help_text="Original template this is a version of"
    )
    is_latest_version = models.BooleanField(
        default=True,
        help_text="Is this the latest version"
    )
    
    # =========================================
    # Settings
    # =========================================
    is_default = models.BooleanField(
        default=False,
        help_text="Default template for new events"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Available for selection (not archived)"
    )
    
    # =========================================
    # Stats (denormalized)
    # =========================================
    usage_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of certificates issued with this template"
    )
    last_used_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When last used to issue a certificate"
    )
    
    class Meta:
        db_table = 'certificate_templates'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner']),
            models.Index(fields=['owner', 'is_active']),
            models.Index(fields=['uuid']),
        ]
        verbose_name = 'Certificate Template'
        verbose_name_plural = 'Certificate Templates'
    
    def __str__(self):
        return f"{self.name} (v{self.version})"
    
    # =========================================
    # Properties
    # =========================================
    @property
    def can_be_deleted(self):
        """Check if template can be deleted (no certificates)."""
        return not self.certificates.exists()
    
    @property
    def can_be_edited(self):
        """Check if template can be edited (no certificates)."""
        return not self.certificates.exists()
    
    # =========================================
    # Methods
    # =========================================
    def set_as_default(self):
        """Set this template as the default for the owner."""
        # Clear other defaults
        CertificateTemplate.objects.filter(
            owner=self.owner,
            is_default=True
        ).exclude(pk=self.pk).update(is_default=False)
        
        self.is_default = True
        self.save(update_fields=['is_default', 'updated_at'])
    
    def create_new_version(self, **changes):
        """
        Create a new version of this template.
        
        Args:
            **changes: Fields to change in new version
        
        Returns:
            New CertificateTemplate instance
        """
        # Mark current as not latest
        self.is_latest_version = False
        self.save(update_fields=['is_latest_version', 'updated_at'])
        
        # Create new version
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
            is_default=self.is_default
        )
        
        # Update default reference if this was default
        if self.is_default:
            self.is_default = False
            self.save(update_fields=['is_default', 'updated_at'])
        
        return new_template
    
    def duplicate(self, new_name=None):
        """
        Create a copy of this template.
        
        Returns:
            New CertificateTemplate instance (version 1)
        """
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
            is_default=False
        )
    
    def increment_usage(self):
        """Increment usage count."""
        from django.db.models import F
        CertificateTemplate.objects.filter(pk=self.pk).update(
            usage_count=F('usage_count') + 1,
            last_used_at=timezone.now()
        )
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('certificates:template_detail', kwargs={'uuid': self.uuid})
```

---

### Certificate

An issued certificate.

```python
import secrets
from django.utils import timezone


def generate_verification_code():
    """Generate unique verification code."""
    return secrets.token_urlsafe(16)  # 22 characters


def generate_short_code():
    """Generate short code for display on certificate."""
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # No ambiguous chars
    return ''.join(secrets.choice(alphabet) for _ in range(8))


class Certificate(SoftDeleteModel):
    """
    An issued certificate.
    
    Immutable after creation — certificate data is snapshotted at issuance
    to preserve historical accuracy even if source data changes.
    
    Soft Delete Behavior:
    - Soft deleted certificates show as "Invalid" on verification
    - Data preserved for audit purposes
    
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
        related_name='certificate',
        help_text="Registration this certificate was issued for"
    )
    template = models.ForeignKey(
        CertificateTemplate,
        on_delete=models.PROTECT,
        related_name='certificates',
        help_text="Template used to generate certificate"
    )
    issued_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='certificates_issued',
        help_text="User who issued the certificate"
    )
    
    # =========================================
    # Verification Codes
    # =========================================
    verification_code = models.CharField(
        max_length=30,
        unique=True,
        default=generate_verification_code,
        db_index=True,
        help_text="Full verification code for URL"
    )
    short_code = models.CharField(
        max_length=10,
        unique=True,
        default=generate_short_code,
        help_text="Short code displayed on certificate"
    )
    
    # =========================================
    # Status
    # =========================================
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True
    )
    
    # Revocation
    revoked_at = models.DateTimeField(
        null=True, blank=True
    )
    revoked_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='certificates_revoked'
    )
    revocation_reason = models.TextField(
        blank=True
    )
    
    # =========================================
    # Generated File
    # =========================================
    file_url = models.URLField(
        blank=True,
        help_text="URL to generated PDF in cloud storage"
    )
    file_generated_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When PDF was generated"
    )
    
    # =========================================
    # Certificate Data Snapshot
    # =========================================
    certificate_data = models.JSONField(
        default=dict,
        help_text="Snapshot of data at time of issuance"
    )
    """
    Schema:
    {
        "attendee_name": "John Smith, MD",
        "attendee_email": "john@example.com",
        "event_title": "Advanced Cardiac Care Workshop",
        "event_date": "2025-01-15",
        "event_datetime": "2025-01-15T14:00:00Z",
        "event_duration_minutes": 60,
        "cpd_type": "CME",
        "cpd_credits": "2.5",
        "cpd_accreditation": "Accredited by XYZ Board",
        "organizer_name": "Medical Education Inc.",
        "organizer_email": "events@meded.com",
        "attendance_minutes": 55,
        "attendance_percent": 92,
        "issued_date": "2025-01-15",
        "issued_datetime": "2025-01-15T16:30:00Z"
    }
    """
    
    # =========================================
    # Delivery
    # =========================================
    email_sent = models.BooleanField(
        default=False
    )
    email_sent_at = models.DateTimeField(
        null=True, blank=True
    )
    
    # =========================================
    # Engagement (denormalized)
    # =========================================
    first_viewed_at = models.DateTimeField(
        null=True, blank=True,
        help_text="First time certificate was viewed"
    )
    view_count = models.PositiveIntegerField(
        default=0
    )
    first_downloaded_at = models.DateTimeField(
        null=True, blank=True,
        help_text="First time PDF was downloaded"
    )
    download_count = models.PositiveIntegerField(
        default=0
    )
    
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
        return f"Certificate: {self.registration.full_name} - {self.event.title}"
    
    # =========================================
    # Properties
    # =========================================
    @property
    def event(self):
        """Shortcut to event."""
        return self.registration.event
    
    @property
    def attendee_name(self):
        """Get attendee name from snapshot."""
        return self.certificate_data.get('attendee_name', self.registration.full_name)
    
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
    
    # =========================================
    # Methods
    # =========================================
    def revoke(self, user, reason=''):
        """
        Revoke the certificate.
        
        Args:
            user: User performing revocation
            reason: Reason for revocation
        """
        if not self.can_be_revoked:
            raise ValueError("Certificate cannot be revoked")
        
        old_status = self.status
        self.status = self.Status.REVOKED
        self.revoked_at = timezone.now()
        self.revoked_by = user
        self.revocation_reason = reason
        self.save(update_fields=[
            'status', 'revoked_at', 'revoked_by', 'revocation_reason', 'updated_at'
        ])
        
        # Create history record
        CertificateStatusHistory.objects.create(
            certificate=self,
            from_status=old_status,
            to_status=self.status,
            changed_by=user,
            reason=reason
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
        """
        Build certificate data snapshot from registration.
        Called at issuance time.
        """
        reg = self.registration
        event = reg.event
        
        self.certificate_data = {
            'attendee_name': reg.full_name,
            'attendee_email': reg.email,
            'attendee_title': reg.professional_title,
            'attendee_organization': reg.organization_name,
            'event_title': event.title,
            'event_date': event.starts_at.date().isoformat(),
            'event_datetime': event.starts_at.isoformat(),
            'event_duration_minutes': event.duration_minutes,
            'cpd_type': event.cpd_credit_type if event.cpd_enabled else '',
            'cpd_credits': str(event.cpd_credit_value) if event.cpd_enabled else '',
            'cpd_accreditation': event.cpd_accreditation_note,
            'organizer_name': event.owner.display_name,
            'organizer_email': event.owner.email,
            'attendance_minutes': reg.total_attendance_minutes,
            'attendance_percent': reg.attendance_percent,
            'issued_date': timezone.now().date().isoformat(),
            'issued_datetime': timezone.now().isoformat()
        }
    
    def send_email(self):
        """Send certificate email to recipient."""
        # Implementation depends on email service
        # Mark as sent
        self.email_sent = True
        self.email_sent_at = timezone.now()
        self.save(update_fields=['email_sent', 'email_sent_at', 'updated_at'])
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('certificates:detail', kwargs={'uuid': self.uuid})
    
    def get_verification_url(self):
        from django.urls import reverse
        return reverse('certificates:verify', kwargs={'code': self.verification_code})


class CertificateStatusHistory(BaseModel):
    """
    Audit log of certificate status changes.
    """
    
    certificate = models.ForeignKey(
        Certificate,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    from_status = models.CharField(
        max_length=20,
        blank=True
    )
    to_status = models.CharField(
        max_length=20
    )
    changed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    reason = models.TextField(
        blank=True
    )
    
    class Meta:
        db_table = 'certificate_status_history'
        ordering = ['-created_at']
        verbose_name = 'Certificate Status History'
        verbose_name_plural = 'Certificate Status Histories'
    
    def __str__(self):
        return f"{self.certificate}: {self.from_status} → {self.to_status}"
```

---

## Certificate Issuance Service

```python
# certificates/services.py

from django.db import transaction
from django.utils import timezone


class CertificateIssuanceService:
    """Service for issuing certificates."""
    
    @classmethod
    @transaction.atomic
    def issue_certificate(cls, registration, template, issued_by, send_email=True):
        """
        Issue a certificate for a registration.
        
        Args:
            registration: Registration to issue certificate for
            template: CertificateTemplate to use
            issued_by: User issuing the certificate
            send_email: Whether to send notification email
        
        Returns:
            Certificate instance
        
        Raises:
            ValueError: If registration is not eligible
        """
        # Validate eligibility
        if not registration.can_receive_certificate:
            raise ValueError("Registration is not eligible for certificate")
        
        if hasattr(registration, 'certificate'):
            raise ValueError("Certificate already issued for this registration")
        
        # Create certificate
        certificate = Certificate(
            registration=registration,
            template=template,
            issued_by=issued_by
        )
        certificate.build_certificate_data()
        certificate.save()
        
        # Update registration
        registration.certificate_issued = True
        registration.certificate_issued_at = timezone.now()
        registration.save(update_fields=[
            'certificate_issued', 'certificate_issued_at', 'updated_at'
        ])
        
        # Update template stats
        template.increment_usage()
        
        # Update event counts
        registration.event.update_counts()
        
        # Generate PDF asynchronously
        from certificates.tasks import generate_certificate_pdf
        generate_certificate_pdf.delay(certificate.id)
        
        # Send email
        if send_email:
            from certificates.tasks import send_certificate_email
            send_certificate_email.delay(certificate.id)
        
        # Create status history
        CertificateStatusHistory.objects.create(
            certificate=certificate,
            from_status='',
            to_status=Certificate.Status.ACTIVE,
            changed_by=issued_by,
            reason='Certificate issued'
        )
        
        return certificate
    
    @classmethod
    def bulk_issue(cls, registrations, template, issued_by, send_emails=True):
        """
        Issue certificates for multiple registrations.
        
        Returns:
            tuple: (issued_count, skipped_count, errors)
        """
        issued = 0
        skipped = 0
        errors = []
        
        for registration in registrations:
            try:
                cls.issue_certificate(
                    registration, template, issued_by, send_email=send_emails
                )
                issued += 1
            except ValueError as e:
                skipped += 1
                errors.append({
                    'registration': registration.id,
                    'email': registration.email,
                    'error': str(e)
                })
        
        return issued, skipped, errors
```

---

## Relationships

```
Certificate
├── Registration (1:1, PROTECT)
├── CertificateTemplate (N:1, PROTECT)
├── User (N:1, PROTECT) — issued_by
├── User (N:1, SET_NULL) — revoked_by
└── CertificateStatusHistory (1:N, CASCADE)

CertificateTemplate
├── User (N:1, PROTECT) — owner
├── Certificate (1:N, PROTECT)
├── Event (1:N, SET_NULL) — default template
└── CertificateTemplate (N:1, SET_NULL) — original_template (versioning)
```

---

## Business Rules

1. **One certificate per registration**: Enforced via OneToOneField
2. **Certificate immutability**: Data snapshotted at issuance
3. **Template immutability**: Cannot edit template with issued certificates
4. **Template versioning**: Create new version instead of editing
5. **Revocation**: Cannot undo (issue new certificate instead)
6. **Verification codes**: Unique, URL-safe, never change
7. **Short codes**: Unique, human-readable, displayed on certificate
8. **PDF generation**: Async task, stored in cloud storage
