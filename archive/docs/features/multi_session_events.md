# Multi-Session Events Enhancement

## Overview

This document describes the architectural changes needed to support **multi-session events** — courses, series, or programs that span multiple meetings/lectures where certification is based on aggregate attendance across all sessions.

### Use Cases

| Scenario | Structure | Certificate Basis |
|----------|-----------|-------------------|
| Single webinar | 1 event, 1 session | Attend ≥80% of session |
| 4-week course | 1 event, 4 sessions | Attend ≥80% of total course time |
| Conference day | 1 event, 6 sessions | Attend ≥4 of 6 sessions |
| Workshop series | 1 event, 3 sessions | Attend all 3 sessions |

---

## Design Decision

### Option A: Event → Session Hierarchy ✅ (Recommended)

```
Event (container)
├── EventSession 1 (Zoom meeting)
├── EventSession 2 (Zoom meeting)
└── EventSession 3 (Zoom meeting)
```

**Pros:**
- Clean mental model: "Register for a course, attend lectures"
- Single registration covers all sessions
- Certificate issued at course level
- Simple URL structure: `/events/{course-slug}/`
- Backward compatible (single-session event = event with 1 session)

### Option B: EventSeries → Event Hierarchy ❌ (Not Recommended)

```
EventSeries (container)
├── Event 1 (standalone)
├── Event 2 (standalone)
└── Event 3 (standalone)
```

**Cons:**
- Registration at which level? Series or individual events?
- Existing Event model overloaded
- Complex queries for aggregate attendance
- URL confusion: `/series/{x}/events/{y}/`

---

## Data Model Changes

### New Model: EventSession

