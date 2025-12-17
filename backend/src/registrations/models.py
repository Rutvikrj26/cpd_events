"""
Registrations app models - Registration, AttendanceRecord, CustomFieldResponse.
"""

from django.db import models
from django.utils import timezone

from common.fields import LowercaseEmailField
from common.models import BaseModel, SoftDeleteModel
from events.models import Event  # Moved from inside update_attendance_summary


class Registration(SoftDeleteModel):
    """
    An attendee's registration for an event.

    Key Concepts:
    - User can be null (guest registration before account creation)
    - Email is always stored (for matching and certificate delivery)
    - When user creates account, registrations are linked via email

    Lifecycle:
        Guest registers → Registration(user=None, email=X)
        Guest creates account → Registration.user = new_user (matched by email)

    Soft Delete Behavior:
    - Certificate is PROTECTED (cannot delete registration with certificate)
    - Attendance records preserved (for audit)
    """

    class Status(models.TextChoices):
        CONFIRMED = 'confirmed', 'Confirmed'
        WAITLISTED = 'waitlisted', 'Waitlisted'
        CANCELLED = 'cancelled', 'Cancelled'

    class Source(models.TextChoices):
        SELF = 'self', 'Self Registration'
        INVITE = 'invite', 'Invitation Link'
        IMPORT = 'import', 'CSV Import'
        MANUAL = 'manual', 'Manual Entry'
        API = 'api', 'API'

    # =========================================
    # Relationships
    # =========================================
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, related_name='registrations')

    # User link (null for guest registrations)
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registrations',
        help_text="Linked user account (null for guests)",
    )

    # Who created this registration
    registered_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registrations_created',
        help_text="User who created this registration (organizer for manual adds)",
    )

    # =========================================
    # Contact Info (always stored)
    # =========================================
    email = LowercaseEmailField(db_index=True, help_text="Registrant email (canonical, lowercase)")
    full_name = models.CharField(max_length=255, help_text="Full name as entered at registration")
    professional_title = models.CharField(max_length=255, blank=True, help_text="Professional title")
    organization_name = models.CharField(max_length=255, blank=True, help_text="Organization/company")

    # =========================================
    # Registration Metadata
    # =========================================
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED, db_index=True)
    source = models.CharField(
        max_length=20, choices=Source.choices, default=Source.SELF, help_text="How this registration was created"
    )

    # Waitlist position (only if waitlisted)
    waitlist_position = models.PositiveIntegerField(null=True, blank=True, help_text="Position in waitlist (1 = first)")
    promoted_from_waitlist_at = models.DateTimeField(
        null=True, blank=True, help_text="When promoted from waitlist to confirmed"
    )

    # Cancellation
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)

    # =========================================
    # Attendance (denormalized summary)
    # =========================================
    attended = models.BooleanField(default=False, help_text="Whether attendee joined the event")
    first_join_at = models.DateTimeField(null=True, blank=True, help_text="First time attendee joined")
    last_leave_at = models.DateTimeField(null=True, blank=True, help_text="Last time attendee left")
    total_attendance_minutes = models.PositiveIntegerField(default=0, help_text="Total minutes attended (sum of all sessions)")
    attendance_eligible = models.BooleanField(default=False, help_text="Met minimum attendance threshold")
    attendance_override = models.BooleanField(default=False, help_text="Attendance manually overridden by organizer")
    attendance_override_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attendance_overrides',
        help_text="Who set the override",
    )
    attendance_override_reason = models.TextField(blank=True, help_text="Reason for override")

    # =========================================
    # Certificate Status (denormalized)
    # =========================================
    certificate_issued = models.BooleanField(default=False)
    certificate_issued_at = models.DateTimeField(null=True, blank=True)

    # =========================================
    # Privacy
    # =========================================
    allow_public_verification = models.BooleanField(default=True, help_text="Allow certificate to be publicly verified")

    class Meta:
        db_table = 'registrations'
        unique_together = [['event', 'email']]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event', 'status']),
            models.Index(fields=['email']),
            models.Index(fields=['user']),
            models.Index(fields=['uuid']),
            models.Index(fields=['event', 'attendance_eligible']),
            models.Index(fields=['user', 'status']),
        ]
        verbose_name = 'Registration'
        verbose_name_plural = 'Registrations'

    def __str__(self):
        return f"{self.full_name} → {self.event.title}"

    # =========================================
    # Properties
    # =========================================
    @property
    def is_confirmed(self):
        return self.status == self.Status.CONFIRMED

    @property
    def is_waitlisted(self):
        return self.status == self.Status.WAITLISTED

    @property
    def can_receive_certificate(self):
        """Check if eligible for certificate."""
        if not self.event.certificates_enabled:
            return False
        if self.status != self.Status.CONFIRMED:
            return False
        return not (not self.attendance_eligible and not self.attendance_override)

    @property
    def attendance_percent(self):
        """Calculate attendance percentage."""
        if self.event.duration_minutes == 0:
            return 0
        return int((self.total_attendance_minutes / self.event.duration_minutes) * 100)

    # =========================================
    # Methods
    # =========================================
    def link_to_user(self, user):
        """
        Link this registration to a user account.
        Called when user verifies email matching this registration.
        """
        if self.user is None and user.email.lower() == self.email.lower():
            self.user = user
            self.save(update_fields=['user', 'updated_at'])
            return True
        return False

    def cancel(self, reason='', cancelled_by=None):
        """Cancel this registration."""
        self.status = self.Status.CANCELLED
        self.cancelled_at = timezone.now()
        self.cancellation_reason = reason
        self.save(update_fields=['status', 'cancelled_at', 'cancellation_reason', 'updated_at'])

        # Update event counts
        self.event.update_counts()

        # Promote from waitlist if applicable
        self._promote_next_from_waitlist()

    def _promote_next_from_waitlist(self):
        """Promote next person from waitlist after cancellation."""
        # Only promote if auto-promote is enabled on the event
        if not self.event.waitlist_enabled or not self.event.waitlist_auto_promote:
            return

        next_waitlisted = (
            Registration.objects.filter(event=self.event, status=self.Status.WAITLISTED, deleted_at__isnull=True)
            .order_by('waitlist_position')
            .first()
        )

        if next_waitlisted:
            next_waitlisted.promote_from_waitlist()

    def promote_from_waitlist(self):
        """Promote from waitlist to confirmed."""
        if self.status != self.Status.WAITLISTED:
            return

        self.status = self.Status.CONFIRMED
        self.promoted_from_waitlist_at = timezone.now()
        self.waitlist_position = None
        self.save(update_fields=['status', 'promoted_from_waitlist_at', 'waitlist_position', 'updated_at'])

        self.event.update_counts()

    def update_attendance_summary(self):
        """
        Recalculate attendance summary from AttendanceRecords and SessionAttendance.
        Called after attendance records are created/updated.
        """

        # General attendance summary for single-session events or initial calculations
        records = self.attendance_records.all()

        total_minutes = sum(r.duration_minutes for r in records)
        self.total_attendance_minutes = total_minutes
        self.attended = total_minutes > 0

        if records.exists():
            first_join = min(r.join_time for r in records)
            last_leave = max(r.leave_time for r in records if r.leave_time) if any(r.leave_time for r in records) else None
            self.first_join_at = first_join
            self.last_leave_at = last_leave
        else:
            self.first_join_at = None
            self.last_leave_at = None

        # Determine attendance eligibility based on event type
        if not self.attendance_override:
            if self.event.event_type == Event.EventType.COURSE:  # Assuming 'COURSE' implies multi-session, adjust as needed
                # Multi-session event logic
                session_progress_records = self.session_attendance.all()
                total_sessions = self.event.sessions.filter(is_published=True).count()
                eligible_sessions_count = session_progress_records.filter(is_eligible=True).count()

                if self.event.multi_session_completion_criteria == Event.MultiSessionCompletionCriteria.ALL_SESSIONS:
                    # All mandatory sessions must be eligible
                    mandatory_sessions_count = self.event.sessions.filter(is_mandatory=True, is_published=True).count()
                    self.attendance_eligible = (eligible_sessions_count >= mandatory_sessions_count) and (
                        mandatory_sessions_count > 0
                    )
                elif (
                    self.event.multi_session_completion_criteria == Event.MultiSessionCompletionCriteria.PERCENTAGE_OF_SESSIONS
                ):
                    if total_sessions > 0 and self.event.multi_session_completion_value is not None:
                        percentage_attended = (eligible_sessions_count / total_sessions) * 100
                        self.attendance_eligible = percentage_attended >= self.event.multi_session_completion_value
                    else:
                        self.attendance_eligible = False  # Cannot determine without total sessions or value
                elif self.event.multi_session_completion_criteria == Event.MultiSessionCompletionCriteria.MIN_SESSIONS_COUNT:
                    if self.event.multi_session_completion_value is not None:
                        self.attendance_eligible = eligible_sessions_count >= self.event.multi_session_completion_value
                    else:
                        self.attendance_eligible = False  # Cannot determine without minimum sessions count
                elif self.event.multi_session_completion_criteria == Event.MultiSessionCompletionCriteria.TOTAL_MINUTES:
                    # Fallback to total minutes across all sessions if specified
                    self.attendance_eligible = total_minutes >= self.event.minimum_attendance_minutes
                else:
                    self.attendance_eligible = False  # Default to false if criteria is not recognized or set
            else:
                # Single-session event logic
                self.attendance_eligible = total_minutes >= self.event.minimum_attendance_minutes

        self.save(
            update_fields=[
                'total_attendance_minutes',
                'attended',
                'first_join_at',
                'last_leave_at',
                'attendance_eligible',
                'updated_at',
            ]
        )

    def set_attendance_override(self, eligible, user, reason=''):
        """Manually override attendance eligibility."""
        self.attendance_override = True
        self.attendance_eligible = eligible
        self.attendance_override_by = user
        self.attendance_override_reason = reason
        self.save(
            update_fields=[
                'attendance_override',
                'attendance_eligible',
                'attendance_override_by',
                'attendance_override_reason',
                'updated_at',
            ]
        )

    @classmethod
    def link_registrations_for_user(cls, user):
        """Link all registrations with matching email to this user."""
        count = cls.objects.filter(email__iexact=user.email, user__isnull=True, deleted_at__isnull=True).update(user=user)
        return count


