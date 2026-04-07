from django.contrib import admin

from conferencing.models import VideoRecording, VideoRecordingFile, VideoRoom, VideoWebhookLog


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
