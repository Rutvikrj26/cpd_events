"""
Events app serializers.
"""

from rest_framework import serializers
from django.utils import timezone
from django.utils.text import slugify

from common.serializers import SoftDeleteModelSerializer, BaseModelSerializer
from common.utils import generate_unique_slug
from .models import Event, EventStatusHistory, EventCustomField


# =============================================================================
# Custom Field Serializers
# =============================================================================

class EventCustomFieldSerializer(BaseModelSerializer):
    """Custom field definition."""
    
    class Meta:
        model = EventCustomField
        fields = [
            'uuid', 'field_type', 'label', 'placeholder', 'default_value',
            'is_required', 'options', 'validation_regex', 'position',
            'created_at',
        ]
        read_only_fields = ['uuid', 'created_at']


class EventCustomFieldCreateSerializer(serializers.ModelSerializer):
    """Create custom field."""
    
    class Meta:
        model = EventCustomField
        fields = [
            'field_type', 'label', 'placeholder', 'default_value',
            'is_required', 'options', 'validation_regex', 'position',
        ]


# =============================================================================
# Event Serializers
# =============================================================================

class EventListSerializer(SoftDeleteModelSerializer):
    """Lightweight event for list views."""
    owner_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            'uuid', 'slug', 'title', 'status', 'event_type',
            'starts_at', 'ends_at', 'timezone',
            'registration_count', 'attendee_count', 'waitlist_count',
            'owner_name',
            'is_featured', 'is_public',
            'created_at',
        ]
        read_only_fields = fields
    
    def get_owner_name(self, obj):
        return obj.owner.display_name


class EventDetailSerializer(SoftDeleteModelSerializer):
    """Full event detail including multi-session fields (H2)."""
    owner = serializers.SerializerMethodField()
    custom_fields = EventCustomFieldSerializer(many=True, read_only=True)
    duration_display = serializers.CharField(source='duration_display', read_only=True)
    status_transitions = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            'uuid', 'slug', 'title', 'short_description', 'description',
            'status', 'event_type',
            # Scheduling
            'starts_at', 'ends_at', 'timezone', 'duration_minutes', 'duration_display',
            # Multi-session fields (H2)
            'is_multi_session', 'minimum_attendance_percent', 'minimum_attendance_minutes',
            # Registration
            'registration_enabled', 'registration_opens_at', 'registration_closes_at',
            'capacity', 'waitlist_enabled',
            # Zoom
            'zoom_meeting_id', 'zoom_join_url', 'zoom_passcode',  # Only for owners
            # CPD
            'cpd_credits', 'cpd_type', 'cpd_type_display',
            # Certificates
            'certificates_enabled', 'certificate_template',
            'auto_issue_certificates', 'certificate_expiration_months',
            # Branding
            'featured_image_url', 'is_featured', 'is_public',
            # Counts
            'registration_count', 'attendee_count', 'waitlist_count',
            # Owner
            'owner',
            # Custom fields
            'custom_fields',
            # Status transitions
            'status_transitions',
            # Timestamps
            'created_at', 'updated_at', 'published_at', 'completed_at',
        ]
        read_only_fields = [
            'uuid', 'slug', 'status', 'zoom_meeting_id', 'zoom_join_url',
            'registration_count', 'attendee_count', 'waitlist_count',
            'created_at', 'updated_at', 'published_at', 'completed_at',
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


class EventCreateSerializer(serializers.ModelSerializer):
    """Create new event with slug uniqueness validation (M1)."""
    custom_fields = EventCustomFieldCreateSerializer(many=True, required=False)
    
    class Meta:
        model = Event
        fields = [
            'title', 'short_description', 'description', 'event_type',
            # Scheduling
            'starts_at', 'ends_at', 'timezone',
            # Registration
            'registration_enabled', 'registration_opens_at', 'registration_closes_at',
            'capacity', 'waitlist_enabled',
            # CPD
            'cpd_credits', 'cpd_type', 'cpd_type_display',
            # Certificates
            'certificates_enabled', 'certificate_template',
            'auto_issue_certificates', 'certificate_expiration_months',
            # Branding
            'featured_image_url', 'is_featured', 'is_public',
            # Multi-session (H2)
            'is_multi_session', 'minimum_attendance_percent',
            # Custom fields
            'custom_fields',
        ]
    
    def validate(self, attrs):
        # Validate timing
        starts_at = attrs.get('starts_at')
        ends_at = attrs.get('ends_at')
        
        if starts_at and ends_at and ends_at <= starts_at:
            raise serializers.ValidationError({
                'ends_at': 'End time must be after start time.'
            })
        
        return attrs
    
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
    
    class Meta:
        model = Event
        fields = [
            'title', 'short_description', 'description',
            # Scheduling
            'starts_at', 'ends_at', 'timezone',
            # Registration
            'registration_enabled', 'registration_opens_at', 'registration_closes_at',
            'capacity', 'waitlist_enabled',
            # CPD
            'cpd_credits', 'cpd_type', 'cpd_type_display',
            # Certificates
            'certificates_enabled', 'certificate_template',
            'auto_issue_certificates', 'certificate_expiration_months',
            # Branding
            'featured_image_url', 'is_featured', 'is_public',
            # Multi-session (H2)
            'is_multi_session', 'minimum_attendance_percent',
        ]


class EventStatusChangeSerializer(serializers.Serializer):
    """Change event status."""
    status = serializers.ChoiceField(choices=Event.Status.choices)
    reason = serializers.CharField(required=False, max_length=500, allow_blank=True)


# =============================================================================
# Public Event Serializers
# =============================================================================

class PublicEventListSerializer(serializers.ModelSerializer):
    """Public event list for discovery."""
    organizer_name = serializers.SerializerMethodField()
    is_registration_open = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            'uuid', 'slug', 'title', 'short_description', 'event_type',
            'starts_at', 'ends_at', 'timezone',
            'cpd_credits', 'cpd_type_display',
            'organizer_name', 'featured_image_url',
            'is_registration_open', 'registration_count', 'capacity',
        ]
    
    def get_organizer_name(self, obj):
        return obj.owner.display_name
    
    def get_is_registration_open(self, obj):
        now = timezone.now()
        if not obj.registration_enabled:
            return False
        if obj.registration_opens_at and now < obj.registration_opens_at:
            return False
        if obj.registration_closes_at and now > obj.registration_closes_at:
            return False
        return True


class PublicEventDetailSerializer(PublicEventListSerializer):
    """Public event detail with registration info."""
    custom_fields = EventCustomFieldSerializer(many=True, read_only=True)
    organizer = serializers.SerializerMethodField()
    spots_remaining = serializers.SerializerMethodField()
    
    class Meta(PublicEventListSerializer.Meta):
        fields = PublicEventListSerializer.Meta.fields + [
            'description', 'custom_fields', 'organizer',
            'certificates_enabled', 'waitlist_enabled', 'spots_remaining',
        ]
    
    def get_organizer(self, obj):
        return {
            'uuid': str(obj.owner.uuid),
            'display_name': obj.owner.display_name,
            'logo_url': obj.owner.organizer_logo_url,
        }
    
    def get_spots_remaining(self, obj):
        if not obj.capacity:
            return None
        return max(0, obj.capacity - obj.registration_count)


class EventStatusHistorySerializer(BaseModelSerializer):
    """Event status change log."""
    changed_by_name = serializers.CharField(source='changed_by.full_name', read_only=True)
    
    class Meta:
        model = EventStatusHistory
        fields = [
            'uuid', 'from_status', 'to_status', 'reason',
            'changed_by_name', 'created_at',
        ]
        read_only_fields = fields