```python
# events/models.py

class EventSession(BaseModel):
    """
    A single session/lecture within an event.
    
    For single-session events: Event has exactly 1 EventSession.
    For multi-session events: Event has multiple EventSessions.
    
    Each session represents one Zoom meeting with its own:
    - Schedule (date/time)
    - Zoom meeting details
    - Attendance tracking
    """
    
    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        LIVE = 'live', 'Live'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
    
    # =========================================
    # Parent Event
    # =========================================
    event = models.ForeignKey(
        'Event',
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    
    # =========================================
    # Session Info
    # =========================================
    title = models.CharField(
        max_length=200,
        help_text="Session title (e.g., 'Week 1: Introduction')"
    )
    description = models.TextField(
        blank=True,
        max_length=5000,
        help_text="Session description"
    )
    session_number = models.PositiveIntegerField(
        default=1,
        help_text="Order within the event (1, 2, 3...)"
    )
    
    # =========================================
    # Schedule
    # =========================================
    starts_at = models.DateTimeField(
        db_index=True,
        help_text="Session start time (UTC)"
    )
    duration_minutes = models.PositiveIntegerField(
        validators=[MinValueValidator(15), MaxValueValidator(480)],
        help_text="Duration in minutes"
    )
    
    # Actual timing (filled after session)
    actual_started_at = models.DateTimeField(
        null=True, blank=True
    )
    actual_ended_at = models.DateTimeField(
        null=True, blank=True
    )
    
    # =========================================
    # Status
    # =========================================
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
        db_index=True
    )
    cancelled_at = models.DateTimeField(
        null=True, blank=True
    )
    cancellation_reason = models.TextField(
        blank=True
    )
    
    # =========================================
    # Zoom Integration
    # =========================================
    zoom_enabled = models.BooleanField(
        default=True
    )
    zoom_meeting_id = models.CharField(
        max_length=20,
        blank=True,
        db_index=True
    )
    zoom_meeting_uuid = models.CharField(
        max_length=100,
        blank=True
    )
    zoom_join_url = models.URLField(
        blank=True
    )
    zoom_host_url = models.URLField(
        blank=True
    )
    zoom_passcode = models.CharField(
        max_length=20,
        blank=True
    )
    zoom_settings = models.JSONField(
        default=dict,
        blank=True,
        validators=[validate_zoom_settings_schema]
    )
    
    # =========================================
    # Session-specific CPD (optional override)
    # =========================================
    cpd_credit_value_override = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True, blank=True,
        help_text="Override credits for this session (null = proportional)"
    )
    
    # =========================================
    # Denormalized Counts
    # =========================================
    attendance_count = models.PositiveIntegerField(
        default=0,
        help_text="Attendees who joined this session"
    )
    
    class Meta:
        db_table = 'event_sessions'
        ordering = ['event', 'session_number', 'starts_at']
        unique_together = [['event', 'session_number']]
        indexes = [
            models.Index(fields=['event', 'status']),
            models.Index(fields=['starts_at']),
            models.Index(fields=['zoom_meeting_id']),
            models.Index(fields=['status', 'starts_at']),
        ]
        verbose_name = 'Event Session'
        verbose_name_plural = 'Event Sessions'
    
    def __str__(self):
        return f"{self.event.title} - {self.title}"
    
    # =========================================
    # Properties
    # =========================================
    @property
    def ends_at(self):
        """Scheduled end time."""
        return self.starts_at + timezone.timedelta(minutes=self.duration_minutes)
    
    @property
    def actual_duration_minutes(self):
        """Actual duration if session has ended."""
        if self.actual_started_at and self.actual_ended_at:
            delta = self.actual_ended_at - self.actual_started_at
            return int(delta.total_seconds() / 60)
        return None
    
    @property
    def is_upcoming(self):
        return self.status == self.Status.SCHEDULED and self.starts_at > timezone.now()
    
    @property
    def is_live(self):
        return self.status == self.Status.LIVE
    
    @property
    def is_past(self):
        return self.ends_at < timezone.now()
    
    @property
    def cpd_credits(self):
        """
        Credits for this session.
        Uses override if set, otherwise proportional to duration.
        """
        if self.cpd_credit_value_override is not None:
            return self.cpd_credit_value_override
        
        if not self.event.cpd_enabled or not self.event.cpd_credit_value:
            return 0
        
        # Proportional: session_duration / total_duration * total_credits
        total_duration = self.event.total_duration_minutes
        if total_duration == 0:
            return 0
        
        return (
            self.duration_minutes / total_duration * 
            float(self.event.cpd_credit_value)
        )
    
    # =========================================
    # Methods
    # =========================================
    def start(self):
        """Mark session as live."""
        self.status = self.Status.LIVE
        self.actual_started_at = timezone.now()
        self.save(update_fields=['status', 'actual_started_at', 'updated_at'])
        
        # Update parent event if this is first session going live
        if self.event.status == Event.Status.PUBLISHED:
            self.event.status = Event.Status.LIVE
            self.event.actual_started_at = timezone.now()
            self.event.save(update_fields=['status', 'actual_started_at', 'updated_at'])
    
    def complete(self):
        """Mark session as completed."""
        self.status = self.Status.COMPLETED
        self.actual_ended_at = timezone.now()
        self.save(update_fields=['status', 'actual_ended_at', 'updated_at'])
        
        # Check if all sessions completed
        self.event.check_all_sessions_completed()
    
    def cancel(self, reason=''):
        """Cancel this session."""
        self.status = self.Status.CANCELLED
        self.cancelled_at = timezone.now()
        self.cancellation_reason = reason
        self.save(update_fields=[
            'status', 'cancelled_at', 'cancellation_reason', 'updated_at'
        ])
    
    def update_attendance_count(self):
        """Update denormalized attendance count."""
        self.attendance_count = SessionAttendance.objects.filter(
            session=self,
            attended=True
        ).count()
        self.save(update_fields=['attendance_count', 'updated_at'])
```

---

### Modified: Event Model

