"""
Events app serializers.
"""

from django.utils import timezone
from django.utils.text import slugify
from rest_framework import serializers

from common.serializers import BaseModelSerializer, SoftDeleteModelSerializer
from common.utils import generate_unique_slug

from .models import Event, EventCustomField, EventStatusHistory
from .sessions import EventSession, SessionAttendance
from certificates.models import CertificateTemplate

# =============================================================================
# Custom Field Serializers
# =============================================================================


class EventCustomFieldSerializer(BaseModelSerializer):
    """Custom field definition."""

    class Meta:
        model = EventCustomField
        fields = [
            'uuid',
            'field_type',
            'label',
            'placeholder',
            'default_value',
            'is_required',
            'options',
            'validation_regex',
            'position',
            'created_at',
        ]
        read_only_fields = ['uuid', 'created_at']


class EventCustomFieldCreateSerializer(serializers.ModelSerializer):
    """Create custom field."""

    class Meta:
        model = EventCustomField
        fields = [
            'field_type',
            'label',
            'placeholder',
            'default_value',
            'is_required',
            'options',
            'validation_regex',
            'position',
        ]


# =============================================================================
# Event Serializers
# =============================================================================


class EventListSerializer(SoftDeleteModelSerializer):
    """Lightweight event for list views."""

    owner_name = serializers.SerializerMethodField()
    registration_count = serializers.IntegerField(read_only=True)
    attendee_count = serializers.IntegerField(read_only=True)
    attendee_count = serializers.IntegerField(read_only=True)
    waitlist_count = serializers.IntegerField(read_only=True)
    featured_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'uuid',
            'slug',
            'title',
            'status',
            'event_type',
            'starts_at',
            'ends_at',
            'timezone',
            'registration_count',
            'attendee_count',
            'waitlist_count',
            'owner_name',
            'is_public',
            'is_public',
            'featured_image_url',
            'created_at',
        ]
        read_only_fields = fields

    def get_owner_name(self, obj):
        return obj.owner.display_name

    def get_featured_image_url(self, obj):
        """Return featured image URL."""
        if obj.featured_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.featured_image.url)
            return obj.featured_image.url
        return None


class EventDetailSerializer(SoftDeleteModelSerializer):
    """Full event detail including multi-session fields (H2)."""

    owner = serializers.SerializerMethodField()
    custom_fields = EventCustomFieldSerializer(many=True, read_only=True)
    status_transitions = serializers.SerializerMethodField()
    # Field aliases to match API contract with model field names
    capacity = serializers.IntegerField(source='max_attendees', read_only=True)
    zoom_passcode = serializers.CharField(source='zoom_password', read_only=True)
    cpd_credits = serializers.DecimalField(source='cpd_credit_value', max_digits=5, decimal_places=2, read_only=True)
    cpd_type = serializers.CharField(source='cpd_credit_type', read_only=True)
    featured_image_url = serializers.SerializerMethodField()
    attendee_count = serializers.IntegerField(source='attendance_count', read_only=True)
    certificate_template = serializers.SlugRelatedField(read_only=True, slug_field='uuid')

    class Meta:
        model = Event
        fields = [
            'uuid',
            'slug',
            'title',
            'short_description',
            'description',
            'status',
            'event_type',
            'format',
            # Scheduling
            'starts_at',
            'ends_at',
            'timezone',
            'duration_minutes',
            # Multi-session fields (H2)
            'is_multi_session',
            'minimum_attendance_percent',
            'minimum_attendance_minutes',
            # Registration
            'registration_enabled',
            'registration_opens_at',
            'registration_closes_at',
            'capacity',
            'waitlist_enabled',
            'waitlist_max',
            'waitlist_auto_promote',
            # Zoom
            'zoom_meeting_id',
            'zoom_join_url',
            'zoom_passcode',
            'zoom_settings',
            # CPD
            'cpd_credits',
            'cpd_type',
            # Certificates
            'certificates_enabled',
            'certificate_template',
            'auto_issue_certificates',
            # Branding
            'featured_image_url',
            'location',
            'is_public',
            # Counts
            'registration_count',
            'attendee_count',
            'waitlist_count',
            # Owner
            'owner',
            # Custom fields
            'custom_fields',
            # Status transitions
            'status_transitions',
            # Timestamps
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'uuid',
            'slug',
            'status',
            'zoom_meeting_id',
            'zoom_join_url',
            'registration_count',
            'attendee_count',
            'waitlist_count',
            'created_at',
            'updated_at',
        ]

    def get_owner(self, obj):
        return {
            'uuid': str(obj.owner.uuid),
            'display_name': obj.owner.display_name,
        }

    def get_status_transitions(self, obj):
        """Available status transitions for current status."""
        transitions = {
            'draft': ['published'],
            'published': ['live', 'cancelled', 'draft'],
            'live': ['completed'],
            'completed': ['closed'],
            'closed': [],
            'cancelled': [],
        }
        return transitions.get(obj.status, [])

    def get_featured_image_url(self, obj):
        """Return featured image URL, preferring uploaded image over URL."""
        if obj.featured_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.featured_image.url)
            return obj.featured_image.url
        return None


