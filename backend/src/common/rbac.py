"""
Declarative Role-Based Access Control (RBAC) using Django Groups.

This module provides a decorator-based system for declaring which groups
(roles) can access which views. The @roles() decorator automatically:
1. Registers the view in ROUTE_REGISTRY for manifest generation
2. Adds RoleBasedPermission to enforce the declared roles via Django Groups

Groups (created via data migration):
- learner: Can attend events, view courses, earn certificates
- educator: Can create/manage events, issue certificates, manage contacts
- course_manager: Can create/manage courses, manage LMS content
- admin: Full system access (also uses is_staff)

Users can belong to multiple groups simultaneously.

Usage:
    from common.rbac import roles

    @roles('educator', 'admin', route_name='events')
    class EventViewSet(ModelViewSet):
        ...

    @roles('public', route_name='public_events')
    class PublicEventViewSet(ReadOnlyModelViewSet):
        ...
"""

from typing import Literal

from rest_framework import permissions

# Valid role types (map to Django Group names)
Role = Literal["learner", "educator", "course_manager", "instructor", "admin", "public"]

# Group names used by the system
SYSTEM_GROUPS = {"learner", "educator", "course_manager", "instructor", "admin"}

# Global registry: route_name -> dict with roles
# Used by the manifest endpoint to return allowed routes per user
ROUTE_REGISTRY: dict[str, dict] = {}


def roles(*allowed_roles: Role, route_name: str | None = None):
    """
    Decorator to declare which groups (roles) can access a view.

    Args:
        *allowed_roles: Variable number of role strings ('learner', 'educator', 'admin', 'public')
        route_name: Optional route identifier for frontend mapping. Defaults to class name.

    Example:
        @roles('educator', 'admin', route_name='events')
        class EventViewSet(ModelViewSet):
            ...
    """

    def decorator(cls):
        name = route_name or cls.__name__

        # Register in global registry
        ROUTE_REGISTRY[name] = {"roles": set(allowed_roles)}

        # Store on class for permission checking
        cls._allowed_roles = set(allowed_roles)
        cls._route_name = name

        # Prepend RoleBasedPermission to existing permission classes
        existing = list(getattr(cls, "permission_classes", []))
        cls.permission_classes = [RoleBasedPermission, *existing]

        return cls

    return decorator


class RoleBasedPermission(permissions.BasePermission):
    """
    Permission class that enforces roles via Django Groups.

    Checks user's group membership against the allowed roles declared
    via the @roles decorator.
    """

    message = "You don't have permission to access this resource."

    def has_permission(self, request, view):
        allowed_roles = getattr(view, "_allowed_roles", set())

        # Public routes are accessible to everyone
        if "public" in allowed_roles:
            return True

        # Must be authenticated for non-public routes
        if not request.user.is_authenticated:
            return False

        # Admin/staff always have access when 'admin' is in allowed roles
        if request.user.is_staff and "admin" in allowed_roles:
            return True

        # Check user's groups against allowed roles
        user_groups = set(request.user.groups.values_list("name", flat=True))
        return bool(user_groups & allowed_roles)


def get_allowed_routes_for_user(user) -> list[str]:
    """
    Get list of route names that a user can access based on their groups.

    Args:
        user: The user object (can be anonymous)

    Returns:
        List of route_name strings the user can access
    """
    if not user.is_authenticated:
        return [route for route, config in ROUTE_REGISTRY.items() if "public" in config["roles"]]

    is_admin = user.is_staff
    user_groups = set(user.groups.values_list("name", flat=True))

    allowed = []
    for route, config in ROUTE_REGISTRY.items():
        route_roles = config["roles"]

        if "public" in route_roles:
            allowed.append(route)
        elif is_admin and "admin" in route_roles:
            allowed.append(route)
        elif user_groups & route_roles:
            allowed.append(route)

    return allowed


def get_features_for_user(user) -> dict[str, bool]:
    """
    Get feature flags for a user based on their Django permissions.

    Uses user.has_perm() which checks both direct permissions
    and permissions inherited from groups.

    Args:
        user: The user object

    Returns:
        Dictionary of feature_name -> enabled boolean
    """
    if not user.is_authenticated:
        return {
            "create_events": False,
            "create_courses": False,
            "manage_certificates": False,
            "manage_users": False,
            "configure_billing": False,
            "browse_events": True,
            "register_for_events": True,
            "view_own_registrations": True,
            "view_own_certificates": True,
        }

    return {
        "create_events": user.has_perm("events.can_create_event"),
        "create_courses": user.has_perm("learning.can_create_course"),
        "manage_certificates": user.has_perm("certificates.can_issue_certificate"),
        "manage_users": user.has_perm("accounts.can_manage_users"),
        "configure_billing": user.has_perm("billing.can_configure_billing"),
        "browse_events": True,
        "register_for_events": True,
        "view_own_registrations": True,
        "view_own_certificates": True,
    }
