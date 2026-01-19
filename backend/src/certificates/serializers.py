"""
Certificates app serializers.
"""

from rest_framework import serializers

from common.serializers import BaseModelSerializer, SoftDeleteModelSerializer

from .models import Certificate, CertificateStatusHistory, CertificateTemplate

# =============================================================================
# Template Serializers
# =============================================================================


class CertificateTemplateListSerializer(SoftDeleteModelSerializer):
    """Lightweight template for list views."""

    class Meta:
        model = CertificateTemplate
        fields = [
            "uuid",
            "name",
            "description",
            "file_url",
            "file_type",
            "field_positions",
            "version",
            "is_default",
            "is_latest_version",
            "usage_count",
            "created_at",
        ]
        read_only_fields = fields


class CertificateTemplateDetailSerializer(SoftDeleteModelSerializer):
    """Full template detail."""

    class Meta:
        model = CertificateTemplate
        fields = [
            "uuid",
            "name",
            "description",
            "version",
            "file_url",
            "file_type",
            "field_positions",
            "width_px",
            "height_px",
            "orientation",
            "is_default",
            "is_latest_version",
            "usage_count",
            "original_template",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "uuid",
            "version",
            "is_latest_version",
            "usage_count",
            "original_template",
            "created_at",
            "updated_at",
        ]


class CertificateTemplateCreateSerializer(serializers.ModelSerializer):
    """Create certificate template."""

    class Meta:
        model = CertificateTemplate
        fields = [
            "uuid",
            "name",
            "description",
            "file_url",
            "file_type",
            "field_positions",
            "width_px",
            "height_px",
            "orientation",
            "is_default",
            "version",
            "usage_count",
            "created_at",
        ]
        read_only_fields = ["uuid", "version", "usage_count", "created_at"]
        extra_kwargs = {
            "file_url": {"required": False, "default": ""},
        }


