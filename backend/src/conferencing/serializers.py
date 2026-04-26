"""Serializers for the conferencing app."""

from rest_framework import serializers

from conferencing.models import VideoRecording, VideoRecordingFile, VideoRoom


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