class EventCreateSerializer(serializers.ModelSerializer):
    """Create new event with slug uniqueness validation (M1)."""

    custom_fields = EventCustomFieldCreateSerializer(many=True, required=False)
    certificate_template = serializers.SlugRelatedField(
        slug_field='uuid', queryset=CertificateTemplate.objects.all(), required=False, allow_null=True
    )


    class Meta:
        model = Event
        fields = [
            'uuid',
            'slug',
            'title',
            'short_description',
            'description',
            'event_type',
            'format',
            # Scheduling
            'starts_at',
            'duration_minutes',
            'timezone',
            # Registration
            'registration_enabled',
            'registration_deadline',
            'registration_opens_at',
            'registration_closes_at',
            'max_attendees',
            'waitlist_enabled',
            'waitlist_max',
            'waitlist_auto_promote',
            # CPD
            'cpd_credit_value',
            'cpd_credit_type',
            # Certificates
            'certificates_enabled',
            'certificate_template',
            'auto_issue_certificates',
            # Branding
            'is_public',
            # Attendance
            'minimum_attendance_percent',
            'minimum_attendance_minutes',
            'custom_fields',
            'zoom_settings',
            # Location
            'location',
            # Multi-session
            'is_multi_session',
        ]
        read_only_fields = ['uuid', 'slug']



    def create(self, validated_data):
        custom_fields_data = validated_data.pop('custom_fields', [])

        # Generate unique slug (M1)
        title = validated_data.get('title', '')
        base_slug = slugify(title)[:40]
        validated_data['slug'] = generate_unique_slug(Event, base_slug)

        event = super().create(validated_data)

        # Create custom fields
        for position, field_data in enumerate(custom_fields_data):
            field_data['position'] = position
            EventCustomField.objects.create(event=event, **field_data)

        return event


