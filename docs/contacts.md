# Contacts App: Contact Management

## Overview

The `contacts` app handles:
- Contact lists for organizing invitees
- Individual contact records
- Tagging system for categorization
- Import/export functionality

---

## Models

### ContactList

A named collection of contacts owned by an organizer.

```python
# contacts/models.py

from django.db import models
from common.models import BaseModel
from common.fields import LowercaseEmailField


class ContactList(BaseModel):
    """
    A named list of contacts for an organizer.
    
    Use cases:
    - "All Physicians"
    - "2024 Conference Attendees"
    - "VIP Clients"
    
    Note: Not soft-deleted. Deleting a list deletes contacts in it.
    If contact preservation is needed, move contacts to another list first.
    """
    
    owner = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='contact_lists',
        help_text="Organizer who owns this list"
    )
    
    # Phase 2: Organization ownership
    # organization = models.ForeignKey(
    #     'organizations.Organization',
    #     on_delete=models.CASCADE,
    #     null=True, blank=True,
    #     related_name='contact_lists'
    # )
    
    name = models.CharField(
        max_length=100,
        help_text="List name"
    )
    description = models.TextField(
        blank=True,
        max_length=500,
        help_text="List description"
    )
    
    # Settings
    is_default = models.BooleanField(
        default=False,
        help_text="Default list for new contacts"
    )
    
    # Stats (denormalized)
    contact_count = models.PositiveIntegerField(
        default=0,
        help_text="Denormalized: number of contacts in list"
    )
    
    class Meta:
        db_table = 'contact_lists'
        ordering = ['name']
        unique_together = [['owner', 'name']]
        indexes = [
            models.Index(fields=['owner']),
            models.Index(fields=['uuid']),
        ]
        verbose_name = 'Contact List'
        verbose_name_plural = 'Contact Lists'
    
    def __str__(self):
        return f"{self.name} ({self.contact_count})"
    
    def set_as_default(self):
        """Set this list as the default for the owner."""
        ContactList.objects.filter(
            owner=self.owner,
            is_default=True
        ).exclude(pk=self.pk).update(is_default=False)
        
        self.is_default = True
        self.save(update_fields=['is_default', 'updated_at'])
    
    def update_contact_count(self):
        """Update denormalized contact count."""
        self.contact_count = self.contacts.count()
        self.save(update_fields=['contact_count', 'updated_at'])
    
    def merge_into(self, target_list):
        """
        Merge this list into another list.
        Moves all contacts, then deletes this list.
        
        Args:
            target_list: ContactList to merge into
        """
        if target_list.owner != self.owner:
            raise ValueError("Cannot merge lists from different owners")
        
        # Move contacts (skip duplicates)
        for contact in self.contacts.all():
            if not Contact.objects.filter(
                contact_list=target_list,
                email=contact.email
            ).exists():
                contact.contact_list = target_list
                contact.save(update_fields=['contact_list', 'updated_at'])
        
        # Update counts
        target_list.update_contact_count()
        
        # Delete this list (remaining contacts cascade)
        self.delete()
    
    def duplicate(self, new_name=None):
        """
        Create a copy of this list with all contacts.
        
        Returns:
            New ContactList instance
        """
        new_list = ContactList.objects.create(
            owner=self.owner,
            name=new_name or f"{self.name} (Copy)",
            description=self.description
        )
        
        # Copy contacts
        for contact in self.contacts.all():
            Contact.objects.create(
                contact_list=new_list,
                email=contact.email,
                full_name=contact.full_name,
                professional_title=contact.professional_title,
                organization_name=contact.organization_name,
                notes=contact.notes
            )
            # Copy tags
            new_contact = new_list.contacts.get(email=contact.email)
            new_contact.tags.set(contact.tags.all())
        
        new_list.update_contact_count()
        return new_list
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('contacts:list_detail', kwargs={'uuid': self.uuid})
```

---

### Contact

An individual contact within a list.

