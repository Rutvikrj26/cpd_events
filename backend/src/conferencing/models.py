"""
Video conferencing models — provider-agnostic.

Replaces the scattered zoom_* fields and Zoom-specific models with
a clean, centralized conferencing data layer.
"""

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

from common.models import BaseModel


class VideoRoom(BaseModel):
    """
    A video conferencing room linked to an Event, Course, or CourseSession.

    Uses GenericForeignKey so any content object can have a video room
    without scattering provider-specific fields across models.
    """

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        ACTIVE = 'active', 'Active'
        ENDED = 'ended', 'Ended'
        ERROR = 'error', 'Error'

    # Link to Event, Course, or CourseSession
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    # Room identification
    room_id = models.CharField(max_length=200, db_index=True, help_text="Provider's room ID (e.g., LiveKit SID)")
    room_name = models.CharField(max_length=200, unique=True, db_index=True, help_text="Room name used for joining")
    provider = models.CharField(max_length=50, default='livekit', help_text="Video provider name")

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    # Settings
    settings = models.JSONField(default=dict, blank=True, help_text="Provider-agnostic room settings")
    max_participants = models.PositiveIntegerField(default=0, help_text="0 = unlimited")

    # Error tracking
    error = models.TextField(blank=True)
    error_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'video_rooms'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['room_name']),
            models.Index(fields=['room_id']),
            models.Index(fields=['status']),
        ]
        verbose_name = 'Video Room'
        verbose_name_plural = 'Video Rooms'

    def __str__(self):
        return f"{self.room_name} ({self.get_status_display()})"

    def mark_active(self):
        self.status = self.Status.ACTIVE
        self.started_at = timezone.now()
        self.error = ''
        self.save(update_fields=['status', 'started_at', 'error', 'updated_at'])

    def mark_ended(self):
        self.status = self.Status.ENDED
        self.ended_at = timezone.now()
        self.save(update_fields=['status', 'ended_at', 'updated_at'])

    def mark_error(self, message: str):
        self.status = self.Status.ERROR
        self.error = message[:2000]
        self.error_at = timezone.now()
        self.save(update_fields=['status', 'error', 'error_at', 'updated_at'])


class VideoWebhookLog(BaseModel):
    """
    Log of webhook events from the video provider.

    Used for debugging, replay, audit trail, and deduplication.
    Retention: 90 days.
    """

    class EventType(models.TextChoices):
        ROOM_STARTED = 'room_started', 'Room Started'
        ROOM_FINISHED = 'room_finished', 'Room Finished'
        PARTICIPANT_JOINED = 'participant_joined', 'Participant Joined'
        PARTICIPANT_LEFT = 'participant_left', 'Participant Left'
        RECORDING_STARTED = 'recording_started', 'Recording Started'
        RECORDING_ENDED = 'recording_ended', 'Recording Ended'
        OTHER = 'other', 'Other'

    class ProcessingStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        SKIPPED = 'skipped', 'Skipped'

    # Event identification
    webhook_id = models.CharField(
        max_length=200, unique=True, db_index=True, help_text="Provider's webhook delivery ID (deduplication)"
    )
    event_type = models.CharField(max_length=50, choices=EventType.choices, default=EventType.OTHER, db_index=True)
    event_timestamp = models.DateTimeField(help_text="When the event occurred (from provider)")
    provider = models.CharField(max_length=50, default='livekit')

    # Room info
    room_name = models.CharField(max_length=200, db_index=True)
    room_id = models.CharField(max_length=200, blank=True)
    video_room = models.ForeignKey(
        VideoRoom, on_delete=models.SET_NULL, null=True, blank=True, related_name='webhook_logs'
    )

    # Payload
    payload = models.JSONField(default=dict)
    headers = models.JSONField(default=dict)

    # Processing
    processing_status = models.CharField(
        max_length=20, choices=ProcessingStatus.choices, default=ProcessingStatus.PENDING, db_index=True
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_attempts = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)

    # Error tracking
    error_message = models.TextField(blank=True)
    error_traceback = models.TextField(blank=True)

    # Results
    attendance_records_created = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'video_webhook_logs'
        ordering = ['-event_timestamp']
        indexes = [
            models.Index(fields=['event_type', '-event_timestamp']),
            models.Index(fields=['room_name']),
            models.Index(fields=['processing_status', '-created_at']),
        ]
        verbose_name = 'Video Webhook Log'
        verbose_name_plural = 'Video Webhook Logs'

    def __str__(self):
        return f"{self.event_type} - {self.room_name}"

    @property
    def can_retry(self):
        return self.processing_status == self.ProcessingStatus.FAILED and self.processing_attempts < 3

    def start_processing(self):
        self.processing_status = self.ProcessingStatus.PROCESSING
        self.processing_attempts += 1
        self.last_attempt_at = timezone.now()
        self.save(update_fields=['processing_status', 'processing_attempts', 'last_attempt_at', 'updated_at'])

    def mark_completed(self, records_created=0):
        self.processing_status = self.ProcessingStatus.COMPLETED
        self.processed_at = timezone.now()
        self.attendance_records_created = records_created
        self.error_message = ''
        self.error_traceback = ''
        self.save(update_fields=[
            'processing_status', 'processed_at', 'attendance_records_created',
            'error_message', 'error_traceback', 'updated_at',
        ])

    def mark_failed(self, error_message, traceback=''):
        self.processing_status = self.ProcessingStatus.FAILED
        self.error_message = error_message[:1000]
        self.error_traceback = traceback[:5000]
        self.save(update_fields=['processing_status', 'error_message', 'error_traceback', 'updated_at'])

    def mark_skipped(self, reason=''):
        self.processing_status = self.ProcessingStatus.SKIPPED
        self.processed_at = timezone.now()
        self.error_message = reason
        self.save(update_fields=['processing_status', 'processed_at', 'error_message', 'updated_at'])

    @classmethod
    def cleanup_old_logs(cls, days=90):
        cutoff = timezone.now() - timezone.timedelta(days=days)
        count, _ = cls.objects.filter(created_at__lt=cutoff).delete()
        return count


