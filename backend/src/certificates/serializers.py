"""
Certificates app serializers.
"""

from django.utils import timezone
from rest_framework import serializers

from common.serializers import BaseModelSerializer, SoftDeleteModelSerializer

from .models import Certificate, CertificateStatusHistory, CertificateTemplate

# =============================================================================
# Template Serializers
# =============================================================================


class CertificateTemplateListSerializer(SoftDeleteModelSerializer):
    """Lightweight template for list views."""

    organization_name = serializers.CharField(source='organization.name', read_only=True, allow_null=True)
    is_org_template = serializers.SerializerMethodField()

    class Meta:
        model = CertificateTemplate
        fields = [
            'uuid',
            'name',
            'description',
            'file_url',
            'file_type',
            'field_positions',
            'version',
            'is_default',
            'is_shared',
            'is_latest_version',
            'usage_count',
            'organization_name',
            'is_org_template',
            'created_at',
        ]
        read_only_fields = fields

    def get_is_org_template(self, obj):
        return obj.organization_id is not None


class CertificateTemplateDetailSerializer(SoftDeleteModelSerializer):
    """Full template detail."""

    organization_name = serializers.CharField(source='organization.name', read_only=True, allow_null=True)

    class Meta:
        model = CertificateTemplate
        fields = [
            'uuid',
            'name',
            'description',
            'version',
            'file_url',
            'file_type',
            'field_positions',
            'width_px',
            'height_px',
            'orientation',
            'is_default',
            'is_shared',
            'is_latest_version',
            'usage_count',
            'organization_name',
            'original_template',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'uuid',
            'version',
            'is_latest_version',
            'usage_count',
            'organization_name',
            'original_template',
            'created_at',
            'updated_at',
        ]


class CertificateTemplateCreateSerializer(serializers.ModelSerializer):
    """Create certificate template."""

    class Meta:
        model = CertificateTemplate
        fields = [
            'uuid',
            'name',
            'description',
            'file_url',
            'file_type',
            'field_positions',
            'width_px',
            'height_px',
            'orientation',
            'is_default',
            'version',
            'usage_count',
            'created_at',
        ]
        read_only_fields = ['uuid', 'version', 'usage_count', 'created_at']
        extra_kwargs = {
            'file_url': {'required': False, 'default': ''},
        }


class CertificateTemplateUpdateSerializer(serializers.ModelSerializer):
    """
    Update template with versioning (H1).

    If template has been used, creates new version instead of updating.
    """

    class Meta:
        model = CertificateTemplate
        fields = [
            'name',
            'description',
            'file_url',
            'file_type',
            'field_positions',
            'width_px',
            'height_px',
            'orientation',
            'is_default',
        ]

    def update(self, instance, validated_data):
        # Check if template has been used
        if instance.usage_count > 0:
            # Create new version instead of updating
            new_template = instance.create_new_version()

            # Apply changes to new version
            for key, value in validated_data.items():
                setattr(new_template, key, value)
            new_template.save()

            return new_template

        return super().update(instance, validated_data)


# =============================================================================
# Certificate Serializers
# =============================================================================


class CertificateListSerializer(SoftDeleteModelSerializer):
    """Lightweight certificate for list views."""

    event_title = serializers.CharField(source='event.title', read_only=True)
    registrant_name = serializers.CharField(source='registration.full_name', read_only=True)

    class Meta:
        model = Certificate
        fields = [
            'uuid',
            'event_title',
            'registrant_name',
            'status',
            'short_code',
            'short_code',
            'created_at',
        ]
        read_only_fields = fields


