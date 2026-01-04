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

    Includes per-seat pricing for team members.
    Only OWNER, ADMIN, MANAGER roles count toward billable seats.
    MEMBER role is free and unlimited.

    Plans:
    - FREE: Basic tier with limited features
    - TEAM: Small team tier with 5 included seats
    - BUSINESS: Medium team tier with 15 included seats
    - ENTERPRISE: Large team tier with 50 included seats
    """

    FREE: dict = {
        'name': 'Free',
        'included_seats': 1,
        'seat_price_cents': 0,
        'events_per_month': 2,
        'courses_per_month': 1,
        'max_attendees_per_event': 50,
    }

    TEAM: dict = {
        'name': 'Team',
        'included_seats': 5,
        'seat_price_cents': 4900,  # $49/seat/month
        'events_per_month': None,  # Unlimited
        'courses_per_month': None,  # Unlimited
        'max_attendees_per_event': None,  # Unlimited
    }

    BUSINESS: dict = {
        'name': 'Business',
        'included_seats': 15,
        'seat_price_cents': 4500,  # $45/seat/month
        'events_per_month': None,  # Unlimited
        'courses_per_month': None,  # Unlimited
        'max_attendees_per_event': None,  # Unlimited
    }

    ENTERPRISE: dict = {
        'name': 'Enterprise',
        'included_seats': 50,
        'seat_price_cents': 4000,  # $40/seat/month
        'events_per_month': None,  # Unlimited
        'courses_per_month': None,  # Unlimited
        'max_attendees_per_event': None,  # Unlimited
    }

    @classmethod
    def get_limits(cls, plan: str) -> dict:
        """Get limits for a plan by name."""
        limits_map = {
            'free': cls.FREE,
            'team': cls.TEAM,
            'business': cls.BUSINESS,
            'enterprise': cls.ENTERPRISE,
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

    # Organization/Team Plans
    TEAM_MONTHLY: int = 29900  # $299/month (base with 5 seats)
    TEAM_ANNUAL: int = 24900  # $249/month (billed annually at $2,988)

    ENTERPRISE: int = 0  # Custom pricing

    # Legacy plan mappings
    ORGANIZER_MONTHLY: int = PROFESSIONAL_MONTHLY
    ORGANIZATION_MONTHLY: int = TEAM_MONTHLY

    @classmethod
    def get_price(cls, plan: str, annual: bool = False) -> int:
        """Get price for a plan."""
        prices = {
            'attendee': cls.ATTENDEE,
            'starter': cls.STARTER_ANNUAL if annual else cls.STARTER_MONTHLY,
            'professional': cls.PROFESSIONAL_ANNUAL if annual else cls.PROFESSIONAL_MONTHLY,
            'premium': cls.PREMIUM_ANNUAL if annual else cls.PREMIUM_MONTHLY,
            'team': cls.TEAM_ANNUAL if annual else cls.TEAM_MONTHLY,
            'enterprise': cls.ENTERPRISE,
            # Legacy
            'organizer': cls.PROFESSIONAL_ANNUAL if annual else cls.PROFESSIONAL_MONTHLY,
            'organization': cls.TEAM_ANNUAL if annual else cls.TEAM_MONTHLY,
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

    ENTERPRISE: Optional[str] = os.environ.get('STRIPE_PRICE_ENTERPRISE')

    # Legacy mappings
    ORGANIZER: Optional[str] = os.environ.get('STRIPE_PRICE_PROFESSIONAL')
    ORGANIZATION: Optional[str] = os.environ.get('STRIPE_PRICE_TEAM')

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
    'IndividualPlanLimits',
    'OrganizationPlanLimits',
    'PricingConfig',
    'StripePriceIds',
    'DefaultPlan',
]
