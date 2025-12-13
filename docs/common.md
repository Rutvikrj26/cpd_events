# Common App: Base Models & Utilities

## Overview

The `common` app provides foundational components used across all other apps:
- Base model classes with standard fields
- Custom field types
- Shared validators
- Utility functions

**No database tables are created directly by this app** — all models are abstract.

---

## Base Models

### TimeStampedModel

Adds automatic timestamp tracking to any model.

```python
# common/models.py

from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    Abstract base model with automatic timestamp tracking.
    
    Fields:
        created_at: Set once when record is created
        updated_at: Updated on every save
    """
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this record was last modified"
    )

    class Meta:
        abstract = True
```

---

### UUIDModel

Adds a UUID field for external reference (URLs, APIs).

```python
import uuid


class UUIDModel(models.Model):
    """
    Abstract base model with UUID for external reference.
    
    The UUID should be used in:
    - URLs: /events/550e8400-e29b-41d4-a716-446655440000/
    - API responses: {"uuid": "550e8400-..."}
    - External integrations
    
    The integer PK should be used for:
    - Internal queries and joins
    - Foreign key relationships
    """
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
        help_text="Public identifier for external use"
    )

    class Meta:
        abstract = True
    
    def get_short_uuid(self):
        """Return first 8 characters of UUID for display."""
        return str(self.uuid)[:8]
```

---

### BaseModel

Standard base combining timestamps and UUID. **Use this for most models.**

```python
class BaseModel(TimeStampedModel, UUIDModel):
    """
    Standard base model with timestamps and UUID.
    
    Provides:
    - id: Auto-increment integer primary key (implicit)
    - uuid: Unique identifier for external use
    - created_at: Creation timestamp
    - updated_at: Last modification timestamp
    """
    
    class Meta:
        abstract = True
```

---

### SoftDeleteModel

For entities that should never be truly deleted.

```python
class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet that supports soft delete operations."""
    
    def delete(self):
        """Soft delete all records in queryset."""
        return self.update(deleted_at=timezone.now())
    
    def hard_delete(self):
        """Actually delete records (use with caution)."""
        return super().delete()
    
    def alive(self):
        """Return only non-deleted records."""
        return self.filter(deleted_at__isnull=True)
    
    def dead(self):
        """Return only deleted records."""
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager):
    """
    Manager that excludes soft-deleted records by default.
    
    Usage:
        Model.objects.all()        # Only non-deleted
        Model.all_objects.all()    # Include deleted
        Model.objects.dead()       # Only deleted
    """
    
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class AllObjectsManager(models.Manager):
    """Manager that includes soft-deleted records."""
    
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class SoftDeleteModel(BaseModel):
    """
    Base model with soft delete capability.
    
    Records are never truly deleted — deleted_at is set instead.
    Use for: Users, Events, Certificates, CertificateTemplates, Registrations
    
    Important: Related object queries (e.g., event.registrations.all()) 
    will bypass the default manager and include deleted records.
    Use event.registrations.filter(deleted_at__isnull=True) to exclude them,
    or use the .alive() queryset method.
    
    Methods:
        soft_delete(): Mark record as deleted
        restore(): Unmark deletion
        hard_delete(): Actually delete (use with caution)
    
    Properties:
        is_deleted: Boolean indicating soft-deleted state
    """
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When this record was soft-deleted (null if active)"
    )
    
    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()
    
    class Meta:
        abstract = True
    
    def soft_delete(self):
        """Mark this record as deleted."""
        if self.deleted_at is None:
            self.deleted_at = timezone.now()
            self.save(update_fields=['deleted_at', 'updated_at'])
    
    def restore(self):
        """Restore a soft-deleted record."""
        if self.deleted_at is not None:
            self.deleted_at = None
            self.save(update_fields=['deleted_at', 'updated_at'])
    
    def hard_delete(self):
        """
        Actually delete the record from database.
        Use with caution — prefer soft_delete() in most cases.
        """
        super().delete()
    
    @property
    def is_deleted(self):
        """Return True if record is soft-deleted."""
        return self.deleted_at is not None
```

