"""
Centralized configuration constants for the CPD Events backend.

This module provides a single entry point for all application constants,
organized by domain. Import from here for cleaner code:

    from common.config import TrialConfig, EventDuration, Pagination

Or import specific modules:

    from common.config.billing import PLAN_LIMITS
    from common.config.events import EventDuration, AttendanceThresholds

All constants are validated at import time - invalid values will raise
ImproperlyConfigured exceptions immediately.

Modules:
- billing: Trial periods, plan limits, Stripe configuration
- events: Duration limits, attendance thresholds, session defaults
- accounts: Token expiry, JWT settings, Zoom integration
- learning: Scoring defaults, assignment settings, course settings
- integrations: Webhook settings, error truncation, feedback ratings
- api: Pagination, throttling, upload limits, certificate dimensions
"""

# Billing configuration
# Accounts configuration
from .accounts import (
    JwtConfig,
    TokenExpiry,
    TokenLength,
    ZoomConfig,
)

# API configuration
from .api import (
    CertificateTemplateDimensions,
    Pagination,
    ThrottleRates,
    UploadLimits,
    VerificationCodes,
)
from .billing import (
    DefaultPlan,
    PLAN_LIMITS,
    PlatformFees,
    TicketingFees,
    TicketingTaxCodes,
)

# Events configuration
from .events import (
    AttendanceThresholds,
    EventDuplication,
    EventDuration,
    SessionDefaults,
)

# Integrations configuration
from .integrations import (
    ErrorTruncation,
    FeedbackRatings,
    TimeConstants,
    WebhookConfig,
)

# Learning configuration
from .learning import (
    AssignmentDefaults,
    CourseDefaults,
    ModuleDefaults,
    ScoringDefaults,
)

__all__ = [
    # Billing
    "PlatformFees",
    "TicketingFees",
    "TicketingTaxCodes",
    "PLAN_LIMITS",
    "DefaultPlan",
    # Events
    "EventDuration",
    "AttendanceThresholds",
    "SessionDefaults",
    "EventDuplication",
    # Accounts
    "TokenExpiry",
    "TokenLength",
    "JwtConfig",
    "ZoomConfig",
    # Learning
    "ScoringDefaults",
    "AssignmentDefaults",
    "CourseDefaults",
    "ModuleDefaults",
    # Integrations
    "WebhookConfig",
    "ErrorTruncation",
    "FeedbackRatings",
    "TimeConstants",
    # API
    "Pagination",
    "ThrottleRates",
    "UploadLimits",
    "CertificateTemplateDimensions",
    "VerificationCodes",
]
