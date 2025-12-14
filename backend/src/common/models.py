"""
Abstract base models for the CPD Events platform.

All models in other apps should inherit from these base classes.
"""

import uuid
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