```python
class Event(SoftDeleteModel):
    """
    Modified Event model supporting both single and multi-session events.
    """
    
    class EventFormat(models.TextChoices):
        SINGLE = 'single', 'Single Session'
        SERIES = 'series', 'Series'
        COURSE = 'course', 'Course'
        CONFERENCE = 'conference', 'Conference'
    
    class AttendanceRequirement(models.TextChoices):
        PERCENTAGE_TIME = 'percentage_time', 'Percentage of Total Time'
        PERCENTAGE_SESSIONS = 'percentage_sessions', 'Percentage of Sessions'
        ALL_SESSIONS = 'all_sessions', 'All Sessions Required'
        MINIMUM_SESSIONS = 'minimum_sessions', 'Minimum Number of Sessions'
    
    # ... existing fields ...
    
    # =========================================
    # NEW: Multi-Session Configuration
    # =========================================
    event_format = models.CharField(
        max_length=20,
        choices=EventFormat.choices,
        default=EventFormat.SINGLE,
        help_text="Single session or multi-session event"
    )
    
    # =========================================
    # NEW: Attendance Requirements
    # =========================================
    attendance_requirement = models.CharField(
        max_length=30,
        choices=AttendanceRequirement.choices,
        default=AttendanceRequirement.PERCENTAGE_TIME,
        help_text="How attendance is calculated for certificate eligibility"
    )
    
    # For PERCENTAGE_TIME (default): minimum_attendance_percent applies to total time
    # For PERCENTAGE_SESSIONS: minimum_attendance_percent applies to session count
    # For ALL_SESSIONS: must attend all sessions
    # For MINIMUM_SESSIONS: must attend minimum_sessions_required
    
    minimum_sessions_required = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Minimum sessions required (for MINIMUM_SESSIONS requirement)"
    )
    
    # Per-session attendance threshold (what % of a session counts as "attended")
    session_attendance_threshold = models.PositiveIntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Minimum % of a session to count as attended"
    )
    
    # =========================================
    # DEPRECATED: Direct Zoom fields (moved to EventSession)
    # Keep for backward compatibility with existing single-session events
    # =========================================
    # zoom_meeting_id, zoom_join_url, etc. - DEPRECATED
    # These are now on EventSession
    
    # =========================================
    # NEW: Computed Properties
    # =========================================
    @property
    def is_multi_session(self):
        """Check if event has multiple sessions."""
        return self.event_format != self.EventFormat.SINGLE
    
    @property
    def session_count(self):
        """Total number of sessions."""
        return self.sessions.exclude(status=EventSession.Status.CANCELLED).count()
    
    @property
    def completed_session_count(self):
        """Number of completed sessions."""
        return self.sessions.filter(status=EventSession.Status.COMPLETED).count()
    
    @property
    def total_duration_minutes(self):
        """Total duration across all sessions."""
        return self.sessions.exclude(
            status=EventSession.Status.CANCELLED
        ).aggregate(
            total=models.Sum('duration_minutes')
        )['total'] or 0
    
    @property
    def first_session(self):
        """Get first scheduled session."""
        return self.sessions.exclude(
            status=EventSession.Status.CANCELLED
        ).order_by('starts_at').first()
    
    @property
    def last_session(self):
        """Get last scheduled session."""
        return self.sessions.exclude(
            status=EventSession.Status.CANCELLED
        ).order_by('-starts_at').first()
    
    @property
    def next_session(self):
        """Get next upcoming session."""
        return self.sessions.filter(
            status=EventSession.Status.SCHEDULED,
            starts_at__gt=timezone.now()
        ).order_by('starts_at').first()
    
    @property
    def starts_at(self):
        """
        Event start time (first session start).
        For backward compatibility.
        """
        first = self.first_session
        return first.starts_at if first else None
    
    @property
    def ends_at(self):
        """Event end time (last session end)."""
        last = self.last_session
        return last.ends_at if last else None
    
    # =========================================
    # NEW: Methods
    # =========================================
    def check_all_sessions_completed(self):
        """
        Check if all sessions are completed and update event status.
        Called after each session completes.
        """
        active_sessions = self.sessions.exclude(
            status__in=[
                EventSession.Status.COMPLETED,
                EventSession.Status.CANCELLED
            ]
        )
        
        if not active_sessions.exists():
            self.status = self.Status.COMPLETED
            self.actual_ended_at = timezone.now()
            self.save(update_fields=['status', 'actual_ended_at', 'updated_at'])
    
    def create_single_session(self):
        """
        Create the single session for a single-session event.
        Called on event creation for single-session events.
        """
        if self.event_format != self.EventFormat.SINGLE:
            raise ValueError("Only for single-session events")
        
        if self.sessions.exists():
            return self.sessions.first()
        
        return EventSession.objects.create(
            event=self,
            title=self.title,
            description=self.description,
            session_number=1,
            starts_at=self._starts_at,  # From form input
            duration_minutes=self._duration_minutes,
            zoom_enabled=self.zoom_enabled
        )
    
    def calculate_registration_eligibility(self, registration):
        """
        Calculate if a registration is eligible for certificate.
        
        Returns:
            tuple: (is_eligible, details_dict)
        """
        session_attendances = SessionAttendance.objects.filter(
            registration=registration,
            session__event=self
        ).select_related('session')
        
        details = {
            'total_sessions': self.session_count,
            'sessions_attended': 0,
            'total_duration_minutes': self.total_duration_minutes,
            'total_attended_minutes': 0,
            'attendance_percent': 0,
            'sessions_percent': 0,
            'requirement_type': self.attendance_requirement,
            'requirement_met': False
        }
        
        for sa in session_attendances:
            details['total_attended_minutes'] += sa.total_attendance_minutes
            if sa.attended:
                details['sessions_attended'] += 1
        
        # Calculate percentages
        if details['total_duration_minutes'] > 0:
            details['attendance_percent'] = int(
                details['total_attended_minutes'] / 
                details['total_duration_minutes'] * 100
            )
        
        if details['total_sessions'] > 0:
            details['sessions_percent'] = int(
                details['sessions_attended'] / 
                details['total_sessions'] * 100
            )
        
        # Check requirement
        if self.attendance_requirement == self.AttendanceRequirement.PERCENTAGE_TIME:
            details['requirement_met'] = (
                details['attendance_percent'] >= self.minimum_attendance_percent
            )
        
        elif self.attendance_requirement == self.AttendanceRequirement.PERCENTAGE_SESSIONS:
            details['requirement_met'] = (
                details['sessions_percent'] >= self.minimum_attendance_percent
            )
        
        elif self.attendance_requirement == self.AttendanceRequirement.ALL_SESSIONS:
            details['requirement_met'] = (
                details['sessions_attended'] == details['total_sessions']
            )
        
        elif self.attendance_requirement == self.AttendanceRequirement.MINIMUM_SESSIONS:
            details['requirement_met'] = (
                details['sessions_attended'] >= (self.minimum_sessions_required or 1)
            )
        
        return details['requirement_met'], details
```

