# Integrations App: External Services

## Overview

The `integrations` app handles:
- Zoom webhook event logging and processing
- Zoom cloud recording storage and access
- Email delivery tracking
- External API interaction logging

---

## Models

### ZoomWebhookLog

Log of Zoom webhook events received.

```python
# integrations/models.py

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
        # Meeting events
        MEETING_STARTED = 'meeting.started', 'Meeting Started'
        MEETING_ENDED = 'meeting.ended', 'Meeting Ended'
        PARTICIPANT_JOINED = 'meeting.participant_joined', 'Participant Joined'
        PARTICIPANT_LEFT = 'meeting.participant_left', 'Participant Left'
        PARTICIPANT_WAITING = 'meeting.participant_joined_waiting_room', 'Participant Waiting'
        # Webinar events
        WEBINAR_STARTED = 'webinar.started', 'Webinar Started'
        WEBINAR_ENDED = 'webinar.ended', 'Webinar Ended'
        WEBINAR_PANELIST_JOINED = 'webinar.participant_joined', 'Webinar Participant Joined'
        WEBINAR_PANELIST_LEFT = 'webinar.participant_left', 'Webinar Participant Left'
        # Other
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
            models.Index(fields=['-created_at']),  # For cleanup job
        ]
        verbose_name = 'Zoom Webhook Log'
        verbose_name_plural = 'Zoom Webhook Logs'
    
    def __str__(self):
        return f"{self.event_type} - {self.zoom_meeting_id}"
    
    # =========================================
    # Properties
    # =========================================
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
    
    # =========================================
    # Methods
    # =========================================
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
        """
        Try to match webhook to a platform event.
        
        Returns:
            Event or None
        """
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
        """
        Delete logs older than specified days.
        
        Returns:
            int: Number of records deleted
        """
        cutoff = timezone.now() - timezone.timedelta(days=days)
        count, _ = cls.objects.filter(created_at__lt=cutoff).delete()
        return count
```

---

### ZoomRecording

Stores Zoom cloud recording information for an event.

