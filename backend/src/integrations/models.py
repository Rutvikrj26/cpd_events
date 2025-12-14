"""
Integrations app models - ZoomWebhookLog, ZoomRecording, ZoomRecordingFile, EmailLog.
"""

from django.db import models
from django.utils import timezone

from common.models import BaseModel


class ZoomWebhookLog(BaseModel):
    """
    Log of Zoom webhook events.
    
    Purposes:
    - Debug delivery issues
    - Replay failed events
    - Audit trail
    - Duplicate detection
    
    Retention: 90 days (cleanup job deletes older records)
    """
    
    class EventType(models.TextChoices):
        MEETING_STARTED = 'meeting.started', 'Meeting Started'
        MEETING_ENDED = 'meeting.ended', 'Meeting Ended'
        PARTICIPANT_JOINED = 'meeting.participant_joined', 'Participant Joined'
        PARTICIPANT_LEFT = 'meeting.participant_left', 'Participant Left'
        PARTICIPANT_WAITING = 'meeting.participant_joined_waiting_room', 'Participant Waiting'
        WEBINAR_STARTED = 'webinar.started', 'Webinar Started'
        WEBINAR_ENDED = 'webinar.ended', 'Webinar Ended'
        RECORDING_COMPLETED = 'recording.completed', 'Recording Completed'
        OTHER = 'other', 'Other'
    
    class ProcessingStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        SKIPPED = 'skipped', 'Skipped'
    
    # =========================================
    # Event Identification
    # =========================================
    webhook_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Zoom's webhook delivery ID (for deduplication)"
    )
    event_type = models.CharField(
        max_length=50,
        choices=EventType.choices,
        default=EventType.OTHER,
        db_index=True
    )
    event_timestamp = models.DateTimeField(
        help_text="When event occurred (from Zoom)"
    )
    
    # =========================================
    # Meeting/Event Info
    # =========================================
    zoom_meeting_id = models.CharField(
        max_length=20,
        db_index=True,
        help_text="Zoom meeting ID"
    )
    zoom_meeting_uuid = models.CharField(
        max_length=100,
        blank=True,
        help_text="Zoom meeting UUID (unique per instance)"
    )
    
    # Link to our event (if matched)
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='zoom_webhooks',
        help_text="Matched platform event"
    )
    
    # =========================================
    # Payload
    # =========================================
    payload = models.JSONField(
        default=dict,
        help_text="Full webhook payload"
    )
    headers = models.JSONField(
        default=dict,
        help_text="Request headers (for debugging)"
    )
    
    # =========================================
    # Processing
    # =========================================
    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
        db_index=True
    )
    processed_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When processing completed"
    )
    processing_attempts = models.PositiveIntegerField(
        default=0,
        help_text="Number of processing attempts"
    )
    last_attempt_at = models.DateTimeField(
        null=True, blank=True
    )
    
    # Error tracking
    error_message = models.TextField(
        blank=True,
        help_text="Error message if processing failed"
    )
    error_traceback = models.TextField(
        blank=True,
        help_text="Full traceback for debugging"
    )
    
    # Results
    attendance_records_created = models.PositiveIntegerField(
        default=0,
        help_text="Number of attendance records created"
    )
    
    class Meta:
        db_table = 'zoom_webhook_logs'
        ordering = ['-event_timestamp']
        indexes = [
            models.Index(fields=['webhook_id']),
            models.Index(fields=['event_type', '-event_timestamp']),
            models.Index(fields=['zoom_meeting_id']),
            models.Index(fields=['processing_status', '-created_at']),
            models.Index(fields=['event', '-event_timestamp']),
            models.Index(fields=['-created_at']),
        ]
        verbose_name = 'Zoom Webhook Log'
        verbose_name_plural = 'Zoom Webhook Logs'
    
    def __str__(self):
        return f"{self.event_type} - {self.zoom_meeting_id}"
    
    @property
    def is_processable(self):
        """Check if webhook can be processed."""
        return self.processing_status in [
            self.ProcessingStatus.PENDING,
            self.ProcessingStatus.FAILED
        ]
    
    @property
    def can_retry(self):
        """Check if failed webhook can be retried."""
        return (
            self.processing_status == self.ProcessingStatus.FAILED and
            self.processing_attempts < 3
        )
    
    def start_processing(self):
        """Mark webhook as being processed."""
        self.processing_status = self.ProcessingStatus.PROCESSING
        self.processing_attempts += 1
        self.last_attempt_at = timezone.now()
        self.save(update_fields=[
            'processing_status', 'processing_attempts', 
            'last_attempt_at', 'updated_at'
        ])
    
    def mark_completed(self, records_created=0):
        """Mark processing as completed."""
        self.processing_status = self.ProcessingStatus.COMPLETED
        self.processed_at = timezone.now()
        self.attendance_records_created = records_created
        self.error_message = ''
        self.error_traceback = ''
        self.save(update_fields=[
            'processing_status', 'processed_at', 
            'attendance_records_created', 'error_message',
            'error_traceback', 'updated_at'
        ])
    
    def mark_failed(self, error_message, traceback=''):
        """Mark processing as failed."""
        self.processing_status = self.ProcessingStatus.FAILED
        self.error_message = error_message[:1000]
        self.error_traceback = traceback[:5000]
        self.save(update_fields=[
            'processing_status', 'error_message', 
            'error_traceback', 'updated_at'
        ])
    
    def mark_skipped(self, reason=''):
        """Mark as skipped (e.g., unknown meeting)."""
        self.processing_status = self.ProcessingStatus.SKIPPED
        self.processed_at = timezone.now()
        self.error_message = reason
        self.save(update_fields=[
            'processing_status', 'processed_at', 
            'error_message', 'updated_at'
        ])
    
    def match_event(self):
        """Try to match webhook to a platform event."""
        from events.models import Event
        
        if self.event:
            return self.event
        
        try:
            event = Event.objects.get(
                zoom_meeting_id=self.zoom_meeting_id,
                deleted_at__isnull=True
            )
            self.event = event
            self.save(update_fields=['event', 'updated_at'])
            return event
        except Event.DoesNotExist:
            return None
    
    @classmethod
    def cleanup_old_logs(cls, days=90):
        """Delete logs older than specified days."""
        cutoff = timezone.now() - timezone.timedelta(days=days)
        count, _ = cls.objects.filter(created_at__lt=cutoff).delete()
        return count


