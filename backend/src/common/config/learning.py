"""
Learning/LMS configuration constants.

Centralizes all learning management system magic numbers including:
- Scoring defaults
- Assignment settings
- Course settings
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


# =============================================================================
# Scoring Defaults
# =============================================================================


class ScoringDefaults:
    """
    Default scoring settings for modules, assignments, and courses.

    - PASSING_SCORE: Default minimum score to pass (percentage)
    - MAX_SCORE: Default maximum score for assignments
    """

    PASSING_SCORE: int = _validate_percentage(70, 'ScoringDefaults.PASSING_SCORE')
    MAX_SCORE: int = _validate_positive(100, 'ScoringDefaults.MAX_SCORE')


# =============================================================================
# Assignment Defaults
# =============================================================================


class AssignmentDefaults:
    """
    Default settings for assignments.

    - DUE_DAYS_AFTER_RELEASE: Days after module release when assignment is due
    - MAX_ATTEMPTS: Maximum number of submission attempts allowed
    - PASSING_SCORE: Default passing score (uses ScoringDefaults if not specified)
    """

    DUE_DAYS_AFTER_RELEASE: int = _validate_positive(7, 'AssignmentDefaults.DUE_DAYS_AFTER_RELEASE')
    MAX_ATTEMPTS: int = _validate_positive(3, 'AssignmentDefaults.MAX_ATTEMPTS')
    PASSING_SCORE: int = ScoringDefaults.PASSING_SCORE
    MAX_SCORE: int = ScoringDefaults.MAX_SCORE


# =============================================================================
# Course Defaults
# =============================================================================


class CourseDefaults:
    """
    Default settings for self-paced courses.

    - PASSING_SCORE: Minimum score to complete the course (percentage)
    """

    PASSING_SCORE: int = ScoringDefaults.PASSING_SCORE


# =============================================================================
# Module Defaults
# =============================================================================


class ModuleDefaults:
    """
    Default settings for learning modules.

    - PASSING_SCORE: Minimum score to pass the module (percentage)
    """

    PASSING_SCORE: int = ScoringDefaults.PASSING_SCORE


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'ScoringDefaults',
    'AssignmentDefaults',
    'CourseDefaults',
    'ModuleDefaults',
]
