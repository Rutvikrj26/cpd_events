"""Serializers for the conferencing app."""

from rest_framework import serializers

from conferencing.models import VideoRecording, VideoRecordingFile, VideoRoom


class VideoRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoRoom
        fields = [
            'uuid', 'room_name', 'status', 'provider',
            'started_at', 'ended_at', 'max_participants',
            'settings', 'created_at',
        ]
        read_only_fields = fields


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
        return VideoRecordingFileSerializer(visible_files, many=True).data


class VideoRecordingFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoRecordingFile
        fields = [
            'uuid', 'file_type', 'file_name', 'file_extension',
            'file_size_bytes', 'storage_url',
        ]
        read_only_fields = fields


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
