"""
Business logic services for Organizations app.

Services:
- OrganizationLinkingService: Link individual organizer accounts to organizations
"""

from django.utils import timezone
from django.utils.text import slugify


class OrganizationLinkingService:
    """
    Service for linking individual organizer accounts to organizations.

    Handles:
    - Creating an organization from an individual organizer's account
    - Linking an existing organizer's events/templates to an organization
    - Tracking linked accounts for billing and audit purposes
    """

    @staticmethod
    def create_org_from_organizer(user, name=None, slug=None):
        """
        Create a new organization from an individual organizer's account.

        Transfers all their events and certificate templates to the new organization.
        The user becomes the owner of the new organization.

        Args:
            user: The organizer User instance
            name: Optional organization name (defaults to user's organization_name or full_name)
            slug: Optional slug (defaults to user's organizer_slug or slugified name)

        Returns:
            Organization: The newly created organization
        """
        from .models import Organization, OrganizationMembership, OrganizationSubscription

        # Determine organization name
        org_name = name or user.organization_name or f"{user.full_name}'s Organization"

        # Determine slug
        org_slug = slug or user.organizer_slug or slugify(user.full_name)

        # Create organization
        organization = Organization.objects.create(
            name=org_name,
            slug=org_slug,
            description=user.organizer_bio or '',
            website=user.organizer_website or '',
            logo_url=user.organizer_logo_url or '',
            created_by=user,
        )

        # Create owner membership
        OrganizationMembership.objects.create(
            organization=organization,
            user=user,
            role=OrganizationMembership.Role.ADMIN,
            accepted_at=timezone.now(),
            linked_from_individual=True,
            linked_at=timezone.now(),
        )

        # Create free subscription
        OrganizationSubscription.create_for_organization(organization)

        # Link existing data
        OrganizationLinkingService._link_user_data(user, organization)

        # Update counts
        organization.update_counts()

        return organization

    @staticmethod
    def link_organizer_to_org(user, organization, role='manager', invited_by=None):
        """
        Link an individual organizer's data to an existing organization.

        This allows organizers to join an organization and bring their
        existing events and templates with them.

        Args:
            user: The organizer User instance
            organization: The Organization to link to
            role: Role to assign (default: 'manager')
            invited_by: User who invited/added this organizer

        Returns:
            dict: Summary of linked data
        """
        from .models import OrganizationMembership

        # Create or update membership
        membership, created = OrganizationMembership.objects.get_or_create(
            organization=organization,
            user=user,
            defaults={
                'role': role,
                'accepted_at': timezone.now(),
                'invited_by': invited_by,
                'linked_from_individual': True,
                'linked_at': timezone.now(),
            },
        )

        if not created and not membership.linked_from_individual:
            # Update existing membership with linking info
            membership.linked_from_individual = True
            membership.linked_at = timezone.now()
            membership.save(update_fields=['linked_from_individual', 'linked_at', 'updated_at'])

        # Link data
        result = OrganizationLinkingService._link_user_data(user, organization)
        result['membership'] = membership
        result['membership_created'] = created

        # Update counts
        organization.update_counts()

        # Update subscription seat usage
        if hasattr(organization, 'subscription'):
            organization.subscription.update_seat_usage()

        return result

    @staticmethod
    def _link_user_data(user, organization):
        """
        Internal method to link a user's events and templates to an organization.

        Args:
            user: The User whose data to link
            organization: The Organization to link to

        Returns:
            dict: Count of linked items
        """
        events_transferred = 0
        templates_transferred = 0

        # Transfer events that don't already belong to an organization
        try:
            from events.models import Event

            events_transferred = Event.objects.filter(
                owner=user, organization__isnull=True
            ).update(organization=organization)
        except (ImportError, Exception):
            # Event model may not have organization field yet
            pass

        # Transfer certificate templates
        try:
            from certificates.models import CertificateTemplate

            templates_transferred = CertificateTemplate.objects.filter(
                owner=user, organization__isnull=True
            ).update(organization=organization)
        except (ImportError, Exception):
            # CertificateTemplate may not have organization field yet
            pass

        # Update organization counts
        organization.events_count = getattr(organization, 'events', type('', (), {'count': lambda: 0})()).count()
        organization.save(update_fields=['events_count', 'updated_at'])

        return {
            'events_transferred': events_transferred,
            'templates_transferred': templates_transferred,
        }

    @staticmethod
    def get_linkable_data_summary(user):
        """
        Get a summary of data that would be linked for a user.

        Useful for showing a preview before linking.

        Args:
            user: The User to check

        Returns:
            dict: Summary of linkable data
        """
        events_count = 0
        templates_count = 0

        try:
            from events.models import Event

            events_count = Event.objects.filter(
                owner=user, organization__isnull=True
            ).count()
        except (ImportError, Exception):
            pass

        try:
            from certificates.models import CertificateTemplate

            templates_count = CertificateTemplate.objects.filter(
                owner=user, organization__isnull=True
            ).count()
        except (ImportError, Exception):
            pass

        return {
            'events_count': events_count,
            'templates_count': templates_count,
            'has_linkable_data': events_count > 0 or templates_count > 0,
        }
