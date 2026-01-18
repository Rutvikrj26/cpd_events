# Events App: Event Management

## Overview

The `events` app handles all event-related functionality:
- Event creation and management
- Event lifecycle (draft → published → live → completed)
- Zoom meeting integration
- Custom registration fields
- Event reminders and invitations

---

## Models

### Event

The core event model representing a virtual event.

```python
# events/models.py

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.text import slugify
from common.models import SoftDeleteModel
from common.validators import validate_zoom_settings_schema, validate_timezone


class Event(SoftDeleteModel):
    """
    A virtual event created by an organizer.
    
    Lifecycle:
        DRAFT → PUBLISHED → LIVE → COMPLETED → CLOSED
                    ↓           ↓
               CANCELLED   CANCELLED
    
    Soft Delete Behavior:
    - Registrations preserved (for certificate access)
    - Certificates remain valid and verifiable
    - Attendance records preserved
    
    Ownership:
    - Always owned by an organizer (User with account_type='organizer')
    - Phase 2: Can optionally belong to an Organization
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
        COURSE = 'course', 'Course'
        CONFERENCE = 'conference', 'Conference'
        TRAINING = 'training', 'Training'
        OTHER = 'other', 'Other'
    
    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Public'        # Listed in discovery, open registration
        UNLISTED = 'unlisted', 'Unlisted'  # Not listed, but link works
        PRIVATE = 'private', 'Private'     # Invite-only
    
    # Status transition rules
    VALID_TRANSITIONS = {
        Status.DRAFT: [Status.PUBLISHED],
        Status.PUBLISHED: [Status.LIVE, Status.CANCELLED],
        Status.LIVE: [Status.COMPLETED, Status.CANCELLED],
        Status.COMPLETED: [Status.CLOSED],
        Status.CLOSED: [Status.COMPLETED],  # Reopen for more certificates
        Status.CANCELLED: [],  # Terminal state
    }
    
    # =========================================
    # Ownership
    # =========================================
    owner = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='events',
        help_text="Organizer who created this event"
    )
    
    # Phase 2: Organization ownership
    # organization = models.ForeignKey(
    #     'organizations.Organization',
    #     on_delete=models.SET_NULL,
    #     null=True, blank=True,
    #     related_name='events'
    # )
    
    # =========================================
    # Basic Info
    # =========================================
    title = models.CharField(
        max_length=200,
        help_text="Event title"
    )
    slug = models.SlugField(
        max_length=220,
        db_index=True,
        help_text="URL-friendly identifier (unique per owner)"
    )
    description = models.TextField(
        blank=True,
        max_length=10000,
        help_text="Event description (supports markdown)"
    )
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices,
        default=EventType.WEBINAR
    )
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
        help_text="Who can see and register for this event"
    )
    
    # =========================================
    # Status
    # =========================================
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True
    )
    published_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When event was published"
    )
    cancelled_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When event was cancelled"
    )
    cancellation_reason = models.TextField(
        blank=True,
        help_text="Reason for cancellation (shown to registrants)"
    )
    
    # =========================================
    # Schedule
    # =========================================
    starts_at = models.DateTimeField(
        db_index=True,
        help_text="Event start time (UTC)"
    )
    duration_minutes = models.PositiveIntegerField(
        validators=[MinValueValidator(15), MaxValueValidator(480)],
        help_text="Duration in minutes (15 min to 8 hours)"
    )
    timezone = models.CharField(
        max_length=50,
        default='UTC',
        validators=[validate_timezone],
        help_text="Display timezone (IANA format)"
    )
    
    # Actual timing (filled after event)
    actual_started_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When event actually started"
    )
    actual_ended_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When event actually ended"
    )
    
    # =========================================
    # Registration Settings
    # =========================================
    registration_enabled = models.BooleanField(
        default=True,
        help_text="Whether registration is enabled"
    )
    capacity = models.PositiveIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10000)],
        help_text="Max registrations (null = unlimited)"
    )
    registration_deadline = models.DateTimeField(
        null=True, blank=True,
        help_text="Registration closes at this time"
    )
    waitlist_enabled = models.BooleanField(
        default=False,
        help_text="Enable waitlist when capacity reached"
    )
    
    # =========================================
    # Zoom Integration
    # =========================================
    zoom_enabled = models.BooleanField(
        default=True,
        help_text="Create Zoom meeting for this event"
    )
    zoom_meeting_id = models.CharField(
        max_length=20,
        blank=True,
        db_index=True,
        help_text="Zoom meeting ID"
    )
    zoom_meeting_uuid = models.CharField(
        max_length=100,
        blank=True,
        help_text="Zoom meeting UUID (for API calls)"
    )
    zoom_join_url = models.URLField(
        blank=True,
        help_text="Attendee join URL"
    )
    zoom_host_url = models.URLField(
        blank=True,
        help_text="Host start URL"
    )
    zoom_passcode = models.CharField(
        max_length=20,
        blank=True,
        help_text="Meeting passcode"
    )
    zoom_settings = models.JSONField(
        default=dict,
        blank=True,
        validators=[validate_zoom_settings_schema],
        help_text="Zoom meeting settings (waiting_room, etc.)"
    )
    
    # =========================================
    # CPD / Credits
    # =========================================
    cpd_enabled = models.BooleanField(
        default=False,
        help_text="Event offers CPD/CE credits"
    )
    cpd_credit_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Credit type (CME, CLE, CPE, etc.)"
    )
    cpd_credit_value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Number of credits"
    )
    cpd_accreditation_note = models.CharField(
        max_length=500,
        blank=True,
        help_text="Accreditation statement (e.g., 'Accredited by XYZ Board')"
    )
    
    # =========================================
    # Certificate Settings
    # =========================================
    certificates_enabled = models.BooleanField(
        default=True,
        help_text="Issue certificates for this event"
    )
    certificate_template = models.ForeignKey(
        'certificates.CertificateTemplate',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='events',
        help_text="Certificate template to use"
    )
    auto_issue_certificates = models.BooleanField(
        default=False,
        help_text="Automatically issue certificates after attendance confirmed"
    )
    minimum_attendance_percent = models.PositiveIntegerField(
        default=80,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Minimum attendance % required for certificate"
    )
    
    # =========================================
    # Recording Settings
    # =========================================
    recording_enabled = models.BooleanField(
        default=True,
        help_text="Enable cloud recording for this event"
    )
    auto_publish_recordings = models.BooleanField(
        default=False,
        help_text="Automatically publish recordings when available"
    )
    recording_access_level = models.CharField(
        max_length=20,
        default='registrants',
        choices=[
            ('registrants', 'Confirmed Registrants Only'),
            ('attendees', 'Attended Only'),
            ('certificate_holders', 'Certificate Holders Only'),
            ('public', 'Public (Anyone with Link)'),
        ],
        help_text="Default access level for recordings"
    )
    
    # =========================================
    # Denormalized Counts
    # =========================================
    # Updated via signals/tasks
    registration_count = models.PositiveIntegerField(
        default=0,
        help_text="Denormalized: confirmed registrations"
    )
    attendance_count = models.PositiveIntegerField(
        default=0,
        help_text="Denormalized: attendees who joined"
    )
    certificate_count = models.PositiveIntegerField(
        default=0,
        help_text="Denormalized: certificates issued"
    )
    
    class Meta:
        db_table = 'events'
        ordering = ['-starts_at']
        unique_together = [['owner', 'slug']]
        indexes = [
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['status', 'starts_at']),
            models.Index(fields=['starts_at']),
            models.Index(fields=['slug']),
            models.Index(fields=['uuid']),
            models.Index(fields=['zoom_meeting_id']),
            models.Index(fields=['visibility', 'status', 'starts_at']),
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
        """Scheduled end time."""
        return self.starts_at + timezone.timedelta(minutes=self.duration_minutes)
    
    @property
    def actual_duration_minutes(self):
        """Actual duration if event has ended."""
        if self.actual_started_at and self.actual_ended_at:
            delta = self.actual_ended_at - self.actual_started_at
            return int(delta.total_seconds() / 60)
        return None
    
    @property
    def is_upcoming(self):
        return self.status == self.Status.PUBLISHED and self.starts_at > timezone.now()
    
    @property
    def is_past(self):
        return self.ends_at < timezone.now()
    
    @property
    def is_live(self):
        return self.status == self.Status.LIVE
    
    @property
    def is_full(self):
        if self.capacity is None:
            return False
        return self.registration_count >= self.capacity
    
    @property
    def spots_remaining(self):
        if self.capacity is None:
            return None
        return max(0, self.capacity - self.registration_count)
    
    @property
    def minimum_attendance_minutes(self):
        """Minimum minutes required for certificate eligibility."""
        return int(self.duration_minutes * self.minimum_attendance_percent / 100)
    
    @property
    def can_register(self):
        """Check if new registrations are allowed."""
        if not self.registration_enabled:
            return False
        if self.status != self.Status.PUBLISHED:
            return False
        if self.registration_deadline and timezone.now() > self.registration_deadline:
            return False
        if self.is_full and not self.waitlist_enabled:
            return False
        return True
    
    @property
    def can_edit(self):
        """Check if event can be edited."""
        return self.status in [self.Status.DRAFT, self.Status.PUBLISHED]
    
    @property
    def can_issue_certificates(self):
        """Check if certificates can be issued."""
        return self.status in [self.Status.COMPLETED, self.Status.CLOSED]
    
    # =========================================
    # Status Transition Methods
    # =========================================
    def can_transition_to(self, new_status):
        """Check if transition to new_status is valid."""
        return new_status in self.VALID_TRANSITIONS.get(self.status, [])
    
    def _change_status(self, new_status, user=None, reason=''):
        """Internal method to change status with history."""
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Cannot transition from {self.status} to {new_status}"
            )
        
        old_status = self.status
        self.status = new_status
        
        # Set timestamp fields based on status
        if new_status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        elif new_status == self.Status.CANCELLED:
            self.cancelled_at = timezone.now()
            self.cancellation_reason = reason
        
        self.save()
        
        # Create history record
        EventStatusHistory.objects.create(
            event=self,
            from_status=old_status,
            to_status=new_status,
            changed_by=user,
            reason=reason
        )
    
    def publish(self, user=None):
        """Publish the event."""
        self._change_status(self.Status.PUBLISHED, user)
    
    def start(self, user=None):
        """Mark event as live."""
        self.actual_started_at = timezone.now()
        self._change_status(self.Status.LIVE, user)
    
    def complete(self, user=None):
        """Mark event as completed."""
        if not self.actual_ended_at:
            self.actual_ended_at = timezone.now()
        self._change_status(self.Status.COMPLETED, user)
    
    def close(self, user=None):
        """Close the event (all certificates issued)."""
        self._change_status(self.Status.CLOSED, user)
    
    def reopen(self, user=None, reason=''):
        """Reopen a closed event (need to issue more certificates)."""
        self._change_status(self.Status.COMPLETED, user, reason)
    
    def cancel(self, user=None, reason=''):
        """Cancel the event."""
        self._change_status(self.Status.CANCELLED, user, reason)
    
    def delete_draft(self):
        """
        Delete a draft event.
        Only allowed if no registrations exist.
        """
        if self.status != self.Status.DRAFT:
            raise ValueError("Only draft events can be deleted")
        if self.registrations.exists():
            raise ValueError("Cannot delete event with registrations")
        self.hard_delete()
    
    # =========================================
    # Other Methods
    # =========================================
    def generate_slug(self):
        """Generate unique slug from title."""
        base_slug = slugify(self.title)[:200]
        
        # Check for existing slugs by this owner
        existing = set(
            Event.all_objects
            .filter(owner=self.owner)
            .exclude(pk=self.pk)
            .values_list('slug', flat=True)
        )
        
        if base_slug not in existing:
            return base_slug
        
        # Add random suffix
        import secrets
        for _ in range(100):
            suffix = secrets.token_hex(4)
            candidate = f"{base_slug}-{suffix}"
            if candidate not in existing:
                return candidate
        
        raise ValueError("Could not generate unique slug")
    
    def update_counts(self):
        """Update denormalized counts."""
        from registrations.models import Registration
        
        self.registration_count = self.registrations.filter(
            status=Registration.Status.CONFIRMED,
            deleted_at__isnull=True
        ).count()
        
        self.attendance_count = self.registrations.filter(
            attended=True,
            deleted_at__isnull=True
        ).count()
        
        self.certificate_count = self.registrations.filter(
            certificate_issued=True,
            deleted_at__isnull=True
        ).count()
        
        self.save(update_fields=[
            'registration_count',
            'attendance_count', 
            'certificate_count',
            'updated_at'
        ])
    
    def duplicate(self, new_title=None, new_start=None, user=None):
        """
        Create a copy of this event as a draft.
        
        Args:
            new_title: Title for duplicated event (defaults to "Copy of {title}")
            new_start: Start time for new event (defaults to same time next week)
            user: User creating the duplicate (defaults to original owner)
        
        Returns:
            Event: New draft event
        
        Copies:
        - Basic info (title, description, event_type, visibility)
        - Schedule (duration, timezone)
        - Registration settings (capacity, waitlist, deadline offset)
        - CPD settings
        - Certificate settings
        - Custom fields (as new EventCustomField instances)
        
        Does NOT copy:
        - Registrations
        - Invitations
        - Attendance records
        - Zoom meeting (new one created)
        - Status history
        """
        from copy import copy
        
        # Determine new values
        title = new_title or f"Copy of {self.title}"
        
        if new_start:
            start = new_start
        else:
            # Default to same time next week
            start = self.starts_at + timezone.timedelta(days=7)
        
        # Calculate deadline offset
        deadline_offset = None
        if self.registration_deadline and self.starts_at:
            deadline_offset = self.starts_at - self.registration_deadline
        
        # Create new event
        new_event = Event(
            owner=user or self.owner,
            title=title,
            description=self.description,
            event_type=self.event_type,
            visibility=self.visibility,
            status=Event.Status.DRAFT,
            starts_at=start,
            duration_minutes=self.duration_minutes,
            timezone=self.timezone,
            registration_deadline=start - deadline_offset if deadline_offset else None,
            capacity=self.capacity,
            waitlist_enabled=self.waitlist_enabled,
            zoom_enabled=self.zoom_enabled,
            zoom_settings=copy(self.zoom_settings) if self.zoom_settings else {},
            cpd_enabled=self.cpd_enabled,
            cpd_credit_type=self.cpd_credit_type,
            cpd_credit_value=self.cpd_credit_value,
            cpd_accreditation_note=self.cpd_accreditation_note,
            certificates_enabled=self.certificates_enabled,
            certificate_template=self.certificate_template,
            auto_issue_certificates=self.auto_issue_certificates,
            minimum_attendance_percent=self.minimum_attendance_percent,
            recording_enabled=self.recording_enabled,
            auto_publish_recordings=self.auto_publish_recordings,
            recording_access_level=self.recording_access_level,
            duplicated_from=self,
        )
        new_event.save()
        
        # Copy custom fields
        for field in self.custom_fields.all():
            EventCustomField.objects.create(
                event=new_event,
                label=field.label,
                field_type=field.field_type,
                required=field.required,
                options=copy(field.options) if field.options else [],
                order=field.order,
                placeholder=field.placeholder,
                help_text=field.help_text,
            )
        
        return new_event
    
    # =========================================
    # Tracking
    # =========================================
    duplicated_from = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='duplicates',
        help_text="Event this was duplicated from"
    )
    
    def clean(self):
        """Model validation."""
        from django.core.exceptions import ValidationError
        errors = {}
        
        # Validate dates
        if self.registration_deadline and self.starts_at:
            if self.registration_deadline > self.starts_at:
                errors['registration_deadline'] = \
                    'Registration deadline must be before event start'
        
        if self.starts_at and self.status == self.Status.DRAFT:
            if self.starts_at < timezone.now():
                errors['starts_at'] = 'Event start time must be in the future'
        
        # Validate CPD
        if self.cpd_enabled:
            if not self.cpd_credit_type:
                errors['cpd_credit_type'] = 'Credit type required when CPD enabled'
            if not self.cpd_credit_value:
                errors['cpd_credit_value'] = 'Credit value required when CPD enabled'
        
        # Validate capacity/waitlist
        if self.waitlist_enabled and not self.capacity:
            errors['waitlist_enabled'] = 'Waitlist requires capacity to be set'
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        # Auto-generate slug if not set
        if not self.slug:
            self.slug = self.generate_slug()
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('events:detail', kwargs={'slug': self.slug})
```

