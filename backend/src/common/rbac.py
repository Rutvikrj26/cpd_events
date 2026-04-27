"""
Declarative Role-Based Access Control (RBAC) using Django Groups.

This module provides a decorator-based system for declaring which groups
(roles) can access which views. The @roles() decorator automatically:
1. Registers the view in ROUTE_REGISTRY for manifest generation
2. Adds RoleBasedPermission to enforce the declared roles via Django Groups

Groups (created via data migration / setup_groups):
- learner: Can attend events, view courses, earn certificates
- organizer: Can create/manage events, issue event certificates, manage contacts
- instructor: Can create/manage courses + programs, issue course certificates,
  schedule live sessions inside courses
- admin: Full institution administrator access (admin group membership)

Users can belong to multiple groups simultaneously.

Usage:
    from common.rbac import roles

    @roles('organizer', 'admin', route_name='events')
    class EventViewSet(ModelViewSet):
        ...

    @roles('public', route_name='public_events')
    class PublicEventViewSet(ReadOnlyModelViewSet):
        ...
"""

from typing import Literal

from rest_framework import permissions

# Valid role types (map to Django Group names)
Role = Literal["learner", "organizer", "instructor", "admin", "public"]

# Group names used by the system
SYSTEM_GROUPS = {"learner", "organizer", "instructor", "admin"}

# Global registry: route_name -> dict with roles
# Used by the manifest endpoint to return allowed routes per user
ROUTE_REGISTRY: dict[str, dict] = {}


def roles(*allowed_roles: Role, route_name: str | None = None):
    """
    Decorator to declare which groups (roles) can access a view.

    Args:
        *allowed_roles: Variable number of role strings ('learner', 'organizer', 'instructor', 'admin', 'public')
        route_name: Optional route identifier for frontend mapping. Defaults to class name.

    Example:
        @roles('organizer', 'admin', route_name='events')
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

        # Check user's groups against allowed roles. `admin` group membership
        # is the only gate for admin-only routes; `is_staff` is not consulted.
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

    user_groups = set(user.groups.values_list("name", flat=True))

    allowed = []
    for route, config in ROUTE_REGISTRY.items():
        route_roles = config["roles"]

        if "public" in route_roles:
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
            "manage_contacts": False,
            "manage_badges": False,
            "manage_video": False,
            "manage_users": False,
            "configure_billing": False,
            "browse_events": True,
            "register_for_events": True,
            "view_own_registrations": True,
            "view_own_certificates": True,
        }

    is_admin = user.groups.filter(name="admin").exists()
    is_organizer = user.groups.filter(name__in=["organizer", "admin"]).exists()
    is_instructor = user.groups.filter(name__in=["instructor", "admin"]).exists()
    is_creator = is_organizer or is_instructor

    # Group membership is the source of truth (matches the DRF permission
    # classes in common/permissions.py — IsOrganizerOrAdmin etc.). The
    # `has_perm` fallback lets per-user grants from Django admin still flow
    # through for any institution that hasn't run setup_groups yet.
    return {
        "create_events": is_organizer or user.has_perm("events.can_create_event"),
        "create_courses": is_creator or user.has_perm("learning.can_create_course"),
        "manage_certificates": is_creator or user.has_perm("certificates.can_issue_certificate"),
        "manage_contacts": is_organizer,
        "manage_badges": is_creator,
        "manage_video": is_creator,
        "manage_users": is_admin or user.has_perm("accounts.can_manage_users"),
        "configure_billing": is_admin or user.has_perm("billing.can_configure_billing"),
        "browse_events": True,
        "register_for_events": True,
        "view_own_registrations": True,
        "view_own_certificates": True,
    }
