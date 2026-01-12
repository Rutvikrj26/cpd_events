"""
Integrations configuration constants.

Centralizes all integration-related magic numbers including:
- Webhook settings
- Error handling truncation
- Feedback/rating configuration
"""

from django.core.exceptions import ImproperlyConfigured

# =============================================================================
# Validation Helpers
# =============================================================================


def _validate_positive(value: int, name: str) -> int:
    """Validate value is positive (> 0)."""
    if value <= 0:
        raise ImproperlyConfigured(f"{name} must be > 0, got {value}")
    return value


# =============================================================================
# Webhook Configuration
# =============================================================================


class WebhookConfig:
    """
    Webhook processing settings.

    - LOG_RETENTION_DAYS: How long to keep webhook logs before cleanup
    - MAX_RETRY_ATTEMPTS: Maximum times to retry failed webhook processing
    """

    LOG_RETENTION_DAYS: int = _validate_positive(90, 'WebhookConfig.LOG_RETENTION_DAYS')
    MAX_RETRY_ATTEMPTS: int = _validate_positive(3, 'WebhookConfig.MAX_RETRY_ATTEMPTS')


# =============================================================================
# Error Truncation
# =============================================================================


class ErrorTruncation:
    """
    Error message truncation limits for database storage.

    Prevents excessively long error messages from bloating the database.

    - MESSAGE_LENGTH: Maximum characters for error messages
    - TRACEBACK_LENGTH: Maximum characters for stack traces
    """

    MESSAGE_LENGTH: int = _validate_positive(1000, 'ErrorTruncation.MESSAGE_LENGTH')
    TRACEBACK_LENGTH: int = _validate_positive(5000, 'ErrorTruncation.TRACEBACK_LENGTH')


# =============================================================================
# Feedback/Rating Configuration
# =============================================================================


class FeedbackRatings:
    """
    Rating scale configuration for event feedback.

    Standard 1-5 star rating scale where:
    - 1 = Poor
    - 2 = Below Average
    - 3 = Average
    - 4 = Good
    - 5 = Excellent
    """

    MIN: int = 1
    MAX: int = 5


# =============================================================================
# Time Constants
# =============================================================================


class TimeConstants:
    """
    Common time conversion constants.

    Used for duration calculations in integrations.
    """

    SECONDS_PER_HOUR: int = 3600
    SECONDS_PER_MINUTE: int = 60
    MINUTES_PER_HOUR: int = 60


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'WebhookConfig',
    'ErrorTruncation',
    'FeedbackRatings',
    'TimeConstants',
]
