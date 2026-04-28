"""Serializers for the conferencing app."""

from rest_framework import serializers

from conferencing.models import (
    Transcript,
    TranscriptSegment,
    VideoRecording,
    VideoRecordingFile,
    VideoRoom,
)


class VideoRoomSerializer(serializers.ModelSerializer):
    target = serializers.SerializerMethodField()

    class Meta:
        model = VideoRoom
        fields = [
            'uuid', 'room_name', 'status', 'provider',
            'started_at', 'ended_at', 'max_participants',
            'settings', 'created_at',
            'target',
        ]
        read_only_fields = fields

    def get_target(self, obj):
        """
        Resolve the join-target for this room (event vs course session).
        Used by admin live-rooms widget to build a one-click host-join button.
        """
        from events.models import Event
        from learning.models import CourseSession

        ct = obj.content_type
        if ct.model_class() is Event:
            try:
                event = Event.objects.get(id=obj.object_id)
            except Event.DoesNotExist:
                return None
            return {'kind': 'event', 'event_uuid': str(event.uuid), 'title': event.title}
        if ct.model_class() is CourseSession:
            try:
                session = CourseSession.objects.select_related('course').get(id=obj.object_id)
            except CourseSession.DoesNotExist:
                return None
            return {
                'kind': 'course_session',
                'course_uuid': str(session.course.uuid),
                'session_uuid': str(session.uuid),
                'title': f'{session.course.title} — {session.title}',
            }
        return None


class VideoRecordingSerializer(serializers.ModelSerializer):
    files = serializers.SerializerMethodField()
    duration_display = serializers.CharField(read_only=True)
    event_uuid = serializers.SerializerMethodField()

    class Meta:
        model = VideoRecording
        fields = [
            'uuid', 'title', 'description', 'status',
            'recording_start', 'recording_end',
            'duration_seconds', 'duration_display', 'total_size_bytes',
            'access_level', 'is_published', 'published_at',
            'view_count', 'unique_viewers',
            'files', 'event_uuid', 'created_at',
        ]
        read_only_fields = fields

    def get_event_uuid(self, obj):
        return str(obj.event.uuid) if obj.event_id else None

    def get_files(self, obj):
        visible_files = obj.files.filter(is_visible=True)
        return VideoRecordingFileSerializer(
            visible_files, many=True, context=self.context,
        ).data


class VideoRecordingFileSerializer(serializers.ModelSerializer):
    storage_url = serializers.SerializerMethodField()

    class Meta:
        model = VideoRecordingFile
        fields = [
            'uuid', 'file_type', 'file_name', 'file_extension',
            'file_size_bytes', 'storage_url',
        ]
        read_only_fields = fields

    def get_storage_url(self, obj):
        """
        Build a signed streaming URL fresh on every serialize. Returns an
        absolute URL because the <video> element resolves it against the
        page's origin, which in dev points at vite (5173) — not the backend.

        The browser's <video> element can't attach our SPA JWT, so the URL
        itself carries a short-lived TimestampSigner token scoped to this
        file's uuid.
        """
        from django.core.signing import TimestampSigner

        signer = TimestampSigner(salt='video-recording-stream')
        token = signer.sign(str(obj.uuid))
        path = (
            f'/api/v1/video/recordings/{obj.recording.uuid}'
            f'/files/{obj.uuid}/stream/?t={token}'
        )
        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(path)
        return path


class JoinVideoResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    ws_url = serializers.CharField()
    room_name = serializers.CharField()
    room_uuid = serializers.CharField()
    is_host = serializers.BooleanField()
    waiting = serializers.BooleanField()
    waiting_room_enabled = serializers.BooleanField()
    recording_enabled_default = serializers.BooleanField()
    recording_active = serializers.BooleanField()


class VideoStatusSerializer(serializers.Serializer):
    configured = serializers.BooleanField()
    provider = serializers.CharField()