class ZoomRecording(BaseModel):
    """
    A Zoom cloud recording for an event.
    
    Created from Zoom webhook when recording is completed.
    """
    
    class Status(models.TextChoices):
        PROCESSING = 'processing', 'Processing'
        AVAILABLE = 'available', 'Available'
        EXPIRED = 'expired', 'Expired'
        DELETED = 'deleted', 'Deleted'
        ERROR = 'error', 'Error'
    
    class AccessLevel(models.TextChoices):
        REGISTRANTS = 'registrants', 'Confirmed Registrants Only'
        ATTENDEES = 'attendees', 'Attended Only'
        CERTIFICATE_HOLDERS = 'certificate_holders', 'Certificate Holders Only'
        PUBLIC = 'public', 'Public (Anyone with Link)'
    
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='recordings'
    )
    
    # Zoom Meeting Info
    zoom_meeting_id = models.CharField(
        max_length=20,
        db_index=True,
        help_text="Zoom meeting ID"
    )
    zoom_meeting_uuid = models.CharField(
        max_length=100,
        help_text="Zoom meeting UUID (unique per instance)"
    )
    zoom_recording_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Zoom's recording ID"
    )
    
    topic = models.CharField(
        max_length=300,
        blank=True,
        help_text="Meeting topic from Zoom"
    )
    
    # Timing
    recording_start = models.DateTimeField(
        help_text="When recording started"
    )
    recording_end = models.DateTimeField(
        help_text="When recording ended"
    )
    duration_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Recording duration in seconds"
    )
    total_size_bytes = models.BigIntegerField(
        default=0,
        help_text="Total size of all recording files"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROCESSING
    )
    zoom_expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When recording expires on Zoom"
    )
    
    # Access Control
    access_level = models.CharField(
        max_length=20,
        choices=AccessLevel.choices,
        default=AccessLevel.REGISTRANTS
    )
    zoom_password = models.CharField(
        max_length=50,
        blank=True,
        help_text="Password for Zoom share URL"
    )
    access_password = models.CharField(
        max_length=50,
        blank=True,
        help_text="Optional platform password for access"
    )
    
    # Display Settings
    title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Display title (defaults to event title)"
    )
    description = models.TextField(
        blank=True,
        max_length=2000,
        help_text="Description shown to viewers"
    )
    thumbnail_url = models.URLField(
        blank=True,
        help_text="Custom thumbnail image URL"
    )
    
    # Visibility
    is_published = models.BooleanField(
        default=False,
        help_text="Whether recording is visible to attendees"
    )
    published_at = models.DateTimeField(
        null=True, blank=True
    )
    auto_publish = models.BooleanField(
        default=False,
        help_text="Automatically publish when available"
    )
    
    # Engagement Stats
    view_count = models.PositiveIntegerField(
        default=0
    )
    unique_viewers = models.PositiveIntegerField(
        default=0
    )
    
    class Meta:
        db_table = 'zoom_recordings'
        ordering = ['-recording_start']
        indexes = [
            models.Index(fields=['event']),
            models.Index(fields=['zoom_recording_id']),
            models.Index(fields=['zoom_meeting_id']),
            models.Index(fields=['status']),
            models.Index(fields=['is_published', '-recording_start']),
        ]
        verbose_name = 'Zoom Recording'
        verbose_name_plural = 'Zoom Recordings'
    
    def __str__(self):
        return f"Recording: {self.event.title}"
    
    @property
    def duration_display(self):
        """Human-readable duration."""
        hours, remainder = divmod(self.duration_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours}h {minutes}m"
        return f"{minutes}m {seconds}s"
    
    @property
    def is_available(self):
        return self.status == self.Status.AVAILABLE
    
    @property
    def display_title(self):
        return self.title or self.event.title
    
    def publish(self):
        """Make recording visible to attendees."""
        self.is_published = True
        self.published_at = timezone.now()
        self.save(update_fields=['is_published', 'published_at', 'updated_at'])
    
    def unpublish(self):
        """Hide recording from attendees."""
        self.is_published = False
        self.save(update_fields=['is_published', 'updated_at'])