```python
class Contact(BaseModel):
    """
    An individual contact in a contact list.
    
    Contacts can optionally be linked to a User account if
    the contact has registered on the platform.
    
    Note: Not soft-deleted. Hard delete removes the contact.
    Historical invite/registration data preserved via EventInvitation.
    """
    
    contact_list = models.ForeignKey(
        ContactList,
        on_delete=models.CASCADE,
        related_name='contacts'
    )
    
    # Optional link to user account
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='contact_records',
        help_text="Linked user account (if they've signed up)"
    )
    
    # Contact info
    email = LowercaseEmailField(
        db_index=True,
        help_text="Contact email (canonical, lowercase)"
    )
    full_name = models.CharField(
        max_length=255,
        help_text="Full name"
    )
    professional_title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Professional title"
    )
    organization_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Organization/company"
    )
    phone = models.CharField(
        max_length=50,
        blank=True,
        help_text="Phone number"
    )
    
    # Additional info
    notes = models.TextField(
        blank=True,
        max_length=2000,
        help_text="Private notes about contact"
    )
    
    # Tags (many-to-many)
    tags = models.ManyToManyField(
        'Tag',
        blank=True,
        related_name='contacts'
    )
    
    # Source tracking
    source = models.CharField(
        max_length=50,
        blank=True,
        help_text="How contact was added (manual, csv, registration)"
    )
    added_from_event = models.ForeignKey(
        'events.Event',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="Event this contact was added from (if applicable)"
    )
    
    # Engagement stats (denormalized)
    events_invited_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of events invited to"
    )
    events_attended_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of events attended"
    )
    last_invited_at = models.DateTimeField(
        null=True, blank=True
    )
    last_attended_at = models.DateTimeField(
        null=True, blank=True
    )
    
    # Email preferences
    email_opted_out = models.BooleanField(
        default=False,
        help_text="Contact has opted out of emails"
    )
    email_bounced = models.BooleanField(
        default=False,
        help_text="Email has bounced"
    )
    
    class Meta:
        db_table = 'contacts'
        ordering = ['full_name']
        unique_together = [['contact_list', 'email']]
        indexes = [
            models.Index(fields=['contact_list']),
            models.Index(fields=['email']),
            models.Index(fields=['user']),
            models.Index(fields=['uuid']),
        ]
        verbose_name = 'Contact'
        verbose_name_plural = 'Contacts'
    
    def __str__(self):
        return f"{self.full_name} <{self.email}>"
    
    @property
    def display_name(self):
        """Name with title if available."""
        if self.professional_title:
            return f"{self.full_name}, {self.professional_title}"
        return self.full_name
    
    @property
    def is_linked(self):
        """Check if linked to a user account."""
        return self.user is not None
    
    def link_to_user(self, user):
        """
        Link this contact to a user account.
        
        Args:
            user: User to link to
        """
        if user.email.lower() == self.email.lower():
            self.user = user
            self.save(update_fields=['user', 'updated_at'])
            return True
        return False
    
    def record_invite(self):
        """Record that an invite was sent."""
        from django.db.models import F
        from django.utils import timezone
        
        Contact.objects.filter(pk=self.pk).update(
            events_invited_count=F('events_invited_count') + 1,
            last_invited_at=timezone.now()
        )
    
    def record_attendance(self):
        """Record event attendance."""
        from django.db.models import F
        from django.utils import timezone
        
        Contact.objects.filter(pk=self.pk).update(
            events_attended_count=F('events_attended_count') + 1,
            last_attended_at=timezone.now()
        )
    
    def move_to_list(self, target_list):
        """
        Move contact to another list.
        
        Args:
            target_list: ContactList to move to
        """
        if target_list.owner != self.contact_list.owner:
            raise ValueError("Cannot move contact to list from different owner")
        
        # Check for duplicate
        if Contact.objects.filter(
            contact_list=target_list,
            email=self.email
        ).exists():
            raise ValueError("Contact with this email already exists in target list")
        
        old_list = self.contact_list
        self.contact_list = target_list
        self.save(update_fields=['contact_list', 'updated_at'])
        
        # Update counts
        old_list.update_contact_count()
        target_list.update_contact_count()
    
    def copy_to_list(self, target_list):
        """
        Copy contact to another list.
        
        Args:
            target_list: ContactList to copy to
        
        Returns:
            New Contact instance
        """
        if target_list.owner != self.contact_list.owner:
            raise ValueError("Cannot copy contact to list from different owner")
        
        # Check for duplicate
        if Contact.objects.filter(
            contact_list=target_list,
            email=self.email
        ).exists():
            raise ValueError("Contact with this email already exists in target list")
        
        new_contact = Contact.objects.create(
            contact_list=target_list,
            user=self.user,
            email=self.email,
            full_name=self.full_name,
            professional_title=self.professional_title,
            organization_name=self.organization_name,
            phone=self.phone,
            notes=self.notes,
            source='copy'
        )
        new_contact.tags.set(self.tags.all())
        
        target_list.update_contact_count()
        return new_contact
```

---

### Tag

Tags for categorizing contacts.

