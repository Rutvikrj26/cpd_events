"""
Events app models - Event, EventStatusHistory, EventCustomField.
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from common.models import BaseModel, SoftDeleteModel
from common.validators import validate_zoom_settings_schema


class Event(SoftDeleteModel):
    """
    A CPD event hosted by an organizer.

    Lifecycle:
        draft → published → live → completed → closed
        At any point can be cancelled

    Key Features:
    - Status management with validation
    - Zoom meeting integration
    - CPD credit configuration
    - Certificate settings
    - Waitlist management
    - Denormalized counts for performance

    Soft Delete Behavior:
    - Registrations preserved (for certificates)
    - Zoom meeting may be deleted via API
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'
        LIVE = 'live', 'Live'
        COMPLETED = 'completed', 'Completed'
        CLOSED = 'closed', 'Closed'
        CANCELLED = 'cancelled', 'Cancelled'

    class EventType(models.TextChoices):
        WEBINAR = 'webinar', 'Webinar'
        WORKSHOP = 'workshop', 'Workshop'
        TRAINING = 'training', 'Training Session'
        LECTURE = 'lecture', 'Lecture'
        OTHER = 'other', 'Other'

    # Valid status transitions
    VALID_TRANSITIONS = {
        Status.DRAFT: [Status.PUBLISHED, Status.CANCELLED],
        Status.PUBLISHED: [Status.LIVE, Status.DRAFT, Status.CANCELLED],
        Status.LIVE: [Status.COMPLETED, Status.CANCELLED],
        Status.COMPLETED: [Status.CLOSED],
        Status.CLOSED: [],
        Status.CANCELLED: [],
    }

    # =========================================
    # Ownership
    # =========================================
    owner = models.ForeignKey(
        'accounts.User', on_delete=models.PROTECT, related_name='events', help_text="Organizer who owns this event"
    )
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='events',
        help_text="Organization that owns this event (null for individual organizers)",
    )

    # =========================================
    # Basic Info
    # =========================================
    class EventFormat(models.TextChoices):
        ONLINE = 'online', 'Online'
        IN_PERSON = 'in-person', 'In Person'
        HYBRID = 'hybrid', 'Hybrid'

    title = models.CharField(max_length=200, help_text="Event title")
    slug = models.SlugField(max_length=250, unique=True, help_text="URL-friendly identifier")
    description = models.TextField(blank=True, max_length=10000, help_text="Event description (supports markdown)")
    short_description = models.CharField(max_length=500, blank=True, help_text="Brief description for listings")
    event_type = models.CharField(
        max_length=20, choices=EventType.choices, default=EventType.WEBINAR, help_text="Type of event"
    )
    format = models.CharField(
        max_length=20, choices=EventFormat.choices, default=EventFormat.ONLINE, help_text="Event format"
    )

    is_multi_session = models.BooleanField(
        default=False, help_text="Is this a multi-session event?"
    )

    class MultiSessionCompletionCriteria(models.TextChoices):
        ALL_SESSIONS = 'all_sessions', 'All Sessions'
        PERCENTAGE_OF_SESSIONS = 'percentage_of_sessions', 'Percentage of Sessions'
        MIN_SESSIONS_COUNT = 'min_sessions_count', 'Minimum Number of Sessions'
        TOTAL_MINUTES = 'total_minutes', 'Total Attendance Minutes (across all sessions)'

    multi_session_completion_criteria = models.CharField(
        max_length=50,
        choices=MultiSessionCompletionCriteria.choices,
        default=MultiSessionCompletionCriteria.TOTAL_MINUTES,
        help_text="Criteria for marking a multi-session event as completed for certificate eligibility",
    )
    multi_session_completion_value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Value for multi-session completion criteria (e.g., 80 for percentage, 3 for min sessions)",
    )

    # =========================================
    # Status
    # =========================================
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)

    # =========================================
    # Schedule
    # =========================================
    timezone = models.CharField(max_length=50, default='UTC', help_text="Event timezone")
    starts_at = models.DateTimeField(db_index=True, help_text="Scheduled start time")
    duration_minutes = models.PositiveIntegerField(
        default=60, validators=[MinValueValidator(15), MaxValueValidator(480)], help_text="Duration in minutes (15-480)"
    )

    # Actual timing (set when event runs)
    actual_start_at = models.DateTimeField(null=True, blank=True, help_text="When event actually started")
    actual_end_at = models.DateTimeField(null=True, blank=True, help_text="When event actually ended")

    # =========================================
    # Registration Settings
    # =========================================
    currency = models.CharField(max_length=3, default='usd', help_text="Currency code (iso 4217)")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Ticket price (0.00 for free)")

    registration_enabled = models.BooleanField(default=True, help_text="Accept new registrations")
    max_attendees = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum attendees (null = unlimited)")
    registration_deadline = models.DateTimeField(null=True, blank=True, help_text="Registration cutoff time") # Deprecated in favor of closes_at? Keeping for back-compat or replacing.
    registration_opens_at = models.DateTimeField(null=True, blank=True, help_text="When registration opens")
    registration_closes_at = models.DateTimeField(null=True, blank=True, help_text="When registration closes")

    # Waitlist
    waitlist_enabled = models.BooleanField(default=False, help_text="Enable waitlist when full")
    waitlist_max = models.PositiveIntegerField(null=True, blank=True, help_text="Max waitlist size")
    waitlist_auto_promote = models.BooleanField(default=False, help_text="Automatically promote from waitlist when spots open")

    # Guest registration
    allow_guest_registration = models.BooleanField(default=True, help_text="Allow registration without account")

    # =========================================
    # Zoom Integration
    # =========================================
    zoom_meeting_id = models.CharField(max_length=20, blank=True, db_index=True, help_text="Zoom meeting ID")
    zoom_meeting_uuid = models.CharField(max_length=100, blank=True, help_text="Zoom meeting UUID")
    zoom_join_url = models.URLField(blank=True, help_text="Zoom join URL for attendees")
    zoom_start_url = models.URLField(max_length=2000, blank=True, help_text="Zoom start URL for host")
    zoom_password = models.CharField(max_length=50, blank=True, help_text="Zoom meeting password")
    zoom_settings = models.JSONField(
        default=dict, validators=[validate_zoom_settings_schema], blank=True, help_text="Zoom meeting settings"
    )

    # =========================================
    # CPD Settings
    # =========================================
    cpd_enabled = models.BooleanField(default=True, help_text="Event offers CPD credits")
    cpd_credit_type = models.CharField(max_length=50, blank=True, help_text="Type of CPD credits (e.g., CME, CPE)")
    cpd_credit_value = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Number of CPD credits")
    cpd_accreditation_note = models.TextField(blank=True, max_length=1000, help_text="Accreditation details")

    # =========================================
    # Attendance Settings
    # =========================================
    minimum_attendance_minutes = models.PositiveIntegerField(default=0, help_text="Minimum minutes for certificate eligibility")
    minimum_attendance_percent = models.PositiveIntegerField(
        default=80, validators=[MinValueValidator(0), MaxValueValidator(100)], help_text="Minimum % attendance for certificate"
    )

    # =========================================
    # Certificate Settings
    # =========================================
    certificates_enabled = models.BooleanField(default=True, help_text="Issue certificates for this event")
    certificate_template = models.ForeignKey(
        'certificates.CertificateTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='events',
        help_text="Template for certificates",
    )
    auto_issue_certificates = models.BooleanField(default=False, help_text="Auto-issue when event completes")

    # =========================================
    # Media & Location
    # =========================================
    cover_image_url = models.URLField(blank=True, help_text="Cover image URL")
    featured_image = models.ImageField(
        upload_to='events/featured_images/',
        blank=True,
        null=True,
        help_text="Featured image upload"
    )
    
    # =========================================
    # Location (for in-person/hybrid events)
    # =========================================
    location = models.CharField(
        max_length=500,
        blank=True,
        help_text="Venue address or location description"
    )

    # =========================================
    # Recording Settings
    # =========================================
    recording_enabled = models.BooleanField(default=False, help_text="Enable cloud recording")
    recording_auto_publish = models.BooleanField(default=False, help_text="Auto-publish recording when available")

    # =========================================
    # Visibility
    # =========================================
    is_public = models.BooleanField(default=True, help_text="Visible in public listings")

    # =========================================
    # Stats (denormalized)
    # =========================================
    registration_count = models.PositiveIntegerField(default=0, help_text="Confirmed registrations")
    waitlist_count = models.PositiveIntegerField(default=0, help_text="Waitlisted registrations")
    attendance_count = models.PositiveIntegerField(default=0, help_text="Attendees who joined")
    certificate_count = models.PositiveIntegerField(default=0, help_text="Certificates issued")

    class Meta:
        db_table = 'events'
        ordering = ['-starts_at']
        indexes = [
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['status', '-starts_at']),
            models.Index(fields=['starts_at']),
            models.Index(fields=['uuid']),
            models.Index(fields=['slug']),
            models.Index(fields=['zoom_meeting_id']),
        ]
        verbose_name = 'Event'
        verbose_name_plural = 'Events'

    def __str__(self):
        return self.title

    # =========================================
    # Properties
    # =========================================
    @property
    def ends_at(self):
        """Calculate scheduled end time."""
        return self.starts_at + timezone.timedelta(minutes=self.duration_minutes)

    @property
    def is_upcoming(self):
        """Check if event is in the future."""
        return self.starts_at > timezone.now()

    @property
    def is_past(self):
        """Check if event end time has passed."""
        return self.ends_at < timezone.now()

    @property
    def owning_entity(self):
        """Return the organization or owner of this event."""
        return self.organization or self.owner

    @property
    def is_free(self):
        """Check if event is free."""
        return self.price == 0

    @property
    def is_full(self):
        """Check if registration is at capacity."""
        if self.max_attendees is None:
            return False
        return self.registration_count >= self.max_attendees

    @property
    def registration_open(self):
        """Check if registration is currently open."""
        if not self.registration_enabled:
            return False
        if self.status not in [self.Status.PUBLISHED]:
            return False
        
        now = timezone.now()
        
        if self.registration_opens_at and now < self.registration_opens_at:
            return False
            
        if self.registration_closes_at and now > self.registration_closes_at:
            return False

        # Fallback/Backward compatibility
        if self.registration_deadline and now > self.registration_deadline:
            return False
            
        return True

    @property
    def is_open_for_registration(self):
        """Alias for registration_open."""
        return self.registration_open

    @property
    def can_waitlist(self):
        """Check if waitlist is available."""
        if not self.waitlist_enabled:
            return False
        if not self.is_full:
            return False
        return not (self.waitlist_max and self.waitlist_count >= self.waitlist_max)

    @property
    def spots_remaining(self):
        """Number of spots remaining."""
        if self.max_attendees is None:
            return None
        return max(0, self.max_attendees - self.registration_count)

    # =========================================
    # Status Methods
    # =========================================
    def can_transition_to(self, new_status):
        """Check if status transition is valid."""
        return new_status in self.VALID_TRANSITIONS.get(self.status, [])

    def _change_status(self, new_status, user=None, reason=''):
        """Internal status change with history."""
        if not self.can_transition_to(new_status):
            raise ValueError(f"Cannot transition from {self.status} to {new_status}")

        old_status = self.status
        self.status = new_status
        self.save(update_fields=['status', 'updated_at'])

        # Create history record
        EventStatusHistory.objects.create(
            event=self, from_status=old_status, to_status=new_status, changed_by=user, reason=reason
        )

    def publish(self, user=None):
        """Publish the event."""
        self._change_status(self.Status.PUBLISHED, user, 'Event published')

    def start(self, user=None):
        """Start the event (go live)."""
        self.actual_start_at = timezone.now()
        self.save(update_fields=['actual_start_at', 'updated_at'])
        self._change_status(self.Status.LIVE, user, 'Event started')

    def complete(self, user=None):
        """Complete the event."""
        self.actual_end_at = timezone.now()
        self.save(update_fields=['actual_end_at', 'updated_at'])
        self._change_status(self.Status.COMPLETED, user, 'Event completed')

    def close(self, user=None):
        """Close the event (no more changes)."""
        self._change_status(self.Status.CLOSED, user, 'Event closed')

    def cancel(self, user=None, reason=''):
        """Cancel the event."""
        self._change_status(self.Status.CANCELLED, user, reason or 'Event cancelled')

    def unpublish(self, user=None):
        """Return to draft status."""
        self._change_status(self.Status.DRAFT, user, 'Event unpublished')

    # =========================================
    # Count Methods
    # =========================================
    def update_counts(self):
        """Update denormalized counts from related objects."""
        from registrations.models import Registration

        registrations = self.registrations.filter(deleted_at__isnull=True)

        self.registration_count = registrations.filter(status=Registration.Status.CONFIRMED).count()

        self.waitlist_count = registrations.filter(status=Registration.Status.WAITLISTED).count()

        self.attendance_count = registrations.filter(attended=True).count()

        self.certificate_count = registrations.filter(certificate_issued=True).count()

        self.save(update_fields=['registration_count', 'waitlist_count', 'attendance_count', 'certificate_count', 'updated_at'])

    def duplicate(self, new_title=None, new_start=None):
        """
        Create a copy of this event.

        Returns:
            New Event instance (unsaved)
        """
        from common.utils import generate_unique_slug

        new_event = Event(
            owner=self.owner,
            title=new_title or f"{self.title} (Copy)",
            description=self.description,
            short_description=self.short_description,
            event_type=self.event_type,
            status=self.Status.DRAFT,
            timezone=self.timezone,
            starts_at=new_start or (self.starts_at + timezone.timedelta(days=7)),
            duration_minutes=self.duration_minutes,
            registration_enabled=self.registration_enabled,
            max_attendees=self.max_attendees,
            waitlist_enabled=self.waitlist_enabled,
            waitlist_max=self.waitlist_max,
            allow_guest_registration=self.allow_guest_registration,
            cpd_enabled=self.cpd_enabled,
            cpd_credit_type=self.cpd_credit_type,
            cpd_credit_value=self.cpd_credit_value,
            cpd_accreditation_note=self.cpd_accreditation_note,
            minimum_attendance_minutes=self.minimum_attendance_minutes,
            minimum_attendance_percent=self.minimum_attendance_percent,
            certificates_enabled=self.certificates_enabled,
            certificate_template=self.certificate_template,
            auto_issue_certificates=self.auto_issue_certificates,
            recording_enabled=self.recording_enabled,
            is_public=self.is_public,
        )

        # Generate unique slug
        new_event.slug = generate_unique_slug(new_event.title, set(Event.objects.values_list('slug', flat=True)))

        return new_event