class EventUpdateSerializer(serializers.ModelSerializer):
    """Update existing event."""

    certificate_template = serializers.SlugRelatedField(
        slug_field='uuid', queryset=CertificateTemplate.objects.all(), required=False, allow_null=True
    )
    certificate_template = serializers.SlugRelatedField(
        slug_field='uuid', queryset=CertificateTemplate.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = Event
        fields = [
            'title',
            'short_description',
            'description',
            'format',
            # Scheduling
            'starts_at',
            'duration_minutes',
            'timezone',
            # Registration
            'registration_enabled',
            'registration_opens_at',
            'registration_closes_at',
            'max_attendees',
            'waitlist_enabled',
            'waitlist_max',
            'waitlist_auto_promote',
            # CPD
            'cpd_credit_value',
            'cpd_credit_type',
            # Certificates
            'certificates_enabled',
            'certificate_template',
            'auto_issue_certificates',
            # Branding
            # Branding
            'is_public',
            'minimum_attendance_percent',
            'minimum_attendance_minutes',
            'zoom_settings',
            # Location
            'location',
            # Multi-session
            'is_multi_session',
        ]

    def validate(self, attrs):
        """
        Validate that the event can be updated.
        """
        instance = self.instance
        if instance and instance.starts_at <= timezone.now():
             raise serializers.ValidationError("Cannot edit event details after the event has started.")
        return attrs


class EventStatusChangeSerializer(serializers.Serializer):
    """Change event status."""

    status = serializers.ChoiceField(choices=Event.Status.choices)
    reason = serializers.CharField(required=False, max_length=500, allow_blank=True)


# =============================================================================
# Public Event Serializers
# =============================================================================


class PublicSessionSerializer(serializers.ModelSerializer):
    """Session info for public event display (agenda view)."""

    ends_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = EventSession
        fields = [
            'uuid',
            'title',
            'description',
            'speaker_names',
            'order',
            'starts_at',
            'ends_at',
            'duration_minutes',
            'session_type',
            'is_mandatory',
        ]
        read_only_fields = fields


class PublicEventListSerializer(serializers.ModelSerializer):
    """Public event list for discovery."""

    organizer_name = serializers.SerializerMethodField()
    is_registration_open = serializers.SerializerMethodField()
    # Field aliases to match API contract with model field names
    cpd_credits = serializers.DecimalField(source='cpd_credit_value', max_digits=5, decimal_places=2, read_only=True)
    featured_image_url = serializers.SerializerMethodField()
    capacity = serializers.IntegerField(source='max_attendees', read_only=True)

    class Meta:
        model = Event
        fields = [
            'uuid',
            'slug',
            'title',
            'short_description',
            'event_type',
            'format',
            'starts_at',
            'ends_at',
            'duration_minutes',
            'timezone',
            'cpd_credits',
            'organizer_name',
            'featured_image_url',
            'is_registration_open',
            'registration_count',
            'capacity',
        ]

    def get_organizer_name(self, obj):
        return obj.owner.display_name

    def get_is_registration_open(self, obj):
        now = timezone.now()
        if not obj.registration_enabled:
            return False
        if obj.registration_opens_at and now < obj.registration_opens_at:
            return False
        return not (obj.registration_closes_at and now > obj.registration_closes_at)

    def get_featured_image_url(self, obj):
        """Return featured image URL, preferring uploaded image over URL."""
        if obj.featured_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.featured_image.url)
            return obj.featured_image.url
        return None


class PublicEventDetailSerializer(PublicEventListSerializer):
    """Public event detail with registration info."""

    custom_fields = EventCustomFieldSerializer(many=True, read_only=True)
    organizer = serializers.SerializerMethodField()
    spots_remaining = serializers.SerializerMethodField()
    sessions = serializers.SerializerMethodField()

    class Meta(PublicEventListSerializer.Meta):
        fields = PublicEventListSerializer.Meta.fields + [
            'description',
            'custom_fields',
            'organizer',
            'certificates_enabled',
            'waitlist_enabled',
            'spots_remaining',
            'is_multi_session',
            'sessions',
            'location',
        ]

    def get_organizer(self, obj):
        return {
            'uuid': str(obj.owner.uuid),
            'display_name': obj.owner.display_name,
            'logo_url': obj.owner.organizer_logo_url,
        }

    def get_spots_remaining(self, obj):
        if not obj.max_attendees:
            return None
        return max(0, obj.max_attendees - obj.registration_count)

    def get_sessions(self, obj):
        """Return published sessions for multi-session events."""
        if not obj.is_multi_session:
            return []
        sessions = obj.sessions.filter(is_published=True).order_by('order', 'starts_at')
        return PublicSessionSerializer(sessions, many=True).data