---

### New Model: SessionAttendance

Aggregate attendance per registration per session.

```python
class SessionAttendance(BaseModel):
    """
    Attendance summary for a registration at a specific session.
    
    Aggregates multiple AttendanceRecords into a single summary.
    Used for certificate eligibility calculation.
    """
    
    registration = models.ForeignKey(
        'registrations.Registration',
        on_delete=models.CASCADE,
        related_name='session_attendances'
    )
    session = models.ForeignKey(
        'events.EventSession',
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    
    # Attendance summary for this session
    attended = models.BooleanField(
        default=False,
        help_text="Met session attendance threshold"
    )
    first_join_at = models.DateTimeField(
        null=True, blank=True
    )
    last_leave_at = models.DateTimeField(
        null=True, blank=True
    )
    total_attendance_minutes = models.PositiveIntegerField(
        default=0
    )
    attendance_percent = models.PositiveIntegerField(
        default=0,
        help_text="Percentage of session attended"
    )
    
    # Override
    attendance_override = models.BooleanField(
        default=False
    )
    attendance_override_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    attendance_override_reason = models.TextField(
        blank=True
    )
    
    class Meta:
        db_table = 'session_attendances'
        unique_together = [['registration', 'session']]
        indexes = [
            models.Index(fields=['registration']),
            models.Index(fields=['session']),
            models.Index(fields=['session', 'attended']),
        ]
        verbose_name = 'Session Attendance'
        verbose_name_plural = 'Session Attendances'
    
    def __str__(self):
        return f"{self.registration.full_name} @ {self.session.title}"
    
    def update_from_records(self):
        """
        Recalculate attendance summary from AttendanceRecords.
        """
        records = AttendanceRecord.objects.filter(
            session=self.session,
            registration=self.registration
        )
        
        if not records.exists():
            self.attended = False
            self.total_attendance_minutes = 0
            self.attendance_percent = 0
            self.first_join_at = None
            self.last_leave_at = None
        else:
            total_minutes = sum(r.duration_minutes for r in records)
            
            self.total_attendance_minutes = total_minutes
            self.first_join_at = min(r.join_time for r in records)
            self.last_leave_at = max(
                r.leave_time for r in records if r.leave_time
            ) if any(r.leave_time for r in records) else None
            
            # Calculate percentage
            if self.session.duration_minutes > 0:
                self.attendance_percent = int(
                    total_minutes / self.session.duration_minutes * 100
                )
            
            # Check threshold (unless overridden)
            if not self.attendance_override:
                threshold = self.session.event.session_attendance_threshold
                self.attended = self.attendance_percent >= threshold
        
        self.save()
        
        # Update registration's overall eligibility
        self.registration.update_attendance_eligibility()
```

