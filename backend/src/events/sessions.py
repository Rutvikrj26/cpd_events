"""
Multi-session event models for events that span multiple dates/times.
"""

from django.db import models
from django.utils import timezone

from common.models import BaseModel


class EventSession(BaseModel):
    """
    Individual session within a multi-session event.
    
    Allows events to have multiple dates/times with separate
    attendance tracking for each session.
    """
    
    class SessionType(models.TextChoices):
        LIVE = 'live', 'Live Session'
        RECORDED = 'recorded', 'Recorded/On-demand'
        HYBRID = 'hybrid', 'Hybrid'
    
    # Relationships
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    
    # Basic info
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    
    # Timing
    starts_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    timezone = models.CharField(max_length=50, default='UTC')
    
    # Session type
    session_type = models.CharField(
        max_length=20,
        choices=SessionType.choices,
        default=SessionType.LIVE
    )
    
    # Zoom integration (if separate from main event)
    has_separate_zoom = models.BooleanField(default=False)
    zoom_meeting_id = models.CharField(max_length=100, blank=True)
    zoom_join_url = models.URLField(max_length=500, blank=True)
    zoom_host_url = models.URLField(max_length=500, blank=True)
    
    # CPD credits for this session
    cpd_credits = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )
    
    # Attendance requirement
    minimum_attendance_percent = models.PositiveIntegerField(
        default=80,
        help_text="Minimum attendance percentage for this session"
    )
    
    # Status
    is_mandatory = models.BooleanField(
        default=True,
        help_text="Whether this session is required for certificate"
    )
    is_published = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'event_sessions'
        ordering = ['event', 'order', 'starts_at']
        verbose_name = 'Event Session'
        verbose_name_plural = 'Event Sessions'
    
    def __str__(self):
        return f"{self.event.title} - {self.title}"
    
    @property
    def ends_at(self):
        """Calculate session end time."""
        return self.starts_at + timezone.timedelta(minutes=self.duration_minutes)
    
    @property
    def is_past(self):
        """Check if session has ended."""
        return timezone.now() > self.ends_at


class SessionAttendance(BaseModel):
    """
    Attendance record for a specific session.
    
    Tracks individual session attendance for multi-session events.
    """
    
    # Relationships
    session = models.ForeignKey(
        EventSession,
        on_delete=models.CASCADE,
        related_name='attendance_records'
    )
    registration = models.ForeignKey(
        'registrations.Registration',
        on_delete=models.CASCADE,
        related_name='session_attendance'
    )
    
    # Attendance data
    joined_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=0)
    
    # From Zoom
    zoom_participant_id = models.CharField(max_length=100, blank=True)
    join_events_count = models.PositiveIntegerField(default=0)
    
    # Eligibility
    is_eligible = models.BooleanField(
        default=False,
        help_text="Met minimum attendance requirement"
    )
    
    # Override
    override_eligible = models.BooleanField(null=True, blank=True)
    override_reason = models.TextField(blank=True)
    override_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='session_attendance_overrides'
    )
    
    class Meta:
        db_table = 'session_attendance'
        unique_together = [['session', 'registration']]
        verbose_name = 'Session Attendance'
        verbose_name_plural = 'Session Attendance'
    
    def __str__(self):
        return f"{self.registration.user.email} - {self.session.title}"
    
    @property
    def attendance_percent(self):
        """Calculate attendance percentage."""
        if self.session.duration_minutes == 0:
            return 100
        return int((self.duration_minutes / self.session.duration_minutes) * 100)
    
    @property
    def final_eligibility(self):
        """Get final eligibility considering overrides."""
        if self.override_eligible is not None:
            return self.override_eligible
        return self.is_eligible
    
    def calculate_eligibility(self):
        """Calculate if attendance meets requirements."""
        self.is_eligible = self.attendance_percent >= self.session.minimum_attendance_percent
        self.save(update_fields=['is_eligible', 'updated_at'])
