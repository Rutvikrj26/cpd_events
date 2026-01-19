"""
Billing configuration constants.

Centralizes all billing-related magic numbers including:
- Trial and grace period settings
- Plan limits
- Platform fees
"""

import os

from django.core.exceptions import ImproperlyConfigured

# =============================================================================
# Validation Helpers
# =============================================================================


def _validate_non_negative(value: int, name: str) -> int:
    """Validate value is non-negative (>= 0)."""
    if value < 0:
        raise ImproperlyConfigured(f"{name} must be >= 0, got {value}")
    return value


def _validate_positive(value: int, name: str) -> int:
    """Validate value is positive (> 0)."""
    if value <= 0:
        raise ImproperlyConfigured(f"{name} must be > 0, got {value}")
    return value


def _validate_percentage(value: float, name: str) -> float:
    """Validate value is a valid percentage (0-100)."""
    if not 0 <= value <= 100:
        raise ImproperlyConfigured(f"{name} must be 0-100, got {value}")
    return value


# =============================================================================
# Platform Fees
# =============================================================================


class PlatformFees:
    """
    Platform fee configuration for paid event registrations.

    - FEE_PERCENT: Percentage of transaction sent to platform via Stripe Connect
    """

    FEE_PERCENT: float = _validate_percentage(float(os.environ.get("PLATFORM_FEE_PERCENT", 2.0)), "PLATFORM_FEE_PERCENT")


# =============================================================================
# Ticketing Fees (Eventbrite-style)
# =============================================================================


class TicketingFees:
    """
    Ticketing fee configuration for paid event registrations.

    - SERVICE_FEE_PERCENT/FIXED: Platform service fee per ticket
    - PROCESSING_FEE_PERCENT/FIXED: Payment processing fee applied to total order

    Per-currency overrides:
    - TICKETING_SERVICE_FEE_PERCENT_{CURRENCY}
    - TICKETING_SERVICE_FEE_FIXED_{CURRENCY}
    - TICKETING_PROCESSING_FEE_PERCENT_{CURRENCY}
    - TICKETING_PROCESSING_FEE_FIXED_{CURRENCY}
    """

    DEFAULT_SERVICE_FEE_PERCENT: float = _validate_percentage(
        float(os.environ.get("TICKETING_SERVICE_FEE_PERCENT", 0.0)), "TICKETING_SERVICE_FEE_PERCENT"
    )
    DEFAULT_SERVICE_FEE_FIXED: float = _validate_non_negative(
        float(os.environ.get("TICKETING_SERVICE_FEE_FIXED", 0.0)), "TICKETING_SERVICE_FEE_FIXED"
    )
    DEFAULT_PROCESSING_FEE_PERCENT: float = _validate_percentage(
        float(os.environ.get("TICKETING_PROCESSING_FEE_PERCENT", 0.0)), "TICKETING_PROCESSING_FEE_PERCENT"
    )
    DEFAULT_PROCESSING_FEE_FIXED: float = _validate_non_negative(
        float(os.environ.get("TICKETING_PROCESSING_FEE_FIXED", 0.0)), "TICKETING_PROCESSING_FEE_FIXED"
    )

    @classmethod
    def _get_percent(cls, key: str, default: float) -> float:
        value = os.environ.get(key)
        if value is None:
            return default
        return _validate_percentage(float(value), key)

    @classmethod
    def _get_fixed(cls, key: str, default: float) -> float:
        value = os.environ.get(key)
        if value is None:
            return default
        return _validate_non_negative(float(value), key)

    @classmethod
    def get_service_fee_percent(cls, currency: str) -> float:
        currency = (currency or "").upper()
        return cls._get_percent(
            f"TICKETING_SERVICE_FEE_PERCENT_{currency}",
            cls.DEFAULT_SERVICE_FEE_PERCENT,
        )

    @classmethod
    def get_service_fee_fixed(cls, currency: str) -> float:
        currency = (currency or "").upper()
        return cls._get_fixed(
            f"TICKETING_SERVICE_FEE_FIXED_{currency}",
            cls.DEFAULT_SERVICE_FEE_FIXED,
        )

    @classmethod
    def get_processing_fee_percent(cls, currency: str) -> float:
        currency = (currency or "").upper()
        return cls._get_percent(
            f"TICKETING_PROCESSING_FEE_PERCENT_{currency}",
            cls.DEFAULT_PROCESSING_FEE_PERCENT,
        )

    @classmethod
    def get_processing_fee_fixed(cls, currency: str) -> float:
        currency = (currency or "").upper()
        return cls._get_fixed(
            f"TICKETING_PROCESSING_FEE_FIXED_{currency}",
            cls.DEFAULT_PROCESSING_FEE_FIXED,
        )


# =============================================================================
# Ticketing Tax Codes
# =============================================================================


class TicketingTaxCodes:
    """Stripe Tax codes for ticketing line items."""

    TICKET_IN_PERSON: str = os.environ.get("TICKETING_TAX_CODE_IN_PERSON", "txcd_20060044")
    TICKET_ONLINE: str = os.environ.get("TICKETING_TAX_CODE_ONLINE", "txcd_20060045")
    SERVICE_FEE: str = os.environ.get("TICKETING_TAX_CODE_SERVICE_FEE", "txcd_20030000")
    NON_TAXABLE: str = os.environ.get("TICKETING_TAX_CODE_NON_TAXABLE", "txcd_00000000")


# =============================================================================
# Plan Limits
# =============================================================================

PLAN_LIMITS = {
    "attendee": {
        "events_per_month": 0,
        "courses_per_month": 0,
        "certificates_per_month": 10,
    },
    "organizer": {
        "events_per_month": 30,
        "courses_per_month": 0,
        "certificates_per_month": 500,
    },
    "lms": {
        "events_per_month": 0,
        "courses_per_month": 30,
        "certificates_per_month": 500,
    },
    "pro": {
        "events_per_month": None,  # unlimited
        "courses_per_month": None,  # unlimited
        "certificates_per_month": None,  # unlimited
    },
}


# =============================================================================
# Default Plan
# =============================================================================


class DefaultPlan:
    """Default plan for new users."""

    NAME: str = os.environ.get("BILLING_DEFAULT_PLAN", "attendee")


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "PlatformFees",
    "TicketingFees",
    "TicketingTaxCodes",
    "PLAN_LIMITS",
    "DefaultPlan",
]