---

### Modified: AttendanceRecord

```python
class AttendanceRecord(BaseModel):
    """
    Individual attendance record from Zoom.
    
    NOW LINKED TO SESSION instead of directly to Event.
    """
    
    # CHANGED: Primary link is to session
    session = models.ForeignKey(
        'events.EventSession',
        on_delete=models.CASCADE,
        related_name='attendance_records',
        help_text="Session this attendance is for"
    )
    
    # KEEP: Event FK for easy querying (denormalized)
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='attendance_records',
        help_text="Event (denormalized from session)"
    )
    
    registration = models.ForeignKey(
        'registrations.Registration',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='attendance_records'
    )
    
    # ... rest of existing fields ...
    
    def save(self, *args, **kwargs):
        # Auto-populate event from session
        if self.session and not self.event_id:
            self.event = self.session.event
        super().save(*args, **kwargs)
    
    def match_to_registration(self, registration, user=None, manual=False):
        """
        Match this record to a registration.
        Also creates/updates SessionAttendance.
        """
        self.registration = registration
        self.is_matched = True
        self.matched_at = timezone.now()
        self.matched_manually = manual
        self.matched_by = user if manual else None
        self.save()
        
        # Create or update SessionAttendance
        session_attendance, created = SessionAttendance.objects.get_or_create(
            registration=registration,
            session=self.session
        )
        session_attendance.update_from_records()
```

---

### Modified: Registration

