"""
Contacts app models - ContactList, Contact, Tag.
"""

from django.db import models

from common.fields import LowercaseEmailField
from common.models import BaseModel


class ContactList(BaseModel):
    """
    A contact list for an organizer.

    Design:
    - Each organizer has exactly ONE personal list (auto-created)
    - Tags are used for segmentation instead of multiple lists
    - Organizations can view member lists for cross-org visibility

    Ownership:
    - organization=NULL: personal list (only owner can access)
    - organization=set: shared with org (all org members can access)
    """

    owner = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='contact_lists',
        help_text="User who created this list",
    )
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='contact_lists',
        help_text="If set, list is shared with all org members",
    )

    name = models.CharField(max_length=100, help_text="List name")
    description = models.TextField(blank=True, max_length=500, help_text="List description")

    # Stats (denormalized)
    contact_count = models.PositiveIntegerField(default=0, help_text="Denormalized: number of contacts in list")

    class Meta:
        db_table = 'contact_lists'
        ordering = ['name']
        indexes = [
            models.Index(fields=['owner']),
            models.Index(fields=['organization']),
            models.Index(fields=['uuid']),
        ]
        constraints = [
            # Personal lists: unique name per owner
            models.UniqueConstraint(
                fields=['owner', 'name'],
                condition=models.Q(organization__isnull=True),
                name='unique_personal_contact_list_name',
            ),
            # Org lists: unique name per organization
            models.UniqueConstraint(
                fields=['organization', 'name'],
                condition=models.Q(organization__isnull=False),
                name='unique_org_contact_list_name',
            ),
        ]
        verbose_name = 'Contact List'
        verbose_name_plural = 'Contact Lists'

    @classmethod
    def get_or_create_for_user(cls, user):
        """
        Get or create the single personal contact list for a user.

        Each organizer has exactly one personal list, auto-created on first access.
        """
        contact_list, created = cls.objects.get_or_create(
            owner=user,
            organization__isnull=True,
            defaults={
                'name': 'My Contacts',
            },
        )
        return contact_list

    @property
    def is_shared(self):
        """Check if this is an organization-shared list."""
        return self.organization_id is not None

    def __str__(self):
        return f"{self.name} ({self.contact_count})"

    def update_contact_count(self):
        """Update denormalized contact count."""
        self.contact_count = self.contacts.count()
        self.save(update_fields=['contact_count', 'updated_at'])

    def merge_into(self, target_list):
        """Merge this list into another list."""
        # Must be same owner OR same organization
        same_owner = target_list.owner == self.owner
        same_org = self.organization_id and target_list.organization_id and self.organization_id == target_list.organization_id
        if not (same_owner or same_org):
            raise ValueError("Cannot merge lists from different owners or organizations")

        for contact in self.contacts.all():
            if not Contact.objects.filter(contact_list=target_list, email=contact.email).exists():
                contact.contact_list = target_list
                contact.save(update_fields=['contact_list', 'updated_at'])

        target_list.update_contact_count()
        self.delete()

    def duplicate(self, new_name=None):
        """Create a copy of this list with all contacts."""
        new_list = ContactList.objects.create(
            owner=self.owner,
            organization=self.organization,  # Preserve org context
            name=new_name or f"{self.name} (Copy)",
            description=self.description,
        )

        for contact in self.contacts.all():
            new_contact = Contact.objects.create(
                contact_list=new_list,
                email=contact.email,
                full_name=contact.full_name,
                professional_title=contact.professional_title,
                organization_name=contact.organization_name,
                phone=contact.phone,
                notes=contact.notes,
            )
            new_contact.tags.set(contact.tags.all())

        new_list.update_contact_count()
        return new_list


