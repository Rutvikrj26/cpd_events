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
from typing import Literal, Set

from rest_framework import permissions

# Valid role types
Role = Literal['attendee', 'organizer', 'admin', 'public']

# Global registry: route_name -> dict with roles and allowed plans
# This is used by the manifest endpoint to return allowed routes per user
ROUTE_REGISTRY: dict[str, dict] = {}


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
        ROUTE_REGISTRY[name] = {
            'roles': set(allowed_roles),
            'plans': set(plans) if plans else set()
        }

        # Store on class for permission checking
        cls._allowed_roles = set(allowed_roles)
        cls._allowed_plans = set(plans) if plans else set()
        cls._route_name = name

        # Prepend RoleBasedPermission to existing permission classes
        existing = list(getattr(cls, 'permission_classes', []))
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
        allowed_roles = getattr(view, '_allowed_roles', set())
        allowed_plans = getattr(view, '_allowed_plans', set())

        # Public routes are accessible to everyone
        if 'public' in allowed_roles:
            return True

        # Must be authenticated for non-public routes
        if not request.user.is_authenticated:
            return False

        # Admin/staff override when 'admin' is in allowed roles
        # Note: We check this early to bypass plan checks for admins
        if request.user.is_staff and 'admin' in allowed_roles:
            return True

        # Check user's role against allowed roles
        user_role = getattr(request.user, 'account_type', None)
        if user_role not in allowed_roles:
            return False

        # If strict plans are defined, check user's subscription plan
        if allowed_plans:
            # Safely get subscription plan
            subscription = getattr(request.user, 'subscription', None)
            user_plan = getattr(subscription, 'plan', 'attendee') if subscription else 'attendee'
            
            # Allow legacy 'premium' to match 'organization' requirements if needed, 
            # or just strict string matching. 
            # We'll assume strict matching based on the arguments passed to @roles.
            if user_plan not in allowed_plans:
                self.message = "Your subscription plan does not allow access to this resource."
                return False

        return True


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
        return [
            route for route, config in ROUTE_REGISTRY.items() if 'public' in config['roles']
        ]

    user_role = getattr(user, 'account_type', None)
    is_admin = user.is_staff
    
    # Get user plan safely
    subscription = getattr(user, 'subscription', None)
    user_plan = getattr(subscription, 'plan', 'attendee') if subscription else 'attendee'

    allowed = []
    for route, config in ROUTE_REGISTRY.items():
        roles = config['roles']
        plans = config['plans']

        if 'public' in roles:
            allowed.append(route)
        elif is_admin and 'admin' in roles:
            allowed.append(route)
        elif user_role in roles:
            # If plans are restricted, check plan matches
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
            'create_events': False,
            'manage_certificates': False,
            'view_billing': False,
            'browse_events': True,
            'register_for_events': True,
        }

    role = getattr(user, 'account_type', 'attendee')
    is_organizer = role in ('organizer', 'admin') or user.is_staff

    # Get user plan
    subscription = getattr(user, 'subscription', None)
    user_plan = getattr(subscription, 'plan', 'attendee') if subscription else 'attendee'
    is_organization_plan = user_plan in ('organization', 'premium')

    # Check if user is already part of an organization
    from organizations.permissions import get_user_organizations
    user_organizations = get_user_organizations(user)
    has_organization = user_organizations.exists()

    return {
        'create_events': is_organizer,
        'manage_certificates': is_organizer,
        'view_billing': role == 'organizer',
        'browse_events': True,
        'register_for_events': True,
        'view_own_registrations': True,
        'view_own_certificates': True,
        'can_create_organization': is_organizer and not has_organization and (is_organization_plan or user.is_staff),
    }
