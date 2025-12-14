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
        return (
            request.user.is_authenticated and 
            request.user.account_type == 'organizer'
        )


class IsOrganizerOrReadOnly(permissions.BasePermission):
    """Organizers can write, everyone can read."""
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return (
            request.user.is_authenticated and 
            request.user.account_type == 'organizer'
        )


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
        if hasattr(obj, 'registration') and obj.registration.user == user:
            return True
        
        return False
