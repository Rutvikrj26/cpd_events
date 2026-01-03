"""
Integrations app serializers - Recordings API (C3).
"""

from rest_framework import serializers

from common.serializers import BaseModelSerializer

from .models import EmailLog, RecordingView, ZoomRecording, ZoomRecordingFile

# =============================================================================
# Recording Serializers
# =============================================================================


class ZoomRecordingFileSerializer(BaseModelSerializer):
    """Individual recording file."""

    class Meta:
        model = ZoomRecordingFile
        fields = [
            'uuid',
            'file_type',
            'file_size',
            'duration_seconds',
            'is_enabled',
            'download_url',
            'play_url',
            'created_at',
        ]
        read_only_fields = fields


class ZoomRecordingListSerializer(BaseModelSerializer):
    """Lightweight recording for list views."""

    event_title = serializers.CharField(source='event.title', read_only=True)

    class Meta:
        model = ZoomRecording
        fields = [
            'uuid',
            'event_title',
            'status',
            'access_level',
            'total_size',
            'duration_seconds',
            'view_count',
            'unique_viewers',
            'created_at',
        ]
        read_only_fields = fields


class ZoomRecordingDetailSerializer(BaseModelSerializer):
    """Full recording detail - organizer view."""

    event = serializers.SerializerMethodField()
    files = ZoomRecordingFileSerializer(many=True, read_only=True)

    class Meta:
        model = ZoomRecording
        fields = [
            'uuid',
            'event',
            'status',
            'access_level',
            'topic',
            'start_time',
            'duration_seconds',
            'total_size',
            'share_url',
            'files',
            'view_count',
            'unique_viewers',
            'total_watch_time_seconds',
            'zoom_expires_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_event(self, obj):
        return {
            'uuid': str(obj.event.uuid),
            'title': obj.event.title,
            'date': obj.event.starts_at.isoformat() if obj.event.starts_at else None,
        }


class ZoomRecordingUpdateSerializer(serializers.ModelSerializer):
    """Update recording settings."""

    class Meta:
        model = ZoomRecording
        fields = ['access_level']


# =============================================================================
# Attendee Recording Access
# =============================================================================


class AttendeeRecordingSerializer(serializers.ModelSerializer):
    """Recording for attendee access."""

    event = serializers.SerializerMethodField()
    files = serializers.SerializerMethodField()
    can_access = serializers.SerializerMethodField()

    class Meta:
        model = ZoomRecording
        fields = [
            'uuid',
            'event',
            'topic',
            'duration_seconds',
            'files',
            'can_access',
            'created_at',
        ]

    def get_event(self, obj):
        return {
            'uuid': str(obj.event.uuid),
            'title': obj.event.title,
        }

    def get_files(self, obj):
        # Only return enabled files
        enabled_files = obj.files.filter(is_enabled=True)
        return [
            {
                'uuid': str(f.uuid),
                'file_type': f.file_type,
                'duration_seconds': f.duration_seconds,
            }
            for f in enabled_files
        ]

    def get_can_access(self, obj):
        return True  # Already filtered by access checks in view


class RecordingStreamSerializer(serializers.Serializer):
    """Get streaming URL for a recording file."""

    file_uuid = serializers.UUIDField()


class RecordingStreamResponseSerializer(serializers.Serializer):
    """Response with signed streaming URL."""

    streaming_url = serializers.URLField()
    expires_at = serializers.DateTimeField()


# =============================================================================
# Recording Analytics
# =============================================================================


class RecordingAnalyticsSerializer(serializers.Serializer):
    """Recording analytics summary."""

    total_views = serializers.IntegerField()
    unique_viewers = serializers.IntegerField()
    total_watch_time_seconds = serializers.IntegerField()
    average_watch_time_seconds = serializers.IntegerField()
    completion_rate = serializers.FloatField()


class RecordingViewLogSerializer(BaseModelSerializer):
    """Individual view record."""

    viewer_name = serializers.SerializerMethodField()

    class Meta:
        model = RecordingView
        fields = [
            'uuid',
            'viewer_name',
            'started_at',
            'ended_at',
            'watch_duration_seconds',
            'percent_watched',
            'created_at',
        ]
        read_only_fields = fields

    def get_viewer_name(self, obj):
        if obj.viewer:
            return obj.viewer.full_name
        return 'Anonymous'


# =============================================================================
# Email Log Serializers
# =============================================================================


class EmailLogSerializer(BaseModelSerializer):
    """Email log entry."""

    class Meta:
        model = EmailLog
        fields = [
            'uuid',
            'recipient_email',
            'email_type',
            'subject',
            'status',
            'sent_at',
            'delivered_at',
            'opened_at',
            'clicked_at',
            'error_message',
            'created_at',
        ]
        read_only_fields = fields


# =============================================================================
# Zoom Meeting List Serializer (for Zoom Management page)
# =============================================================================


class ZoomMeetingListSerializer(serializers.Serializer):
    """Event with Zoom meeting details for organizer management page."""

    uuid = serializers.UUIDField(source='event_uuid')
    title = serializers.CharField(source='event_title')
    status = serializers.CharField(source='event_status')
    starts_at = serializers.DateTimeField()
    zoom_meeting_id = serializers.CharField()
    zoom_join_url = serializers.URLField()
    zoom_password = serializers.CharField()
    created_at = serializers.DateTimeField(source='event_created_at')

