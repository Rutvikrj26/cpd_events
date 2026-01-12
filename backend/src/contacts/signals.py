"""
Contacts app signals - handle registration-to-contact linking.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='registrations.Registration')
def link_registration_to_contact(sender, instance, created, **kwargs):
    """
    When a registration is confirmed, find or create a contact record.

    Contacts are created in the organizer's default contact list.
    If a contact with matching email already exists, just update invite counts.
    """
    from django.utils import timezone

    from contacts.models import Contact, ContactList

    # Only process confirmed registrations
    if instance.status != 'confirmed':
        return

    # Get the event organizer
    organizer = instance.event.owner
    if not organizer:
        return

    # Get or create default contact list for organizer
    default_list = ContactList.get_or_create_for_user(organizer)

    # Check if contact already exists in any of organizer's lists
    existing_contact = Contact.objects.filter(contact_list__owner=organizer, email__iexact=instance.email).first()

    if existing_contact:
        # Update invite count
        existing_contact.record_invite()

        # Link to user if not already linked
        if instance.user and not existing_contact.user:
            existing_contact.link_to_user(instance.user)
    else:
        # Create new contact
        Contact.objects.create(
            contact_list=default_list,
            email=instance.email,
            full_name=instance.full_name,
            professional_title=instance.professional_title or '',
            organization_name=instance.organization_name or '',
            user=instance.user,
            source='registration',
            added_from_event=instance.event,
            events_invited_count=1,
            last_invited_at=timezone.now(),
        )
        default_list.update_contact_count()


@receiver(post_save, sender='registrations.Registration')
def update_contact_attendance(sender, instance, created, **kwargs):
    """
    Update contact attendance stats when registration attendance is confirmed.

    This is called when a registration's attendance_eligible changes to True.
    """
    from contacts.models import Contact

    # Skip if not eligible for attendance
    if not instance.attendance_eligible:
        return

    # Find contact by email in organizer's lists
    organizer = instance.event.owner
    if not organizer:
        return

    contact = Contact.objects.filter(contact_list__owner=organizer, email__iexact=instance.email).first()

    if contact:
        # Check if this is a new attendance (not already counted)
        # We use a simple approach: check if last_attended_at < event start
        if contact.last_attended_at is None or contact.last_attended_at < instance.event.starts_at:
            contact.record_attendance()
