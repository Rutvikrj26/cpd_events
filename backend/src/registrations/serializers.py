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

import logging

from rest_framework import serializers

logger = logging.getLogger(__name__)

from common.serializers import BaseModelSerializer, MinimalEventSerializer, MinimalUserSerializer, SoftDeleteModelSerializer

from .models import AttendanceRecord, CustomFieldResponse, Registration

# =============================================================================
# Attendance Serializers
# =============================================================================


class AttendanceRecordSerializer(BaseModelSerializer):
    """Individual join/leave record from the video provider."""

    class Meta:
        model = AttendanceRecord
        fields = [
            'uuid',
            'join_time',
            'leave_time',
            'duration_minutes',
            'join_method',
            'device_type',
            'participant_name',
            'participant_email',
            'is_matched',
            'created_at',
        ]
        read_only_fields = fields


class UnmatchedAttendanceRecordSerializer(BaseModelSerializer):
    """Unmatched attendance record with fuzzy match suggestions."""

    match_suggestions = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceRecord
        fields = [
            'uuid',
            'participant_name',
            'participant_email',
            'join_time',
            'leave_time',
            'duration_minutes',
            'join_method',
            'device_type',
            'created_at',
            'match_suggestions',
        ]
        read_only_fields = fields

    def get_match_suggestions(self, obj):
        """Return potential registration matches based on email/name similarity."""
        from difflib import SequenceMatcher

        event = obj.event
        registrations = event.registrations.filter(
            status__in=['confirmed', 'waitlisted'],
            deleted_at__isnull=True
        ).only('uuid', 'full_name', 'email')

        suggestions = []
        attendee_email = (obj.participant_email or '').lower()
        attendee_name = (obj.participant_name or '').lower()

        for reg in registrations:
            reg_email = (reg.email or '').lower()
            reg_name = (reg.full_name or '').lower()

            # Calculate similarity scores
            email_score = SequenceMatcher(None, attendee_email, reg_email).ratio() if attendee_email and reg_email else 0
            name_score = SequenceMatcher(None, attendee_name, reg_name).ratio() if attendee_name and reg_name else 0

            # Use best score
            best_score = max(email_score, name_score)

            # Only include if similarity > 40%
            if best_score >= 0.4:
                suggestions.append({
                    'uuid': str(reg.uuid),
                    'full_name': reg.full_name,
                    'email': reg.email,
                    'confidence': round(best_score * 100),
                    'match_type': 'email' if email_score >= name_score else 'name',
                })

        # Sort by confidence descending, limit to top 5
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        return suggestions[:5]


