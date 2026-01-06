"""
Centralized configuration constants for the CPD Events backend.

This module provides a single entry point for all application constants,
organized by domain. Import from here for cleaner code:

    from common.config import TrialConfig, EventDuration, Pagination

Or import specific modules:

    from common.config.billing import TrialConfig, IndividualPlanLimits
    from common.config.events import EventDuration, AttendanceThresholds

All constants are validated at import time - invalid values will raise
ImproperlyConfigured exceptions immediately.

Modules:
- billing: Trial periods, plan limits, pricing, Stripe configuration
- events: Duration limits, attendance thresholds, session defaults
- accounts: Token expiry, JWT settings, Zoom integration
- learning: Scoring defaults, assignment settings, course settings
- integrations: Webhook settings, error truncation, feedback ratings
- api: Pagination, throttling, upload limits, certificate dimensions
"""

# Billing configuration
from .billing import (
    PlatformFees,
    TicketingFees,
    TicketingTaxCodes,
    IndividualPlanLimits,
    OrganizationPlanLimits,
    PricingConfig,
    StripePriceIds,
    DefaultPlan,
)

# Events configuration
from .events import (
    EventDuration,
    AttendanceThresholds,
    SessionDefaults,
    EventDuplication,
)

# Accounts configuration
from .accounts import (
    TokenExpiry,
    TokenLength,
    JwtConfig,
    ZoomConfig,
)

# Learning configuration
from .learning import (
    ScoringDefaults,
    AssignmentDefaults,
    CourseDefaults,
    ModuleDefaults,
)

# Integrations configuration
from .integrations import (
    WebhookConfig,
    ErrorTruncation,
    FeedbackRatings,
    TimeConstants,
)

# API configuration
from .api import (
    Pagination,
    ThrottleRates,
    UploadLimits,
    CertificateTemplateDimensions,
    VerificationCodes,
)


__all__ = [
    # Billing
    'PlatformFees',
    'TicketingFees',
    'TicketingTaxCodes',
    'IndividualPlanLimits',
    'OrganizationPlanLimits',
    'PricingConfig',
    'StripePriceIds',
    'DefaultPlan',
    # Events
    'EventDuration',
    'AttendanceThresholds',
    'SessionDefaults',
    'EventDuplication',
    # Accounts
    'TokenExpiry',
    'TokenLength',
    'JwtConfig',
    'ZoomConfig',
    # Learning
    'ScoringDefaults',
    'AssignmentDefaults',
    'CourseDefaults',
    'ModuleDefaults',
    # Integrations
    'WebhookConfig',
    'ErrorTruncation',
    'FeedbackRatings',
    'TimeConstants',
    # API
    'Pagination',
    'ThrottleRates',
    'UploadLimits',
    'CertificateTemplateDimensions',
    'VerificationCodes',
]
