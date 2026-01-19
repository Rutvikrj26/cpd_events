"""
Declarative Role-Based Access Control (RBAC).

This module provides a decorator-based system for declaring which roles
can access which views. The @roles() decorator automatically:
1. Registers the view in ROUTE_REGISTRY for manifest generation
2. Adds RoleBasedPermission to enforce the declared roles

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

# Valid role types
Role = Literal["attendee", "organizer", "course_manager", "instructor", "admin", "public"]

# Global registry: route_name -> dict with roles and allowed plans
# This is used by the manifest endpoint to return allowed routes per user
ROUTE_REGISTRY: dict[str, dict] = {}

# Plan hierarchy for capability inheritance
PLAN_HIERARCHY = {
    "attendee": 0,
    "organizer": 1,
    "lms": 1,
    "organization": 2,
}


def get_effective_plan(user) -> str:
    """
    Get user's effective plan based on personal subscription and org membership.

    A user's capabilities can come from their personal subscription
    OR from being a member of an organization.

    Returns:
        str: The effective plan ('attendee', 'organizer', 'lms', 'organization')
    """
    # Start with personal plan
    subscription = getattr(user, "subscription", None)
    personal_plan = getattr(subscription, "plan", "attendee") if subscription else "attendee"
    personal_level = PLAN_HIERARCHY.get(personal_plan, 0)

    # Check if user is a member of any organization
    from organizations.permissions import get_user_organizations

    user_orgs = get_user_organizations(user)

    if user_orgs.exists():
        # Org members inherit 'organization' tier capabilities
        org_level = PLAN_HIERARCHY.get("organization", 2)
        # Return the higher of personal plan or org-derived plan
        if org_level > personal_level:
            return "organization"

    return personal_plan


def roles(*allowed_roles: Role, route_name: str | None = None, plans: list[str] | None = None):
    """
    Decorator to declare which roles can access a view.

    Args:
        *allowed_roles: Variable number of role strings ('attendee', 'organizer', 'admin', 'public')
        route_name: Optional route identifier for frontend mapping. Defaults to class name.
        plans: Optional list of subscription plans that allow access (e.g. ['organization']).
               If None, all plans defined by the role are allowed.

    Example:
        @roles('organizer', 'admin', route_name='events')
        class EventViewSet(ModelViewSet):
            ...

        @roles('organizer', plans=['organization'])
        class OrganizationViewSet(ModelViewSet):
            ...
    """

    def decorator(cls):
        # Determine route name (use provided or fall back to class name)
        name = route_name or cls.__name__

        # Register in global registry
        ROUTE_REGISTRY[name] = {"roles": set(allowed_roles), "plans": set(plans) if plans else set()}

        # Store on class for permission checking
        cls._allowed_roles = set(allowed_roles)
        cls._allowed_plans = set(plans) if plans else set()
        cls._route_name = name

        # Prepend RoleBasedPermission to existing permission classes
        existing = list(getattr(cls, "permission_classes", []))
        cls.permission_classes = [RoleBasedPermission, *existing]

        return cls

    return decorator


class RoleBasedPermission(permissions.BasePermission):
    """
    Permission class that enforces roles declared via @roles decorator.

    Checks are performed in has_permission (route-level).
    Object-level permissions should still be handled by other permission classes.
    """

    message = "You don't have permission to access this resource."

    def has_permission(self, request, view):
        """Check if the user's role is in the allowed roles for this view."""
        allowed_roles = getattr(view, "_allowed_roles", set())
        allowed_plans = getattr(view, "_allowed_plans", set())

        # Public routes are accessible to everyone
        if "public" in allowed_roles:
            return True

        # Must be authenticated for non-public routes
        if not request.user.is_authenticated:
            return False

        # Admin/staff override when 'admin' is in allowed roles
        # Note: We check this early to bypass plan checks for admins
        if request.user.is_staff and "admin" in allowed_roles:
            return True

        # Check user's role against allowed roles
        user_role = getattr(request.user, "account_type", None)
        if user_role not in allowed_roles:
            org_roles = self._get_allowed_org_roles(allowed_roles)
            if not org_roles:
                return False
            if not self._has_org_role(request.user, org_roles):
                return False

        # If strict plans are defined, check user's effective plan
        if allowed_plans:
            # Use effective plan (considers org membership)
            user_plan = get_effective_plan(request.user)

            if user_plan not in allowed_plans:
                self.message = "Your subscription plan does not allow access to this resource."
                return False

        return True

    def _get_allowed_org_roles(self, allowed_roles: set[str]) -> set[str]:
        """
        Map allowed roles to organization membership roles.
        Organization admins should be allowed wherever organizer or course_manager is allowed.
        """
        org_roles = {role for role in allowed_roles if role in {"organizer", "course_manager", "instructor"}}
        if "organizer" in allowed_roles or "course_manager" in allowed_roles:
            org_roles.add("admin")
        # Do not map allowed 'admin' (staff) to org admin unless explicitly allowed above.
        return org_roles

    def _has_org_role(self, user, org_roles: set[str]) -> bool:
        from organizations.models import OrganizationMembership

        return OrganizationMembership.objects.filter(
            user=user,
            is_active=True,
            role__in=org_roles,
        ).exists()


def get_allowed_routes_for_user(user) -> list[str]:
    """
    Get list of route names that a user can access based on their role.

    Args:
        user: The user object (can be anonymous)

    Returns:
        List of route_name strings the user can access
    """
    if not user.is_authenticated:
        # Anonymous users can only access public routes
        return [route for route, config in ROUTE_REGISTRY.items() if "public" in config["roles"]]

    user_role = getattr(user, "account_type", None)
    is_admin = user.is_staff

    # Use effective plan (considers org membership)
    user_plan = get_effective_plan(user)

    allowed = []
    for route, config in ROUTE_REGISTRY.items():
        roles = config["roles"]
        plans = config["plans"]

        if "public" in roles or is_admin and "admin" in roles:
            allowed.append(route)
        elif user_role in roles:
            # If plans are restricted, check effective plan matches
            if plans and user_plan not in plans:
                continue
            allowed.append(route)

    return allowed


def get_features_for_user(user) -> dict[str, bool]:
    """
    Get feature flags for a user based on their role.

    These are high-level capabilities, not tied to specific routes.

    Args:
        user: The user object

    Returns:
        Dictionary of feature_name -> enabled boolean
    """
    if not user.is_authenticated:
        return {
            "create_events": False,
            "manage_certificates": False,
            "view_billing": False,
            "browse_events": True,
            "register_for_events": True,
        }

    role = getattr(user, "account_type", "attendee")
    is_event_creator = role in ("organizer", "admin") or user.is_staff
    is_course_creator = role in ("course_manager", "admin") or user.is_staff

    # Get user plan
    subscription = getattr(user, "subscription", None)
    user_plan = getattr(subscription, "plan", "attendee") if subscription else "attendee"
    effective_plan = get_effective_plan(user)

    # Check if user is already part of an organization
    from organizations.permissions import get_user_organizations

    user_organizations = get_user_organizations(user)
    has_organization = user_organizations.exists()

    return {
        "create_events": is_event_creator and effective_plan in ("organizer", "organization"),
        "create_courses": is_course_creator and effective_plan in ("lms", "organization"),
        "manage_certificates": is_event_creator,
        "view_billing": role in ("organizer", "course_manager", "admin"),
        "browse_events": True,
        "register_for_events": True,
        "view_own_registrations": True,
        "view_own_certificates": True,
        "can_create_organization": is_event_creator
        and not has_organization
        and (effective_plan == "organization" or user.is_staff),
    }
