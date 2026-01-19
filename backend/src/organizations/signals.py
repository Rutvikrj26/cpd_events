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
    if created and not hasattr(instance, "subscription"):
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
    if hasattr(organization, "subscription"):
        organization.subscription.update_seat_usage()


@receiver(post_save, sender=OrganizationMembership)
@receiver(post_delete, sender=OrganizationMembership)
def handle_admin_membership_change(sender, instance, **kwargs):
    """
    Auto-downgrade user if they're no longer an org admin anywhere.

    When a user loses their last admin role (either by membership deletion,
    deactivation, or role change), we downgrade them based on their subscription.
    """
    # Only handle admin role changes
    if instance.role != OrganizationMembership.Role.ADMIN:
        return

    user = instance.user
    if not user or user.account_type != "admin":
        return

    # Check if user is still admin in any other active org
    still_admin = (
        OrganizationMembership.objects.filter(
            user=user,
            role=OrganizationMembership.Role.ADMIN,
            is_active=True,
        )
        .exclude(pk=instance.pk if kwargs.get("created") is False else None)
        .exists()
    )

    # If no longer admin anywhere, downgrade
    if not still_admin:
        user.downgrade_from_admin()