class Contact(BaseModel):
    """
    An individual contact in a contact list.

    Contacts can optionally be linked to a User account if
    the contact has registered on the platform.
    """

    contact_list = models.ForeignKey(ContactList, on_delete=models.CASCADE, related_name='contacts')

    # Optional link to user account
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contact_records',
        help_text="Linked user account (if they've signed up)",
    )

    # Contact info
    email = LowercaseEmailField(db_index=True, help_text="Contact email (canonical, lowercase)")
    full_name = models.CharField(max_length=255, help_text="Full name")
    professional_title = models.CharField(max_length=255, blank=True, help_text="Professional title")
    organization_name = models.CharField(max_length=255, blank=True, help_text="Organization/company")
    phone = models.CharField(max_length=50, blank=True, help_text="Phone number")

    # Additional info
    notes = models.TextField(blank=True, max_length=2000, help_text="Private notes about contact")

    # Tags (many-to-many)
    tags = models.ManyToManyField('Tag', blank=True, related_name='contacts')

    # Source tracking
    source = models.CharField(max_length=50, blank=True, help_text="How contact was added (manual, csv, registration)")
    added_from_event = models.ForeignKey(
        'events.Event',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Event this contact was added from (if applicable)",
    )

    # Engagement stats (denormalized)
    events_invited_count = models.PositiveIntegerField(default=0, help_text="Number of events invited to")
    events_attended_count = models.PositiveIntegerField(default=0, help_text="Number of events attended")
    last_invited_at = models.DateTimeField(null=True, blank=True)
    last_attended_at = models.DateTimeField(null=True, blank=True)

    # Email preferences
    email_opted_out = models.BooleanField(default=False, help_text="Contact has opted out of emails")
    email_bounced = models.BooleanField(default=False, help_text="Email has bounced")

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
        """Link this contact to a user account."""
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
            events_invited_count=F('events_invited_count') + 1, last_invited_at=timezone.now()
        )

    def record_attendance(self):
        """Record event attendance."""
        from django.db.models import F
        from django.utils import timezone

        Contact.objects.filter(pk=self.pk).update(
            events_attended_count=F('events_attended_count') + 1, last_attended_at=timezone.now()
        )

    def move_to_list(self, target_list):
        """Move contact to another list."""
        if target_list.owner != self.contact_list.owner:
            raise ValueError("Cannot move contact to list from different owner")

        if Contact.objects.filter(contact_list=target_list, email=self.email).exists():
            raise ValueError("Contact with this email already exists in target list")

        old_list = self.contact_list
        self.contact_list = target_list
        self.save(update_fields=['contact_list', 'updated_at'])

        old_list.update_contact_count()
        target_list.update_contact_count()


class Tag(BaseModel):
    """
    Tag for categorizing contacts.

    Tags are owned by a user and optionally shared with an organization.
    If organization is set, all org members can use the tag.
    """

    owner = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='tags',
        help_text="User who created this tag",
    )
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tags',
        help_text="If set, tag is shared with all org members",
    )

    name = models.CharField(max_length=50, help_text="Tag name")
    color = models.CharField(max_length=7, default='#6B7280', help_text="Hex color for display")
    description = models.CharField(max_length=200, blank=True, help_text="Tag description")

    # Stats (denormalized)
    contact_count = models.PositiveIntegerField(default=0, help_text="Number of contacts with this tag")

    class Meta:
        db_table = 'tags'
        ordering = ['name']
        indexes = [
            models.Index(fields=['owner']),
            models.Index(fields=['organization']),
        ]
        constraints = [
            # Personal tags: unique name per owner
            models.UniqueConstraint(
                fields=['owner', 'name'],
                condition=models.Q(organization__isnull=True),
                name='unique_personal_tag_name',
            ),
            # Org tags: unique name per organization
            models.UniqueConstraint(
                fields=['organization', 'name'],
                condition=models.Q(organization__isnull=False),
                name='unique_org_tag_name',
            ),
        ]
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'

    def __str__(self):
        return self.name

    @property
    def is_shared(self):
        """Check if this is an organization-shared tag."""
        return self.organization_id is not None

    def update_contact_count(self):
        """Update denormalized contact count."""
        self.contact_count = self.contacts.count()
        self.save(update_fields=['contact_count', 'updated_at'])

    def merge_into(self, target_tag):
        """Merge this tag into another tag."""
        # Must be same owner OR same organization
        same_owner = target_tag.owner == self.owner
        same_org = self.organization_id and target_tag.organization_id and self.organization_id == target_tag.organization_id
        if not (same_owner or same_org):
            raise ValueError("Cannot merge tags from different owners or organizations")

        for contact in self.contacts.all():
            contact.tags.add(target_tag)

        target_tag.update_contact_count()
        self.delete()