---

### EventStatusHistory

Audit trail for event status changes.

```python
class EventStatusHistory(BaseModel):
    """
    Audit log of event status changes.
    
    Created automatically when status transitions occur.
    """
    
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    from_status = models.CharField(
        max_length=20,
        blank=True,
        help_text="Previous status (blank for initial creation)"
    )
    to_status = models.CharField(
        max_length=20,
        help_text="New status"
    )
    changed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="User who made the change"
    )
    reason = models.TextField(
        blank=True,
        help_text="Reason for change (e.g., cancellation reason)"
    )
    
    class Meta:
        db_table = 'event_status_history'
        ordering = ['-created_at']
        verbose_name = 'Event Status History'
        verbose_name_plural = 'Event Status Histories'
    
    def __str__(self):
        return f"{self.event.title}: {self.from_status} → {self.to_status}"
```

---

### EventCustomField

Custom registration fields defined by the organizer.

```python
class EventCustomField(BaseModel):
    """
    Custom field for event registration form.
    
    Allows organizers to collect additional information from attendees.
    Responses are stored in CustomFieldResponse (registrations app).
    """
    
    class FieldType(models.TextChoices):
        TEXT = 'text', 'Single Line Text'
        TEXTAREA = 'textarea', 'Multi-line Text'
        SELECT = 'select', 'Dropdown Select'
        MULTISELECT = 'multiselect', 'Multiple Select'
        CHECKBOX = 'checkbox', 'Checkbox'
        RADIO = 'radio', 'Radio Buttons'
        DATE = 'date', 'Date'
        NUMBER = 'number', 'Number'
    
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='custom_fields'
    )
    
    label = models.CharField(
        max_length=200,
        help_text="Field label shown to attendees"
    )
    field_type = models.CharField(
        max_length=20,
        choices=FieldType.choices
    )
    required = models.BooleanField(
        default=False,
        help_text="Whether this field is required"
    )
    placeholder = models.CharField(
        max_length=200,
        blank=True,
        help_text="Placeholder text for input"
    )
    help_text = models.CharField(
        max_length=500,
        blank=True,
        help_text="Help text shown below field"
    )
    options = models.JSONField(
        default=list,
        blank=True,
        help_text="Options for select/radio/multiselect fields"
    )
    default_value = models.CharField(
        max_length=500,
        blank=True,
        help_text="Default value"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order"
    )
    
    class Meta:
        db_table = 'event_custom_fields'
        ordering = ['order', 'id']
        verbose_name = 'Event Custom Field'
        verbose_name_plural = 'Event Custom Fields'
    
    def __str__(self):
        return f"{self.event.title} - {self.label}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        errors = {}
        
        # Validate options for select-type fields
        if self.field_type in ['select', 'multiselect', 'radio']:
            if not self.options:
                errors['options'] = 'Options required for this field type'
            elif not isinstance(self.options, list):
                errors['options'] = 'Options must be a list'
            elif len(self.options) < 2:
                errors['options'] = 'At least 2 options required'
        
        if errors:
            raise ValidationError(errors)
```

