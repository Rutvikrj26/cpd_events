# Data Models Specification

## Table of Contents
1. [Design Principles](#design-principles)
2. [Entity Relationship Diagram](#entity-relationship-diagram)
3. [Django App Structure](#django-app-structure)
4. [Core Models](#core-models)
5. [Model Specifications](#model-specifications)
6. [Indexes & Constraints](#indexes--constraints)
7. [Phase 2 Considerations](#phase-2-considerations)
8. [Migration Strategy](#migration-strategy)

---

## Design Principles

### Primary Keys
- **Internal:** Auto-increment integers (fast joins, efficient indexes)
- **External:** UUIDs exposed in URLs and APIs (no enumeration attacks, no count leakage)
- Pattern: Every model has both `id` (int PK) and `uuid` (unique, indexed)

### Soft Deletes
Entities that need soft deletes (never truly deleted):
- `User` — GDPR: anonymize instead of delete
- `Event` — Historical record, certificate references
- `Certificate` — Must remain verifiable forever (even if revoked)
- `CertificateTemplate` — Issued certificates reference them

Entities with hard deletes:
- `Registration` — Can be removed (before event)
- `ContactList`, `Contact` — User data, can delete
- `ZoomWebhookLog` — Retention policy, can purge old

### Timestamps
Every model includes:
```python
created_at = models.DateTimeField(auto_now_add=True)
updated_at = models.DateTimeField(auto_now=True)
```

### Null vs Blank Philosophy
- `null=True` — Database allows NULL (for optional FKs, optional data)
- `blank=True` — Form/validation allows empty (for optional text fields)
- Avoid `null=True` on CharFields; use `blank=True` with empty string default

### Email Canonicalization
All emails stored lowercase, stripped. Use a custom field or validation:
```python
email = models.EmailField(unique=True)  # Always lowercase
```

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  ┌──────────┐         ┌──────────────┐         ┌────────────────┐          │
│  │   User   │────────▶│ ZoomConnection│         │ ContactList    │          │
│  │          │ 1    0-1│              │         │                │          │
│  │ (base)   │         └──────────────┘         └───────┬────────┘          │
│  └────┬─────┘                                          │ 1                  │
│       │                                                │                    │
│       │ 1                                              ▼ *                  │
│       │         ┌──────────────────┐           ┌──────────────┐            │
│       │         │      Event       │           │   Contact    │            │
│       └────────▶│                  │           │              │            │
│         creates │ owner (FK)       │           └──────────────┘            │
│           *     │                  │                                        │
│                 └───────┬──────────┘                                        │
│                         │                                                   │
│          ┌──────────────┼──────────────┬────────────────┐                  │
│          │ 1            │ 1            │ 1              │ 1                │
│          ▼ *            ▼ *            ▼ *              ▼ *                │
│  ┌───────────────┐ ┌──────────┐ ┌─────────────┐ ┌──────────────┐          │
│  │ EventCustom   │ │Registration│ │ Attendance  │ │ZoomWebhookLog│          │
│  │ Field         │ │           │ │ Record      │ │              │          │
│  └───────┬───────┘ └─────┬─────┘ └──────┬──────┘ └──────────────┘          │
│          │ 1             │              │                                   │
│          ▼ *             │ 1            │                                   │
│  ┌───────────────┐       │              │                                   │
│  │ CustomField   │       ▼ *            │                                   │
│  │ Response      │◀──────┘              │                                   │
│  └───────────────┘                      │                                   │
│                                         │                                   │
│  ┌────────────────┐                     │                                   │
│  │ Certificate    │ 1                   │                                   │
│  │ Template       │◀────────────────────┤                                   │
│  └───────┬────────┘                     │                                   │
│          │ 1                            │                                   │
│          ▼ *                            │                                   │
│  ┌───────────────┐                      │                                   │
│  │  Certificate  │◀─────────────────────┘                                   │
│  │               │  (via Registration)                                      │
│  └───────────────┘                                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

LEGEND:
────▶  Foreign Key (many-to-one)
1 / *  Cardinality (one / many)
```

### Simplified Relationships

| From | To | Relationship | Notes |
|------|----|--------------|-------|
| User | Event | One-to-Many | Organizer creates events |
| User | ZoomConnection | One-to-One | Organizer's Zoom OAuth |
| User | CertificateTemplate | One-to-Many | Organizer owns templates |
| User | ContactList | One-to-Many | Organizer owns lists |
| User | Registration | One-to-Many (nullable) | User can have many registrations; guests have null user |
| Event | Registration | One-to-Many | Event has many registrations |
| Event | AttendanceRecord | One-to-Many | Event has attendance data |
| Event | EventCustomField | One-to-Many | Event defines custom fields |
| Registration | CustomFieldResponse | One-to-Many | Registration has field responses |
| Registration | Certificate | One-to-One | One certificate per registration |
| CertificateTemplate | Certificate | One-to-Many | Template used for many certs |
| ContactList | Contact | One-to-Many | List contains contacts |

---

## Django App Structure

```
project/
├── config/                 # Project settings
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
│
├── apps/
│   ├── accounts/          # User management
│   │   ├── models.py      # User, ZoomConnection
│   │   ├── managers.py    # Custom user manager
│   │   └── ...
│   │
│   ├── events/            # Event management
│   │   ├── models.py      # Event, EventCustomField
│   │   └── ...
│   │
│   ├── registrations/     # Registration & attendance
│   │   ├── models.py      # Registration, AttendanceRecord, CustomFieldResponse
│   │   └── ...
│   │
│   ├── certificates/      # Certificate issuance
│   │   ├── models.py      # Certificate, CertificateTemplate
│   │   └── ...
│   │
│   ├── contacts/          # Contact management
│   │   ├── models.py      # ContactList, Contact
│   │   └── ...
│   │
│   └── integrations/      # External integrations
│       ├── models.py      # ZoomWebhookLog
│       ├── zoom/          # Zoom-specific logic
│       └── ...
│
└── common/                # Shared utilities
    ├── models.py          # Base models, mixins
    ├── fields.py          # Custom fields
    └── utils.py
```

---

## Core Models

### Base Model (common/models.py)

```python
import uuid
from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base model with timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """Abstract base model with UUID for external reference."""
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True
    )

    class Meta:
        abstract = True


class BaseModel(TimeStampedModel, UUIDModel):
    """Standard base model with timestamps and UUID."""
    
    class Meta:
        abstract = True


class SoftDeleteManager(models.Manager):
    """Manager that excludes soft-deleted records by default."""
    
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class SoftDeleteModel(BaseModel):
    """Base model with soft delete capability."""
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    objects = SoftDeleteManager()
    all_objects = models.Manager()  # Include deleted records
    
    class Meta:
        abstract = True
    
    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at', 'updated_at'])
    
    def restore(self):
        self.deleted_at = None
        self.save(update_fields=['deleted_at', 'updated_at'])
    
    @property
    def is_deleted(self):
        return self.deleted_at is not None
```

---

## Model Specifications

### accounts/models.py

```python
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from common.models import SoftDeleteModel, BaseModel


class UserManager(models.Manager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('email_verified', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, SoftDeleteModel):
    """
    Custom user model with email as the primary identifier.
    All users start as attendees; organizer is an upgrade.
    """
    
    class AccountType(models.TextChoices):
        ATTENDEE = 'attendee', 'Attendee'
        ORGANIZER = 'organizer', 'Organizer'
    
    # Authentication
    email = models.EmailField(unique=True, db_index=True)
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=100, blank=True)
    email_verification_sent_at = models.DateTimeField(null=True, blank=True)
    
    # Account type
    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.ATTENDEE
    )
    upgraded_to_organizer_at = models.DateTimeField(null=True, blank=True)
    
    # Profile
    full_name = models.CharField(max_length=255)
    professional_title = models.CharField(max_length=255, blank=True)
    credentials = models.CharField(max_length=255, blank=True)  # e.g., "MD, PhD"
    organization_name = models.CharField(max_length=255, blank=True)  # Free text
    profile_photo = models.URLField(blank=True)  # GCS URL
    bio = models.TextField(blank=True)
    
    # Preferences
    timezone = models.CharField(max_length=50, default='UTC')
    
    # Notifications
    notify_event_reminders = models.BooleanField(default=True)
    notify_certificate_issued = models.BooleanField(default=True)
    notify_marketing = models.BooleanField(default=False)
    # Organizer-specific notifications
    notify_new_registration = models.BooleanField(default=True)
    notify_event_summary = models.BooleanField(default=True)
    
    # Admin
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Onboarding
    onboarding_completed = models.BooleanField(default=False)
    
    # Phase 2: Organization membership (nullable, add FK later)
    # organization = models.ForeignKey('organizations.Organization', null=True, ...)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['account_type']),
            models.Index(fields=['uuid']),
        ]
    
    def __str__(self):
        return self.email
    
    @property
    def is_organizer(self):
        return self.account_type == self.AccountType.ORGANIZER
    
    @property
    def is_attendee(self):
        return self.account_type == self.AccountType.ATTENDEE
    
    def upgrade_to_organizer(self):
        if self.account_type != self.AccountType.ORGANIZER:
            self.account_type = self.AccountType.ORGANIZER
            self.upgraded_to_organizer_at = timezone.now()
            self.save(update_fields=['account_type', 'upgraded_to_organizer_at', 'updated_at'])
    
    @property
    def display_name(self):
        """Name with credentials if available."""
        if self.credentials:
            return f"{self.full_name}, {self.credentials}"
        return self.full_name


class ZoomConnection(BaseModel):
    """
    Stores Zoom OAuth tokens for an organizer.
    One-to-one with User.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='zoom_connection'
    )
    
    # OAuth tokens
    access_token = models.TextField()  # Encrypted in production
    refresh_token = models.TextField()  # Encrypted in production
    token_expires_at = models.DateTimeField()
    
    # Zoom account info
    zoom_user_id = models.CharField(max_length=100)
    zoom_email = models.EmailField()
    zoom_account_id = models.CharField(max_length=100, blank=True)
    
    # Connection status
    is_active = models.BooleanField(default=True)
    last_refresh_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    
    class Meta:
        db_table = 'zoom_connections'
    
    def __str__(self):
        return f"Zoom: {self.zoom_email} ({self.user.email})"
    
    @property
    def is_token_expired(self):
        return timezone.now() >= self.token_expires_at
    
    @property
    def needs_refresh(self):
        """Refresh if within 5 minutes of expiry."""
        buffer = timedelta(minutes=5)
        return timezone.now() >= (self.token_expires_at - buffer)
```

---

### events/models.py

```python
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from common.models import SoftDeleteModel, BaseModel


class Event(SoftDeleteModel):
    """
    An event created by an organizer.
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
        OTHER = 'other', 'Other'
    
    # Ownership
    owner = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,  # Don't delete events if user deleted
        related_name='events'
    )
    
    # Basic info
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, db_index=True)
    description = models.TextField(blank=True)
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices,
        default=EventType.WEBINAR
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True
    )
    published_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    
    # Schedule
    starts_at = models.DateTimeField(db_index=True)
    duration_minutes = models.PositiveIntegerField(
        validators=[MinValueValidator(15), MaxValueValidator(480)]  # 15 min to 8 hrs
    )
    timezone = models.CharField(max_length=50, default='UTC')
    
    # Registration settings
    registration_open = models.BooleanField(default=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)  # null = unlimited
    registration_deadline = models.DateTimeField(null=True, blank=True)
    waitlist_enabled = models.BooleanField(default=False)
    
    # Zoom integration
    zoom_meeting_id = models.CharField(max_length=20, blank=True, db_index=True)
    zoom_meeting_uuid = models.CharField(max_length=100, blank=True)
    zoom_join_url = models.URLField(blank=True)
    zoom_host_url = models.URLField(blank=True)
    zoom_passcode = models.CharField(max_length=20, blank=True)
    zoom_settings = models.JSONField(default=dict, blank=True)  # waiting_room, etc.
    
    # CPD / Credits
    cpd_enabled = models.BooleanField(default=False)
    cpd_credit_type = models.CharField(max_length=50, blank=True)  # CME, CLE, CPE, etc.
    cpd_credit_value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    cpd_accreditation_note = models.CharField(max_length=500, blank=True)
    
    # Certificate settings
    certificates_enabled = models.BooleanField(default=True)
    certificate_template = models.ForeignKey(
        'certificates.CertificateTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='events'
    )
    auto_issue_certificates = models.BooleanField(default=False)
    minimum_attendance_percent = models.PositiveIntegerField(
        default=80,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Notifications
    reminder_24h_sent = models.BooleanField(default=False)
    reminder_1h_sent = models.BooleanField(default=False)
    
    # Phase 2: Organization ownership
    # organization = models.ForeignKey('organizations.Organization', null=True, ...)
    
    class Meta:
        db_table = 'events'
        ordering = ['-starts_at']
        indexes = [
            models.Index(fields=['owner', 'status']),
            models.Index(fields=['starts_at']),
            models.Index(fields=['status', 'starts_at']),
            models.Index(fields=['slug']),
            models.Index(fields=['uuid']),
            models.Index(fields=['zoom_meeting_id']),
        ]
    
    def __str__(self):
        return self.title
    
    @property
    def ends_at(self):
        return self.starts_at + timedelta(minutes=self.duration_minutes)
    
    @property
    def is_upcoming(self):
        return self.status == self.Status.PUBLISHED and self.starts_at > timezone.now()
    
    @property
    def is_past(self):
        return self.ends_at < timezone.now()
    
    @property
    def registration_count(self):
        return self.registrations.filter(status='confirmed').count()
    
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
        return int(self.duration_minutes * self.minimum_attendance_percent / 100)
    
    def can_register(self):
        """Check if registration is currently allowed."""
        if not self.registration_open:
            return False
        if self.status != self.Status.PUBLISHED:
            return False
        if self.registration_deadline and timezone.now() > self.registration_deadline:
            return False
        if self.is_full and not self.waitlist_enabled:
            return False
        return True
    
    def publish(self):
        if self.status == self.Status.DRAFT:
            self.status = self.Status.PUBLISHED
            self.published_at = timezone.now()
            self.save(update_fields=['status', 'published_at', 'updated_at'])
    
    def cancel(self, reason=''):
        if self.status not in [self.Status.CANCELLED, self.Status.CLOSED]:
            self.status = self.Status.CANCELLED
            self.cancelled_at = timezone.now()
            self.cancellation_reason = reason
            self.save(update_fields=['status', 'cancelled_at', 'cancellation_reason', 'updated_at'])


class EventStatusHistory(BaseModel):
    """
    Tracks status changes for events.
    """
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True
    )
    note = models.TextField(blank=True)
    
    class Meta:
        db_table = 'event_status_history'
        ordering = ['-created_at']


class EventCustomField(BaseModel):
    """
    Custom registration fields defined by the organizer.
    """
    
    class FieldType(models.TextChoices):
        TEXT = 'text', 'Text'
        TEXTAREA = 'textarea', 'Text Area'
        SELECT = 'select', 'Dropdown'
        CHECKBOX = 'checkbox', 'Checkbox'
        RADIO = 'radio', 'Radio Buttons'
    
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='custom_fields'
    )
    label = models.CharField(max_length=200)
    field_type = models.CharField(max_length=20, choices=FieldType.choices)
    required = models.BooleanField(default=False)
    options = models.JSONField(default=list, blank=True)  # For select, radio
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'event_custom_fields'
        ordering = ['order']
```

---

### registrations/models.py

```python
from django.db import models
from common.models import BaseModel


class Registration(BaseModel):
    """
    An attendee's registration for an event.
    User can be null for guest registrations (pre-account).
    """
    
    class Status(models.TextChoices):
        CONFIRMED = 'confirmed', 'Confirmed'
        CANCELLED = 'cancelled', 'Cancelled'
        WAITLISTED = 'waitlisted', 'Waitlisted'
    
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='registrations'
    )
    
    # User link (null for guests)
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registrations'
    )
    
    # Contact info (always stored, for guest matching)
    email = models.EmailField(db_index=True)  # Canonical, lowercase
    full_name = models.CharField(max_length=255)
    professional_title = models.CharField(max_length=255, blank=True)
    organization_name = models.CharField(max_length=255, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CONFIRMED,
        db_index=True
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Attendance summary (denormalized for quick access)
    attended = models.BooleanField(default=False)
    total_attendance_minutes = models.PositiveIntegerField(default=0)
    attendance_eligible = models.BooleanField(default=False)  # Met minimum threshold
    attendance_manually_set = models.BooleanField(default=False)  # Override
    
    # Certificate
    certificate_issued = models.BooleanField(default=False)
    certificate_issued_at = models.DateTimeField(null=True, blank=True)
    
    # Privacy
    allow_public_verification = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'registrations'
        unique_together = [['event', 'email']]  # One registration per email per event
        indexes = [
            models.Index(fields=['event', 'status']),
            models.Index(fields=['email']),
            models.Index(fields=['user']),
            models.Index(fields=['uuid']),
        ]
    
    def __str__(self):
        return f"{self.full_name} - {self.event.title}"
    
    def link_to_user(self, user):
        """Link this registration to a user account."""
        if self.user is None and user.email.lower() == self.email.lower():
            self.user = user
            self.save(update_fields=['user', 'updated_at'])
    
    def update_attendance_summary(self):
        """Recalculate attendance from AttendanceRecords."""
        records = self.attendance_records.all()
        total_minutes = sum(r.duration_minutes for r in records)
        
        self.total_attendance_minutes = total_minutes
        self.attended = total_minutes > 0
        
        if not self.attendance_manually_set:
            self.attendance_eligible = total_minutes >= self.event.minimum_attendance_minutes
        
        self.save(update_fields=[
            'total_attendance_minutes',
            'attended',
            'attendance_eligible',
            'updated_at'
        ])


class AttendanceRecord(BaseModel):
    """
    Individual attendance record from Zoom.
    A registration can have multiple records (join/leave/rejoin).
    """
    
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='attendance_records'
    )
    registration = models.ForeignKey(
        Registration,
        on_delete=models.CASCADE,
        null=True,  # Null if unmatched attendee
        blank=True,
        related_name='attendance_records'
    )
    
    # Zoom participant info (for matching)
    zoom_participant_id = models.CharField(max_length=100, blank=True)
    zoom_user_id = models.CharField(max_length=100, blank=True)
    zoom_user_email = models.EmailField(blank=True)
    zoom_user_name = models.CharField(max_length=255, blank=True)
    join_method = models.CharField(max_length=50, blank=True)  # web, phone, app
    
    # Timing
    join_time = models.DateTimeField()
    leave_time = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=0)
    
    # Matching status
    is_matched = models.BooleanField(default=False)  # Matched to a registration
    matched_manually = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'attendance_records'
        indexes = [
            models.Index(fields=['event', 'registration']),
            models.Index(fields=['zoom_user_email']),
            models.Index(fields=['zoom_participant_id']),
        ]
    
    def __str__(self):
        name = self.zoom_user_name or self.zoom_user_email or 'Unknown'
        return f"{name} - {self.event.title}"
    
    def calculate_duration(self):
        """Calculate duration in minutes."""
        if self.leave_time and self.join_time:
            delta = self.leave_time - self.join_time
            self.duration_minutes = int(delta.total_seconds() / 60)
        else:
            self.duration_minutes = 0