---

## Custom Fields

### LowercaseEmailField

Ensures all emails are stored in lowercase for consistent matching.

```python
# common/fields.py

from django.db import models


class LowercaseEmailField(models.EmailField):
    """
    Email field that automatically converts to lowercase.
    
    Ensures consistent email matching across the application.
    Always use this instead of models.EmailField.
    """
    
    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is not None:
            value = value.lower().strip()
        return value
    
    def pre_save(self, model_instance, add):
        value = getattr(model_instance, self.attname)
        if value is not None:
            value = value.lower().strip()
            setattr(model_instance, self.attname, value)
        return value
```

---

### EncryptedTextField

For sensitive data like OAuth tokens.

```python
# Requires: pip install django-fernet-fields

from fernet_fields import EncryptedTextField as FernetEncryptedTextField


class EncryptedTextField(FernetEncryptedTextField):
    """
    Text field that encrypts data at rest.
    
    Use for:
    - OAuth access tokens
    - OAuth refresh tokens
    - API keys
    - Other sensitive credentials
    
    Note: Encrypted fields cannot be queried with filters.
    """
    pass
```

**Alternative without django-fernet-fields:**

```python
from django.conf import settings
from cryptography.fernet import Fernet
import base64


class EncryptedTextField(models.TextField):
    """
    Text field with Fernet encryption.
    
    Requires ENCRYPTION_KEY in settings.
    """
    
    def __init__(self, *args, **kwargs):
        kwargs['editable'] = False
        super().__init__(*args, **kwargs)
    
    def _get_fernet(self):
        key = settings.ENCRYPTION_KEY.encode()
        return Fernet(key)
    
    def get_prep_value(self, value):
        if value is None:
            return None
        f = self._get_fernet()
        return f.encrypt(value.encode()).decode()
    
    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        f = self._get_fernet()
        return f.decrypt(value.encode()).decode()
```

---

## Validators

### JSON Schema Validators

For validating JSONField contents.

```python
# common/validators.py

from django.core.exceptions import ValidationError
import json


def validate_field_positions_schema(value):
    """
    Validate certificate template field positions JSON.
    
    Expected schema:
    {
        "field_name": {
            "x": <int>,
            "y": <int>,
            "font_size": <int>,
            "font": <str>,
            "align": "left" | "center" | "right",
            "color": <str, optional>,
            "image_url": <str, optional>,
            "width": <int, optional>
        },
        ...
    }
    """
    if not isinstance(value, dict):
        raise ValidationError("Field positions must be a dictionary")
    
    valid_fields = {
        'attendee_name', 'event_title', 'event_date', 
        'cpd_credits', 'cpd_type', 'certificate_id',
        'organizer_name', 'signature', 'issue_date'
    }
    valid_alignments = {'left', 'center', 'right'}
    
    for field_name, config in value.items():
        if field_name not in valid_fields:
            raise ValidationError(f"Unknown field: {field_name}")
        
        if not isinstance(config, dict):
            raise ValidationError(f"Config for {field_name} must be a dictionary")
        
        # Required position fields
        if 'x' not in config or 'y' not in config:
            raise ValidationError(f"Field {field_name} must have x and y coordinates")
        
        if not isinstance(config['x'], (int, float)):
            raise ValidationError(f"Field {field_name}: x must be a number")
        
        if not isinstance(config['y'], (int, float)):
            raise ValidationError(f"Field {field_name}: y must be a number")
        
        # Optional fields validation
        if 'align' in config and config['align'] not in valid_alignments:
            raise ValidationError(f"Field {field_name}: align must be left, center, or right")
        
        if 'font_size' in config and not isinstance(config['font_size'], int):
            raise ValidationError(f"Field {field_name}: font_size must be an integer")


def validate_zoom_settings_schema(value):
    """
    Validate Zoom meeting settings JSON.
    
    Expected schema:
    {
        "waiting_room": <bool>,
        "join_before_host": <bool>,
        "mute_upon_entry": <bool>,
        "auto_recording": "none" | "local" | "cloud"
    }
    """
    if not isinstance(value, dict):
        raise ValidationError("Zoom settings must be a dictionary")
    
    valid_keys = {'waiting_room', 'join_before_host', 'mute_upon_entry', 'auto_recording'}
    valid_recording = {'none', 'local', 'cloud'}
    
    for key, val in value.items():
        if key not in valid_keys:
            raise ValidationError(f"Unknown Zoom setting: {key}")
        
        if key in {'waiting_room', 'join_before_host', 'mute_upon_entry'}:
            if not isinstance(val, bool):
                raise ValidationError(f"Zoom setting {key} must be boolean")
        
        if key == 'auto_recording' and val not in valid_recording:
            raise ValidationError(f"auto_recording must be one of: {valid_recording}")


def validate_certificate_data_schema(value):
    """
    Validate certificate snapshot data JSON.
    
    Expected schema:
    {
        "attendee_name": <str, required>,
        "event_title": <str, required>,
        "event_date": <str, required, ISO date>,
        "cpd_type": <str, optional>,
        "cpd_credits": <str, optional>,
        "organizer_name": <str, required>,
        "issued_date": <str, required, ISO date>
    }
    """
    if not isinstance(value, dict):
        raise ValidationError("Certificate data must be a dictionary")
    
    required = {'attendee_name', 'event_title', 'event_date', 'organizer_name', 'issued_date'}
    
    for field in required:
        if field not in value:
            raise ValidationError(f"Missing required field: {field}")
        if not isinstance(value[field], str):
            raise ValidationError(f"Field {field} must be a string")
```