```python
class ZoomRecording(BaseModel):
    """
    A Zoom cloud recording for an event.
    
    Created from Zoom webhook when recording is completed.
    Contains multiple files (video, audio, chat, transcript).
    
    Access Control:
    - Only confirmed registrants can view by default
    - Organizer can make recording public
    - Organizer can restrict to certificate holders only
    
    Lifecycle:
    1. Meeting ends with cloud recording enabled
    2. Zoom processes recording (can take minutes to hours)
    3. Zoom sends 'recording.completed' webhook
    4. We create ZoomRecording + ZoomRecordingFile records
    5. Attendees can access via event page
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
    
    # =========================================
    # Zoom Meeting Info
    # =========================================
    zoom_meeting_id = models.CharField(
        max_length=20,
        db_index=True,
        help_text="Zoom meeting ID"
    )
    zoom_meeting_uuid = models.CharField(
        max_length=100,
        help_text="Zoom meeting UUID (unique per instance)"
    )
    
    # =========================================
    # Recording Info from Zoom
    # =========================================
    zoom_recording_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Zoom's recording ID"
    )
    
    # Topic/title from Zoom
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
    
    # Size
    total_size_bytes = models.BigIntegerField(
        default=0,
        help_text="Total size of all recording files"
    )
    
    # =========================================
    # Status
    # =========================================
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROCESSING
    )
    
    # Zoom-side expiration
    zoom_expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When recording expires on Zoom (trash after 30 days)"
    )
    
    # =========================================
    # Access Control
    # =========================================
    access_level = models.CharField(
        max_length=20,
        choices=AccessLevel.choices,
        default=AccessLevel.REGISTRANTS
    )
    
    # Zoom password (for share_url)
    zoom_password = models.CharField(
        max_length=50,
        blank=True,
        help_text="Password for Zoom share URL"
    )
    
    # Platform-level password (optional additional protection)
    access_password = models.CharField(
        max_length=50,
        blank=True,
        help_text="Optional platform password for access"
    )
    
    # =========================================
    # Display Settings
    # =========================================
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
    
    # Auto-publish setting
    auto_publish = models.BooleanField(
        default=False,
        help_text="Automatically publish when available"
    )
    
    # =========================================
    # Engagement Stats
    # =========================================
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
        return f"Recording: {self.event.title} ({self.recording_start.date()})"
    
    # =========================================
    # Properties
    # =========================================
    @property
    def duration_display(self):
        """Human-readable duration."""
        hours, remainder = divmod(self.duration_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours}h {minutes}m"
        return f"{minutes}m {seconds}s"
    
    @property
    def size_display(self):
        """Human-readable file size."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.total_size_bytes < 1024:
                return f"{self.total_size_bytes:.1f} {unit}"
            self.total_size_bytes /= 1024
        return f"{self.total_size_bytes:.1f} TB"
    
    @property
    def is_available(self):
        return self.status == self.Status.AVAILABLE
    
    @property
    def is_expired(self):
        if self.zoom_expires_at:
            return timezone.now() > self.zoom_expires_at
        return self.status == self.Status.EXPIRED
    
    @property
    def primary_video(self):
        """Get the main video file."""
        return self.files.filter(
            file_type=ZoomRecordingFile.FileType.VIDEO,
            recording_type='shared_screen_with_speaker_view'
        ).first() or self.files.filter(
            file_type=ZoomRecordingFile.FileType.VIDEO
        ).first()
    
    @property
    def display_title(self):
        return self.title or self.event.title
    
    # =========================================
    # Access Control Methods
    # =========================================
    def can_access(self, user=None, registration=None):
        """
        Check if a user/registration can access this recording.
        
        Args:
            user: User attempting access (optional)
            registration: Registration for the event (optional)
        
        Returns:
            bool: Whether access is allowed
        """
        if not self.is_published:
            return False
        
        if not self.is_available:
            return False
        
        if self.access_level == self.AccessLevel.PUBLIC:
            return True
        
        if not registration:
            return False
        
        if self.access_level == self.AccessLevel.REGISTRANTS:
            return registration.status == 'confirmed'
        
        if self.access_level == self.AccessLevel.ATTENDEES:
            return registration.attended
        
        if self.access_level == self.AccessLevel.CERTIFICATE_HOLDERS:
            return registration.certificate_issued
        
        return False
    
    # =========================================
    # Methods
    # =========================================
    def publish(self):
        """Make recording visible to attendees."""
        self.is_published = True
        self.published_at = timezone.now()
        self.save(update_fields=['is_published', 'published_at', 'updated_at'])
    
    def unpublish(self):
        """Hide recording from attendees."""
        self.is_published = False
        self.save(update_fields=['is_published', 'updated_at'])
    
    def record_view(self, registration=None):
        """Record a view of the recording."""
        from django.db.models import F
        
        ZoomRecording.objects.filter(pk=self.pk).update(
            view_count=F('view_count') + 1
        )
        
        # Track unique viewers
        if registration:
            viewed, created = RecordingView.objects.get_or_create(
                recording=self,
                registration=registration,
                defaults={'first_viewed_at': timezone.now()}
            )
            if created:
                ZoomRecording.objects.filter(pk=self.pk).update(
                    unique_viewers=F('unique_viewers') + 1
                )
            else:
                viewed.view_count = F('view_count') + 1
                viewed.last_viewed_at = timezone.now()
                viewed.save(update_fields=['view_count', 'last_viewed_at'])
    
    def update_from_zoom(self, recording_data):
        """
        Update recording info from Zoom API/webhook data.
        
        Args:
            recording_data: Recording object from Zoom
        """
        self.topic = recording_data.get('topic', '')[:300]
        self.duration_seconds = recording_data.get('duration', 0) * 60  # Zoom sends minutes
        self.total_size_bytes = recording_data.get('total_size', 0)
        
        if recording_data.get('recording_start'):
            self.recording_start = recording_data['recording_start']
        if recording_data.get('recording_end'):
            self.recording_end = recording_data['recording_end']
        
        self.status = self.Status.AVAILABLE
        
        if self.auto_publish:
            self.is_published = True
            self.published_at = timezone.now()
        
        self.save()
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('recordings:detail', kwargs={'uuid': self.uuid})
```

---

### ZoomRecordingFile

Individual files within a recording (video, audio, chat, transcript).

```python
class ZoomRecordingFile(BaseModel):
    """
    An individual file within a Zoom recording.
    
    A recording typically contains:
    - Video file(s) (MP4) - main recording
    - Audio file (M4A) - audio only
    - Chat file (TXT) - chat messages
    - Transcript (VTT) - auto-generated captions
    - Timeline (JSON) - speaker timeline
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
    
    # =========================================
    # Zoom File Info
    # =========================================
    zoom_file_id = models.CharField(
        max_length=100,
        help_text="Zoom's file ID"
    )
    
    file_type = models.CharField(
        max_length=20,
        choices=FileType.choices
    )
    
    # Zoom's recording type (for video files)
    recording_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="E.g., shared_screen_with_speaker_view, gallery_view"
    )
    """
    Common recording_type values:
    - shared_screen_with_speaker_view: Screen share + active speaker
    - shared_screen_with_gallery_view: Screen share + gallery
    - active_speaker: Active speaker view only
    - gallery_view: Gallery view only
    - shared_screen: Screen share only
    - audio_only: Audio
    - audio_transcript: Transcript
    - chat_file: Chat
    - timeline: Timeline
    """
    
    # =========================================
    # File Details
    # =========================================
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
    
    # =========================================
    # URLs
    # =========================================
    # Direct download URL (requires authentication or token)
    download_url = models.URLField(
        max_length=2000,
        blank=True,
        help_text="Zoom download URL (may require auth)"
    )
    
    # Play/stream URL
    play_url = models.URLField(
        max_length=2000,
        blank=True,
        help_text="Zoom play URL (for embedding)"
    )
    
    # Share URL (password protected)
    share_url = models.URLField(
        max_length=2000,
        blank=True,
        help_text="Shareable URL (uses recording password)"
    )
    
    # Our CDN/storage URL (if we copy the file)
    storage_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="Our storage URL (if file is copied locally)"
    )
    
    # =========================================
    # Processing Status
    # =========================================
    processing_status = models.CharField(
        max_length=20,
        default='completed',
        help_text="Zoom processing status"
    )
    
    # =========================================
    # Visibility
    # =========================================
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
    def size_display(self):
        """Human-readable file size."""
        size = self.file_size_bytes
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
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
    
    def get_access_url(self, use_storage=True):
        """
        Get the best URL for accessing this file.
        
        Args:
            use_storage: Prefer our storage URL if available
        
        Returns:
            URL string
        """
        if use_storage and self.storage_url:
            return self.storage_url
        
        if self.file_type == self.FileType.VIDEO:
            return self.play_url or self.share_url or self.download_url
        
        return self.download_url or self.share_url
```