class CertificateTemplateUpdateSerializer(serializers.ModelSerializer):
    """
    Update template with versioning (H1).

    If template has been used, creates new version instead of updating.
    """

    class Meta:
        model = CertificateTemplate
        fields = [
            "name",
            "description",
            "file_url",
            "file_type",
            "field_positions",
            "width_px",
            "height_px",
            "orientation",
            "is_default",
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

    event_title = serializers.CharField(source="event.title", read_only=True)
    registrant_name = serializers.CharField(source="registration.full_name", read_only=True)

    class Meta:
        model = Certificate
        fields = [
            "uuid",
            "event_title",
            "registrant_name",
            "status",
            "short_code",
            "short_code",
            "created_at",
        ]
        read_only_fields = fields


class CertificateDetailSerializer(SoftDeleteModelSerializer):
    """Full certificate detail."""

    event = serializers.SerializerMethodField()
    registration = serializers.SerializerMethodField()
    verification_url = serializers.SerializerMethodField()
    public_url = serializers.SerializerMethodField()
    last_viewed_at = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = [
            "uuid",
            "event",
            "registration",
            "template",
            "status",
            "verification_code",
            "short_code",
            "certificate_data",
            "file_url",
            "public_url",
            "created_at",
            "revocation_reason",
            "revoked_at",
            "revoked_by",
            "view_count",
            "download_count",
            "last_viewed_at",
            "verification_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_event(self, obj):
        return {
            "uuid": str(obj.event.uuid),
            "title": obj.event.title,
            "date": obj.event.starts_at.isoformat() if obj.event.starts_at else None,
        }

    def get_registration(self, obj):
        return {
            "uuid": str(obj.registration.uuid),
            "full_name": obj.registration.full_name,
            "email": obj.registration.email,
        }

    def get_verification_url(self, obj):
        from django.conf import settings

        return f"{settings.SITE_URL}/verify/{obj.short_code}"

    def get_public_url(self, obj):
        from django.conf import settings

        return f"{settings.SITE_URL}/verify/{obj.short_code}"

    def get_last_viewed_at(self, obj):
        return obj.last_viewed_at if hasattr(obj, "last_viewed_at") else None


class CertificateIssueSerializer(serializers.Serializer):
    """Issue certificate to registration(s)."""

    registration_uuids = serializers.ListField(child=serializers.UUIDField(), required=False)
    issue_all_eligible = serializers.BooleanField(default=False)
    send_email = serializers.BooleanField(default=True)

    def validate(self, attrs):
        if not attrs.get("registration_uuids") and not attrs.get("issue_all_eligible"):
            raise serializers.ValidationError("Either registration_uuids or issue_all_eligible is required.")
        return attrs


class CertificateRevokeSerializer(serializers.Serializer):
    """Revoke a certificate."""

    reason = serializers.CharField(max_length=500)


# =============================================================================
# Public Verification Serializers
# =============================================================================


class PublicCertificateVerificationSerializer(serializers.ModelSerializer):
    """Public certificate verification response."""

    file_url = serializers.SerializerMethodField()
    is_valid = serializers.SerializerMethodField()
    event = serializers.SerializerMethodField()
    registrant = serializers.SerializerMethodField()
    organizer = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = [
            "uuid",
            "status",
            "is_valid",
            "event",
            "registrant",
            "organizer",
            "certificate_data",
            "created_at",
            "file_url",
            "verification_code",
        ]

    def get_event(self, obj):
        if obj.registration:
            return {
                "title": obj.event.title,
                "date": obj.event.starts_at.strftime("%B %d, %Y") if obj.event.starts_at else None,
                "cpd_credits": str(obj.event.cpd_credit_value) if obj.event.cpd_credit_value else None,
                "cpd_type": obj.event.cpd_credit_type,
                "type": "event",
            }
        elif obj.course_enrollment:
            return {
                "title": obj.course_enrollment.course.title,
                "date": obj.course_enrollment.completed_at.strftime("%B %d, %Y")
                if obj.course_enrollment.completed_at
                else None,
                "cpd_credits": str(obj.course_enrollment.course.cpd_credits)
                if obj.course_enrollment.course.cpd_credits
                else None,
                "cpd_type": obj.course_enrollment.course.cpd_type,
                "type": "course",
            }
        return None

    def get_registrant(self, obj):
        registrant_name = "Unknown"
        allow_public = False

        if obj.registration:
            registrant_name = obj.registration.full_name
            allow_public = obj.registration.allow_public_verification
        elif obj.course_enrollment:
            registrant_name = obj.course_enrollment.user.display_name
            # Assuming course enrollments might not have the same privacy flag yet, defaulting to True or checking user prefs
            # For now, let's assume public if they shared the link.
            allow_public = True

        # Check if registration allows public verification
        if not allow_public:
            return {"full_name": "[Private]"}
        return {
            "full_name": registrant_name,
        }

    def get_organizer(self, obj):
        if obj.event:
            return {"display_name": obj.event.owner.display_name}
        elif obj.course_enrollment:
            return {"display_name": obj.course_enrollment.course.owner.display_name}
        return {"display_name": "Unknown"}

    def get_is_valid(self, obj):
        # Certificate is valid unless explicitly revoked
        return obj.status != "revoked"

    def get_file_url(self, obj):
        if obj.file_url:
            # For public view, we might want a signed URL if it's private,
            # but usually these are public read if knowing the UUID?
            # Sticking to the service method to be safe.
            from .services import certificate_service

            # 1 hour expiration for the download link on this page load
            return certificate_service.get_pdf_url(obj, expiration_minutes=60)
        return None


class CertificateStatusHistorySerializer(BaseModelSerializer):
    """Status change log."""

    class Meta:
        model = CertificateStatusHistory
        fields = ["uuid", "from_status", "to_status", "notes", "created_at"]
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
    issued_at = serializers.DateTimeField(source="created_at", read_only=True)
    feedback_required = serializers.SerializerMethodField()
    feedback_submitted = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = [
            "uuid",
            "event",
            "status",
            "short_code",
            "issued_at",
            "created_at",
            "is_valid",
            "download_url",
            "share_url",
            "verification_url",
            "view_count",
            "download_count",
            "feedback_required",
            "feedback_submitted",
        ]
        read_only_fields = fields

    def get_verification_url(self, obj):
        from django.conf import settings

        return f"{settings.SITE_URL}/verify/{obj.short_code}"

    def get_event(self, obj):
        if obj.registration:
            return {
                "uuid": str(obj.event.uuid),
                "title": obj.event.title,
                "cpd_credits": str(obj.event.cpd_credit_value) if obj.event.cpd_credit_value else None,
                "cpd_type": obj.event.cpd_credit_type,
                "event_type": obj.event.event_type,  # Ensure this exists on event model or helper
            }
        if obj.course_enrollment:
            return {
                "uuid": str(obj.course_enrollment.course.uuid),
                "title": obj.course_enrollment.course.title,
                "cpd_credits": str(obj.course_enrollment.course.cpd_credits),
                "cpd_type": obj.course_enrollment.course.cpd_type,
                "event_type": "course",
            }
        return None

    def get_download_url(self, obj):
        if obj.status == "active" and obj.file_url:
            # M7: Return signed URL instead of direct URL
            from .services import certificate_service

            return certificate_service.get_pdf_url(obj, expiration_minutes=60)
        return None

    def get_share_url(self, obj):
        from django.conf import settings

        return f"{settings.SITE_URL}/verify/{obj.short_code}"

    def get_is_valid(self, obj):
        # Certificate is valid unless explicitly revoked
        return obj.status != "revoked"

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

        return EventFeedback.objects.filter(event=obj.registration.event, registration=obj.registration).exists()
