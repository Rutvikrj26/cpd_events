"""
Accounts configuration constants.

Centralizes all authentication and user-related magic numbers including:
- Token expiry times
- Token lengths
- JWT settings
- Zoom integration settings
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
# Token Expiry Configuration
# =============================================================================


class TokenExpiry:
    """
    Token expiration settings in hours.

    - EMAIL_VERIFICATION_HOURS: How long email verification tokens are valid
    - PASSWORD_RESET_HOURS: How long password reset tokens are valid
    """

    EMAIL_VERIFICATION_HOURS: int = _validate_positive(24, 'TokenExpiry.EMAIL_VERIFICATION_HOURS')
    PASSWORD_RESET_HOURS: int = _validate_positive(24, 'TokenExpiry.PASSWORD_RESET_HOURS')


# =============================================================================
# Token Length Configuration
# =============================================================================


class TokenLength:
    """
    Token length settings.

    - VERIFICATION_CODE: Length of generated verification tokens (characters)
    """

    VERIFICATION_CODE: int = _validate_positive(32, 'TokenLength.VERIFICATION_CODE')


# =============================================================================
# JWT Configuration
# =============================================================================


class JwtConfig:
    """
    JWT token lifetime settings.

    - ACCESS_TOKEN_MINUTES: How long access tokens are valid
    - REFRESH_TOKEN_DAYS: How long refresh tokens are valid
    """

    ACCESS_TOKEN_MINUTES: int = _validate_positive(60, 'JwtConfig.ACCESS_TOKEN_MINUTES')
    REFRESH_TOKEN_DAYS: int = _validate_positive(7, 'JwtConfig.REFRESH_TOKEN_DAYS')


# =============================================================================
# Zoom Integration Configuration
# =============================================================================


class ZoomConfig:
    """
    Zoom OAuth integration settings.

    - TOKEN_REFRESH_BUFFER_MINUTES: Refresh tokens this many minutes before expiry
    - MAX_ERROR_COUNT: Number of errors before deactivating connection
    """

    TOKEN_REFRESH_BUFFER_MINUTES: int = _validate_positive(5, 'ZoomConfig.TOKEN_REFRESH_BUFFER_MINUTES')
    MAX_ERROR_COUNT: int = _validate_positive(5, 'ZoomConfig.MAX_ERROR_COUNT')


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'TokenExpiry',
    'TokenLength',
    'JwtConfig',
    'ZoomConfig',
]