---

### RecordingView

Track who has viewed recordings (for analytics and access verification).

```python
class RecordingView(BaseModel):
    """
    Tracks recording views by registration.
    
    Used for:
    - Analytics (who watched, for how long)
    - Unique viewer counting
    - Compliance (proof of viewing for CPD)
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
    
    # View tracking
    view_count = models.PositiveIntegerField(
        default=1
    )
    first_viewed_at = models.DateTimeField()
    last_viewed_at = models.DateTimeField(
        auto_now=True
    )
    
    # Watch time tracking (optional, requires player integration)
    total_watch_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Total seconds watched"
    )
    max_position_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Furthest point reached in video"
    )
    completed = models.BooleanField(
        default=False,
        help_text="Watched to completion (90%+)"
    )
    
    class Meta:
        db_table = 'recording_views'
        unique_together = [['recording', 'registration']]
        indexes = [
            models.Index(fields=['recording']),
            models.Index(fields=['registration']),
        ]
        verbose_name = 'Recording View'
        verbose_name_plural = 'Recording Views'
    
    def __str__(self):
        return f"{self.registration.full_name} viewed {self.recording}"
    
    @property
    def watch_percent(self):
        """Percentage of recording watched."""
        if self.recording.duration_seconds == 0:
            return 0
        return int(
            (self.max_position_seconds / self.recording.duration_seconds) * 100
        )
    
    def update_progress(self, position_seconds, watch_time_seconds=0):
        """
        Update viewing progress.
        
        Args:
            position_seconds: Current position in video
            watch_time_seconds: Additional watch time to add
        """
        from django.db.models import F
        
        updates = {}
        
        if position_seconds > self.max_position_seconds:
            updates['max_position_seconds'] = position_seconds
            
            # Check for completion (90% threshold)
            if self.recording.duration_seconds > 0:
                if position_seconds >= (self.recording.duration_seconds * 0.9):
                    updates['completed'] = True
        
        if watch_time_seconds > 0:
            RecordingView.objects.filter(pk=self.pk).update(
                total_watch_seconds=F('total_watch_seconds') + watch_time_seconds,
                **updates
            )
        elif updates:
            for key, value in updates.items():
                setattr(self, key, value)
            self.save(update_fields=list(updates.keys()) + ['updated_at'])

---

### EmailLog

Log of sent emails for tracking and debugging.

```python
class EmailLog(BaseModel):
    """
    Log of sent emails.
    
    Purposes:
    - Debug delivery issues
    - Track engagement (opens, clicks)
    - Prevent duplicate sends
    - Support resend functionality
    
    Retention: 1 year (cleanup job deletes older records)
    """
    
    class EmailType(models.TextChoices):
        # Auth emails
        VERIFICATION = 'verification', 'Email Verification'
        PASSWORD_RESET = 'password_reset', 'Password Reset'
        WELCOME = 'welcome', 'Welcome Email'
        
        # Event emails
        REGISTRATION_CONFIRMATION = 'registration_confirmation', 'Registration Confirmation'
        EVENT_REMINDER_24H = 'event_reminder_24h', '24-Hour Reminder'
        EVENT_REMINDER_1H = 'event_reminder_1h', '1-Hour Reminder'
        EVENT_CANCELLED = 'event_cancelled', 'Event Cancelled'
        EVENT_UPDATED = 'event_updated', 'Event Updated'
        WAITLIST_CONFIRMATION = 'waitlist_confirmation', 'Waitlist Confirmation'
        WAITLIST_PROMOTED = 'waitlist_promoted', 'Waitlist Promotion'
        
        # Certificate emails
        CERTIFICATE_ISSUED = 'certificate_issued', 'Certificate Issued'
        
        # Invitation emails
        EVENT_INVITATION = 'event_invitation', 'Event Invitation'
        
        # Other
        OTHER = 'other', 'Other'
    
    class DeliveryStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        DELIVERED = 'delivered', 'Delivered'
        OPENED = 'opened', 'Opened'
        CLICKED = 'clicked', 'Clicked'
        BOUNCED = 'bounced', 'Bounced'
        FAILED = 'failed', 'Failed'
        SPAM = 'spam', 'Marked as Spam'
        UNSUBSCRIBED = 'unsubscribed', 'Unsubscribed'
    
    # =========================================
    # Recipient
    # =========================================
    recipient_email = LowercaseEmailField(
        db_index=True,
        help_text="Recipient email address"
    )
    recipient_name = models.CharField(
        max_length=255,
        blank=True
    )
    recipient_user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='received_emails',
        help_text="Recipient user (if registered)"
    )
    
    # =========================================
    # Email Details
    # =========================================
    email_type = models.CharField(
        max_length=50,
        choices=EmailType.choices,
        db_index=True
    )
    subject = models.CharField(
        max_length=500,
        help_text="Email subject line"
    )
    
    # Optional body storage (for debugging)
    body_html = models.TextField(
        blank=True,
        help_text="HTML body (optional, for debugging)"
    )
    body_text = models.TextField(
        blank=True,
        help_text="Plain text body (optional)"
    )
    
    # =========================================
    # Related Objects
    # =========================================
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='email_logs'
    )
    registration = models.ForeignKey(
        'registrations.Registration',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='email_logs'
    )
    certificate = models.ForeignKey(
        'certificates.Certificate',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='email_logs'
    )
    invitation = models.ForeignKey(
        'events.EventInvitation',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='email_logs'
    )
    
    # =========================================
    # Sender
    # =========================================
    sent_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sent_emails',
        help_text="User who triggered the send (for manual sends)"
    )
    from_email = models.EmailField(
        help_text="From email address"
    )
    from_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="From display name"
    )
    reply_to = models.EmailField(
        blank=True,
        help_text="Reply-to address"
    )
    
    # =========================================
    # Delivery Status
    # =========================================
    delivery_status = models.CharField(
        max_length=20,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
        db_index=True
    )
    
    # Timing
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
    bounced_at = models.DateTimeField(
        null=True, blank=True
    )
    failed_at = models.DateTimeField(
        null=True, blank=True
    )
    
    # Engagement counts
    open_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times opened"
    )
    click_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of link clicks"
    )
    
    # =========================================
    # Provider Info
    # =========================================
    provider = models.CharField(
        max_length=50,
        blank=True,
        help_text="Email provider (resend, sendgrid, etc.)"
    )
    provider_message_id = models.CharField(
        max_length=200,
        blank=True,
        db_index=True,
        help_text="Message ID from provider (for webhook matching)"
    )
    
    # =========================================
    # Error Tracking
    # =========================================
    error_message = models.TextField(
        blank=True,
        help_text="Error message if failed"
    )
    error_code = models.CharField(
        max_length=50,
        blank=True,
        help_text="Error code from provider"
    )
    bounce_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Bounce type (hard, soft)"
    )
    
    # =========================================
    # Retry Tracking
    # =========================================
    send_attempts = models.PositiveIntegerField(
        default=0
    )
    last_attempt_at = models.DateTimeField(
        null=True, blank=True
    )
    
    class Meta:
        db_table = 'email_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient_email', '-created_at']),
            models.Index(fields=['email_type', '-created_at']),
            models.Index(fields=['delivery_status', '-created_at']),
            models.Index(fields=['event', '-created_at']),
            models.Index(fields=['provider_message_id']),
            models.Index(fields=['-created_at']),  # For cleanup job
        ]
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'
    
    def __str__(self):
        return f"{self.email_type} to {self.recipient_email}"
    
    # =========================================
    # Properties
    # =========================================
    @property
    def was_delivered(self):
        """Check if email was delivered."""
        return self.delivery_status in [
            self.DeliveryStatus.DELIVERED,
            self.DeliveryStatus.OPENED,
            self.DeliveryStatus.CLICKED
        ]
    
    @property
    def can_retry(self):
        """Check if email can be retried."""
        return (
            self.delivery_status == self.DeliveryStatus.FAILED and
            self.send_attempts < 3
        )
    
    # =========================================
    # Methods
    # =========================================
    def mark_sent(self, provider_message_id=''):
        """Mark email as sent."""
        self.delivery_status = self.DeliveryStatus.SENT
        self.sent_at = timezone.now()
        self.send_attempts += 1
        self.last_attempt_at = timezone.now()
        if provider_message_id:
            self.provider_message_id = provider_message_id
        self.save(update_fields=[
            'delivery_status', 'sent_at', 'send_attempts',
            'last_attempt_at', 'provider_message_id', 'updated_at'
        ])
    
    def mark_delivered(self):
        """Mark email as delivered."""
        self.delivery_status = self.DeliveryStatus.DELIVERED
        self.delivered_at = timezone.now()
        self.save(update_fields=['delivery_status', 'delivered_at', 'updated_at'])
    
    def mark_opened(self):
        """Mark email as opened."""
        from django.db.models import F
        
        if self.delivery_status not in [
            self.DeliveryStatus.OPENED, 
            self.DeliveryStatus.CLICKED
        ]:
            self.delivery_status = self.DeliveryStatus.OPENED
            if not self.opened_at:
                self.opened_at = timezone.now()
        
        EmailLog.objects.filter(pk=self.pk).update(
            delivery_status=self.DeliveryStatus.OPENED,
            opened_at=self.opened_at or timezone.now(),
            open_count=F('open_count') + 1,
            updated_at=timezone.now()
        )
    
    def mark_clicked(self):
        """Mark email link as clicked."""
        from django.db.models import F
        
        self.delivery_status = self.DeliveryStatus.CLICKED
        if not self.clicked_at:
            self.clicked_at = timezone.now()
        
        EmailLog.objects.filter(pk=self.pk).update(
            delivery_status=self.DeliveryStatus.CLICKED,
            clicked_at=self.clicked_at or timezone.now(),
            click_count=F('click_count') + 1,
            updated_at=timezone.now()
        )
    
    def mark_bounced(self, bounce_type='', error_message=''):
        """Mark email as bounced."""
        self.delivery_status = self.DeliveryStatus.BOUNCED
        self.bounced_at = timezone.now()
        self.bounce_type = bounce_type
        self.error_message = error_message
        self.save(update_fields=[
            'delivery_status', 'bounced_at', 'bounce_type',
            'error_message', 'updated_at'
        ])
        
        # Update contact if exists
        from contacts.models import Contact
        Contact.objects.filter(
            email__iexact=self.recipient_email,
            contact_list__owner=self.sent_by
        ).update(email_bounced=True)
    
    def mark_failed(self, error_message='', error_code=''):
        """Mark email as failed."""
        self.delivery_status = self.DeliveryStatus.FAILED
        self.failed_at = timezone.now()
        self.error_message = error_message
        self.error_code = error_code
        self.save(update_fields=[
            'delivery_status', 'failed_at', 'error_message',
            'error_code', 'updated_at'
        ])
    
    def retry(self):
        """Retry sending failed email."""
        if not self.can_retry:
            raise ValueError("Email cannot be retried")
        
        self.delivery_status = self.DeliveryStatus.PENDING
        self.error_message = ''
        self.error_code = ''
        self.save(update_fields=[
            'delivery_status', 'error_message', 'error_code', 'updated_at'
        ])
        
        # Trigger send task
        from integrations.tasks import send_email
        send_email.delay(self.id)
    
    @classmethod
    def cleanup_old_logs(cls, days=365):
        """
        Delete logs older than specified days.
        
        Returns:
            int: Number of records deleted
        """
        cutoff = timezone.now() - timezone.timedelta(days=days)
        count, _ = cls.objects.filter(created_at__lt=cutoff).delete()
        return count
    
    @classmethod
    def check_duplicate(cls, recipient_email, email_type, related_object=None, 
                        window_minutes=60):
        """
        Check if similar email was recently sent (prevent duplicates).
        
        Args:
            recipient_email: Recipient email
            email_type: Type of email
            related_object: Related event/registration/certificate
            window_minutes: Time window to check
        
        Returns:
            bool: True if duplicate exists
        """
        cutoff = timezone.now() - timezone.timedelta(minutes=window_minutes)
        
        query = cls.objects.filter(
            recipient_email__iexact=recipient_email,
            email_type=email_type,
            created_at__gte=cutoff,
            delivery_status__in=[
                cls.DeliveryStatus.PENDING,
                cls.DeliveryStatus.SENT,
                cls.DeliveryStatus.DELIVERED,
                cls.DeliveryStatus.OPENED,
                cls.DeliveryStatus.CLICKED
            ]
        )
        
        if related_object:
            if hasattr(related_object, '_meta'):
                model_name = related_object._meta.model_name
                if model_name == 'event':
                    query = query.filter(event=related_object)
                elif model_name == 'registration':
                    query = query.filter(registration=related_object)
                elif model_name == 'certificate':
                    query = query.filter(certificate=related_object)
        
        return query.exists()
