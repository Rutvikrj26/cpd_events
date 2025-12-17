from django.contrib import admin

from .models import EmailLog, ZoomRecording, ZoomRecordingFile, ZoomWebhookLog


@admin.register(ZoomWebhookLog)
class ZoomWebhookLogAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'zoom_meeting_id', 'processing_status', 'event_timestamp')
    list_filter = ('event_type', 'processing_status')
    search_fields = ('webhook_id', 'zoom_meeting_id')
    ordering = ('-event_timestamp',)
    readonly_fields = ('payload', 'headers')


class ZoomRecordingFileInline(admin.TabularInline):
    model = ZoomRecordingFile
    extra = 0
    readonly_fields = ('zoom_file_id', 'file_type', 'file_size_bytes')


@admin.register(ZoomRecording)
class ZoomRecordingAdmin(admin.ModelAdmin):
    list_display = ('event', 'status', 'is_published', 'duration_seconds', 'view_count')
    list_filter = ('status', 'is_published', 'access_level')
    search_fields = ('event__title', 'zoom_recording_id')
    inlines = [ZoomRecordingFileInline]


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('recipient_email', 'email_type', 'status', 'sent_at')
    list_filter = ('email_type', 'status')
    search_fields = ('recipient_email', 'subject')
    ordering = ('-created_at',)