class VideoRecording(BaseModel):
    """
    A recording of a video room session.

    Created when the provider signals that recording/egress has completed.
    """

    class Status(models.TextChoices):
        RECORDING = 'recording', 'Recording'
        PROCESSING = 'processing', 'Processing'
        AVAILABLE = 'available', 'Available'
        ERROR = 'error', 'Error'
        DELETED = 'deleted', 'Deleted'

    class AccessLevel(models.TextChoices):
        REGISTRANTS = 'registrants', 'Confirmed Registrants Only'
        ATTENDEES = 'attendees', 'Attended Only'
        CERTIFICATE_HOLDERS = 'certificate_holders', 'Certificate Holders Only'
        PUBLIC = 'public', 'Public (Anyone with Link)'

    video_room = models.ForeignKey(VideoRoom, on_delete=models.CASCADE, related_name='recordings')
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, null=True, blank=True, related_name='video_recordings')

    # Provider reference
    egress_id = models.CharField(max_length=200, unique=True, db_index=True, help_text="Provider's recording/egress ID")
    provider = models.CharField(max_length=50, default='livekit')

    # Timing
    recording_start = models.DateTimeField(null=True, blank=True)
    recording_end = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    total_size_bytes = models.BigIntegerField(default=0)

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECORDING)

    # Storage
    storage_path = models.CharField(max_length=500, blank=True, help_text="Path to recording file (local or cloud)")

    # Access control
    access_level = models.CharField(max_length=20, choices=AccessLevel.choices, default=AccessLevel.REGISTRANTS)

    # Display
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True, max_length=2000)

    # Visibility
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    auto_publish = models.BooleanField(default=False)

    # Engagement
    view_count = models.PositiveIntegerField(default=0)
    unique_viewers = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'video_recordings'
        ordering = ['-recording_start']
        indexes = [
            models.Index(fields=['video_room']),
            models.Index(fields=['egress_id']),
            models.Index(fields=['status']),
            models.Index(fields=['is_published', '-recording_start']),
        ]
        verbose_name = 'Video Recording'
        verbose_name_plural = 'Video Recordings'

    def __str__(self):
        return f"Recording: {self.title or self.video_room.room_name}"

    @property
    def duration_display(self):
        hours, remainder = divmod(self.duration_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours}h {minutes}m"
        return f"{minutes}m {seconds}s"

    @property
    def is_available(self):
        return self.status == self.Status.AVAILABLE

    def publish(self):
        self.is_published = True
        self.published_at = timezone.now()
        self.save(update_fields=['is_published', 'published_at', 'updated_at'])

    def unpublish(self):
        self.is_published = False
        self.save(update_fields=['is_published', 'updated_at'])


class VideoRecordingFile(BaseModel):
    """
    An individual file within a video recording (e.g., MP4, audio, chat log).
    """

    class FileType(models.TextChoices):
        VIDEO = 'video', 'Video (MP4)'
        AUDIO = 'audio', 'Audio'
        CHAT = 'chat', 'Chat Log'
        TRANSCRIPT = 'transcript', 'Transcript'

    recording = models.ForeignKey(VideoRecording, on_delete=models.CASCADE, related_name='files')

    file_type = models.CharField(max_length=20, choices=FileType.choices)
    file_name = models.CharField(max_length=255, blank=True)
    file_extension = models.CharField(max_length=10, blank=True)
    file_size_bytes = models.BigIntegerField(default=0)

    # Storage
    storage_url = models.CharField(max_length=500, blank=True, help_text="URL or path to the file")

    # Visibility
    is_visible = models.BooleanField(default=True)

    class Meta:
        db_table = 'video_recording_files'
        ordering = ['file_type']
        indexes = [
            models.Index(fields=['recording', 'file_type']),
        ]
        verbose_name = 'Video Recording File'
        verbose_name_plural = 'Video Recording Files'

    def __str__(self):
        return f"{self.recording} - {self.get_file_type_display()}"


class RecordingView(BaseModel):
    """Track who has viewed recordings."""

    recording = models.ForeignKey(VideoRecording, on_delete=models.CASCADE, related_name='views')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='recording_views')

    first_viewed_at = models.DateTimeField(default=timezone.now)
    last_viewed_at = models.DateTimeField(null=True, blank=True)
    view_count = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = 'video_recording_views'
        unique_together = [['recording', 'user']]
        verbose_name = 'Recording View'
        verbose_name_plural = 'Recording Views'
