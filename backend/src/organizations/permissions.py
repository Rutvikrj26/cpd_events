"""
DRF permissions for Organizations app.
"""

from rest_framework.permissions import BasePermission

from .models import OrganizationMembership


class IsOrganizationMember(BasePermission):
    """Check if user is a member of the organization."""

    def has_permission(self, request, view):
        """Check if user is authenticated."""
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Check if user is a member of the organization."""
        organization = self._get_organization(obj)
        if not organization:
            return False
        return organization.memberships.filter(user=request.user, is_active=True).exists()

    def _get_organization(self, obj):
        """Get organization from object (handles both Organization and nested objects)."""
        from .models import Organization

        if isinstance(obj, Organization):
            return obj
        if hasattr(obj, 'organization'):
            return obj.organization
        return None


class OrganizationRolePermission(BasePermission):
    """
    Check if user has required role in the organization.

    Role hierarchy (each role includes permissions of roles below):
    - owner: Full control, billing, can delete org
    - admin: Manage members, events, courses, templates
    - manager: Create/edit events & courses
    - member: View only
    """

    ROLE_HIERARCHY = {
        'owner': ['owner', 'admin', 'manager', 'member'],
        'admin': ['admin', 'manager', 'member'],
        'manager': ['manager', 'member'],
        'member': ['member'],
    }

    # Action -> required role mapping
    ACTION_ROLES = {
        # Organization management
        'delete_organization': 'owner',
        'manage_billing': 'owner',
        'update_organization': 'admin',
        # Member management
        'manage_members': 'admin',
        'invite_member': 'admin',
        'update_member_role': 'admin',
        'remove_member': 'admin',
        # Content creation
        'create_event': 'manager',
        'edit_event': 'manager',
        'create_course': 'manager',
        'edit_course': 'manager',
        'create_template': 'manager',
        # Viewing
        'view_reports': 'manager',
        'view_organization': 'member',
        'view_members': 'member',
    }

    def has_organization_permission(self, user, organization, action):
        """
        Check if user has permission for the specified action on the organization.

        Args:
            user: The User instance
            organization: The Organization instance
            action: Action key from ACTION_ROLES

        Returns:
            bool: True if user has permission
        """
        try:
            membership = OrganizationMembership.objects.get(
                organization=organization, user=user, is_active=True
            )
        except OrganizationMembership.DoesNotExist:
            return False

        required_role = self.ACTION_ROLES.get(action, 'owner')  # Default to owner if unknown
        allowed_roles = self.ROLE_HIERARCHY.get(membership.role, [])

        return required_role in allowed_roles


class IsOrgOwner(BasePermission):
    """Check if user is an owner of the organization."""

    def has_object_permission(self, request, view, obj):
        from .models import Organization

        if isinstance(obj, Organization):
            organization = obj
        elif hasattr(obj, 'organization'):
            organization = obj.organization
        else:
            return False

        return organization.memberships.filter(
            user=request.user, role='owner', is_active=True
        ).exists()


class IsOrgAdmin(BasePermission):
    """Check if user is an admin or owner of the organization."""

    def has_object_permission(self, request, view, obj):
        from .models import Organization

        if isinstance(obj, Organization):
            organization = obj
        elif hasattr(obj, 'organization'):
            organization = obj.organization
        else:
            return False

        return organization.memberships.filter(
            user=request.user, role__in=['owner', 'admin'], is_active=True
        ).exists()


class IsOrgManager(BasePermission):
    """Check if user has manager-level access (manager, admin, or owner)."""

    def has_object_permission(self, request, view, obj):
        from .models import Organization

        if isinstance(obj, Organization):
            organization = obj
        elif hasattr(obj, 'organization'):
            organization = obj.organization
        else:
            return False

        return organization.memberships.filter(
            user=request.user, role__in=['owner', 'admin', 'manager'], is_active=True
        ).exists()


def get_user_organizations(user, role_filter=None):
    """
    Get all organizations the user is a member of.

    Args:
        user: The User instance
        role_filter: Optional list of roles to filter by

    Returns:
        QuerySet of Organizations
    """
    from .models import Organization

    memberships = OrganizationMembership.objects.filter(user=user, is_active=True)

    if role_filter:
        memberships = memberships.filter(role__in=role_filter)

    org_ids = memberships.values_list('organization_id', flat=True)
    return Organization.objects.filter(id__in=org_ids, is_active=True)