class EventStatusHistory(BaseModel):
    """
    Audit log for event status changes.
    """

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.TextField(blank=True)

    class Meta:
        db_table = 'event_status_history'
        ordering = ['-created_at']
        verbose_name = 'Event Status History'
        verbose_name_plural = 'Event Status Histories'

    def __str__(self):
        return f"{self.event.title}: {self.from_status} → {self.to_status}"


class EventCustomField(BaseModel):
    """
    Custom field for event registration form.

    Organizers can add custom fields to collect additional
    information from registrants.
    """

    class FieldType(models.TextChoices):
        TEXT = 'text', 'Single Line Text'
        TEXTAREA = 'textarea', 'Multi-line Text'
        SELECT = 'select', 'Dropdown'
        MULTISELECT = 'multiselect', 'Multi-select'
        CHECKBOX = 'checkbox', 'Checkbox'
        RADIO = 'radio', 'Radio Buttons'
        DATE = 'date', 'Date'
        NUMBER = 'number', 'Number'

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='custom_fields')

    label = models.CharField(max_length=200, help_text="Field label")
    field_type = models.CharField(max_length=20, choices=FieldType.choices)
    required = models.BooleanField(default=False, help_text="Is this field required")
    placeholder = models.CharField(max_length=200, blank=True, help_text="Placeholder text")
    help_text = models.CharField(max_length=500, blank=True, help_text="Help text shown below field")

    # For select/multiselect/radio
    options = models.JSONField(default=list, blank=True, help_text="Options for select field (list of strings)")

    # For number fields
    min_value = models.IntegerField(null=True, blank=True)
    max_value = models.IntegerField(null=True, blank=True)

    # Display order
    order = models.PositiveIntegerField(default=0, help_text="Display order (0 = first)")

    class Meta:
        db_table = 'event_custom_fields'
        ordering = ['order', 'id']
        verbose_name = 'Event Custom Field'
        verbose_name_plural = 'Event Custom Fields'

    def __str__(self):
        return f"{self.event.title} - {self.label}"