class CertificateDetailSerializer(SoftDeleteModelSerializer):
    """Full certificate detail."""

    event = serializers.SerializerMethodField()
    registration = serializers.SerializerMethodField()
    verification_url = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = [
            'uuid',
            'event',
            'registration',
            'template',
            'status',
            'verification_code',
            'short_code',
            'certificate_data',
            'file_url',
            'public_url',
            'created_at',
            'revocation_reason',
            'revoked_at',
            'revoked_by',
            'view_count',
            'download_count',
            'last_viewed_at',
            'verification_url',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_event(self, obj):
        return {
            'uuid': str(obj.event.uuid),
            'title': obj.event.title,
            'date': obj.event.starts_at.isoformat() if obj.event.starts_at else None,
        }

    def get_registration(self, obj):
        return {
            'uuid': str(obj.registration.uuid),
            'full_name': obj.registration.full_name,
            'email': obj.registration.email,
        }

    def get_verification_url(self, obj):
        from django.conf import settings

        return f"{settings.SITE_URL}/verify/{obj.short_code}"


class CertificateIssueSerializer(serializers.Serializer):
    """Issue certificate to registration(s)."""

    registration_uuids = serializers.ListField(child=serializers.UUIDField(), required=False)
    issue_all_eligible = serializers.BooleanField(default=False)
    send_email = serializers.BooleanField(default=True)

    def validate(self, attrs):
        if not attrs.get('registration_uuids') and not attrs.get('issue_all_eligible'):
            raise serializers.ValidationError('Either registration_uuids or issue_all_eligible is required.')
        return attrs


class CertificateRevokeSerializer(serializers.Serializer):
    """Revoke a certificate."""

    reason = serializers.CharField(max_length=500)


# =============================================================================
# Public Verification Serializers
# =============================================================================


class PublicCertificateVerificationSerializer(serializers.ModelSerializer):
    """Public certificate verification response."""

    event = serializers.SerializerMethodField()
    registrant = serializers.SerializerMethodField()
    organizer = serializers.SerializerMethodField()
    is_valid = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = [
            'status',
            'is_valid',
            'event',
            'registrant',
            'organizer',
            'certificate_data',
            'created_at',
        ]

    def get_event(self, obj):
        return {
            'title': obj.event.title,
            'date': obj.event.starts_at.strftime('%B %d, %Y') if obj.event.starts_at else None,
            'cpd_credits': str(obj.event.cpd_credit_value) if obj.event.cpd_credit_value else None,
            'cpd_type': obj.event.cpd_credit_type,
        }

    def get_registrant(self, obj):
        # Check if registration allows public verification
        if not obj.registration.allow_public_verification:
            return {'full_name': '[Private]'}
        return {
            'full_name': obj.registration.full_name,
        }

    def get_organizer(self, obj):
        return {
            'display_name': obj.event.owner.display_name,
        }

    def get_is_valid(self, obj):
        # Certificate is valid unless explicitly revoked
        return obj.status != 'revoked'


class CertificateStatusHistorySerializer(BaseModelSerializer):
    """Status change log."""

    class Meta:
        model = CertificateStatusHistory
        fields = ['uuid', 'from_status', 'to_status', 'notes', 'created_at']
        read_only_fields = fields


# =============================================================================
# Attendee Certificate Serializers
# =============================================================================


class MyCertificateSerializer(SoftDeleteModelSerializer):
    """Certificate from attendee's perspective."""

    event = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    share_url = serializers.SerializerMethodField()
    verification_url = serializers.SerializerMethodField()
    is_valid = serializers.SerializerMethodField()
    issued_at = serializers.DateTimeField(source='created_at', read_only=True)
    feedback_required = serializers.SerializerMethodField()
    feedback_submitted = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = [
            'uuid',
            'event',
            'status',
            'short_code',
            'issued_at',
            'created_at',
            'is_valid',
            'download_url',
            'share_url',
            'verification_url',
            'view_count',
            'download_count',
            'feedback_required',
            'feedback_submitted',
        ]
        read_only_fields = fields

    def get_verification_url(self, obj):
        from django.conf import settings

        return f"{settings.SITE_URL}/verify/{obj.short_code}"

    def get_event(self, obj):
        if obj.registration:
            return {
                'uuid': str(obj.event.uuid),
                'title': obj.event.title,
                'cpd_credits': str(obj.event.cpd_credit_value) if obj.event.cpd_credit_value else None,
                'cpd_type': obj.event.cpd_credit_type,
                'event_type': obj.event.event_type, # Ensure this exists on event model or helper
            }
        if obj.course_enrollment:
            return {
                'uuid': str(obj.course_enrollment.course.uuid),
                'title': obj.course_enrollment.course.title,
                'cpd_credits': str(obj.course_enrollment.course.cpd_credits),
                'cpd_type': obj.course_enrollment.course.cpd_type,
                'event_type': 'course',
            }
        return None

    def get_download_url(self, obj):
        if obj.status == 'active' and obj.file_url:
            # M7: Return signed URL instead of direct URL
            from .services import certificate_service

            return certificate_service.get_pdf_url(obj, expiration_minutes=60)
        return None

    def get_share_url(self, obj):
        from django.conf import settings

        return f"{settings.SITE_URL}/verify/{obj.short_code}"

    def get_is_valid(self, obj):
        # Certificate is valid unless explicitly revoked
        return obj.status != 'revoked'

    def get_feedback_required(self, obj):
        """Check if feedback is required for this certificate."""
        if obj.registration:
            return obj.registration.event.require_feedback_for_certificate
        return False

    def get_feedback_submitted(self, obj):
        """Check if feedback has been submitted for this certificate."""
        if not obj.registration:
            return True  # No feedback needed if no registration

        from feedback.models import EventFeedback
        return EventFeedback.objects.filter(
            event=obj.registration.event,
            registration=obj.registration
        ).exists()