---

### EventInvitation

Tracks invitations sent for an event.

```python
class EventInvitation(BaseModel):
    """
    Tracks invitations sent for an event.
    
    Used for:
    - Tracking invite → registration conversion
    - Preventing duplicate invites
    - Reminder targeting
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        DELIVERED = 'delivered', 'Delivered'
        OPENED = 'opened', 'Opened'
        REGISTERED = 'registered', 'Registered'
        BOUNCED = 'bounced', 'Bounced'
    
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='invitations'
    )
    
    # Recipient info
    email = LowercaseEmailField(
        db_index=True,
        help_text="Invitee email"
    )
    full_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Invitee name (if known)"
    )
    
    # Source tracking
    source = models.CharField(
        max_length=50,
        blank=True,
        help_text="How they were invited (manual, csv, contact_list)"
    )
    contact_list = models.ForeignKey(
        'contacts.ContactList',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="Contact list used for invite"
    )
    invited_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="User who sent the invite"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # Timing
    sent_at = models.DateTimeField(
        null=True, blank=True
    )
    opened_at = models.DateTimeField(
        null=True, blank=True
    )
    registered_at = models.DateTimeField(
        null=True, blank=True
    )
    
    # Link to registration if created
    registration = models.OneToOneField(
        'registrations.Registration',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='invitation'
    )
    
    class Meta:
        db_table = 'event_invitations'
        unique_together = [['event', 'email']]
        indexes = [
            models.Index(fields=['event', 'status']),
            models.Index(fields=['email']),
        ]
        verbose_name = 'Event Invitation'
        verbose_name_plural = 'Event Invitations'
    
    def __str__(self):
        return f"{self.email} → {self.event.title}"
    
    def mark_sent(self):
        self.status = self.Status.SENT
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at', 'updated_at'])
    
    def mark_opened(self):
        if self.status in [self.Status.SENT, self.Status.DELIVERED]:
            self.status = self.Status.OPENED
            self.opened_at = timezone.now()
            self.save(update_fields=['status', 'opened_at', 'updated_at'])
    
    def mark_registered(self, registration):
        self.status = self.Status.REGISTERED
        self.registered_at = timezone.now()
        self.registration = registration
        self.save(update_fields=[
            'status', 'registered_at', 'registration', 'updated_at'
        ])
```

