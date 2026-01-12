"""
API configuration constants.

Centralizes all API-related magic numbers including:
- Pagination settings
- Throttle rates
- Upload limits
- Certificate template dimensions
- Verification code settings
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
# Pagination Configuration
# =============================================================================


class Pagination:
    """
    Pagination settings for API endpoints.

    - DEFAULT_PAGE_SIZE: Default number of items per page
    - MAX_PAGE_SIZE: Maximum allowed items per page
    - SMALL_PAGE_SIZE: Default for nested resources
    - SMALL_MAX_PAGE_SIZE: Maximum for nested resources
    """

    DEFAULT_PAGE_SIZE: int = _validate_positive(20, 'Pagination.DEFAULT_PAGE_SIZE')
    MAX_PAGE_SIZE: int = _validate_positive(100, 'Pagination.MAX_PAGE_SIZE')
    SMALL_PAGE_SIZE: int = _validate_positive(10, 'Pagination.SMALL_PAGE_SIZE')
    SMALL_MAX_PAGE_SIZE: int = _validate_positive(50, 'Pagination.SMALL_MAX_PAGE_SIZE')


# =============================================================================
# Throttle Rates
# =============================================================================


class ThrottleRates:
    """
    API rate limiting configuration.

    Format: "{count}/{period}" where period is second/minute/hour/day.

    - ANON: Rate limit for anonymous users
    - USER: Rate limit for authenticated users
    - AUTH: Rate limit for authentication endpoints
    - BULK: Rate limit for bulk operations
    - IMPORT: Rate limit for import operations
    - EXPORT: Rate limit for export operations
    """

    ANON: str = '1000/min'
    USER: str = '10000/min'
    AUTH: str = '100/hour'
    BULK: str = '10/hour'
    IMPORT: str = '5/hour'
    EXPORT: str = '20/hour'


# =============================================================================
# Upload Limits
# =============================================================================


class UploadLimits:
    """
    File upload size limits.

    - MAX_IMAGE_SIZE_BYTES: Maximum size for image uploads (5MB)
    - MAX_DOCUMENT_SIZE_BYTES: Maximum size for document uploads (10MB)
    """

    MAX_IMAGE_SIZE_BYTES: int = 5 * 1024 * 1024  # 5MB
    MAX_DOCUMENT_SIZE_BYTES: int = 10 * 1024 * 1024  # 10MB


# =============================================================================
# Certificate Template Dimensions
# =============================================================================


class CertificateTemplateDimensions:
    """
    Default certificate template dimensions.

    Based on standard letter size (11" x 8.5") at 96 DPI.
    Default orientation is landscape.
    """

    WIDTH_PX: int = _validate_positive(1056, 'CertificateTemplateDimensions.WIDTH_PX')  # 11" @ 96dpi
    HEIGHT_PX: int = _validate_positive(816, 'CertificateTemplateDimensions.HEIGHT_PX')  # 8.5" @ 96dpi


# =============================================================================
# Verification Code Configuration
# =============================================================================


class VerificationCodes:
    """
    Certificate verification code settings.

    - SHORT_CODE_LENGTH: Length of short code displayed on certificate (alphanumeric)
    - URL_TOKEN_LENGTH: Length of URL-safe token for verification links
    """

    SHORT_CODE_LENGTH: int = _validate_positive(8, 'VerificationCodes.SHORT_CODE_LENGTH')
    URL_TOKEN_LENGTH: int = _validate_positive(16, 'VerificationCodes.URL_TOKEN_LENGTH')


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'Pagination',
    'ThrottleRates',
    'UploadLimits',
    'CertificateTemplateDimensions',
    'VerificationCodes',
]
