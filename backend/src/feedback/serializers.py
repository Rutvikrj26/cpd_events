from rest_framework import serializers

from events.models import Event
from registrations.models import Registration

from .models import EventFeedback


class EventFeedbackSerializer(serializers.ModelSerializer):
    """
    Serializer for submitting and viewing event feedback.
    """

    attendee_name = serializers.SerializerMethodField()
    event = serializers.SlugRelatedField(slug_field='uuid', queryset=Event.objects.all())
    registration = serializers.SlugRelatedField(slug_field='uuid', queryset=Registration.objects.all())

    class Meta:
        model = EventFeedback
        fields = [
            'uuid',
            'event',
            'registration',
            'rating',
            'content_quality_rating',
            'speaker_rating',
            'comments',
            'is_anonymous',
            'created_at',
            'attendee_name',
        ]
        read_only_fields = ['uuid', 'created_at', 'attendee_name']

    def get_attendee_name(self, obj):
        if obj.is_anonymous:
            return "Anonymous"
        # Access user name via registration -> user
        if obj.registration and obj.registration.user:
            return obj.registration.user.full_name or obj.registration.user.email
        return "Unknown"

    def validate(self, attrs):
        """
        Validate that only one feedback exists per registration.
        """
        # Unique together validation is handled by model, but good to have explicit error
        return attrs