class CustomFieldResponse(BaseModel):
    """
    Response to a custom registration field.
    """
    registration = models.ForeignKey(
        Registration,
        on_delete=models.CASCADE,
        related_name='custom_field_responses'
    )
    field = models.ForeignKey(
        'events.EventCustomField',
        on_delete=models.CASCADE,
        related_name='responses'
    )
    value = models.TextField()
    
    class Meta:
        db_table = 'custom_field_responses'
        unique_together = [['registration', 'field']]
```

---

### certificates/models.py

```python
import secrets
from django.db import models
from common.models import SoftDeleteModel, BaseModel


def generate_verification_code():
    """Generate a unique, URL-safe verification code."""
    return secrets.token_urlsafe(16)  # 22 characters


class CertificateTemplate(SoftDeleteModel):
    """
    Certificate template owned by an organizer.
    """
    owner = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='certificate_templates'
    )
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Template file
    file_url = models.URLField()  # GCS URL
    file_type = models.CharField(max_length=10)  # pdf, png, jpg
    
    # Field positions (for overlaying data)
    field_positions = models.JSONField(default=dict)
    """
    Example structure:
    {
        "attendee_name": {"x": 400, "y": 300, "font_size": 24, "font": "Helvetica", "align": "center"},
        "event_title": {"x": 400, "y": 350, "font_size": 18, "font": "Helvetica", "align": "center"},
        "event_date": {"x": 400, "y": 380, "font_size": 14, "font": "Helvetica", "align": "center"},
        "cpd_credits": {"x": 400, "y": 410, "font_size": 14, "font": "Helvetica", "align": "center"},
        "certificate_id": {"x": 100, "y": 550, "font_size": 10, "font": "Helvetica", "align": "left"},
        "signature": {"x": 400, "y": 500, "image_url": "...", "width": 150}
    }
    """
    
    # Settings
    is_default = models.BooleanField(default=False)
    
    # Usage stats (denormalized)
    usage_count = models.PositiveIntegerField(default=0)
    
    # Phase 2: Organization ownership
    # organization = models.ForeignKey('organizations.Organization', null=True, ...)
    
    class Meta:
        db_table = 'certificate_templates'
        indexes = [
            models.Index(fields=['owner']),
            models.Index(fields=['uuid']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.owner.email})"