class EventStatusHistorySerializer(BaseModelSerializer):
    """Event status change log."""

    changed_by_name = serializers.CharField(source='changed_by.full_name', read_only=True)

    class Meta:
        model = EventStatusHistory
        fields = [
            'uuid',
            'from_status',
            'to_status',
            'reason',
            'changed_by_name',
            'created_at',
        ]
        read_only_fields = fields


# =============================================================================
# Session Serializers (C1: Multi-Session Events API)
# =============================================================================


class EventSessionListSerializer(BaseModelSerializer):
    """Lightweight session for list views."""

    is_past = serializers.BooleanField(read_only=True)
    ends_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = EventSession
        fields = [
            'uuid',
            'title',
            'order',
            'starts_at',
            'ends_at',
            'duration_minutes',
            'timezone',
            'session_type',
            'is_mandatory',
            'is_published',
            'is_past',
            'cpd_credits',
            'created_at',
        ]
        read_only_fields = fields


class EventSessionDetailSerializer(BaseModelSerializer):
    """Full session detail."""

    is_past = serializers.BooleanField(read_only=True)
    ends_at = serializers.DateTimeField(read_only=True)
    minimum_required_minutes = serializers.IntegerField(read_only=True)
    attendance_count = serializers.SerializerMethodField()

    class Meta:
        model = EventSession
        fields = [
            'uuid',
            'title',
            'description',
            'order',
            'starts_at',
            'ends_at',
            'duration_minutes',
            'timezone',
            'session_type',
            # Zoom
            'has_separate_zoom',
            'zoom_meeting_id',
            'zoom_join_url',
            # CPD
            'cpd_credits',
            # Attendance
            'minimum_attendance_percent',
            'minimum_required_minutes',
            # Status
            'is_mandatory',
            'is_published',
            'is_past',
            'attendance_count',
            # Timestamps
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'uuid',
            'ends_at',
            'is_past',
            'minimum_required_minutes',
            'zoom_meeting_id',
            'zoom_join_url',
            'attendance_count',
            'created_at',
            'updated_at',
        ]

    def get_attendance_count(self, obj):
        """Count attendees for this session."""
        return SessionAttendance.objects.filter(session=obj, is_eligible=True).count()


class EventSessionCreateSerializer(serializers.ModelSerializer):
    """Create a new session."""

    class Meta:
        model = EventSession
        fields = [
            'title',
            'description',
            'order',
            'starts_at',
            'duration_minutes',
            'timezone',
            'session_type',
            'cpd_credits',
            'minimum_attendance_percent',
            'is_mandatory',
            'is_published',
        ]


class EventSessionUpdateSerializer(serializers.ModelSerializer):
    """Update an existing session."""

    class Meta:
        model = EventSession
        fields = [
            'title',
            'description',
            'order',
            'starts_at',
            'duration_minutes',
            'timezone',
            'session_type',
            'cpd_credits',
            'minimum_attendance_percent',
            'is_mandatory',
            'is_published',
        ]


class SessionReorderSerializer(serializers.Serializer):
    """Reorder sessions within an event."""

    order = serializers.ListField(child=serializers.UUIDField(), help_text="List of session UUIDs in desired order")


class SessionAttendanceSerializer(BaseModelSerializer):
    """Session attendance for a registration."""

    session_title = serializers.CharField(source='session.title', read_only=True)
    session_starts_at = serializers.DateTimeField(source='session.starts_at', read_only=True)
    attendance_percent = serializers.IntegerField(read_only=True)
    final_eligibility = serializers.BooleanField(read_only=True)

    class Meta:
        model = SessionAttendance
        fields = [
            'uuid',
            'session',
            'session_title',
            'session_starts_at',
            'joined_at',
            'left_at',
            'duration_minutes',
            'attendance_percent',
            'is_eligible',
            'override_eligible',
            'override_reason',
            'final_eligibility',
            'created_at',
        ]
        read_only_fields = fields


class SessionAttendanceOverrideSerializer(serializers.Serializer):
    """Override session attendance eligibility."""

    eligible = serializers.BooleanField()
    reason = serializers.CharField(max_length=500)