---

### Other Validators

```python
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator


# Color hex code validator
hex_color_validator = RegexValidator(
    regex=r'^#[0-9A-Fa-f]{6}$',
    message='Enter a valid hex color (e.g., #FF5733)'
)


# Timezone validator
def validate_timezone(value):
    """Validate that value is a valid timezone string."""
    import pytz
    if value not in pytz.all_timezones:
        raise ValidationError(f"'{value}' is not a valid timezone")


# Slug with UUID prefix validator
slug_with_uuid_validator = RegexValidator(
    regex=r'^[a-z0-9]+(?:-[a-z0-9]+)*$',
    message='Enter a valid slug (lowercase letters, numbers, hyphens only)'
)
```

---

## Utility Functions

```python
# common/utils.py

import secrets
import string
from django.utils.text import slugify


def generate_unique_slug(base_string, existing_slugs=None, max_length=200):
    """
    Generate a unique slug from a string.
    
    Args:
        base_string: String to slugify
        existing_slugs: Set of existing slugs to avoid
        max_length: Maximum slug length
    
    Returns:
        Unique slug string
    """
    base_slug = slugify(base_string)[:max_length-9]  # Leave room for suffix
    
    if existing_slugs is None:
        return base_slug
    
    if base_slug not in existing_slugs:
        return base_slug
    
    # Add random suffix
    for _ in range(100):
        suffix = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
        candidate = f"{base_slug}-{suffix}"
        if candidate not in existing_slugs:
            return candidate
    
    raise ValueError("Could not generate unique slug")


def generate_verification_code(length=22):
    """
    Generate a URL-safe verification code.
    
    Default length of 22 chars provides ~131 bits of entropy.
    """
    return secrets.token_urlsafe(length)[:length]


def generate_short_code(length=8):
    """
    Generate a short alphanumeric code.
    
    Useful for display (e.g., certificate ID shown on document).
    Excludes ambiguous characters (0, O, l, 1, I).
    """
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def normalize_email(email):
    """
    Normalize an email address.
    
    - Lowercase
    - Strip whitespace
    - Could add: Gmail dot removal, plus addressing handling
    """
    if email is None:
        return None
    return email.lower().strip()


def mask_email(email):
    """
    Mask an email for display.
    
    Example: john.doe@example.com → j***e@example.com
    """
    if not email or '@' not in email:
        return email
    
    local, domain = email.rsplit('@', 1)
    if len(local) <= 2:
        masked_local = local[0] + '***'
    else:
        masked_local = local[0] + '***' + local[-1]
    
    return f"{masked_local}@{domain}"
```