class Certificate(SoftDeleteModel):
    """
    An issued certificate.
    """
    
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        REVOKED = 'revoked', 'Revoked'
    
    # Relationships
    registration = models.OneToOneField(
        'registrations.Registration',
        on_delete=models.PROTECT,
        related_name='certificate'
    )
    template = models.ForeignKey(
        CertificateTemplate,
        on_delete=models.PROTECT,
        related_name='certificates'
    )
    issued_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='certificates_issued'
    )
    
    # Verification
    verification_code = models.CharField(
        max_length=30,
        unique=True,
        default=generate_verification_code,
        db_index=True
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='certificates_revoked'
    )
    revocation_reason = models.TextField(blank=True)
    
    # Generated file
    file_url = models.URLField(blank=True)  # GCS URL to generated PDF
    
    # Snapshot of data at time of issuance (for historical accuracy)
    certificate_data = models.JSONField(default=dict)
    """
    Example:
    {
        "attendee_name": "John Smith, MD",
        "event_title": "Advanced Cardiac Care",
        "event_date": "2025-01-15",
        "cpd_type": "CME",
        "cpd_credits": "2.5",
        "organizer_name": "Medical Education Inc.",
        "issued_date": "2025-01-15"
    }
    """
    
    # Delivery
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'certificates'
        indexes = [
            models.Index(fields=['verification_code']),
            models.Index(fields=['status']),
            models.Index(fields=['uuid']),
        ]
    
    def __str__(self):
        return f"Certificate: {self.registration.full_name} - {self.registration.event.title}"
    
    @property
    def is_valid(self):
        return self.status == self.Status.ACTIVE and not self.is_deleted
    
    @property
    def event(self):
        return self.registration.event
    
    @property
    def attendee(self):
        return self.registration
    
    def revoke(self, user, reason=''):
        self.status = self.Status.REVOKED
        self.revoked_at = timezone.now()
        self.revoked_by = user
        self.revocation_reason = reason
        self.save(update_fields=[
            'status', 'revoked_at', 'revoked_by', 'revocation_reason', 'updated_at'
        ])


