from django.contrib import admin

from conferencing.models import (
    Transcript,
    TranscriptSegment,
    VideoRecording,
    VideoRecordingFile,
    VideoRoom,
    VideoWebhookLog,
)


@admin.register(VideoRoom)
class VideoRoomAdmin(admin.ModelAdmin):
    list_display = ['room_name', 'status', 'provider', 'started_at', 'ended_at', 'created_at']
    list_filter = ['status', 'provider']
    search_fields = ['room_name', 'room_id']
    readonly_fields = ['uuid', 'room_id', 'room_name', 'content_type', 'object_id']


@admin.register(VideoWebhookLog)
class VideoWebhookLogAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'room_name', 'processing_status', 'event_timestamp']
    list_filter = ['event_type', 'processing_status', 'provider']
    search_fields = ['room_name', 'webhook_id']
    readonly_fields = ['webhook_id', 'payload', 'headers']


@admin.register(VideoRecording)
class VideoRecordingAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'duration_display', 'is_published', 'recording_start']
    list_filter = ['status', 'is_published', 'access_level']
    search_fields = ['title', 'egress_id']


@admin.register(VideoRecordingFile)
class VideoRecordingFileAdmin(admin.ModelAdmin):
    list_display = ['recording', 'file_type', 'file_name', 'file_size_bytes']
    list_filter = ['file_type']


@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    list_display = ['video_room', 'provider', 'language_code', 'status', 'word_count', 'finalized_at']
    list_filter = ['status', 'provider', 'language_code']
    search_fields = ['video_room__room_name', 'provider_model']
    readonly_fields = ['uuid', 'video_room', 'provider', 'provider_model']


@admin.register(TranscriptSegment)
class TranscriptSegmentAdmin(admin.ModelAdmin):
    list_display = ['transcript', 'start_ms', 'end_ms', 'speaker_name_snapshot', 'source', 'is_final']
    list_filter = ['source', 'is_final']
    # Don't put `text` in search_fields without the trgm GIN — full-table
    # ILIKE on a million-row transcript table will lock up the admin.
    # Search by livekit_segment_id + speaker; use the public search
    # endpoint (which uses GIN) for content lookups.
    search_fields = ['livekit_segment_id', 'speaker_name_snapshot']
    raw_id_fields = ['transcript', 'replaced_by', 'edited_by', 'speaker_user']
    readonly_fields = ['uuid', 'livekit_segment_id', 'source']