# =========================================================================
# Transcripts
# =========================================================================
#
# Serializer split:
#
#   TranscriptSegmentReadSerializer  — public read shape (panel + search).
#                                      Excludes provenance the UI doesn't
#                                      need; includes speaker attribution
#                                      snapshot.
#
#   TranscriptSegmentHistorySerializer — read shape for the audit-trail
#                                        endpoint (organisers only).
#                                        Adds source/edited_by/edited_at.
#
#   TranscriptSegmentIngestSerializer — agent-only WRITE shape. Validates
#                                       livekit_segment_id is non-empty
#                                       (the unique-constraint condition)
#                                       and clamps confidence to [0, 1].
#
#   TranscriptSegmentEditSerializer  — organiser PATCH shape. Only `text`
#                                      is editable; timing and speaker
#                                      attribution are immutable for
#                                      compliance traceability.
#
#   TranscriptSerializer             — wraps a Transcript with its current
#                                      segments (filtered to replaced_by
#                                      __isnull=True).


class TranscriptSegmentReadSerializer(serializers.ModelSerializer):
    speaker_name = serializers.CharField(source='speaker_name_snapshot', read_only=True)

    class Meta:
        model = TranscriptSegment
        fields = [
            'uuid',
            'start_ms',
            'end_ms',
            'text',
            'is_final',
            'participant_identity',
            'speaker_name',
            'confidence',
        ]
        read_only_fields = fields


class TranscriptSegmentHistorySerializer(TranscriptSegmentReadSerializer):
    """Read shape that exposes provenance for the audit-trail endpoint.

    Inherits from the public read serializer so any field added to the
    public shape automatically lands here too — preventing drift where
    history shows fewer fields than the live transcript view.
    """

    edited_by_name = serializers.SerializerMethodField()

    class Meta(TranscriptSegmentReadSerializer.Meta):
        fields = TranscriptSegmentReadSerializer.Meta.fields + [
            'source',
            'edited_at',
            'edited_by_name',
            'created_at',
        ]
        read_only_fields = fields

    def get_edited_by_name(self, obj) -> str:
        return obj.edited_by.full_name if obj.edited_by_id else ''


class TranscriptSegmentIngestSerializer(serializers.Serializer):
    """Validates a single segment posted by the agent."""

    livekit_segment_id = serializers.CharField(max_length=128)
    start_ms = serializers.IntegerField(min_value=0)
    end_ms = serializers.IntegerField(min_value=0)
    text = serializers.CharField(allow_blank=False, max_length=10_000)
    is_final = serializers.BooleanField(default=True)
    participant_identity = serializers.CharField(
        required=False, allow_blank=True, max_length=255,
    )
    speaker_name = serializers.CharField(
        required=False, allow_blank=True, max_length=255,
    )
    # Some plugins (Whisper) don't emit confidence — accept null so the
    # agent doesn't need to fabricate a value.
    confidence = serializers.FloatField(
        required=False, allow_null=True, min_value=0.0, max_value=1.0,
    )

    def validate(self, attrs):
        if attrs['end_ms'] < attrs['start_ms']:
            raise serializers.ValidationError(
                {'end_ms': 'end_ms must be >= start_ms'}
            )
        return attrs


class TranscriptSegmentEditSerializer(serializers.Serializer):
    """Validates an organiser edit payload.

    Only `text` is editable — timing, speaker attribution, and provenance
    are immutable so the audit trail records exactly what the STT said
    versus what was changed. If an organiser needs to retime a segment,
    they should use the recording's chapter/marker tooling (separate
    feature) rather than rewriting transcript history.
    """

    text = serializers.CharField(allow_blank=False, max_length=10_000)


class TranscriptSerializer(serializers.ModelSerializer):
    segments = serializers.SerializerMethodField()

    class Meta:
        model = Transcript
        fields = [
            'uuid',
            'provider',
            'provider_model',
            'language_code',
            'status',
            'started_at',
            'finalized_at',
            'word_count',
            'error_message',
            'segments',
        ]
        read_only_fields = fields

    def get_segments(self, obj):
        # Default read filters to the *current* version of each segment
        # (replaced_by IS NULL) so consumers don't have to know about the
        # edit history schema. The history endpoint exposes the full chain
        # for auditors.
        qs = obj.segments.filter(replaced_by__isnull=True).order_by('start_ms')
        return TranscriptSegmentReadSerializer(qs, many=True).data