class CertificateStatusHistory(BaseModel):
    """
    Tracks status changes for certificates (audit trail).
    """
    certificate = models.ForeignKey(
        Certificate,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True
    )
    reason = models.TextField(blank=True)
    
    class Meta:
        db_table = 'certificate_status_history'
        ordering = ['-created_at']
```

---

### contacts/models.py

```python
from django.db import models
from common.models import BaseModel


class ContactList(BaseModel):
    """
    A named list of contacts owned by an organizer.
    """
    owner = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='contact_lists'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Stats (denormalized)
    contact_count = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'contact_lists'
        unique_together = [['owner', 'name']]
        indexes = [
            models.Index(fields=['owner']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.owner.email})"
    
    def update_contact_count(self):
        self.contact_count = self.contacts.count()
        self.save(update_fields=['contact_count', 'updated_at'])


class Contact(BaseModel):
    """
    A contact within a contact list.
    """
    contact_list = models.ForeignKey(
        ContactList,
        on_delete=models.CASCADE,
        related_name='contacts'
    )
    
    email = models.EmailField()
    full_name = models.CharField(max_length=255, blank=True)
    professional_title = models.CharField(max_length=255, blank=True)
    organization_name = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    
    # Engagement tracking
    events_invited_count = models.PositiveIntegerField(default=0)
    events_attended_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'contacts'
        unique_together = [['contact_list', 'email']]
        indexes = [
            models.Index(fields=['email']),
        ]
    
    def __str__(self):
        return f"{self.email} ({self.contact_list.name})"
