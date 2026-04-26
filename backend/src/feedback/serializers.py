from rest_framework import serializers

from events.models import Event, EventSession
from registrations.models import Registration

from .models import EventFeedback, FeedbackField, FeedbackFieldResponse


class FeedbackFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackField
        fields = [
            'uuid',
            'label',
            'field_type',
            'required',
            'placeholder',
            'help_text',
            'options',
            'min_value',
            'max_value',
            'order',
            'created_at',
        ]
        read_only_fields = ['uuid', 'created_at']


class FeedbackFieldCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackField
        fields = [
            'label',
            'field_type',
            'required',
            'placeholder',
            'help_text',
            'options',
            'min_value',
            'max_value',
            'order',
        ]


class FeedbackFieldResponseSerializer(serializers.ModelSerializer):
    field_uuid = serializers.UUIDField(source='field.uuid', read_only=True)
    field_label = serializers.CharField(source='field.label', read_only=True)
    field_type = serializers.CharField(source='field.field_type', read_only=True)
    field_order = serializers.IntegerField(source='field.order', read_only=True)

    class Meta:
        model = FeedbackFieldResponse
        fields = ['uuid', 'field_uuid', 'field_label', 'field_type', 'field_order', 'value']
        read_only_fields = fields


class EventFeedbackSerializer(serializers.ModelSerializer):
    """
    Read / write serializer for submitting and viewing feedback.

    On write, `responses` is a {field_uuid: value} dict. On read it is
    serialized as a list of FeedbackFieldResponseSerializer entries.
    """

    attendee_name = serializers.SerializerMethodField()
    event = serializers.SlugRelatedField(slug_field='uuid', queryset=Event.objects.all())
    session = serializers.SlugRelatedField(
        slug_field='uuid', queryset=EventSession.objects.all(), required=False, allow_null=True
    )
    registration = serializers.SlugRelatedField(slug_field='uuid', queryset=Registration.objects.all())
    responses = serializers.DictField(write_only=True, required=False)
    field_responses = FeedbackFieldResponseSerializer(many=True, read_only=True)

    class Meta:
        model = EventFeedback
        fields = [
            'uuid',
            'event',
            'session',
            'registration',
            'is_anonymous',
            'created_at',
            'attendee_name',
            'responses',
            'field_responses',
        ]
        read_only_fields = ['uuid', 'created_at', 'attendee_name', 'field_responses']

    def get_attendee_name(self, obj):
        if obj.is_anonymous:
            return "Anonymous"
        if obj.registration and obj.registration.user:
            return obj.registration.user.full_name or obj.registration.user.email
        return "Unknown"

    def validate(self, attrs):
        event = attrs.get('event') or getattr(self.instance, 'event', None)
        session = attrs.get('session') if 'session' in attrs else getattr(self.instance, 'session', None)
        responses = attrs.get('responses') or {}

        if not event:
            return attrs

        fields = list(event.feedback_fields.all())
        field_by_uuid = {str(f.uuid): f for f in fields}

        missing_required = [
            f.label
            for f in fields
            if f.required and (str(f.uuid) not in responses or responses[str(f.uuid)] in (None, ''))
        ]
        if missing_required and not self.instance:
            raise serializers.ValidationError(
                {'responses': f"Required fields missing: {', '.join(missing_required)}"}
            )

        unknown = [k for k in responses if k not in field_by_uuid]
        if unknown:
            raise serializers.ValidationError(
                {'responses': f"Unknown field(s): {', '.join(unknown)}"}
            )

        if session and session.event_id != event.id:
            raise serializers.ValidationError({'session': 'Session does not belong to this event.'})

        return attrs

    def create(self, validated_data):
        responses = validated_data.pop('responses', {}) or {}
        feedback = EventFeedback.objects.create(**validated_data)
        self._persist_responses(feedback, responses)
        return feedback

    def update(self, instance, validated_data):
        responses = validated_data.pop('responses', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if responses is not None:
            instance.field_responses.all().delete()
            self._persist_responses(instance, responses)
        return instance

    @staticmethod
    def _persist_responses(feedback, responses):
        field_by_uuid = {
            str(f.uuid): f for f in feedback.event.feedback_fields.all()
        }
        for field_uuid, value in responses.items():
            field = field_by_uuid.get(str(field_uuid))
            if field is None:
                continue
            FeedbackFieldResponse.objects.update_or_create(
                feedback=feedback,
                field=field,
                defaults={'value': value},
            )
