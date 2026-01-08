"""
Billing configuration constants.

Centralizes all billing-related magic numbers including:
- Trial and grace period settings
- Plan limits (individual and organization)
- Pricing configuration
- Stripe price IDs
- Platform fees
"""

import os
from typing import Optional

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
    FEE_PERCENT: float = _validate_percentage(
        float(os.environ.get('PLATFORM_FEE_PERCENT', 2.0)),
        'PLATFORM_FEE_PERCENT'
    )


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
        float(os.environ.get('TICKETING_SERVICE_FEE_PERCENT', 0.0)),
        'TICKETING_SERVICE_FEE_PERCENT'
    )
    DEFAULT_SERVICE_FEE_FIXED: float = _validate_non_negative(
        float(os.environ.get('TICKETING_SERVICE_FEE_FIXED', 0.0)),
        'TICKETING_SERVICE_FEE_FIXED'
    )
    DEFAULT_PROCESSING_FEE_PERCENT: float = _validate_percentage(
        float(os.environ.get('TICKETING_PROCESSING_FEE_PERCENT', 0.0)),
        'TICKETING_PROCESSING_FEE_PERCENT'
    )
    DEFAULT_PROCESSING_FEE_FIXED: float = _validate_non_negative(
        float(os.environ.get('TICKETING_PROCESSING_FEE_FIXED', 0.0)),
        'TICKETING_PROCESSING_FEE_FIXED'
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
        currency = (currency or '').upper()
        return cls._get_percent(
            f'TICKETING_SERVICE_FEE_PERCENT_{currency}',
            cls.DEFAULT_SERVICE_FEE_PERCENT,
        )

    @classmethod
    def get_service_fee_fixed(cls, currency: str) -> float:
        currency = (currency or '').upper()
        return cls._get_fixed(
            f'TICKETING_SERVICE_FEE_FIXED_{currency}',
            cls.DEFAULT_SERVICE_FEE_FIXED,
        )

    @classmethod
    def get_processing_fee_percent(cls, currency: str) -> float:
        currency = (currency or '').upper()
        return cls._get_percent(
            f'TICKETING_PROCESSING_FEE_PERCENT_{currency}',
            cls.DEFAULT_PROCESSING_FEE_PERCENT,
        )

    @classmethod
    def get_processing_fee_fixed(cls, currency: str) -> float:
        currency = (currency or '').upper()
        return cls._get_fixed(
            f'TICKETING_PROCESSING_FEE_FIXED_{currency}',
            cls.DEFAULT_PROCESSING_FEE_FIXED,
        )


# =============================================================================
# Ticketing Tax Codes
# =============================================================================

class TicketingTaxCodes:
    """Stripe Tax codes for ticketing line items."""

    TICKET_IN_PERSON: str = os.environ.get('TICKETING_TAX_CODE_IN_PERSON', 'txcd_20060044')
    TICKET_ONLINE: str = os.environ.get('TICKETING_TAX_CODE_ONLINE', 'txcd_20060045')
    SERVICE_FEE: str = os.environ.get('TICKETING_TAX_CODE_SERVICE_FEE', 'txcd_20030000')
    NON_TAXABLE: str = os.environ.get('TICKETING_TAX_CODE_NON_TAXABLE', 'txcd_00000000')


# =============================================================================
# Individual Subscription Plan Limits
# =============================================================================

class IndividualPlanLimits:
    """
    Feature limits for individual user subscription plans.

    None = unlimited for that feature.

    Plans:
    - ATTENDEE: Free tier, can only attend events (no creation)
    - PROFESSIONAL: Paid tier for individual organizers
    - ORGANIZATION: Paid tier with team features
    """

    ATTENDEE: dict = {
        'events_per_month': 0,
        'certificates_per_month': 0,
        'max_attendees_per_event': 0,
    }

    PROFESSIONAL: dict = {
        'events_per_month': 30,
        'certificates_per_month': 500,
        'max_attendees_per_event': 500,
    }

    ORGANIZATION: dict = {
        'events_per_month': None,  # Unlimited
        'certificates_per_month': None,  # Unlimited
        'max_attendees_per_event': 2000,
    }

    @classmethod
    def get_limits(cls, plan: str) -> dict:
        """Get limits for a plan by name."""
        limits_map = {
            'attendee': cls.ATTENDEE,
            'professional': cls.PROFESSIONAL,
            'organization': cls.ORGANIZATION,
        }
        return limits_map.get(plan, cls.ATTENDEE)


# =============================================================================
# Organization Subscription Plan Limits
# =============================================================================

class OrganizationPlanLimits:
    """
    Feature limits for organization subscription plans.

    Organization plan structure:
    - $199/month base price
    - 1 Admin included (can create courses + events)
    - Unlimited Course Instructors (free)
    - Can add Organizers (requires separate organizer subscription)
    """

    FREE: dict = {
        'name': 'Free',
        'base_price_cents': 0,
        'events_per_month': 2,
        'courses_per_month': 1,
        'max_attendees_per_event': 50,
        'course_instructors_limit': None,  # Unlimited free instructors
    }

    # Organization Plan - $199/month
    ORGANIZATION: dict = {
        'name': 'Organization',
        'base_price_cents': 19900,  # $199/month base
        'events_per_month': None,  # Unlimited (admin has organizer capabilities)
        'courses_per_month': None,  # Unlimited
        'max_attendees_per_event': None,  # Unlimited
        'course_instructors_limit': None,  # Unlimited free instructors
        'admin_has_organizer_capabilities': True,  # Admin can create events
        
        # Seat Configuration
        'included_seats': 1, # 1 admin included
        'seat_price_cents': 12900, # $129/seat/month
    }

    @classmethod
    def get_limits(cls, plan: str) -> dict:
        """Get limits for a plan by name."""
        limits_map = {
            'free': cls.FREE,
            'organization': cls.ORGANIZATION,
            # Legacy fallbacks
            'team': cls.ORGANIZATION,
            'business': cls.ORGANIZATION,
            'enterprise': cls.ORGANIZATION,
        }
        return limits_map.get(plan, cls.FREE)


# =============================================================================
# Pricing Configuration (in cents)
# =============================================================================

class PricingConfig:
    """
    Plan pricing in cents.

    For display purposes - actual pricing is managed in Stripe.
    Annual prices reflect ~17% discount from monthly.
    """

    # Individual Plans
    ATTENDEE: int = 0  # Free

    STARTER_MONTHLY: int = 4900  # $49/month
    STARTER_ANNUAL: int = 4100  # $41/month (billed annually at $492)

    PROFESSIONAL_MONTHLY: int = 9900  # $99/month
    PROFESSIONAL_ANNUAL: int = 8300  # $83/month (billed annually at $996)

    PREMIUM_MONTHLY: int = 19900  # $199/month
    PREMIUM_ANNUAL: int = 16600  # $166/month (billed annually at $1,992)

    # Organization Plan
    ORGANIZATION_MONTHLY: int = 19900  # $199/month
    ORGANIZATION_ANNUAL: int = 16600   # $166/month (~17% off, billed $1992/year)

    @classmethod
    def get_price(cls, plan: str, annual: bool = False) -> int:
        """Get price for a plan."""
        prices = {
            'attendee': cls.ATTENDEE,
            'starter': cls.STARTER_ANNUAL if annual else cls.STARTER_MONTHLY,
            'professional': cls.PROFESSIONAL_ANNUAL if annual else cls.PROFESSIONAL_MONTHLY,
            'premium': cls.PREMIUM_ANNUAL if annual else cls.PREMIUM_MONTHLY,
            'organization': cls.ORGANIZATION_ANNUAL if annual else cls.ORGANIZATION_MONTHLY,
            # Legacy mappings
            'team': cls.ORGANIZATION_ANNUAL if annual else cls.ORGANIZATION_MONTHLY,
        }
        return prices.get(plan, 0)


# =============================================================================
# Stripe Price IDs (from environment)
# =============================================================================

class StripePriceIds:
    """
    Stripe Price IDs loaded from environment variables.

    These map to prices configured in the Stripe Dashboard.
    If not set, billing will use database-driven pricing (StripeProduct model).
    """

    STARTER: Optional[str] = os.environ.get('STRIPE_PRICE_STARTER')
    STARTER_ANNUAL: Optional[str] = os.environ.get('STRIPE_PRICE_STARTER_ANNUAL')

    PROFESSIONAL: Optional[str] = os.environ.get('STRIPE_PRICE_PROFESSIONAL')
    PROFESSIONAL_ANNUAL: Optional[str] = os.environ.get('STRIPE_PRICE_PROFESSIONAL_ANNUAL')

    PREMIUM: Optional[str] = os.environ.get('STRIPE_PRICE_PREMIUM')
    PREMIUM_ANNUAL: Optional[str] = os.environ.get('STRIPE_PRICE_PREMIUM_ANNUAL')

    TEAM: Optional[str] = os.environ.get('STRIPE_PRICE_TEAM')
    TEAM_ANNUAL: Optional[str] = os.environ.get('STRIPE_PRICE_TEAM_ANNUAL')

    ORGANIZATION: Optional[str] = os.environ.get('STRIPE_PRICE_ORGANIZATION')
    ORGANIZATION_ANNUAL: Optional[str] = os.environ.get('STRIPE_PRICE_ORGANIZATION_ANNUAL')

    ENTERPRISE: Optional[str] = os.environ.get('STRIPE_PRICE_ENTERPRISE')

    # Legacy mappings
    ORGANIZER: Optional[str] = os.environ.get('STRIPE_PRICE_PROFESSIONAL')
    
    @classmethod
    def get_price_id(cls, plan: str, annual: bool = False) -> Optional[str]:
        """Get Stripe price ID for a plan."""
        suffix = '_ANNUAL' if annual else ''
        attr_name = f"{plan.upper()}{suffix}"
        # Handle 'team' mapping to organization if needed, or leave rigid
        if plan == 'team': attr_name = f"ORGANIZATION{suffix}"
        return getattr(cls, attr_name, None)

    @classmethod
    def get_price_id(cls, plan: str, annual: bool = False) -> Optional[str]:
        """Get Stripe price ID for a plan."""
        suffix = '_ANNUAL' if annual else ''
        attr_name = f"{plan.upper()}{suffix}"
        return getattr(cls, attr_name, None)

    @classmethod
    def as_dict(cls) -> dict:
        """Return all price IDs as a dictionary (for backward compatibility)."""
        return {
            'starter': cls.STARTER,
            'starter_annual': cls.STARTER_ANNUAL,
            'professional': cls.PROFESSIONAL,
            'professional_annual': cls.PROFESSIONAL_ANNUAL,
            'premium': cls.PREMIUM,
            'premium_annual': cls.PREMIUM_ANNUAL,
            'team': cls.TEAM,
            'team_annual': cls.TEAM_ANNUAL,
            'enterprise': cls.ENTERPRISE,
            # Legacy
            'organizer': cls.ORGANIZER,
            'organization': cls.ORGANIZATION,
        }


# =============================================================================
# Default Plan
# =============================================================================

class DefaultPlan:
    """Default plan for new users."""

    NAME: str = os.environ.get('BILLING_DEFAULT_PLAN', 'attendee')


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'PlatformFees',
    'TicketingFees',
    'TicketingTaxCodes',
    'IndividualPlanLimits',
    'OrganizationPlanLimits',
    'PricingConfig',
    'StripePriceIds',
    'DefaultPlan',
]