```

---

### integrations/models.py

```python
from django.db import models
from common.models import BaseModel


class ZoomWebhookLog(BaseModel):
    """
    Log of Zoom webhook events for debugging and replay.
    """
    
    class EventType(models.TextChoices):
        MEETING_STARTED = 'meeting.started', 'Meeting Started'
        MEETING_ENDED = 'meeting.ended', 'Meeting Ended'
        PARTICIPANT_JOINED = 'meeting.participant_joined', 'Participant Joined'
        PARTICIPANT_LEFT = 'meeting.participant_left', 'Participant Left'
        RECORDING_COMPLETED = 'recording.completed', 'Recording Completed'
        OTHER = 'other', 'Other'
    
    # Event identification
    webhook_event_id = models.CharField(max_length=100, unique=True, db_index=True)
    event_type = models.CharField(max_length=50)
    event_timestamp = models.DateTimeField()
    
    # Related entities
    zoom_meeting_id = models.CharField(max_length=20, db_index=True)
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='zoom_webhook_logs'
    )
    
    # Payload
    raw_payload = models.JSONField()
    
    # Processing
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_error = models.TextField(blank=True)
    
    class Meta:
        db_table = 'zoom_webhook_logs'
        indexes = [
            models.Index(fields=['zoom_meeting_id', 'event_type']),
            models.Index(fields=['processed', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.zoom_meeting_id}"
```

---

## Indexes & Constraints

### Critical Query Patterns & Their Indexes

| Query Pattern | Index |
|---------------|-------|
| Get user by email | `users.email` (unique) |
| Get user by UUID | `users.uuid` (unique) |
| Get organizer's events | `events(owner_id, status)` |
| Get upcoming events | `events(status, starts_at)` |
| Find event by slug | `events.slug` (unique) |
| Find event by Zoom ID | `events.zoom_meeting_id` |
| Get event registrations | `registrations(event_id, status)` |
| Find registration by email | `registrations.email` |
| Find user's registrations | `registrations.user_id` |
| Verify certificate | `certificates.verification_code` (unique) |
| Get attendance by meeting | `attendance_records.zoom_meeting_id` |
| Match attendance by email | `attendance_records.zoom_user_email` |

### Unique Constraints

| Table | Constraint |
|-------|------------|
| users | email |
| users | uuid |
| events | slug |
| events | uuid |
| registrations | (event_id, email) |
| certificates | verification_code |
| contact_lists | (owner_id, name) |
| contacts | (contact_list_id, email) |
| custom_field_responses | (registration_id, field_id) |

### Foreign Key Behaviors

| Relationship | On Delete |
|--------------|-----------|
| Event → Owner | PROTECT (can't delete user with events) |
| Registration → Event | CASCADE (delete registrations if event deleted) |
| Registration → User | SET_NULL (keep registration if user deleted) |
| Certificate → Registration | PROTECT (can't delete registration with certificate) |
| Certificate → Template | PROTECT (can't delete template with certificates) |
| AttendanceRecord → Registration | CASCADE |
| ContactList → Owner | CASCADE |

---

## Phase 2 Considerations

### Organization Model (Future)

```python
class Organization(SoftDeleteModel):
    """Phase 2: Organization that organizers can belong to."""
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    
    # Branding
    logo_url = models.URLField(blank=True)
    primary_color = models.CharField(max_length=7, blank=True)  # Hex
    
    # Settings
    default_cpd_type = models.CharField(max_length=50, blank=True)
    
    # Subscription
    subscription_tier = models.CharField(max_length=20)
    
    class Meta:
        db_table = 'organizations'


class OrganizationMembership(BaseModel):
    """Phase 2: Links organizers to organizations."""
    
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        MANAGER = 'manager', 'Event Manager'
        MEMBER = 'member', 'Member'
    
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=Role.choices)
    
    class Meta:
        db_table = 'organization_memberships'
        unique_together = [['organization', 'user']]
```

### Migration Path

Models already have nullable org references planned:
```python
# In Event, CertificateTemplate, ContactList:
# organization = models.ForeignKey('organizations.Organization', null=True, blank=True, ...)
```

When Phase 2 launches:
1. Add `organizations` app with models
2. Add migrations for FK fields
3. Existing data remains with `organization=None`
4. Organizers invited to orgs get FK populated
5. Query logic: `owner=user OR organization__memberships__user=user`

---

## Migration Strategy

### Initial Migration Order

```
1. common (base models, no dependencies)
2. accounts (User, ZoomConnection)
3. certificates (CertificateTemplate - needs User)
4. events (Event, EventCustomField - needs User, CertificateTemplate)
5. registrations (Registration, AttendanceRecord - needs User, Event)
6. certificates (Certificate - needs Registration, CertificateTemplate)
7. contacts (ContactList, Contact - needs User)
8. integrations (ZoomWebhookLog - needs Event)
```

### Data Migration Notes

1. **Email normalization**: All emails lowercase
2. **UUID backfill**: If importing existing data, generate UUIDs
3. **Slug generation**: Auto-generate from title if not provided
4. **Verification codes**: Generate unique codes for existing certificates
