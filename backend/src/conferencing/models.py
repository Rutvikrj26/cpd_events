"""
Video conferencing models — provider-agnostic.

Replaces the scattered zoom_* fields and Zoom-specific models with
a clean, centralized conferencing data layer.
"""

import secrets

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.utils import timezone

from common.models import BaseModel


def generate_room_name(content_type_model: str, content_object_uuid) -> str:
    """Generate a globally-unique LiveKit room_name for a new meeting session.

    Format: ``{model}-{uuid}-{token}`` — e.g. ``event-7e08d14f-…-a4f9``.

    The token suffix is critical for the Zoom-model lifecycle: each
    meeting session gets its own VideoRoom row with its own room_name.
    Without the suffix, re-running a meeting on the same Event would
    collide with the unique=True constraint on `room_name`. 6 hex
    chars = 24 bits = ~16M values; collision risk is negligible across
    a single event's lifetime (and the unique constraint catches it
    if it ever happens).
    """
    return f"{content_type_model}-{content_object_uuid}-{secrets.token_hex(3)}"


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
    room_id = models.CharField(max_length=200, db_index=True, help_text="Provider's room ID (e.g., LiveKit SID, Zoom meeting UUID)")
    room_name = models.CharField(max_length=200, unique=True, db_index=True, help_text="Room name used for joining")
    provider = models.CharField(max_length=50, default='livekit', help_text="Video provider name")

    # Zoom-specific. The numeric Zoom meeting ID (distinct from `room_id`,
    # which holds the meeting UUID). Used for REST calls that take the
    # numeric id (e.g. /meetings/{id}/registrants). Nullable so legacy
    # LiveKit rooms remain unaffected.
    zoom_meeting_id = models.CharField(max_length=32, blank=True, db_index=True, help_text="Zoom numeric meeting ID")
    # Personalized join URL surfaced to UI/lobby — for Zoom this is the
    # meeting's host/start URL or generic join URL; per-attendee
    # registrant URLs live on Registration.zoom_registrant_join_url.
    zoom_join_url = models.URLField(blank=True, max_length=1000, help_text="Generic Zoom join URL for this meeting")

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
        # Zoom-model invariant: at most one ACTIVE meeting per content
        # object (Event/CourseSession) at any time. Enforced as a
        # partial unique index — concurrent host clicks racing to start
        # a second meeting fail at the DB layer with IntegrityError,
        # which the API translates to "rejoin existing meeting". Older
        # ENDED rows are unconstrained (the Event may host many
        # sessions over its lifetime; only one is live at once).
        constraints = [
            UniqueConstraint(
                fields=['content_type', 'object_id'],
                condition=Q(status='active'),
                name='one_active_room_per_content',
            ),
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

    # NOTE: `reopen()` was deliberately removed in the Zoom-model
    # redesign. Each meeting session is single-shot (SCHEDULED →
    # ACTIVE → ENDED is terminal). To run another meeting on the same
    # Event, the host calls POST /events/{uuid}/meetings/start/ which
    # creates a fresh VideoRoom row.

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
    course_session = models.ForeignKey(
        'learning.CourseSession',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='recordings',
    )

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


# =========================================================================
# Transcripts
# =========================================================================
#
# A Transcript is one-to-one with a VideoRoom: every video session can have
# at most one canonical transcript. Segments are append-only — edits create
# a new row with `replaced_by` pointed back to the row it supersedes, so the
# full edit history (including the original STT output) is queryable for
# compliance review without polluting normal reads.
#
# Why one transcript per VideoRoom (not per VideoRecording): the live agent
# starts persisting segments while the room is active, before any recording
# file exists. We anchor on the room so live captures and post-event reads
# share a single record even if recording is disabled or fails.


class Transcript(BaseModel):
    """A transcript of a video session, one per VideoRoom."""

    class Status(models.TextChoices):
        # Live segments still arriving from the agent. Reads work but the
        # transcript should be presented as in-progress (e.g. don't render
        # the export button yet).
        STREAMING = 'streaming', 'Streaming'
        # Room finished, agent has flushed final segments. Read-only by
        # default; organiser edits still produce new rows but are gated on
        # explicit edit permission.
        FINALIZED = 'finalized', 'Finalized'
        # Provider error or agent crash; partial segments may still be
        # present. Surfaces an inline notice on the playback page so users
        # know the transcript is incomplete.
        ERROR = 'error', 'Error'

    video_room = models.OneToOneField(
        VideoRoom,
        on_delete=models.CASCADE,
        related_name='transcript',
        help_text='The video session this transcript belongs to.',
    )

    # Snapshotted at provisioning time so historical rows survive provider
    # changes — when an org switches from Deepgram to AssemblyAI we don't
    # want old transcripts to render with the wrong attribution.
    provider = models.CharField(
        max_length=32,
        help_text="STT provider used (e.g. 'deepgram', 'openai', 'assemblyai').",
    )
    provider_model = models.CharField(
        max_length=64,
        blank=True,
        help_text="Model identifier within the provider (e.g. 'nova-3').",
    )
    language_code = models.CharField(
        max_length=10,
        default='en-US',
        help_text='BCP-47 language code (e.g. en-US, fr-FR).',
    )

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.STREAMING,
        db_index=True,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    # Aggregate stats — populated on finalize. Cheap to maintain because
    # the agent already iterates all finals. Storing here saves a sum
    # query for the UI badge.
    word_count = models.IntegerField(default=0)

    # Surfaces on the playback page when status=ERROR so users can tell
    # the difference between "no transcript configured" and "we tried but
    # failed". Empty for healthy transcripts.
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = 'transcripts'
        ordering = ['-created_at']

    def __str__(self):
        return f'Transcript({self.provider}/{self.language_code}) for {self.video_room.room_name}'


class TranscriptSegment(BaseModel):
    """
    A single time-anchored chunk of a transcript.

    Append-only: edits create a NEW row with `source='edit'` and a
    `replaced_by` FK on the row that's being superseded. Default queries
    filter `replaced_by__isnull=True` to get the current version; the
    history endpoint walks the chain via the reverse `replaces` relation.

    Live revisions DO update in place (LiveKit re-publishes a segment with
    the same `lk.segment_id` until it's finalised; Zoom's VTT cues use a
    `{file_id}:{cue_index}` key), keyed on
    `(transcript_id, provider_segment_id, source='live')`. Once a segment
    has been edited by an organiser, the live row's text is locked.
    """

    class Source(models.TextChoices):
        LIVE = 'live', 'Live (streaming)'
        EDIT = 'edit', 'Organizer edit'
        BATCH_REPAIR = 'batch_repair', 'Post-event batch re-pass'

    transcript = models.ForeignKey(
        Transcript,
        on_delete=models.CASCADE,
        related_name='segments',
    )

    # Timing relative to recording_start, in milliseconds. Integer (not
    # float) because Postgres BTREE on int is faster and we never need
    # sub-millisecond resolution for transcript scrubbing.
    start_ms = models.IntegerField(help_text='Start offset from recording start, in ms.')
    end_ms = models.IntegerField(help_text='End offset from recording start, in ms.')

    # Content.
    text = models.TextField()

    # Preserved on the row even though normal reads filter to finals.
    # Useful for analytics ("how often did we revise?") and for the live
    # overlay's optimistic merge during streaming.
    is_final = models.BooleanField(default=True)

    # Speaker attribution. LiveKit participant identity is the user's
    # uuid — we set it at JWT issuance (see meetings._build_join_response). The hard
    # FK to User flows renames through; the snapshot preserves the name
    # at recording time so the transcript reads correctly even if the
    # user changes their display name later.
    participant_identity = models.CharField(max_length=255, blank=True, db_index=True)
    speaker_user = models.ForeignKey(
        'accounts.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='transcript_segments',
    )
    speaker_name_snapshot = models.CharField(max_length=255, blank=True)

    # Provider-supplied confidence (0.0–1.0). Optional because not every
    # plugin reports it; Deepgram does, OpenAI Whisper does not.
    confidence = models.FloatField(null=True, blank=True)

    # Provider's stable ID for this segment within the session. Idempotency
    # key for the live ingest endpoint: `(transcript, provider_segment_id)`
    # uniquely identifies the live source row. Edits create siblings with
    # the same `provider_segment_id` but different `source`. Format depends
    # on provider: LiveKit uses `lk.segment_id`; Zoom uses
    # `{recording_file_id}:{cue_index}` for VTT-derived rows.
    provider_segment_id = models.CharField(max_length=128, blank=True, db_index=True)

    # Edit history — acyclic linked list of versions. The newest version
    # has `replaced_by IS NULL`; older versions point forward through this
    # FK. Walking backward via `replaces` (the reverse relation) yields
    # the chronological history.
    source = models.CharField(
        max_length=16,
        choices=Source.choices,
        default=Source.LIVE,
        db_index=True,
    )
    replaced_by = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='replaces',
    )
    edited_by = models.ForeignKey(
        'accounts.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'transcript_segments'
        ordering = ['transcript_id', 'start_ms']
        indexes = [
            # Primary access pattern: list a transcript's current segments
            # in playback order.
            models.Index(fields=['transcript', 'start_ms']),
            # Idempotency lookups during live ingest.
            models.Index(fields=['transcript', 'provider_segment_id', 'source']),
        ]
        # Live ingest invariant: at most one live segment per (transcript,
        # provider_segment_id) — re-publishes update in place. Edit rows
        # get `source='edit'` so they don't collide with this constraint.
        constraints = [
            models.UniqueConstraint(
                fields=['transcript', 'provider_segment_id', 'source'],
                condition=models.Q(source='live') & ~models.Q(provider_segment_id=''),
                name='one_live_segment_per_provider_id',
            ),
        ]

    def __str__(self):
        return f'Segment[{self.start_ms}-{self.end_ms}ms] {self.text[:40]!r}'
