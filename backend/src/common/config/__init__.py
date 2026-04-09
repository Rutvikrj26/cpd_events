"""
Centralized configuration constants for the CPD Events backend.

This module provides a single entry point for all application constants,
organized by domain. Import from here for cleaner code:

    from common.config import EventDuration, Pagination

Or import specific modules:

    from common.config.events import EventDuration, AttendanceThresholds
    from common.config.deployment import DEPLOYMENT_MODE, INSTITUTION_NAME

Modules:
- deployment: Deployment mode, registration mode, institution branding
- events: Duration limits, attendance thresholds, session defaults
- accounts: Token expiry, JWT settings
- learning: Scoring defaults, assignment settings, course settings
- integrations: Webhook settings, error truncation, feedback ratings
- api: Pagination, throttling, upload limits, certificate dimensions
"""

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

# Deployment configuration
from .deployment import (
    DEPLOYMENT_MODE,
    INSTITUTION_LOGO_URL,
    INSTITUTION_NAME,
    REGISTRATION_MODE,
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
    # Deployment
    'DEPLOYMENT_MODE',
    'REGISTRATION_MODE',
    'INSTITUTION_NAME',
    'INSTITUTION_LOGO_URL',
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