```python
class Registration(SoftDeleteModel):
    """
    Modified Registration with multi-session attendance tracking.
    """
    
    # ... existing fields ...
    
    # =========================================
    # MODIFIED: Attendance (now aggregate across sessions)
    # =========================================
    
    # Keep these for backward compat and quick access
    attended = models.BooleanField(
        default=False,
        help_text="Attended at least one session"
    )
    total_attendance_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Total minutes across all sessions"
    )
    sessions_attended = models.PositiveIntegerField(
        default=0,
        help_text="Number of sessions attended"
    )
    attendance_eligible = models.BooleanField(
        default=False,
        help_text="Met attendance requirement for certificate"
    )
    
    # =========================================
    # NEW: Methods
    # =========================================
    def update_attendance_eligibility(self):
        """
        Recalculate attendance eligibility from SessionAttendances.
        Called after each SessionAttendance update.
        """
        event = self.event
        
        if not event.is_multi_session:
            # Single session: use existing logic
            return self.update_attendance_summary()
        
        # Multi-session: aggregate from SessionAttendances
        session_attendances = self.session_attendances.all()
        
        self.sessions_attended = session_attendances.filter(attended=True).count()
        self.total_attendance_minutes = sum(
            sa.total_attendance_minutes for sa in session_attendances
        )
        self.attended = self.sessions_attended > 0
        
        # Calculate eligibility
        if not self.attendance_override:
            is_eligible, _ = event.calculate_registration_eligibility(self)
            self.attendance_eligible = is_eligible
        
        self.save(update_fields=[
            'attended', 'total_attendance_minutes', 'sessions_attended',
            'attendance_eligible', 'updated_at'
        ])
    
    def get_attendance_details(self):
        """
        Get detailed attendance breakdown.
        
        Returns:
            dict with per-session and aggregate attendance
        """
        return self.event.calculate_registration_eligibility(self)[1]
```

---

### Modified: EventReminder

```python
class EventReminder(BaseModel):
    """
    Modified to support both event-level and session-level reminders.
    """
    
    event = models.ForeignKey(
        'Event',
        on_delete=models.CASCADE,
        related_name='reminders'
    )
    
    # NEW: Optional session-specific reminder
    session = models.ForeignKey(
        'EventSession',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='reminders',
        help_text="Specific session (null = event-level reminder)"
    )
    
    # ... rest of existing fields ...
    
    @classmethod
    def create_reminders_for_event(cls, event):
        """
        Create appropriate reminders for event.
        
        For single-session: reminders for the session
        For multi-session: reminders for each session + event start
        """
        reminders = []
        
        if event.is_multi_session:
            # Event-level reminder (course starts)
            first_session = event.first_session
            if first_session:
                reminders.append(cls(
                    event=event,
                    session=None,  # Event-level
                    reminder_type=cls.ReminderType.BEFORE_24H,
                    scheduled_for=first_session.starts_at - timezone.timedelta(hours=24)
                ))
            
            # Per-session reminders
            for session in event.sessions.all():
                reminders.append(cls(
                    event=event,
                    session=session,
                    reminder_type=cls.ReminderType.BEFORE_1H,
                    scheduled_for=session.starts_at - timezone.timedelta(hours=1)
                ))
        else:
            # Single session: standard reminders
            session = event.sessions.first()
            if session:
                reminders.extend([
                    cls(
                        event=event,
                        session=session,
                        reminder_type=cls.ReminderType.BEFORE_24H,
                        scheduled_for=session.starts_at - timezone.timedelta(hours=24)
                    ),
                    cls(
                        event=event,
                        session=session,
                        reminder_type=cls.ReminderType.BEFORE_1H,
                        scheduled_for=session.starts_at - timezone.timedelta(hours=1)
                    )
                ])
        
        cls.objects.bulk_create(reminders)
        return reminders
```

---

### Modified: ZoomWebhookLog

```python
class ZoomWebhookLog(BaseModel):
    """
    Modified to link to EventSession.
    """
    
    # ... existing fields ...
    
    # CHANGED: Link to session instead of event
    session = models.ForeignKey(
        'events.EventSession',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='zoom_webhooks',
        help_text="Matched session"
    )
    
    # KEEP: Event for convenience (denormalized)
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='zoom_webhooks'
    )
    
    def match_session(self):
        """
        Try to match webhook to a session.
        """
        if self.session:
            return self.session
        
        try:
            session = EventSession.objects.get(
                zoom_meeting_id=self.zoom_meeting_id
            )
            self.session = session
            self.event = session.event
            self.save(update_fields=['session', 'event', 'updated_at'])
            return session
        except EventSession.DoesNotExist:
            return None
```

