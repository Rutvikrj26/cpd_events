from rest_framework import serializers

from badges.models import BadgeTemplate, IssuedBadge


class BadgeTemplateSerializer(serializers.ModelSerializer):
    """Serializer for Badge templates."""

    class Meta:
        model = BadgeTemplate
        fields = [
            'uuid', 'name', 'description',
            'start_image', 'width_px', 'height_px',
            'field_positions', 'is_active', 'is_shared',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Set owner from context
        validated_data['owner'] = self.context['request'].user
        # Optional: set organization if user is in one context
        return super().create(validated_data)


class IssuedBadgeSerializer(serializers.ModelSerializer):
    """Serializer for issued badges."""
    template_name = serializers.CharField(source='template.name', read_only=True)
    recipient_name = serializers.CharField(source='recipient.display_name', read_only=True)
    image_url = serializers.CharField(read_only=True)

    # Event/Course details
    event_title = serializers.SerializerMethodField()
    course_title = serializers.SerializerMethodField()

    class Meta:
        model = IssuedBadge
        fields = [
            'uuid', 'template', 'template_name',
            'recipient_name', 'image_url',
            'verification_code', 'short_code',
            'status', 'issued_at',
            'event_title', 'course_title',
            'badge_data'
        ]
        read_only_fields = fields

    def get_event_title(self, obj):
        if obj.registration:
            return obj.registration.event.title
        return None

    def get_course_title(self, obj):
        if obj.course_enrollment:
            return obj.course_enrollment.course.title
        return None
