"""
Billing types and data classes.

Centralized type definitions for capability checks, access status,
and usage tracking across the billing system.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CapabilityResult:
    """
    Result of a capability check or limit enforcement operation.

    Used for:
    - Checking if user can perform an action
    - Atomic check-and-increment operations
    - Returning detailed error information

    Attributes:
        allowed: Whether the action is permitted
        error_code: Machine-readable error code for frontend handling
        error_message: Human-readable error message for display
        limit: The configured limit (if applicable)
        current_usage: Current usage count (if applicable)
        remaining: Remaining quota (if applicable)
    """

    allowed: bool
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    limit: Optional[int] = None
    current_usage: Optional[int] = None
    remaining: Optional[int] = None

    def __bool__(self) -> bool:
        """Allow using CapabilityResult in boolean context."""
        return self.allowed

    @classmethod
    def success(cls, limit: Optional[int] = None, current_usage: Optional[int] = None) -> "CapabilityResult":
        """Create a successful result."""
        remaining = None
        if limit is not None and current_usage is not None:
            remaining = max(0, limit - current_usage)
        return cls(allowed=True, limit=limit, current_usage=current_usage, remaining=remaining)

    @classmethod
    def denied(cls, error_code: str, error_message: str, **kwargs) -> "CapabilityResult":
        """Create a denied result."""
        return cls(allowed=False, error_code=error_code, error_message=error_message, **kwargs)


@dataclass
class AccessStatus:
    """
    Comprehensive access status for a user's subscription.

    Used by frontend to display appropriate UI states and messages.

    Attributes:
        is_active: Subscription is in active/trialing state
        is_trialing: Currently in trial period
        is_trial_expired: Trial has ended without conversion
        is_in_grace_period: Post-trial grace period (limited access)
        is_access_blocked: Complete access block (no subscription features)
        days_until_trial_ends: Days remaining in trial (None if not trialing)
        plan: Current plan name
        status: Current subscription status
        has_payment_method: User has a valid payment method on file
    """

    is_active: bool
    is_trialing: bool
    is_trial_expired: bool
    is_in_grace_period: bool
    is_access_blocked: bool
    days_until_trial_ends: Optional[int]
    plan: str
    status: str
    has_payment_method: bool = False


@dataclass
class UsageSummary:
    """
    Usage summary for a subscription period.

    Attributes:
        events_created: Events created this period
        events_limit: Event limit for the plan (None = unlimited)
        events_remaining: Remaining event quota (None = unlimited)
        courses_created: Courses created this period
        courses_limit: Course limit for the plan (None = unlimited)
        courses_remaining: Remaining course quota (None = unlimited)
        certificates_issued: Certificates issued this period
        certificates_limit: Certificate limit for the plan (None = unlimited)
        certificates_remaining: Remaining certificate quota (None = unlimited)
        period_start: Start of current billing period
        period_end: End of current billing period
    """

    events_created: int = 0
    events_limit: Optional[int] = None
    events_remaining: Optional[int] = None
    courses_created: int = 0
    courses_limit: Optional[int] = None
    courses_remaining: Optional[int] = None
    certificates_issued: int = 0
    certificates_limit: Optional[int] = None
    certificates_remaining: Optional[int] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None

    @classmethod
    def from_subscription(cls, subscription) -> "UsageSummary":
        """Create UsageSummary from a Subscription instance."""
        limits = subscription.limits if subscription else {}

        events_limit = limits.get("events_per_month")
        courses_limit = limits.get("courses_per_month")
        certificates_limit = limits.get("certificates_per_month")

        events_created = subscription.events_created_this_period if subscription else 0
        courses_created = subscription.courses_created_this_period if subscription else 0
        certificates_issued = subscription.certificates_issued_this_period if subscription else 0

        return cls(
            events_created=events_created,
            events_limit=events_limit,
            events_remaining=None if events_limit is None else max(0, events_limit - events_created),
            courses_created=courses_created,
            courses_limit=courses_limit,
            courses_remaining=None if courses_limit is None else max(0, courses_limit - courses_created),
            certificates_issued=certificates_issued,
            certificates_limit=certificates_limit,
            certificates_remaining=None if certificates_limit is None else max(0, certificates_limit - certificates_issued),
            period_start=subscription.current_period_start.isoformat()
            if subscription and subscription.current_period_start
            else None,
            period_end=subscription.current_period_end.isoformat()
            if subscription and subscription.current_period_end
            else None,
        )


@dataclass
class PlanCapabilities:
    """
    Capabilities available for a subscription plan.

    Defines what actions are permitted and at what limits.
    This can be extended to support feature flags from StripeProduct.
    """

    can_create_events: bool = False
    can_create_courses: bool = False
    can_issue_certificates: bool = False
    can_use_zoom_integration: bool = False
    can_use_custom_branding: bool = False
    can_access_api: bool = False
    events_per_month: Optional[int] = None  # None = unlimited
    courses_per_month: Optional[int] = None  # None = unlimited
    certificates_per_month: Optional[int] = None  # None = unlimited
    max_attendees_per_event: Optional[int] = None  # None = unlimited


# Error codes for machine-readable error handling
class ErrorCodes:
    """Standard error codes for capability checks."""

    # Access errors
    NO_SUBSCRIPTION = "NO_SUBSCRIPTION"
    SUBSCRIPTION_EXPIRED = "SUBSCRIPTION_EXPIRED"
    SUBSCRIPTION_CANCELED = "SUBSCRIPTION_CANCELED"
    TRIAL_EXPIRED = "TRIAL_EXPIRED"
    ACCESS_BLOCKED = "ACCESS_BLOCKED"
    PAYMENT_REQUIRED = "PAYMENT_REQUIRED"

    # Capability errors
    PLAN_UPGRADE_REQUIRED = "PLAN_UPGRADE_REQUIRED"
    FEATURE_NOT_AVAILABLE = "FEATURE_NOT_AVAILABLE"

    # Limit errors
    EVENT_LIMIT_REACHED = "EVENT_LIMIT_REACHED"
    COURSE_LIMIT_REACHED = "COURSE_LIMIT_REACHED"
    CERTIFICATE_LIMIT_REACHED = "CERTIFICATE_LIMIT_REACHED"
    ATTENDEE_LIMIT_REACHED = "ATTENDEE_LIMIT_REACHED"

    # Transition errors
    ACTIVE_CONTENT_EXISTS = "ACTIVE_CONTENT_EXISTS"
    ALREADY_ON_PLAN = "ALREADY_ON_PLAN"
    INVALID_PLAN = "INVALID_PLAN"