```python
class Tag(BaseModel):
    """
    Tag for categorizing contacts.
    
    Tags are owned by an organizer and can be applied to any
    contact in their lists.
    """
    
    owner = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='tags'
    )
    
    name = models.CharField(
        max_length=50,
        help_text="Tag name"
    )
    color = models.CharField(
        max_length=7,
        default='#6B7280',
        help_text="Hex color for display"
    )
    description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Tag description"
    )
    
    # Stats (denormalized)
    contact_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of contacts with this tag"
    )
    
    class Meta:
        db_table = 'tags'
        ordering = ['name']
        unique_together = [['owner', 'name']]
        indexes = [
            models.Index(fields=['owner']),
        ]
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'
    
    def __str__(self):
        return self.name
    
    def update_contact_count(self):
        """Update denormalized contact count."""
        self.contact_count = self.contacts.count()
        self.save(update_fields=['contact_count', 'updated_at'])
    
    def merge_into(self, target_tag):
        """
        Merge this tag into another tag.
        Moves all contacts to target tag, then deletes this tag.
        """
        if target_tag.owner != self.owner:
            raise ValueError("Cannot merge tags from different owners")
        
        # Add target tag to all contacts with this tag
        for contact in self.contacts.all():
            contact.tags.add(target_tag)
        
        # Update count
        target_tag.update_contact_count()
        
        # Delete this tag
        self.delete()
```

---

## Import/Export Service

```python
# contacts/services.py

import csv
import io
from django.db import transaction


class ContactImportService:
    """Service for importing contacts from CSV."""
    
    REQUIRED_COLUMNS = {'email'}
    OPTIONAL_COLUMNS = {'full_name', 'name', 'professional_title', 'title', 
                        'organization_name', 'organization', 'company', 
                        'phone', 'notes', 'tags'}
    
    @classmethod
    def parse_csv(cls, file_content, has_header=True):
        """
        Parse CSV content and return list of contact dicts.
        
        Args:
            file_content: CSV file content (string or bytes)
            has_header: Whether first row is header
        
        Returns:
            tuple: (contacts_list, errors_list)
        """
        if isinstance(file_content, bytes):
            file_content = file_content.decode('utf-8-sig')
        
        reader = csv.DictReader(io.StringIO(file_content))
        
        contacts = []
        errors = []
        
        # Normalize column names
        fieldnames = [f.lower().strip() for f in reader.fieldnames]
        
        # Check required columns
        if 'email' not in fieldnames:
            return [], [{'row': 0, 'error': 'Missing required column: email'}]
        
        for row_num, row in enumerate(reader, start=2):
            # Normalize keys
            row = {k.lower().strip(): v.strip() for k, v in row.items()}
            
            email = row.get('email', '').lower().strip()
            
            if not email:
                errors.append({'row': row_num, 'error': 'Missing email'})
                continue
            
            # Basic email validation
            if '@' not in email:
                errors.append({'row': row_num, 'error': f'Invalid email: {email}'})
                continue
            
            contact = {
                'email': email,
                'full_name': row.get('full_name') or row.get('name') or email.split('@')[0],
                'professional_title': row.get('professional_title') or row.get('title') or '',
                'organization_name': (row.get('organization_name') or 
                                     row.get('organization') or 
                                     row.get('company') or ''),
                'phone': row.get('phone') or '',
                'notes': row.get('notes') or '',
                'tags': [t.strip() for t in (row.get('tags') or '').split(',') if t.strip()]
            }
            
            contacts.append(contact)
        
        return contacts, errors
    
    @classmethod
    @transaction.atomic
    def import_contacts(cls, contact_list, contacts_data, skip_duplicates=True):
        """
        Import contacts into a list.
        
        Args:
            contact_list: ContactList to import into
            contacts_data: List of contact dicts from parse_csv
            skip_duplicates: Whether to skip existing emails
        
        Returns:
            tuple: (created_count, updated_count, skipped_count)
        """
        created = 0
        updated = 0
        skipped = 0
        
        # Get existing emails in list
        existing_emails = set(
            contact_list.contacts.values_list('email', flat=True)
        )
        
        # Get or create tags
        tag_cache = {}
        
        for data in contacts_data:
            email = data['email']
            
            if email in existing_emails:
                if skip_duplicates:
                    skipped += 1
                    continue
                else:
                    # Update existing
                    contact = contact_list.contacts.get(email=email)
                    contact.full_name = data['full_name']
                    contact.professional_title = data['professional_title']
                    contact.organization_name = data['organization_name']
                    contact.phone = data['phone']
                    if data['notes']:
                        contact.notes = data['notes']
                    contact.save()
                    updated += 1
            else:
                # Create new
                contact = Contact.objects.create(
                    contact_list=contact_list,
                    email=email,
                    full_name=data['full_name'],
                    professional_title=data['professional_title'],
                    organization_name=data['organization_name'],
                    phone=data['phone'],
                    notes=data['notes'],
                    source='csv'
                )
                created += 1
                existing_emails.add(email)
            
            # Handle tags
            for tag_name in data.get('tags', []):
                if tag_name not in tag_cache:
                    tag, _ = Tag.objects.get_or_create(
                        owner=contact_list.owner,
                        name=tag_name,
                        defaults={'color': '#6B7280'}
                    )
                    tag_cache[tag_name] = tag
                contact.tags.add(tag_cache[tag_name])
        
        # Update list count
        contact_list.update_contact_count()
        
        # Update tag counts
        for tag in tag_cache.values():
            tag.update_contact_count()
        
        return created, updated, skipped


class ContactExportService:
    """Service for exporting contacts to CSV."""
    
    @classmethod
    def export_list(cls, contact_list, include_tags=True):
        """
        Export contact list to CSV.
        
        Returns:
            str: CSV content
        """
        output = io.StringIO()
        
        fieldnames = [
            'email', 'full_name', 'professional_title', 
            'organization_name', 'phone', 'notes'
        ]
        if include_tags:
            fieldnames.append('tags')
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for contact in contact_list.contacts.prefetch_related('tags'):
            row = {
                'email': contact.email,
                'full_name': contact.full_name,
                'professional_title': contact.professional_title,
                'organization_name': contact.organization_name,
                'phone': contact.phone,
                'notes': contact.notes
            }
            if include_tags:
                row['tags'] = ', '.join(t.name for t in contact.tags.all())
            
            writer.writerow(row)
        
        return output.getvalue()
    
    @classmethod
    def export_event_registrants(cls, event, include_attendance=True):
        """
        Export event registrants to CSV.
        
        Returns:
            str: CSV content
        """
        output = io.StringIO()
        
        fieldnames = [
            'email', 'full_name', 'professional_title', 
            'organization_name', 'status', 'registered_at'
        ]
        if include_attendance:
            fieldnames.extend([
                'attended', 'attendance_minutes', 'attendance_percent', 
                'certificate_issued'
            ])
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for reg in event.registrations.filter(deleted_at__isnull=True):
            row = {
                'email': reg.email,
                'full_name': reg.full_name,
                'professional_title': reg.professional_title,
                'organization_name': reg.organization_name,
                'status': reg.status,
                'registered_at': reg.created_at.isoformat()
            }
            if include_attendance:
                row.update({
                    'attended': 'Yes' if reg.attended else 'No',
                    'attendance_minutes': reg.total_attendance_minutes,
                    'attendance_percent': reg.attendance_percent,
                    'certificate_issued': 'Yes' if reg.certificate_issued else 'No'
                })
            
            writer.writerow(row)
        
        return output.getvalue()
```