```

---

## Zoom Webhook Handler

```python
# integrations/zoom/webhooks.py

import hashlib
import hmac
import json
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


@csrf_exempt
@require_POST
def zoom_webhook(request):
    """
    Handle incoming Zoom webhooks.
    
    Zoom sends various event types:
    - meeting.started / meeting.ended
    - meeting.participant_joined / meeting.participant_left
    - recording.completed / recording.transcript_completed
    - webinar.* events
    
    Process:
    1. Validate signature
    2. Handle challenge (for webhook verification)
    3. Log webhook
    4. Queue for processing
    """
    # Get headers
    signature = request.headers.get('x-zm-signature', '')
    timestamp = request.headers.get('x-zm-request-timestamp', '')
    
    # Parse body
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    # Handle challenge (webhook URL verification)
    if body.get('event') == 'endpoint.url_validation':
        plain_token = body.get('payload', {}).get('plainToken', '')
        encrypted_token = hmac.new(
            settings.ZOOM_WEBHOOK_SECRET.encode(),
            plain_token.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return JsonResponse({
            'plainToken': plain_token,
            'encryptedToken': encrypted_token
        })
    
    # Validate signature
    if not validate_zoom_signature(request.body, timestamp, signature):
        return JsonResponse({'error': 'Invalid signature'}, status=401)
    
    # Get event details
    event_type = body.get('event', '')
    payload = body.get('payload', {})
    webhook_id = request.headers.get('x-zm-trackingid', '')
    
    # Check for duplicate
    if ZoomWebhookLog.objects.filter(webhook_id=webhook_id).exists():
        return JsonResponse({'status': 'duplicate'})
    
    # Extract meeting info
    meeting_obj = payload.get('object', {})
    meeting_id = str(meeting_obj.get('id', ''))
    meeting_uuid = meeting_obj.get('uuid', '')
    
    # Create log entry
    log = ZoomWebhookLog.objects.create(
        webhook_id=webhook_id,
        event_type=event_type,
        event_timestamp=body.get('event_ts'),
        zoom_meeting_id=meeting_id,
        zoom_meeting_uuid=meeting_uuid,
        payload=body,
        headers=dict(request.headers)
    )
    
    # Try to match event
    log.match_event()
    
    # Queue for processing based on event type
    if event_type.startswith('recording.'):
        from integrations.tasks import process_recording_webhook
        process_recording_webhook.delay(log.id)
    else:
        from integrations.tasks import process_zoom_webhook
        process_zoom_webhook.delay(log.id)
    
    return JsonResponse({'status': 'received'})


def validate_zoom_signature(body, timestamp, signature):
    """
    Validate Zoom webhook signature.
    
    Zoom signs webhooks with: 
    HMAC-SHA256(webhook_secret, "v0:{timestamp}:{body}")
    """
    message = f"v0:{timestamp}:{body.decode()}"
    expected = 'v0=' + hmac.new(
        settings.ZOOM_WEBHOOK_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)
```

---

## Recording Webhook Processing

```python
# integrations/tasks.py

from celery import shared_task


@shared_task
def process_recording_webhook(log_id):
    """
    Process a recording-related webhook.
    
    Handles:
    - recording.completed: Create ZoomRecording and files
    - recording.transcript_completed: Add transcript file
    - recording.deleted: Mark recording as deleted
    """
    from integrations.models import ZoomWebhookLog, ZoomRecording, ZoomRecordingFile
    from events.models import Event
    
    log = ZoomWebhookLog.objects.get(id=log_id)
    log.start_processing()
    
    try:
        event_type = log.event_type
        payload = log.payload.get('payload', {})
        recording_obj = payload.get('object', {})
        
        # Find matching event
        meeting_id = str(recording_obj.get('id', ''))
        try:
            event = Event.objects.get(zoom_meeting_id=meeting_id)
        except Event.DoesNotExist:
            log.mark_skipped(f"No event found for meeting {meeting_id}")
            return
        
        if event_type == 'recording.completed':
            # Create or update recording
            recording, created = ZoomRecording.objects.update_or_create(
                zoom_recording_id=recording_obj.get('uuid', ''),
                defaults={
                    'event': event,
                    'zoom_meeting_id': meeting_id,
                    'zoom_meeting_uuid': recording_obj.get('uuid', ''),
                    'topic': recording_obj.get('topic', '')[:300],
                    'recording_start': recording_obj.get('start_time'),
                    'recording_end': recording_obj.get('end_time'),
                    'duration_seconds': recording_obj.get('duration', 0) * 60,
                    'total_size_bytes': recording_obj.get('total_size', 0),
                    'zoom_password': recording_obj.get('password', ''),
                    'status': ZoomRecording.Status.AVAILABLE,
                    'auto_publish': event.auto_publish_recordings,
                }
            )
            
            # Auto-publish if configured
            if event.auto_publish_recordings and not recording.is_published:
                recording.publish()
            
            # Create file records
            files_created = 0
            for file_data in recording_obj.get('recording_files', []):
                file_type = map_zoom_file_type(file_data.get('file_type', ''))
                
                ZoomRecordingFile.objects.update_or_create(
                    recording=recording,
                    zoom_file_id=file_data.get('id', ''),
                    defaults={
                        'file_type': file_type,
                        'recording_type': file_data.get('recording_type', ''),
                        'file_name': file_data.get('file_name', ''),
                        'file_extension': file_data.get('file_extension', ''),
                        'file_size_bytes': file_data.get('file_size', 0),
                        'download_url': file_data.get('download_url', ''),
                        'play_url': file_data.get('play_url', ''),
                        'processing_status': file_data.get('status', 'completed'),
                    }
                )
                files_created += 1
            
            log.mark_completed(records_created=files_created)
            
        elif event_type == 'recording.transcript_completed':
            # Add transcript to existing recording
            try:
                recording = ZoomRecording.objects.get(
                    zoom_meeting_uuid=recording_obj.get('uuid', '')
                )
                
                for file_data in recording_obj.get('recording_files', []):
                    if file_data.get('file_type') in ['TRANSCRIPT', 'CC']:
                        ZoomRecordingFile.objects.update_or_create(
                            recording=recording,
                            zoom_file_id=file_data.get('id', ''),
                            defaults={
                                'file_type': ZoomRecordingFile.FileType.TRANSCRIPT,
                                'file_name': file_data.get('file_name', ''),
                                'file_extension': 'vtt',
                                'file_size_bytes': file_data.get('file_size', 0),
                                'download_url': file_data.get('download_url', ''),
                            }
                        )
                
                log.mark_completed()
                
            except ZoomRecording.DoesNotExist:
                log.mark_skipped("Recording not found for transcript")
        
        elif event_type == 'recording.deleted':
            # Mark recording as deleted
            ZoomRecording.objects.filter(
                zoom_meeting_uuid=recording_obj.get('uuid', '')
            ).update(status=ZoomRecording.Status.DELETED)
            
            log.mark_completed()
        
        else:
            log.mark_skipped(f"Unhandled recording event: {event_type}")
    
    except Exception as e:
        import traceback
        log.mark_failed(str(e), traceback.format_exc())
        raise


def map_zoom_file_type(zoom_type):
    """Map Zoom file type to our FileType."""
    mapping = {
        'MP4': ZoomRecordingFile.FileType.VIDEO,
        'M4A': ZoomRecordingFile.FileType.AUDIO,
        'CHAT': ZoomRecordingFile.FileType.CHAT,
        'TRANSCRIPT': ZoomRecordingFile.FileType.TRANSCRIPT,
        'CC': ZoomRecordingFile.FileType.CC,
        'TIMELINE': ZoomRecordingFile.FileType.TIMELINE,
        'SUMMARY': ZoomRecordingFile.FileType.SUMMARY,
    }
    return mapping.get(zoom_type, ZoomRecordingFile.FileType.VIDEO)
```

---

## Relationships

```
ZoomWebhookLog
└── Event (N:1, SET_NULL)

ZoomRecording
├── Event (N:1, CASCADE)
├── ZoomRecordingFile (1:N, CASCADE)
└── RecordingView (1:N, CASCADE)

ZoomRecordingFile
└── ZoomRecording (N:1, CASCADE)

RecordingView
├── ZoomRecording (N:1, CASCADE)
└── Registration (N:1, CASCADE)

EmailLog
├── User (N:1, SET_NULL) — recipient_user
├── User (N:1, SET_NULL) — sent_by
├── Event (N:1, SET_NULL)
├── Registration (N:1, SET_NULL)
├── Certificate (N:1, SET_NULL)
└── EventInvitation (N:1, SET_NULL)
```

---

## Indexes

| Table | Index | Purpose |
|-------|-------|---------|
| zoom_webhook_logs | webhook_id (unique) | Deduplication |
| zoom_webhook_logs | event_type, -event_timestamp | Filter by type |
| zoom_webhook_logs | zoom_meeting_id | Match to events |
| zoom_webhook_logs | processing_status, -created_at | Find pending |
| zoom_webhook_logs | -created_at | Cleanup job |
| zoom_recordings | event_id | Event's recordings |
| zoom_recordings | zoom_recording_id (unique) | Zoom matching |
| zoom_recordings | zoom_meeting_id | Meeting lookup |
| zoom_recordings | status | Filter by status |
| zoom_recordings | is_published, -recording_start | Published list |
| zoom_recording_files | recording_id, file_type | Files by type |
| zoom_recording_files | zoom_file_id | Zoom matching |
| recording_views | recording_id | Recording analytics |
| recording_views | registration_id | User's views |
| recording_views | recording_id, registration_id (unique) | One per user |
| email_logs | recipient_email, -created_at | User's emails |
| email_logs | email_type, -created_at | Filter by type |
| email_logs | delivery_status, -created_at | Find pending/failed |
| email_logs | provider_message_id | Webhook matching |
| email_logs | -created_at | Cleanup job |

---

## Retention & Cleanup

```python
# integrations/tasks.py

from celery import shared_task


@shared_task
def cleanup_old_logs():
    """
    Daily task to clean up old integration logs.
    """
    from integrations.models import ZoomWebhookLog, EmailLog
    
    # Zoom webhooks: 90 days
    zoom_deleted = ZoomWebhookLog.cleanup_old_logs(days=90)
    
    # Email logs: 1 year
    email_deleted = EmailLog.cleanup_old_logs(days=365)
    
    return {
        'zoom_deleted': zoom_deleted,
        'email_deleted': email_deleted
    }


@shared_task
def retry_failed_webhooks():
    """
    Retry failed webhook processing (up to 3 attempts).
    """
    from integrations.models import ZoomWebhookLog
    
    failed = ZoomWebhookLog.objects.filter(
        processing_status=ZoomWebhookLog.ProcessingStatus.FAILED,
        processing_attempts__lt=3
    )[:100]  # Batch size
    
    for log in failed:
        process_zoom_webhook.delay(log.id)


@shared_task
def retry_failed_emails():
    """
    Retry failed email sends (up to 3 attempts).
    """
    from integrations.models import EmailLog
    
    failed = EmailLog.objects.filter(
        delivery_status=EmailLog.DeliveryStatus.FAILED,
        send_attempts__lt=3
    )[:100]  # Batch size
    
    for log in failed:
        send_email.delay(log.id)
```

---

## Business Rules

### Webhooks
1. **Webhook deduplication**: webhook_id is unique, duplicates return early
2. **Signature validation**: All webhooks must have valid signature
3. **Processing retries**: Max 3 attempts for failed webhooks/emails
4. **Log retention**: 90 days for webhooks, 1 year for emails

### Recordings
5. **Recording creation**: Only from Zoom webhook (not manual)
6. **Access control**: Four levels (registrants, attendees, certificate holders, public)
7. **Auto-publish**: Optional per-event setting
8. **Recording expiration**: Zoom deletes recordings after retention period (check zoom_expires_at)
9. **View tracking**: Unique viewers counted, watch progress tracked
10. **Completion threshold**: 90% watched = completed

### Email
11. **Email duplicate check**: Prevent same email type within window
12. **Bounce handling**: Updates contact records to prevent future sends

---

## Recording API Endpoints

```
# Recordings (Attendee)
GET    /api/events/{uuid}/recordings/           # List event recordings
GET    /api/recordings/{uuid}/                  # Recording detail + files
GET    /api/recordings/{uuid}/access/           # Get access URL (with auth)
POST   /api/recordings/{uuid}/progress/         # Update watch progress

# Recordings (Organizer)
GET    /api/organizer/events/{uuid}/recordings/ # List with analytics
PUT    /api/recordings/{uuid}/                  # Update settings
POST   /api/recordings/{uuid}/publish/          # Publish recording
POST   /api/recordings/{uuid}/unpublish/        # Hide recording
```

---

## Integration with Learning Module

Recordings can be added as module content:

```python
# In learning/models.py - extend ModuleContent

class ModuleContent(BaseModel):
    class ContentType(models.TextChoices):
        VIDEO = 'video', 'Video'
        DOCUMENT = 'document', 'Document'
        LINK = 'link', 'External Link'
        TEXT = 'text', 'Text/HTML Content'
        AUDIO = 'audio', 'Audio'
        PRESENTATION = 'presentation', 'Presentation'
        QUIZ = 'quiz', 'Quiz'
        DOWNLOAD = 'download', 'Downloadable File'
        RECORDING = 'recording', 'Zoom Recording'  # NEW
    
    # ... existing fields ...
    
    # Link to Zoom recording (for recording content type)
    zoom_recording = models.ForeignKey(
        'integrations.ZoomRecording',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='module_contents',
        help_text="Linked Zoom recording (for recording content type)"
    )
```

**Usage:**
1. Event has a live Zoom session → Recording created automatically
2. Organizer can add recording as module content
3. Progress tracking unified (RecordingView syncs to ContentProgress)

```python
# Sync recording view to content progress
def sync_recording_progress(recording_view):
    """
    Sync RecordingView to ContentProgress for LMS tracking.
    """
    from learning.models import ModuleContent, ContentProgress
    
    # Find any module content linked to this recording
    contents = ModuleContent.objects.filter(
        zoom_recording=recording_view.recording,
        module__event=recording_view.recording.event
    )
    
    for content in contents:
        progress, _ = ContentProgress.objects.get_or_create(
            registration=recording_view.registration,
            content=content
        )
        
        # Update progress
        progress.total_time_seconds = recording_view.total_watch_seconds
        progress.video_progress_seconds = recording_view.max_position_seconds
        
        if recording_view.completed:
            progress.status = ContentProgress.Status.COMPLETED
            progress.completed_at = timezone.now()
            progress.video_completed = True
        elif recording_view.total_watch_seconds > 0:
            progress.status = ContentProgress.Status.IN_PROGRESS
        
        progress.save()
```