class ZoomRecordingFile(BaseModel):
    """
    An individual file within a Zoom recording.
    
    A recording typically contains:
    - Video file(s) (MP4)
    - Audio file (M4A)
    - Chat file (TXT)
    - Transcript (VTT)
    """
    
    class FileType(models.TextChoices):
        VIDEO = 'video', 'Video (MP4)'
        AUDIO = 'audio', 'Audio (M4A)'
        CHAT = 'chat', 'Chat Log (TXT)'
        TRANSCRIPT = 'transcript', 'Transcript (VTT)'
        TIMELINE = 'timeline', 'Timeline (JSON)'
        CC = 'cc', 'Closed Captions (VTT)'
        SUMMARY = 'summary', 'AI Summary'
    
    recording = models.ForeignKey(
        ZoomRecording,
        on_delete=models.CASCADE,
        related_name='files'
    )
    
    zoom_file_id = models.CharField(
        max_length=100,
        help_text="Zoom's file ID"
    )
    file_type = models.CharField(
        max_length=20,
        choices=FileType.choices
    )
    recording_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="E.g., shared_screen_with_speaker_view, gallery_view"
    )
    
    # File Details
    file_name = models.CharField(
        max_length=255,
        blank=True
    )
    file_extension = models.CharField(
        max_length=10,
        blank=True
    )
    file_size_bytes = models.BigIntegerField(
        default=0
    )
    
    # URLs
    download_url = models.URLField(
        max_length=2000,
        blank=True,
        help_text="Zoom download URL"
    )
    play_url = models.URLField(
        max_length=2000,
        blank=True,
        help_text="Zoom play URL (for embedding)"
    )
    share_url = models.URLField(
        max_length=2000,
        blank=True,
        help_text="Shareable URL"
    )
    storage_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="Our storage URL (if file is copied locally)"
    )
    
    # Processing Status
    processing_status = models.CharField(
        max_length=20,
        default='completed',
        help_text="Zoom processing status"
    )
    
    # Visibility
    is_visible = models.BooleanField(
        default=True,
        help_text="Whether this file is shown to viewers"
    )
    
    class Meta:
        db_table = 'zoom_recording_files'
        ordering = ['file_type', 'recording_type']
        indexes = [
            models.Index(fields=['recording', 'file_type']),
            models.Index(fields=['zoom_file_id']),
        ]
        verbose_name = 'Zoom Recording File'
        verbose_name_plural = 'Zoom Recording Files'
    
    def __str__(self):
        return f"{self.recording.event.title} - {self.file_type}"
    
    @property
    def is_video(self):
        return self.file_type == self.FileType.VIDEO
    
    @property
    def is_downloadable(self):
        """Check if file can be downloaded."""
        return self.file_type in [
            self.FileType.VIDEO,
            self.FileType.AUDIO,
            self.FileType.CHAT,
            self.FileType.TRANSCRIPT
        ]


