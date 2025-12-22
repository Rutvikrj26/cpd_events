"""
Registrations app serializers.

Field names match the actual model fields:
- email (not guest_email)
- full_name (not guest_name)
- first_join_at (not join_time)
- last_leave_at (not leave_time)
- total_attendance_minutes
- attendance_eligible
- promoted_from_waitlist_at (not waitlisted_at/promoted_at)
"""

from rest_framework import serializers

from common.serializers import BaseModelSerializer, MinimalEventSerializer, MinimalUserSerializer, SoftDeleteModelSerializer

from .models import AttendanceRecord, CustomFieldResponse, Registration

# =============================================================================
# Attendance Serializers
# =============================================================================


class AttendanceRecordSerializer(BaseModelSerializer):
    """Individual Zoom join/leave record."""

    class Meta:
        model = AttendanceRecord
        fields = [
            'uuid',
            'join_time',
            'leave_time',
            'duration_minutes',
            'join_method',
            'device_type',
            'zoom_user_name',
            'zoom_user_email',
            'is_matched',
            'created_at',
        ]
        read_only_fields = fields


class AttendanceUpdateSerializer(serializers.Serializer):
    """Manual attendance update by organizer."""

    attended = serializers.BooleanField()
    attendance_eligible = serializers.BooleanField(required=False)
    notes = serializers.CharField(required=False, max_length=500)


class AttendanceOverrideSerializer(serializers.Serializer):
    """Override attendance eligibility."""

    eligible = serializers.BooleanField()
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)


# =============================================================================
# Custom Field Response Serializers
# =============================================================================


class CustomFieldResponseSerializer(serializers.Serializer):
    """Custom field response data."""

    field_uuid = serializers.UUIDField()
    field_label = serializers.CharField()
    value = serializers.JSONField()


class CustomFieldResponseDetailSerializer(BaseModelSerializer):
    """Full custom field response."""

    field_label = serializers.CharField(source='field.label', read_only=True)
    field_type = serializers.CharField(source='field.field_type', read_only=True)

    class Meta:
        model = CustomFieldResponse
        fields = ['uuid', 'field_label', 'field_type', 'value', 'created_at']
        read_only_fields = fields


# =============================================================================
# Registration Serializers
# =============================================================================


class RegistrationListSerializer(SoftDeleteModelSerializer):
    """Lightweight registration for list views."""

    user = MinimalUserSerializer(read_only=True)
    event_title = serializers.CharField(source='event.title', read_only=True)
    attendance_percent = serializers.IntegerField(read_only=True)

    certificate_uuid = serializers.UUIDField(source='certificate.uuid', read_only=True, allow_null=True)

    class Meta:
        model = Registration
        fields = [
            'uuid',
            'user',
            'event_title',
            'email',
            'full_name',
            'status',
            'attended',
            'check_in_time',
            'total_attendance_minutes',
            'attendance_eligible',
            'attendance_percent',
            'attendance_override',
            'certificate_issued',
            'certificate_uuid',
            'waitlist_position',
            'created_at',
        ]
        read_only_fields = fields


class RegistrationDetailSerializer(SoftDeleteModelSerializer):
    """Full registration detail."""

    user = MinimalUserSerializer(read_only=True)
    event = MinimalEventSerializer(read_only=True)
    custom_field_responses = CustomFieldResponseDetailSerializer(many=True, read_only=True)
    attendance_records = AttendanceRecordSerializer(many=True, read_only=True)
    attendance_percent = serializers.IntegerField(read_only=True)
    can_receive_certificate = serializers.BooleanField(read_only=True)

    class Meta:
        model = Registration
        fields = [
            'uuid',
            'user',
            'event',
            'status',
            # Contact info
            'email',
            'full_name',
            'professional_title',
            'organization_name',
            # Source
            'source',
            # Attendance
            'attended',
            'check_in_time',
            'first_join_at',
            'last_leave_at',
            'total_attendance_minutes',
            'attendance_percent',
            'attendance_eligible',
            'attendance_override',
            'attendance_override_reason',
            'attendance_records',
            # Certificate
            'certificate_issued',
            'certificate_issued_at',
            'can_receive_certificate',
            # Privacy
            'allow_public_verification',
            # Custom fields
            'custom_field_responses',
            # Waitlist
            'waitlist_position',
            'promoted_from_waitlist_at',
            # Cancellation
            'cancelled_at',
            'cancellation_reason',
            # Timestamps
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class RegistrationCreateSerializer(serializers.Serializer):
    """
    Register for an event.

    For authenticated users: email optional (uses account email)
    For guests: email required
    """

    email = serializers.EmailField(required=False)
    full_name = serializers.CharField(required=False, max_length=255)
    professional_title = serializers.CharField(required=False, max_length=255, allow_blank=True)
    organization_name = serializers.CharField(required=False, max_length=255, allow_blank=True)
    custom_field_responses = serializers.DictField(required=False)
    allow_public_verification = serializers.BooleanField(default=True)

    def validate(self, attrs):
        request = self.context.get('request')

        # Guest registration requires email
        if not request or not request.user.is_authenticated:
            if not attrs.get('email'):
                raise serializers.ValidationError({'email': 'Email required for guest registration.'})
            if not attrs.get('full_name'):
                raise serializers.ValidationError({'full_name': 'Name required for guest registration.'})

        return attrs


class RegistrationBulkCreateSerializer(serializers.Serializer):
    """Bulk add registrations (organizer use)."""

    registrations = serializers.ListField(child=serializers.DictField(), min_length=1, max_length=500)
    send_confirmation = serializers.BooleanField(default=True)

    def validate_registrations(self, value):
        for reg in value:
            if 'email' not in reg:
                raise serializers.ValidationError('Each registration requires an email.')
        return value


# =============================================================================
# Attendee-facing Serializers
# =============================================================================


class MyRegistrationSerializer(SoftDeleteModelSerializer):
    """Registration from attendee's perspective."""

    event = MinimalEventSerializer(read_only=True)
    zoom_join_url = serializers.SerializerMethodField()
    can_join = serializers.SerializerMethodField()
    certificate_url = serializers.SerializerMethodField()
    attendance_percent = serializers.IntegerField(read_only=True)

    class Meta:
        model = Registration
        fields = [
            'uuid',
            'event',
            'status',
            'email',
            'full_name',
            'attended',
            'attendance_percent',
            'attendance_eligible',
            'certificate_issued',
            'certificate_issued_at',
            'allow_public_verification',
            'waitlist_position',
            'promoted_from_waitlist_at',
            'zoom_join_url',
            'can_join',
            'certificate_url',
            'created_at',
        ]
        read_only_fields = fields

    def get_zoom_join_url(self, obj):
        if obj.status == 'confirmed' and obj.event.status in ['published', 'live']:
            return obj.event.zoom_join_url
        return None

    def get_can_join(self, obj):
        return obj.status == 'confirmed' and obj.event.status in ['published', 'live']

    def get_certificate_url(self, obj):
        if obj.certificate_issued:
            try:
                cert = obj.certificate
                return f"/api/v1/certificates/{cert.uuid}/"
            except Exception:
                pass
        return None


class WaitlistPositionSerializer(serializers.Serializer):
    """Waitlist position info for attendee."""

    position = serializers.IntegerField()
    total_waitlisted = serializers.IntegerField()
    estimated_chance = serializers.CharField()


class RegistrationCancelSerializer(serializers.Serializer):
    """Cancel registration request."""

    reason = serializers.CharField(required=False, max_length=500, allow_blank=True)