---

### Modified: Certificate Data

```python
def build_certificate_data(self):
    """
    Build certificate data snapshot.
    Modified for multi-session events.
    """
    reg = self.registration
    event = reg.event
    
    # Get attendance details
    _, attendance_details = event.calculate_registration_eligibility(reg)
    
    self.certificate_data = {
        # ... existing fields ...
        
        # NEW: Multi-session data
        'event_format': event.event_format,
        'total_sessions': attendance_details['total_sessions'],
        'sessions_attended': attendance_details['sessions_attended'],
        'total_duration_minutes': attendance_details['total_duration_minutes'],
        'total_attended_minutes': attendance_details['total_attended_minutes'],
        'attendance_percent': attendance_details['attendance_percent'],
        
        # Session breakdown (for detailed certificates)
        'sessions': [
            {
                'title': sa.session.title,
                'date': sa.session.starts_at.date().isoformat(),
                'attended': sa.attended,
                'minutes': sa.total_attendance_minutes
            }
            for sa in reg.session_attendances.select_related('session')
        ] if event.is_multi_session else []
    }
```

---

## Updated ERD

```
Event (container)
├── EventSession (1:N) ─────────────────┐
│   ├── zoom_meeting_id                 │
│   ├── starts_at, duration             │
│   └── status                          │
│                                       │
├── Registration (1:N) ────────┬────────┤
│   └── SessionAttendance (1:N)│        │
│       ├── session ───────────┼────────┘
│       ├── attended           │
│       └── total_minutes      │
│                              │
└── AttendanceRecord (1:N) ────┘
    ├── session (FK)
    ├── registration (FK)
    └── zoom participant data
```

---

## Migration Strategy

### Phase 1: Add Models (Non-Breaking)

```python
# migrations/0001_add_multi_session.py

class Migration(migrations.Migration):
    
    operations = [
        # 1. Add EventSession model
        migrations.CreateModel(
            name='EventSession',
            # ... fields ...
        ),
        
        # 2. Add SessionAttendance model
        migrations.CreateModel(
            name='SessionAttendance',
            # ... fields ...
        ),
        
        # 3. Add new fields to Event
        migrations.AddField(
            model_name='event',
            name='event_format',
            field=models.CharField(default='single', max_length=20),
        ),
        migrations.AddField(
            model_name='event',
            name='attendance_requirement',
            field=models.CharField(default='percentage_time', max_length=30),
        ),
        
        # 4. Add session FK to AttendanceRecord (nullable)
        migrations.AddField(
            model_name='attendancerecord',
            name='session',
            field=models.ForeignKey(null=True, ...),
        ),
    ]
```

### Phase 2: Data Migration

```python
# migrations/0002_migrate_to_sessions.py

def migrate_single_session_events(apps, schema_editor):
    """Create EventSession for each existing Event."""
    Event = apps.get_model('events', 'Event')
    EventSession = apps.get_model('events', 'EventSession')
    
    for event in Event.objects.all():
        # Create session from event's Zoom data
        session = EventSession.objects.create(
            event=event,
            title=event.title,
            description=event.description,
            session_number=1,
            starts_at=event.starts_at,
            duration_minutes=event.duration_minutes,
            zoom_enabled=event.zoom_enabled,
            zoom_meeting_id=event.zoom_meeting_id,
            zoom_join_url=event.zoom_join_url,
            zoom_host_url=event.zoom_host_url,
            zoom_passcode=event.zoom_passcode,
            status='completed' if event.status == 'completed' else 'scheduled'
        )
        
        # Link attendance records to session
        event.attendance_records.update(session=session)


def migrate_session_attendances(apps, schema_editor):
    """Create SessionAttendance summaries."""
    Registration = apps.get_model('registrations', 'Registration')
    SessionAttendance = apps.get_model('registrations', 'SessionAttendance')
    
    for reg in Registration.objects.filter(attended=True):
        session = reg.event.sessions.first()
        if session:
            SessionAttendance.objects.create(
                registration=reg,
                session=session,
                attended=reg.attended,
                total_attendance_minutes=reg.total_attendance_minutes,
                attendance_percent=reg.attendance_percent
            )
```