class RecordingView(BaseModel):
    """
    Track who has viewed recordings.
    """
    
    recording = models.ForeignKey(
        ZoomRecording,
        on_delete=models.CASCADE,
        related_name='views'
    )
    registration = models.ForeignKey(
        'registrations.Registration',
        on_delete=models.CASCADE,
        related_name='recording_views'
    )
    
    first_viewed_at = models.DateTimeField(
        default=timezone.now
    )
    last_viewed_at = models.DateTimeField(
        null=True, blank=True
    )
    view_count = models.PositiveIntegerField(
        default=1
    )
    
    class Meta:
        db_table = 'recording_views'
        unique_together = [['recording', 'registration']]
        verbose_name = 'Recording View'
        verbose_name_plural = 'Recording Views'


class EmailLog(BaseModel):
    """
    Log of emails sent through the platform.
    """
    
    class EmailType(models.TextChoices):
        VERIFICATION = 'verification', 'Email Verification'
        PASSWORD_RESET = 'password_reset', 'Password Reset'
        EVENT_REMINDER = 'event_reminder', 'Event Reminder'
        REGISTRATION_CONFIRM = 'registration_confirm', 'Registration Confirmation'
        CERTIFICATE = 'certificate', 'Certificate Delivery'
        INVITATION = 'invitation', 'Event Invitation'
        EVENT_UPDATE = 'event_update', 'Event Update'
        WAITLIST_PROMOTION = 'waitlist_promotion', 'Waitlist Promotion'
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        DELIVERED = 'delivered', 'Delivered'
        OPENED = 'opened', 'Opened'
        CLICKED = 'clicked', 'Clicked'
        BOUNCED = 'bounced', 'Bounced'
        FAILED = 'failed', 'Failed'
    
    # Recipient
    recipient_email = models.EmailField(
        db_index=True
    )
    recipient_name = models.CharField(
        max_length=255,
        blank=True
    )
    recipient_user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='emails_received'
    )
    
    # Email Details
    email_type = models.CharField(
        max_length=30,
        choices=EmailType.choices,
        db_index=True
    )
    subject = models.CharField(
        max_length=255
    )
    
    # Related Objects
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='emails'
    )
    registration = models.ForeignKey(
        'registrations.Registration',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='emails'
    )
    certificate = models.ForeignKey(
        'certificates.Certificate',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='emails'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    
    # Timestamps
    sent_at = models.DateTimeField(
        null=True, blank=True
    )
    delivered_at = models.DateTimeField(
        null=True, blank=True
    )
    opened_at = models.DateTimeField(
        null=True, blank=True
    )
    clicked_at = models.DateTimeField(
        null=True, blank=True
    )
    
    # Error
    error_message = models.TextField(
        blank=True
    )
    
    # Provider
    provider_message_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Message ID from email provider"
    )
    
    class Meta:
        db_table = 'email_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient_email']),
            models.Index(fields=['email_type', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['event']),
        ]
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'
    
    def __str__(self):
        return f"{self.email_type} to {self.recipient_email}"
    
    def mark_sent(self, message_id=''):
        """Mark email as sent."""
        self.status = self.Status.SENT
        self.sent_at = timezone.now()
        self.provider_message_id = message_id
        self.save(update_fields=['status', 'sent_at', 'provider_message_id', 'updated_at'])
    
    def mark_delivered(self):
        """Mark email as delivered."""
        self.status = self.Status.DELIVERED
        self.delivered_at = timezone.now()
        self.save(update_fields=['status', 'delivered_at', 'updated_at'])
    
    def mark_opened(self):
        """Mark email as opened."""
        if self.status not in [self.Status.OPENED, self.Status.CLICKED]:
            self.status = self.Status.OPENED
            self.opened_at = timezone.now()
            self.save(update_fields=['status', 'opened_at', 'updated_at'])
    
    def mark_clicked(self):
        """Mark email as clicked."""
        self.status = self.Status.CLICKED
        self.clicked_at = timezone.now()
        if not self.opened_at:
            self.opened_at = timezone.now()
        self.save(update_fields=['status', 'clicked_at', 'opened_at', 'updated_at'])
    
    def mark_bounced(self, error=''):
        """Mark email as bounced."""
        self.status = self.Status.BOUNCED
        self.error_message = error
        self.save(update_fields=['status', 'error_message', 'updated_at'])
    
    def mark_failed(self, error):
        """Mark email as failed."""
        self.status = self.Status.FAILED
        self.error_message = error
        self.save(update_fields=['status', 'error_message', 'updated_at'])