---

## Mixins

### StatusMixin

For models with status fields that need history tracking.

```python
# common/mixins.py

from django.db import models


class StatusMixin(models.Model):
    """
    Mixin for models that track status changes.
    
    Subclasses should define:
    - Status (TextChoices)
    - status field
    - StatusHistory model
    
    Provides:
    - change_status() method with history tracking
    - can_transition_to() method for validation
    """
    
    class Meta:
        abstract = True
    
    # Override in subclass
    VALID_TRANSITIONS = {}  # {from_status: [to_status, ...]}
    STATUS_HISTORY_MODEL = None  # Reference to history model
    
    def can_transition_to(self, new_status):
        """Check if transition to new_status is valid."""
        if not self.VALID_TRANSITIONS:
            return True  # No restrictions defined
        
        current = self.status
        valid = self.VALID_TRANSITIONS.get(current, [])
        return new_status in valid
    
    def change_status(self, new_status, user=None, reason=''):
        """
        Change status with validation and history tracking.
        
        Args:
            new_status: Target status
            user: User making the change
            reason: Optional reason for change
        
        Raises:
            ValueError: If transition is invalid
        """
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Cannot transition from {self.status} to {new_status}"
            )
        
        old_status = self.status
        self.status = new_status
        self.save(update_fields=['status', 'updated_at'])
        
        # Create history record
        if self.STATUS_HISTORY_MODEL:
            self.STATUS_HISTORY_MODEL.objects.create(
                **{self._meta.model_name: self},
                from_status=old_status,
                to_status=new_status,
                changed_by=user,
                reason=reason
            )
```

---

### AddressableMixin

For models that need URL generation.

```python
from django.urls import reverse


class AddressableMixin(models.Model):
    """
    Mixin for models that have public URLs.
    
    Subclasses should define:
    - URL_NAME: Name of URL pattern
    - get_url_kwargs(): Return kwargs for URL
    """
    
    class Meta:
        abstract = True
    
    URL_NAME = None
    
    def get_url_kwargs(self):
        """Return kwargs for URL reverse. Override in subclass."""
        return {'uuid': str(self.uuid)}
    
    def get_absolute_url(self):
        """Return the canonical URL for this object."""
        if self.URL_NAME is None:
            raise NotImplementedError("URL_NAME not defined")
        return reverse(self.URL_NAME, kwargs=self.get_url_kwargs())
```

---

## Model Validation Pattern

All models should implement validation in `clean()`:

```python
class ExampleModel(BaseModel):
    start_date = models.DateField()
    end_date = models.DateField()
    
    def clean(self):
        super().clean()
        
        errors = {}
        
        if self.end_date and self.start_date:
            if self.end_date < self.start_date:
                errors['end_date'] = 'End date must be after start date'
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
```

---

## Index

| Component | Type | Purpose |
|-----------|------|---------|
| TimeStampedModel | Abstract Model | Adds created_at, updated_at |
| UUIDModel | Abstract Model | Adds uuid field |
| BaseModel | Abstract Model | Combines timestamps + UUID |
| SoftDeleteModel | Abstract Model | Adds soft delete capability |
| LowercaseEmailField | Custom Field | Normalizes emails |
| EncryptedTextField | Custom Field | Encrypts sensitive data |
| validate_field_positions_schema | Validator | Certificate template positions |
| validate_zoom_settings_schema | Validator | Zoom meeting settings |
| validate_certificate_data_schema | Validator | Certificate snapshot data |
| generate_unique_slug | Utility | Slug generation |
| generate_verification_code | Utility | Secure code generation |
| StatusMixin | Mixin | Status change tracking |
| AddressableMixin | Mixin | URL generation |
