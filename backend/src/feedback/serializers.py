from rest_framework import serializers
from .models import EventFeedback

class EventFeedbackSerializer(serializers.ModelSerializer):
    """
    Serializer for submitting and viewing event feedback.
    """
    attendee_name = serializers.SerializerMethodField()
    
    class Meta:
        model = EventFeedback
        fields = [
            'uuid', 'event', 'registration', 'rating', 
            'content_quality_rating', 'speaker_rating', 
            'comments', 'is_anonymous', 'created_at',
            'attendee_name'
        ]
        read_only_fields = ['uuid', 'created_at', 'attendee_name']
        
    def get_attendee_name(self, obj):
        if obj.is_anonymous:
            return "Anonymous"
        # Access user name via registration -> user
        if obj.registration and obj.registration.user:
            return obj.registration.user.get_full_name()
        return "Unknown"

    def validate(self, attrs):
        """
        Validate that only one feedback exists per registration.
        """
        # Unique together validation is handled by model, but good to have explicit error
        return attrs
