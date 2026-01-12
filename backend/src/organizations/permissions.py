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

    Role hierarchy (no implicit inheritance):
    - admin: Manage org settings, members, templates
    - organizer: Create/edit events and contacts
    - course_manager: Create/edit courses and manage instructors
    - instructor: Limited to assigned course
    """

    # Role hierarchy: higher roles include permissions of lower roles
    # Note: Roles are now parallel (admin, organizer, course_manager, instructor)
    # Each role has specific permissions, no inheritance except all can view
    ROLE_HIERARCHY = {
        'admin': ['admin'],
        'organizer': ['organizer'],
        'course_manager': ['course_manager'],
        'instructor': ['instructor'],
    }

    # Action -> required role mapping
    # Action -> required role mapping
    ACTION_ROLES = {
        # Organization management (Admin only)
        'update_organization': 'admin',
        'manage_templates': 'admin',
        # Member management (Admin + Course Manager)
        # Note: Views must strictly limit Course Manager to only managing 'instructor' role
        'manage_members': ['admin', 'course_manager'],
        'invite_member': ['admin', 'course_manager'],
        'update_member_role': ['admin', 'course_manager'],
        'remove_member': ['admin', 'course_manager'],
        # Event management (Organizer only)
        'create_event': 'organizer',
        'edit_event': 'organizer',
        'manage_contacts': 'organizer',
        # Course management (Course Manager only)
        'create_course': 'course_manager',
        'edit_course': 'course_manager',
        'manage_all_courses': 'course_manager',
        # Instructor (limited to assigned course)
        'manage_assigned_course': 'instructor',
        # Viewing (all roles)
        'view_organization': ['admin', 'organizer', 'course_manager', 'instructor'],
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
            membership = OrganizationMembership.objects.get(organization=organization, user=user, is_active=True)
        except OrganizationMembership.DoesNotExist:
            return False

        required_roles = self.ACTION_ROLES.get(action, ['admin'])
        if isinstance(required_roles, str):
            required_roles = [required_roles]

        # Check if user's role is in the required roles list
        return membership.role in required_roles


class IsOrgOwner(BasePermission):
    """Check if user is an admin of the organization."""

    def has_object_permission(self, request, view, obj):
        from .models import Organization

        if isinstance(obj, Organization):
            organization = obj
        elif hasattr(obj, 'organization'):
            organization = obj.organization
        else:
            return False

        return organization.memberships.filter(user=request.user, role='admin', is_active=True).exists()


class IsOrgAdmin(BasePermission):
    """Check if user is an admin of the organization."""

    def has_object_permission(self, request, view, obj):
        from .models import Organization

        if isinstance(obj, Organization):
            organization = obj
        elif hasattr(obj, 'organization'):
            organization = obj.organization
        else:
            return False

        return organization.memberships.filter(user=request.user, role='admin', is_active=True).exists()


class IsOrgManager(BasePermission):
    """Check if user has manager-level access (admin, organizer, or course manager)."""

    def has_object_permission(self, request, view, obj):
        from .models import Organization

        if isinstance(obj, Organization):
            organization = obj
        elif hasattr(obj, 'organization'):
            organization = obj.organization
        else:
            return False

        return organization.memberships.filter(
            user=request.user, role__in=['admin', 'organizer', 'course_manager'], is_active=True
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