class AttendanceRecord(BaseModel):
    """
    Individual attendance record from Zoom.

    A registration can have multiple records (join → leave → rejoin → leave).
    Records are created from Zoom webhook events or participant reports.
    """

    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, related_name='attendance_records')

    registration = models.ForeignKey(
        Registration,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='attendance_records',
        help_text="Matched registration (null if unmatched)",
    )

    # =========================================
    # Zoom Participant Info
    # =========================================
    zoom_participant_id = models.CharField(
        max_length=100, blank=True, help_text="Zoom participant ID (unique per meeting session)"
    )
    zoom_user_id = models.CharField(max_length=100, blank=True, help_text="Zoom user ID (for registered Zoom users)")
    zoom_user_email = LowercaseEmailField(blank=True, db_index=True, help_text="Email from Zoom (for matching)")
    zoom_user_name = models.CharField(max_length=255, blank=True, help_text="Display name in Zoom")

    # =========================================
    # Join Method
    # =========================================
    join_method = models.CharField(max_length=50, blank=True, help_text="How attendee joined (web, app, phone)")
    device_type = models.CharField(max_length=50, blank=True, help_text="Device type (Windows, Mac, iOS, Android)")
    ip_address = models.GenericIPAddressField(null=True, blank=True, help_text="IP address (if available)")
    location = models.CharField(max_length=100, blank=True, help_text="GeoIP location")

    # =========================================
    # Timing
    # =========================================
    join_time = models.DateTimeField(db_index=True, help_text="When participant joined")
    leave_time = models.DateTimeField(null=True, blank=True, help_text="When participant left (null if still in meeting)")
    duration_minutes = models.PositiveIntegerField(default=0, help_text="Duration in minutes")

    # =========================================
    # Matching Status
    # =========================================
    is_matched = models.BooleanField(default=False, db_index=True, help_text="Successfully matched to a registration")
    matched_at = models.DateTimeField(null=True, blank=True, help_text="When match was made")
    matched_manually = models.BooleanField(default=False, help_text="Match was done manually by organizer")
    matched_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attendance_matches',
        help_text="Who performed manual match",
    )

    class Meta:
        db_table = 'attendance_records'
        ordering = ['join_time']
        indexes = [
            models.Index(fields=['event', 'registration']),
            models.Index(fields=['event', 'is_matched']),
            models.Index(fields=['zoom_user_email']),
            models.Index(fields=['zoom_participant_id']),
            models.Index(fields=['join_time']),
        ]
        verbose_name = 'Attendance Record'
        verbose_name_plural = 'Attendance Records'

    def __str__(self):
        name = self.zoom_user_name or self.zoom_user_email or 'Unknown'
        return f"{name} @ {self.event.title}"

    @property
    def is_in_meeting(self):
        """Check if participant is currently in the meeting."""
        return self.leave_time is None

    @property
    def display_name(self):
        """Best available name for display."""
        return self.zoom_user_name or self.zoom_user_email or 'Unknown Participant'

    def calculate_duration(self):
        """Calculate and update duration from join/leave times."""
        if self.leave_time and self.join_time:
            delta = self.leave_time - self.join_time
            self.duration_minutes = max(0, int(delta.total_seconds() / 60))
        else:
            self.duration_minutes = 0

    def participant_left(self, leave_time=None):
        """Mark participant as having left the meeting."""
        self.leave_time = leave_time or timezone.now()
        self.calculate_duration()
        self.save(update_fields=['leave_time', 'duration_minutes', 'updated_at'])

        # Update registration summary
        if self.registration:
            self.registration.update_attendance_summary()

    def match_to_registration(self, registration, user=None, manual=False):
        """Match this record to a registration."""
        self.registration = registration
        self.is_matched = True
        self.matched_at = timezone.now()
        self.matched_manually = manual
        self.matched_by = user if manual else None
        self.save(update_fields=['registration', 'is_matched', 'matched_at', 'matched_manually', 'matched_by', 'updated_at'])

        # Update registration summary
        registration.update_attendance_summary()

    def save(self, *args, **kwargs):
        # Auto-calculate duration on save
        if self.leave_time and not kwargs.get('update_fields'):
            self.calculate_duration()
        super().save(*args, **kwargs)


class CustomFieldResponse(BaseModel):
    """
    Response to a custom registration field.

    Stores the value(s) submitted for each custom field in the registration.
    """

    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='custom_field_responses')
    field = models.ForeignKey('events.EventCustomField', on_delete=models.CASCADE, related_name='responses')

    # Value storage
    value = models.TextField(blank=True, help_text="Response value (JSON for multi-select)")

    class Meta:
        db_table = 'custom_field_responses'
        unique_together = [['registration', 'field']]
        verbose_name = 'Custom Field Response'
        verbose_name_plural = 'Custom Field Responses'

    def __str__(self):
        return f"{self.registration.email} - {self.field.label}"

    @property
    def parsed_value(self):
        """Parse value for multi-select fields."""
        import json

        if self.field.field_type in ['multiselect']:
            try:
                return json.loads(self.value)
            except (json.JSONDecodeError, TypeError):
                return []
        return self.value
