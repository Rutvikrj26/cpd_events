"""
Centralized user-facing messages for the CPD Events platform.

This module contains all error messages, success messages, and notification
text used throughout the application. Centralizing messages ensures:

1. Consistent tone and wording across the platform
2. Easy updates without hunting through code
3. Future i18n/l10n support
4. DRY principle compliance

Usage:
    from billing.types import ErrorCodes
    from common.messages import CAPABILITY_MESSAGES

    result = CapabilityResult.denied(
        ErrorCodes.EVENT_LIMIT_REACHED,
        CAPABILITY_MESSAGES['event_limit_reached'].format(limit=10)
    )
"""

from typing import Final


# =============================================================================
# Capability & Subscription Messages
# =============================================================================

CAPABILITY_MESSAGES: Final[dict[str, str]] = {
    # Access errors
    "subscription_required": "No subscription found. Please subscribe to a plan.",
    "subscription_expired": "Your subscription has expired. Please renew to continue.",
    "subscription_canceled": "Your subscription has been canceled. Please resubscribe to access this feature.",
    "trial_expired": "Your trial has ended. Please upgrade to a paid plan to continue.",
    "access_blocked": "Access to this feature is blocked. Please update your subscription.",
    "payment_required": "Payment is required to access this feature. Please update your billing information.",
    # Capability errors
    "event_creation_required": "Event creation requires an Organizer or Pro plan.",
    "course_creation_required": "Course creation requires an LMS or Pro plan.",
    "certificate_issuance_required": "Certificate issuance requires an Organizer, LMS, or Pro plan.",
    "feature_not_available": "This feature is not available on your current plan.",
    "plan_upgrade_required": "Please upgrade your plan to access this feature.",
    # Limit errors
    "event_limit_reached": "You've reached your monthly event limit ({limit}). Please upgrade for more.",
    "course_limit_reached": "You've reached your monthly course limit ({limit}). Please upgrade for more.",
    "certificate_limit_reached": "Certificate limit reached ({limit}/month). Please upgrade your plan.",
    "attendee_limit_reached": "This event has reached its attendee limit ({limit}). Please upgrade your plan for more attendees.",
    # Plan transition errors
    "active_content_exists": "You must archive or cancel active events/courses before downgrading.",
    "already_on_plan": "You are already on the {plan} plan.",
    "invalid_plan": "Invalid plan: {plan}.",
    "downgrade_failed": "Failed to downgrade subscription. Please try again.",
    "upgrade_failed": "Failed to upgrade subscription. Please try again.",
}


# =============================================================================
# Success Messages
# =============================================================================

SUCCESS_MESSAGES: Final[dict[str, str]] = {
    "subscription_created": "Subscription created successfully.",
    "subscription_updated": "Subscription updated successfully.",
    "subscription_canceled": "Subscription canceled successfully.",
    "subscription_reactivated": "Subscription reactivated successfully.",
    "plan_upgraded": "Successfully upgraded to {plan} plan.",
    "plan_downgraded": "Successfully downgraded to {plan} plan.",
    "payment_method_added": "Payment method added successfully.",
    "payment_method_removed": "Payment method removed successfully.",
}


# =============================================================================
# Notification Messages
# =============================================================================

NOTIFICATION_MESSAGES: Final[dict[str, dict[str, str]]] = {
    "trial_ending": {
        "title": "Trial ending soon",
        "message": "Your trial ends on {trial_end_date}. Upgrade now to keep your access.",
    },
    "trial_expired": {
        "title": "Trial expired",
        "message": "Your {plan} trial has ended. Upgrade to continue creating events and courses.",
    },
    "payment_failed": {
        "title": "Payment failed",
        "message": "We could not process your latest payment. Please update your billing details.",
    },
    "payment_method_expired": {
        "title": "Payment method expired",
        "message": "Your {card_brand} card ending in {card_last4} has expired.",
    },
    "refund_processed": {
        "title": "Refund processed",
        "message": "Your refund for {event_title} has been processed.",
    },
}


# =============================================================================
# Plan Display Names
# =============================================================================

PLAN_DISPLAY_NAMES: Final[dict[str, str]] = {
    "attendee": "Attendee (Free)",
    "organizer": "Organizer",
    "lms": "LMS",
    "pro": "Pro",
}


# =============================================================================
# Feature Descriptions for Plans
# =============================================================================

PLAN_FEATURES: Final[dict[str, list[str]]] = {
    "attendee": [
        "Register for events",
        "Earn certificates",
        "Track CPD credits",
    ],
    "organizer": [
        "Create unlimited events",
        "Issue certificates",
        "Zoom integration",
        "Custom certificate templates",
        "Priority email support",
    ],
    "lms": [
        "Create unlimited courses",
        "Self-paced course builder",
        "Course certificates",
        "Learner progress tracking",
    ],
    "pro": [
        "Unlimited events and courses",
        "All Organizer features",
        "All LMS features",
        "API access",
        "White-label options",
        "Priority support",
        "Dedicated account manager",
    ],
}


# =============================================================================
# HTTP Error Responses (for API consistency)
# =============================================================================

HTTP_ERRORS: Final[dict[str, dict[str, str]]] = {
    "unauthorized": {
        "code": "UNAUTHORIZED",
        "message": "Authentication required.",
    },
    "forbidden": {
        "code": "FORBIDDEN",
        "message": "You do not have permission to perform this action.",
    },
    "not_found": {
        "code": "NOT_FOUND",
        "message": "The requested resource was not found.",
    },
    "validation_error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid input provided.",
    },
    "rate_limited": {
        "code": "RATE_LIMITED",
        "message": "Too many requests. Please try again later.",
    },
    "server_error": {
        "code": "SERVER_ERROR",
        "message": "An unexpected error occurred. Please try again.",
    },
}
