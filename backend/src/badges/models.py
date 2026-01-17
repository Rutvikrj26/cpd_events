"""
Badges app models - BadgeTemplate, IssuedBadge.
"""

import secrets
from django.db import models
from django.utils import timezone
from common.models import BaseModel, SoftDeleteModel
from common.validators import validate_field_positions_schema


def generate_verification_code():
    """Generate unique verification code."""
    return secrets.token_urlsafe(16)


def generate_short_code():
    """Generate short code for display on badge."""
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return ''.join(secrets.choice(alphabet) for _ in range(8))


class BadgeTemplate(SoftDeleteModel):
    """
    A template for generating badges.
    
    Similar to certificates but uses images instead of PDFs.
    """

    # Ownership
    owner = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='badge_templates',
        help_text="Organizer who owns this template",
    )
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='badge_templates',
        help_text="Organization that owns this template",
    )

    # Basic Info
    name = models.CharField(max_length=100, help_text="Template name")
    description = models.TextField(blank=True, max_length=500)
    
    # Template Image
    start_image = models.ImageField(
        upload_to='badges/templates/',
        help_text="Base image for the badge (PNG/JPG)"
    )
    width_px = models.PositiveIntegerField(default=500, help_text="Image width in pixels")
    height_px = models.PositiveIntegerField(default=500, help_text="Image height in pixels")

    # Dynamic Field Positions
    field_positions = models.JSONField(
        default=dict,
        validators=[validate_field_positions_schema],
        blank=True,
        help_text="Positions and styling for dynamic fields (x, y, font, color)"
    )

    # Settings
    is_active = models.BooleanField(default=True)
    is_shared = models.BooleanField(default=False)

    class Meta:
        db_table = 'badge_templates'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner']),
            models.Index(fields=['organization']),
        ]

    def __str__(self):
        return self.name


class IssuedBadge(SoftDeleteModel):
    """
    An earned badge issued to a user.
    """

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        REVOKED = 'revoked', 'Revoked'

    # Relationships
    registration = models.ForeignKey(
        'registrations.Registration',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='badges',
    )
    course_enrollment = models.ForeignKey(
        'learning.CourseEnrollment',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='badges',
    )
    template = models.ForeignKey(
        BadgeTemplate,
        on_delete=models.PROTECT,
        related_name='issued_badges',
    )
    recipient = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='earned_badges',
    )
    issued_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='badges_issued',
    )

    # Verification
    verification_code = models.CharField(
        max_length=30,
        unique=True,
        default=generate_verification_code,
        db_index=True
    )
    short_code = models.CharField(
        max_length=10, 
        unique=True, 
        default=generate_short_code
    )

    # Status
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.ACTIVE,
        db_index=True
    )
    issued_at = models.DateTimeField(default=timezone.now)

    # Generated Image
    image_url = models.URLField(blank=True, help_text="URL to generated badge image")
    image_generated_at = models.DateTimeField(null=True, blank=True)

    # Snapshot Data
    badge_data = models.JSONField(default=dict, help_text="Snapshot of data at issuance")

    class Meta:
        db_table = 'issued_badges'
        ordering = ['-issued_at']
        indexes = [
            models.Index(fields=['recipient']),
            models.Index(fields=['template']),
            models.Index(fields=['short_code']),
        ]

    def __str__(self):
        return f"Badge: {self.template.name} - {self.recipient.display_name}"

    def get_verification_url(self):
        """Get full verification URL."""
        from django.conf import settings
        base = getattr(settings, 'SITE_URL', 'https://example.com')
        # Use existing frontend route
        return f"{base}/badges/verify/{self.short_code}"

    @property
    def can_be_revoked(self):
        """Check if badge can be revoked."""
        return self.status == self.Status.ACTIVE

    def revoke(self, user, reason=''):
        """Revoke the badge."""
        if not self.can_be_revoked:
            raise ValueError("Badge cannot be revoked")

        old_status = self.status
        self.status = self.Status.REVOKED
        self.save(update_fields=['status', 'updated_at'])

        BadgeStatusHistory.objects.create(
            badge=self, from_status=old_status, to_status=self.status, changed_by=user, reason=reason
        )


class BadgeStatusHistory(BaseModel):
    """
    Audit log of badge status changes.
    """

    badge = models.ForeignKey(IssuedBadge, on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.TextField(blank=True)

    class Meta:
        db_table = 'badge_status_history'
        ordering = ['-created_at']
        verbose_name = 'Badge Status History'
        verbose_name_plural = 'Badge Status Histories'

    def __str__(self):
        return f"{self.badge}: {self.from_status} → {self.to_status}"
