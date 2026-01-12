"""
Signals for the organizations app.
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Organization, OrganizationMembership, OrganizationSubscription


@receiver(post_save, sender=Organization)
def create_organization_subscription(sender, instance, created, **kwargs):
    """
    Ensure every organization has a subscription.
    """
    if created and not hasattr(instance, 'subscription'):
        OrganizationSubscription.create_for_organization(instance)


@receiver(post_save, sender=OrganizationMembership)
@receiver(post_delete, sender=OrganizationMembership)
def update_organization_counts(sender, instance, **kwargs):
    """
    Update organization counts and subscription seat usage when a membership
    is saved or deleted.
    """
    organization = instance.organization

    # Update active member count on the organization model
    organization.update_counts()

    # Update subscription seat usage if a subscription exists
    if hasattr(organization, 'subscription'):
        organization.subscription.update_seat_usage()
