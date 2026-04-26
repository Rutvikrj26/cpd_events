"""
Common API permissions using Django Groups and Permissions.
"""

from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """Object-level permission: only owner can access."""

    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Object-level permission: owner can edit, others read-only."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.owner == request.user


class IsOrganizerOrAdmin(permissions.BasePermission):
    """Organizers or admins (group membership is the source of truth).

    Use on event-management views that require the user to be an event
    organizer — promo codes, speakers, event certificates, contacts, etc.
    Instructors do NOT pass this check (they manage courses, not events).
    """

    message = "Organizer or admin role required."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.groups.filter(name__in=["organizer", "admin"]).exists()


class IsContentCreator(permissions.BasePermission):
    """Organizers, instructors, or admins.

    Use on views that are shared between event organizers and course
    instructors (e.g. top-level event list includes both so instructors
    can see events they're running sessions for; certificate templates
    are shared; integrations are shared).
    """

    message = "Organizer, instructor, or admin role required."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.groups.filter(name__in=["organizer", "instructor", "admin"]).exists()


class IsEventOwner(permissions.BasePermission):
    """Permission for event-related objects."""

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "event"):
            return obj.event.owner == request.user
        if hasattr(obj, "owner"):
            return obj.owner == request.user
        return False


class IsRegistrant(permissions.BasePermission):
    """User can access their own registrations."""

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "user"):
            return obj.user == request.user
        if hasattr(obj, "registration"):
            return obj.registration.user == request.user
        return False


class IsEventOwnerOrRegistrant(permissions.BasePermission):
    """Either event owner or the registrant can access."""

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Check if owner
        if hasattr(obj, "event") and obj.event.owner == user:
            return True
        if hasattr(obj, "owner") and obj.owner == user:
            return True

        # Check if registrant
        if hasattr(obj, "user") and obj.user == user:
            return True
        return bool(hasattr(obj, "registration") and obj.registration.user == user)


class HasPerm(permissions.BasePermission):
    """
    Generic permission class that checks a specific Django permission.

    Usage:
        permission_classes = [HasPerm('events.can_create_event')]

    Or use the factory:
        permission_classes = [has_perm('events.can_create_event')]
    """

    perm = None

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if self.perm is None:
            return True
        return request.user.has_perm(self.perm)


def has_perm(perm_string: str):
    """Factory to create a permission class for a specific Django permission."""
    return type(f"HasPerm_{perm_string}", (HasPerm,), {"perm": perm_string})


class IsAdminOrReadOnly(permissions.BasePermission):
    """Institution admins can write, others can only read."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return (
            request.user.is_authenticated
            and request.user.groups.filter(name="admin").exists()
        )


class IsSelfOrAdmin(permissions.BasePermission):
    """User can only access their own data, unless institution admin."""

    def has_object_permission(self, request, view, obj):
        if request.user.is_authenticated and request.user.groups.filter(name="admin").exists():
            return True

        if hasattr(obj, "user"):
            return obj.user == request.user

        return obj == request.user