---

## Relationships

```
ContactList
├── User (N:1, CASCADE) — owner
└── Contact (1:N, CASCADE)

Contact
├── ContactList (N:1, CASCADE)
├── User (N:1, SET_NULL) — linked account
├── Event (N:1, SET_NULL) — added_from_event
└── Tag (N:N)

Tag
├── User (N:1, CASCADE) — owner
└── Contact (N:N)
```

---

## Indexes

| Table | Index | Purpose |
|-------|-------|---------|
| contact_lists | owner_id | Owner's lists |
| contact_lists | owner_id, name (unique) | Unique list names per owner |
| contacts | contact_list_id | List's contacts |
| contacts | contact_list_id, email (unique) | One per email per list |
| contacts | email | Find across all lists |
| contacts | user_id | Linked contacts |
| tags | owner_id | Owner's tags |
| tags | owner_id, name (unique) | Unique tag names per owner |

---

## Business Rules

1. **List names**: Unique per owner
2. **Contact emails**: Unique within a list (can exist in multiple lists)
3. **Tag names**: Unique per owner
4. **List deletion**: Cascades to contacts (use merge_into to preserve)
5. **Contact linking**: Automatic when email matches verified user
6. **Email opt-out**: Respected by all invite/reminder emails
7. **Email bounced**: Prevents further sends, requires manual reset

---

## Signals

```python
# contacts/signals.py

from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver

@receiver(post_save, sender=Contact)
def on_contact_save(sender, instance, created, **kwargs):
    if created:
        instance.contact_list.update_contact_count()
        
        # Try to link to existing user
        from accounts.models import User
        try:
            user = User.objects.get(email__iexact=instance.email)
            instance.link_to_user(user)
        except User.DoesNotExist:
            pass

@receiver(post_delete, sender=Contact)
def on_contact_delete(sender, instance, **kwargs):
    instance.contact_list.update_contact_count()

@receiver(m2m_changed, sender=Contact.tags.through)
def on_contact_tags_changed(sender, instance, action, **kwargs):
    if action in ['post_add', 'post_remove', 'post_clear']:
        # Update tag counts
        for tag in instance.tags.all():
            tag.update_contact_count()
```
