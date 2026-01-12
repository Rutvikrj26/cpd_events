"""
Event configuration constants.

Centralizes all event-related magic numbers including:
- Event duration limits
- Attendance thresholds for certificates
- Session defaults
- Event duplication settings
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


def _validate_percentage(value: int, name: str) -> int:
    """Validate value is a valid percentage (0-100)."""
    if not 0 <= value <= 100:
        raise ImproperlyConfigured(f"{name} must be 0-100, got {value}")
    return value


def _validate_non_negative(value: int, name: str) -> int:
    """Validate value is non-negative (>= 0)."""
    if value < 0:
        raise ImproperlyConfigured(f"{name} must be >= 0, got {value}")
    return value


# =============================================================================
# Event Duration Configuration
# =============================================================================


class EventDuration:
    """
    Event duration settings in minutes.

    - DEFAULT: Default event duration when creating new events
    - MIN: Minimum allowed event duration
    - MAX: Maximum allowed event duration (8 hours)
    """

    DEFAULT: int = _validate_positive(60, 'EventDuration.DEFAULT')
    MIN: int = _validate_positive(15, 'EventDuration.MIN')
    MAX: int = _validate_positive(480, 'EventDuration.MAX')  # 8 hours


# =============================================================================
# Attendance Thresholds
# =============================================================================


class AttendanceThresholds:
    """
    Attendance requirements for certificate eligibility.

    Backend eligibility is based on minimum minutes. Percentage is
    UI-derived only and should not be used for server-side checks.

    - DEFAULT_PERCENT: Default minimum attendance percentage (0-100)
    - DEFAULT_MINUTES: Default minimum attendance minutes (0 = no minimum)
    """

    DEFAULT_PERCENT: int = _validate_percentage(80, 'AttendanceThresholds.DEFAULT_PERCENT')
    DEFAULT_MINUTES: int = _validate_non_negative(0, 'AttendanceThresholds.DEFAULT_MINUTES')


# =============================================================================
# Session Defaults
# =============================================================================


class SessionDefaults:
    """
    Default values for event sessions.

    Used when creating new sessions within a multi-session event.
    """

    DURATION_MINUTES: int = _validate_positive(60, 'SessionDefaults.DURATION_MINUTES')
    ATTENDANCE_PERCENT: int = _validate_percentage(80, 'SessionDefaults.ATTENDANCE_PERCENT')


# =============================================================================
# Event Duplication
# =============================================================================


class EventDuplication:
    """
    Settings for event duplication feature.

    When duplicating an event, the start date is offset by DAYS_OFFSET days.
    """

    DAYS_OFFSET: int = _validate_positive(7, 'EventDuplication.DAYS_OFFSET')


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'EventDuration',
    'AttendanceThresholds',
    'SessionDefaults',
    'EventDuplication',
]
