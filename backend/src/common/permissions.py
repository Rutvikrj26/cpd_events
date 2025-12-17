"""
Common API permissions.
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


class IsOrganizer(permissions.BasePermission):
    """Only users with organizer account type."""

    message = "Organizer account required."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.account_type == 'organizer'


class IsOrganizerOrReadOnly(permissions.BasePermission):
    """Organizers can write, everyone can read."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.account_type == 'organizer'


class IsEventOwner(permissions.BasePermission):
    """Permission for event-related objects."""

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'event'):
            return obj.event.owner == request.user
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        return False


class IsRegistrant(permissions.BasePermission):
    """User can access their own registrations."""

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'registration'):
            return obj.registration.user == request.user
        return False


class IsEventOwnerOrRegistrant(permissions.BasePermission):
    """Either event owner or the registrant can access."""

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Check if owner
        if hasattr(obj, 'event') and obj.event.owner == user:
            return True
        if hasattr(obj, 'owner') and obj.owner == user:
            return True

        # Check if registrant
        if hasattr(obj, 'user') and obj.user == user:
            return True
        return bool(hasattr(obj, 'registration') and obj.registration.user == user)


class HasActiveSubscription(permissions.BasePermission):
    """
    Requires user to have an active subscription.

    Checks that user has a subscription in 'active' or 'trialing' status.
    """

    message = "Active subscription required."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        try:
            from billing.models import Subscription

            subscription = Subscription.objects.get(user=request.user)
            return subscription.is_active
        except Exception:
            return False


class CanCreateEvent(permissions.BasePermission):
    """
    Checks if user can create events based on subscription limits.
    """

    message = "Event creation limit reached for your plan."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.user.account_type != 'organizer':
            return False

        try:
            from billing.models import Subscription

            subscription = Subscription.objects.get(user=request.user)
            return subscription.check_event_limit()
        except Exception:
            # No subscription - allow if they're a new user (will get free tier)
            return True


class CanIssueCertificate(permissions.BasePermission):
    """
    Checks if user can issue certificates based on subscription limits.
    """

    message = "Certificate issuance limit reached for your plan."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.user.account_type != 'organizer':
            return False

        try:
            from billing.models import Subscription

            subscription = Subscription.objects.get(user=request.user)
            return subscription.check_certificate_limit()
        except Exception:
            return True


class IsAdminOrReadOnly(permissions.BasePermission):
    """Admin users can write, others can only read."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.is_staff


class IsSelfOrAdmin(permissions.BasePermission):
    """User can only access their own data, unless admin."""

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True

        if hasattr(obj, 'user'):
            return obj.user == request.user

        return obj == request.user