---

### EventReminder

Scheduled reminders for events.

```python
class EventReminder(BaseModel):
    """
    Scheduled reminder for an event.
    
    Allows flexible reminder scheduling beyond just 24h/1h.
    """
    
    class ReminderType(models.TextChoices):
        BEFORE_24H = 'before_24h', '24 Hours Before'
        BEFORE_1H = 'before_1h', '1 Hour Before'
        BEFORE_15M = 'before_15m', '15 Minutes Before'
        CUSTOM = 'custom', 'Custom Time'
    
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='reminders'
    )
    
    reminder_type = models.CharField(
        max_length=20,
        choices=ReminderType.choices
    )
    
    # For custom reminders
    scheduled_for = models.DateTimeField(
        help_text="When to send the reminder"
    )
    
    # Status
    sent = models.BooleanField(
        default=False
    )
    sent_at = models.DateTimeField(
        null=True, blank=True
    )
    recipient_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of recipients when sent"
    )
    
    class Meta:
        db_table = 'event_reminders'
        ordering = ['scheduled_for']
        verbose_name = 'Event Reminder'
        verbose_name_plural = 'Event Reminders'
    
    def __str__(self):
        return f"{self.event.title} - {self.reminder_type}"
    
    @classmethod
    def create_default_reminders(cls, event):
        """Create default reminders for an event."""
        reminders = []
        
        # 24 hours before
        reminders.append(cls(
            event=event,
            reminder_type=cls.ReminderType.BEFORE_24H,
            scheduled_for=event.starts_at - timezone.timedelta(hours=24)
        ))
        
        # 1 hour before
        reminders.append(cls(
            event=event,
            reminder_type=cls.ReminderType.BEFORE_1H,
            scheduled_for=event.starts_at - timezone.timedelta(hours=1)
        ))
        
        cls.objects.bulk_create(reminders)
        return reminders
```

