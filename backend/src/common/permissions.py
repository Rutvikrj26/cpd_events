"""
Common API permissions for CPD Events platform.

Simple capability-based permissions tied to subscription plans.
"""

from rest_framework import permissions


# ============================================================================
# Object-level Permissions
# ============================================================================


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


class IsEventOwner(permissions.BasePermission):
    """Permission for event-related objects (modules, sessions, etc.)."""

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


class IsSelfOrAdmin(permissions.BasePermission):
    """User can only access their own data, unless admin."""

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True

        if hasattr(obj, "user"):
            return obj.user == request.user

        return obj == request.user


# ============================================================================
# Capability-based Permissions (Subscription-driven)
# ============================================================================


class CanCreateEvents(permissions.BasePermission):
    """
    User can create events if they have organizer or pro plan.
    Checks both capability and quota limits.
    """

    message = "Event creation requires organizer or pro plan."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        from billing.capability_service import capability_service

        # Check capability (subscription plan)
        if not capability_service.can_create_events(request.user):
            return False

        # Check quota limit (if creating)
        if request.method == "POST":
            summary = capability_service.get_usage_summary(request.user)
            # If remaining is 0 (and limit exists/is not None), deny
            if summary.events_remaining is not None and summary.events_remaining <= 0:
                self.message = f"Event creation limit reached ({summary.events_limit}/month). Please upgrade."
                return False

        return True


class CanCreateCourses(permissions.BasePermission):
    """
    User can create courses if they have LMS or pro plan.
    Checks both capability and quota limits.
    """

    message = "Course creation requires LMS or pro plan."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        from billing.capability_service import capability_service

        # Check capability (subscription plan)
        if not capability_service.can_create_courses(request.user):
            return False

        # Check quota limit (if creating)
        if request.method == "POST":
            summary = capability_service.get_usage_summary(request.user)
            if summary.courses_remaining is not None and summary.courses_remaining <= 0:
                self.message = f"Course creation limit reached ({summary.courses_limit}/month). Please upgrade."
                return False

        return True


class CanIssueCertificates(permissions.BasePermission):
    """
    Checks if user can issue certificates based on subscription limits.
    """

    message = "Certificate issuance limit reached for your plan."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        from billing.capability_service import capability_service

        # Only event/course creators can issue certificates
        if not capability_service.can_issue_certificates(request.user):
            self.message = "Certificate issuance requires Organizer, LMS, or Pro plan."
            return False

        # Check quota limit
        summary = capability_service.get_usage_summary(request.user)
        if summary.certificates_remaining is not None and summary.certificates_remaining <= 0:
            self.message = f"Certificate issuance limit reached ({summary.certificates_limit}/month)."
            return False

        return True


class HasActiveSubscription(permissions.BasePermission):
    """
    Requires user to have an active subscription.
    Checks that user has a subscription in 'active' or 'trialing' status.
    """

    message = "Active subscription required."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        from billing.capability_service import capability_service

        return capability_service.has_active_subscription(request.user)


# ============================================================================
# Legacy Permission Aliases (for migration period)
# ============================================================================


class IsOrganizer(permissions.BasePermission):
    """
    User can create events (has organizer or pro plan).
    Legacy alias for CanCreateEvents.
    """

    message = "Event creation capability required."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.can_create_events or request.user.can_create_courses


class IsOrganizerOrCourseManager(permissions.BasePermission):
    """
    User can create events or courses.
    Legacy alias - checks if user has any content creation capability.
    """

    message = "Content creation capability required."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.can_create_events or request.user.can_create_courses


class IsOrganizerOrOrgAdmin(permissions.BasePermission):
    """
    User can create events.
    Legacy alias for CanCreateEvents (org admin concept removed).
    """

    message = "Event creation capability required."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.can_create_events


# ============================================================================
# Admin Permissions
# ============================================================================


class IsAdminOrReadOnly(permissions.BasePermission):
    """Admin users can write, others can only read."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.is_staff