### Phase 3: Deprecate Old Fields

```python
# After confirming migration success, mark old fields as deprecated
# Eventually remove in future migration:
# - Event.zoom_meeting_id (use session.zoom_meeting_id)
# - Event.starts_at (use first_session.starts_at)
# - Event.duration_minutes (use total_duration_minutes)
```

---

## API Changes

### Event Creation

```python
# Single-session event (backward compatible)
POST /api/events/
{
    "title": "Webinar",
    "event_format": "single",
    "starts_at": "2025-02-01T14:00:00Z",
    "duration_minutes": 60,
    "zoom_enabled": true
}

# Multi-session event
POST /api/events/
{
    "title": "4-Week Course",
    "event_format": "course",
    "attendance_requirement": "percentage_sessions",
    "minimum_attendance_percent": 75,
    "sessions": [
        {
            "title": "Week 1: Introduction",
            "starts_at": "2025-02-01T14:00:00Z",
            "duration_minutes": 60
        },
        {
            "title": "Week 2: Deep Dive",
            "starts_at": "2025-02-08T14:00:00Z",
            "duration_minutes": 60
        }
    ]
}
```

### Registration Response

```python
GET /api/registrations/{uuid}/
{
    "uuid": "...",
    "event": {...},
    "attendance": {
        "total_sessions": 4,
        "sessions_attended": 3,
        "total_duration_minutes": 240,
        "total_attended_minutes": 175,
        "attendance_percent": 73,
        "sessions_percent": 75,
        "eligible_for_certificate": true,
        "sessions": [
            {"session": "Week 1", "attended": true, "minutes": 55},
            {"session": "Week 2", "attended": true, "minutes": 60},
            {"session": "Week 3", "attended": true, "minutes": 60},
            {"session": "Week 4", "attended": false, "minutes": 0}
        ]
    }
}
```

---

## UI Considerations

### Event Creation Flow

1. **Format Selection**: Single session / Course / Conference
2. **Session Builder**: Add/remove sessions with date/time picker
3. **Attendance Rules**: Configure requirement type and thresholds

### Attendee Dashboard

- Show course progress: "3 of 4 sessions attended"
- Session-by-session breakdown
- Next session reminder
- Overall eligibility status

### Organizer Dashboard

- Per-session attendance overview
- Aggregate course completion rates
- Session-level Zoom controls

---

## Business Rules

1. **Single-session backward compatibility**: Existing events continue working
2. **Session order**: Sessions numbered 1, 2, 3... in chronological order
3. **Session cancellation**: Cancelled sessions don't count toward totals
4. **Attendance threshold**: Per-session threshold determines "attended" status
5. **Certificate eligibility**: Based on aggregate per attendance_requirement
6. **Zoom meetings**: One per session, created when session is created
7. **Reminders**: Both event-level (course starting) and session-level
8. **CPD credits**: Can be split proportionally or set per-session

---

## Index Summary

| Table | Index | Purpose |
|-------|-------|---------|
| event_sessions | event_id, session_number (unique) | Session ordering |
| event_sessions | starts_at | Calendar queries |
| event_sessions | zoom_meeting_id | Webhook matching |
| event_sessions | status, starts_at | Upcoming sessions |
| session_attendances | registration_id, session_id (unique) | One per reg per session |
| session_attendances | session_id, attended | Session attendance stats |
| attendance_records | session_id | Records per session |