---

## Relationships

```
Event
├── User (owner, N:1, PROTECT)
├── CertificateTemplate (N:1, SET_NULL)
├── EventStatusHistory (1:N, CASCADE)
├── EventCustomField (1:N, CASCADE)
├── EventInvitation (1:N, CASCADE)
├── EventReminder (1:N, CASCADE)
├── Registration (1:N, CASCADE) — see registrations.md
├── AttendanceRecord (1:N, CASCADE) — see registrations.md
├── ZoomWebhookLog (1:N, SET_NULL) — see integrations.md
└── ZoomRecording (1:N, CASCADE) — see integrations.md
```

---

## Indexes

| Table | Index | Purpose |
|-------|-------|---------|
| events | owner_id, status | Organizer's events by status |
| events | status, starts_at | Upcoming published events |
| events | starts_at | Events by date |
| events | uuid | API/URL lookup |
| events | owner_id, slug (unique) | Unique slug per owner |
| events | zoom_meeting_id | Webhook matching |
| events | visibility, status, starts_at | Public event discovery |
| event_invitations | event_id, email (unique) | Prevent duplicate invites |
| event_invitations | email | Find all invites for email |

---

## Business Rules

1. **Slug uniqueness**: Per-owner, not global
2. **Draft deletion**: Only if no registrations
3. **Status transitions**: Enforced via VALID_TRANSITIONS
4. **Capacity**: Waitlist only available if capacity set
5. **CPD fields**: Required if cpd_enabled is True
6. **Zoom meeting**: Created on publish (if zoom_enabled)
7. **Certificates**: Can only be issued in COMPLETED or CLOSED status
8. **Cancellation**: Notifies all registrants, preserves data

---

## Signals

```python
# events/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=Event)
def on_event_save(sender, instance, created, **kwargs):
    if created and instance.status == Event.Status.DRAFT:
        # Create default reminders
        EventReminder.create_default_reminders(instance)

@receiver(post_save, sender=Event)
def on_event_publish(sender, instance, **kwargs):
    if instance.status == Event.Status.PUBLISHED:
        # Create Zoom meeting if enabled and not exists
        if instance.zoom_enabled and not instance.zoom_meeting_id:
            # Trigger async task
            from events.tasks import create_zoom_meeting
            create_zoom_meeting.delay(instance.id)
```