class AttendanceMatchSerializer(serializers.Serializer):
    """Request to match an attendance record to a registration."""

    registration_uuid = serializers.UUIDField()


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
    purchase_uuid = serializers.SerializerMethodField()

    certificate_uuid = serializers.SerializerMethodField()

    def get_certificate_uuid(self, obj):
        cert = obj.certificates.filter(
            status='active', deleted_at__isnull=True
        ).order_by('-created_at').first()
        return str(cert.uuid) if cert else None

    def get_purchase_uuid(self, obj):
        """Surface the unified-receipt UUID for refund flows in the attendees roster."""
        return str(obj.purchase.uuid) if obj.purchase_id else None

    class Meta:
        model = Registration
        fields = [
            'uuid',
            'user',
            'event_title',
            'email',
            'full_name',
            'status',
            'payment_status',
            'amount_paid',
            'tax_amount',
            'total_amount',
            'stripe_checkout_session_id',
            'purchase_uuid',
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
    purchase_uuid = serializers.SerializerMethodField()

    def get_purchase_uuid(self, obj):
        """Surface the unified-receipt UUID for refund flows."""
        return str(obj.purchase.uuid) if obj.purchase_id else None

    class Meta:
        model = Registration
        fields = [
            'uuid',
            'user',
            'event',
            'status',
            'payment_status',
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
            # Payment
            'amount_paid',
            'tax_amount',
            'total_amount',
            'payment_intent_id',
            'stripe_checkout_session_id',
            'purchase_uuid',
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


class AttendeeInputSerializer(serializers.Serializer):
    """One attendee row in a multi-attendee registration submission."""

    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=255)
    professional_title = serializers.CharField(required=False, max_length=255, allow_blank=True)
    organization_name = serializers.CharField(required=False, max_length=255, allow_blank=True)
    allow_public_verification = serializers.BooleanField(default=True)


class RegistrationCreateSerializer(serializers.Serializer):
    """
    Register for an event. Supports either:

    - Single-attendee (legacy): top-level email/full_name/professional_title/...
    - Multi-attendee:           top-level ``attendees`` list (1..25 entries).

    For authenticated users: email optional in the single-attendee shape.
    For guests: email always required (per attendee in multi-attendee).
    """

    # Single-attendee fields (all optional — only validated when
    # ``attendees`` is omitted).
    email = serializers.EmailField(required=False)
    full_name = serializers.CharField(required=False, max_length=255)
    professional_title = serializers.CharField(required=False, max_length=255, allow_blank=True)
    organization_name = serializers.CharField(required=False, max_length=255, allow_blank=True)
    allow_public_verification = serializers.BooleanField(default=True)

    # Multi-attendee field. When present, the single-attendee fields are ignored.
    attendees = serializers.ListField(
        child=AttendeeInputSerializer(),
        required=False,
        min_length=1,
        max_length=25,
    )

    # Custom fields are global per submission (event-level fields apply to
    # all attendees uniformly).
    custom_field_responses = serializers.DictField(required=False)

    def validate(self, attrs):
        request = self.context.get('request')
        attendees = attrs.get('attendees')

        if attendees:
            return attrs  # AttendeeInputSerializer enforces email + full_name per row.

        # Single-attendee shape — guest mode still requires email + full_name.
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
    """Registration from attendee's perspective.

    ``view_state`` is the discriminated UI projection — six kinds the
    My Registrations cards exhaustively switch on. See
    ``learning.view_states.derive_registration_view_state`` for the
    derivation. Consumers should bind to ``view_state.kind`` rather than
    composing ``status × payment_status × event.is_past`` themselves.
    """

    event = MinimalEventSerializer(read_only=True)
    meeting_join_url = serializers.SerializerMethodField()
    can_join = serializers.SerializerMethodField()
    certificate_url = serializers.SerializerMethodField()
    attendance_percent = serializers.IntegerField(read_only=True)
    view_state = serializers.SerializerMethodField()

    class Meta:
        model = Registration
        fields = [
            'uuid',
            'event',
            'status',
            'payment_status',
            'email',
            'full_name',
            'attended',
            'attendance_percent',
            'attendance_eligible',
            'certificate_issued',
            'certificate_issued_at',
            'amount_paid',
            'tax_amount',
            'total_amount',
            'stripe_checkout_session_id',
            'allow_public_verification',
            'waitlist_position',
            'promoted_from_waitlist_at',
            'meeting_join_url',
            'can_join',
            'certificate_url',
            'view_state',
            'created_at',
        ]
        read_only_fields = fields

    def get_view_state(self, obj):
        from learning.view_states import derive_registration_view_state

        return derive_registration_view_state(obj)

    def get_meeting_join_url(self, obj):
        """Return video join URL if available. Clients should use the in-app /join-video endpoint instead."""
        return None

    def get_can_join(self, obj):
        return obj.status == 'confirmed' and obj.event.status in ['published', 'live']

    def get_certificate_url(self, obj):
        if obj.certificate_issued:
            try:
                cert = obj.certificates.filter(
                    status='active', deleted_at__isnull=True
                ).order_by('-created_at').first()
                if cert:
                    return f"/api/v1/certificates/{cert.uuid}/"
            except Exception as e:
                logger.warning(f"Failed to resolve certificate for registration {obj.uuid}: {e}")
        return None


class WaitlistPositionSerializer(serializers.Serializer):
    """Waitlist position info for attendee."""

    position = serializers.IntegerField()
    total_waitlisted = serializers.IntegerField()
    estimated_chance = serializers.CharField()


class RegistrationCancelSerializer(serializers.Serializer):
    """Cancel registration request."""

    reason = serializers.CharField(required=False, max_length=500, allow_blank=True)


class RegistrationRefundSerializer(serializers.Serializer):
    """Refund registration request.

    ``amount_cents`` is optional; if omitted, issues a full refund. ``reason``
    is required because refunds are audit-logged and a blank reason makes the
    audit entry useless during later review.
    """

    reason = serializers.CharField(required=True, max_length=500, allow_blank=False)
    amount_cents = serializers.IntegerField(required=False, min_value=1)
