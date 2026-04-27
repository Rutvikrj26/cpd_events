"""
Deployment configuration for single-tenant institutional deployments.

Controls how the platform behaves based on deployment mode:
- single_tenant: Private institutional deployment (default)
- saas: Legacy multi-tenant SaaS mode
"""

import os


# =============================================================================
# Deployment Mode
# =============================================================================

DEPLOYMENT_MODE: str = os.environ.get("DEPLOYMENT_MODE", "single_tenant")

# =============================================================================
# User Registration
# =============================================================================

# 'invite_only' - Admin creates all users via invitation
# 'admin_approval' - Self-registration requires admin approval
# 'open' - Anyone can register (legacy SaaS)
REGISTRATION_MODE: str = os.environ.get("REGISTRATION_MODE", "invite_only")

# =============================================================================
# Institution Branding
# =============================================================================

INSTITUTION_NAME: str = os.environ.get("INSTITUTION_NAME", "Accredit")
INSTITUTION_LOGO_URL: str = os.environ.get("INSTITUTION_LOGO_URL", "")
INSTITUTION_FAVICON_URL: str = os.environ.get("INSTITUTION_FAVICON_URL", "")
INSTITUTION_PRIMARY_COLOR: str = os.environ.get("INSTITUTION_PRIMARY_COLOR", "")
INSTITUTION_SUPPORT_EMAIL: str = os.environ.get("INSTITUTION_SUPPORT_EMAIL", "")
INSTITUTION_FOOTER_TEXT: str = os.environ.get("INSTITUTION_FOOTER_TEXT", "")
INSTITUTION_WEBSITE_URL: str = os.environ.get("INSTITUTION_WEBSITE_URL", "")

# =============================================================================
# Billing Currency
# =============================================================================
# ISO-4217 currency code used as the default for every paid surface
# (events, courses, programs) and for receipts/refunds. Stored uppercase
# so all comparisons are case-stable. Models reference this in their
# `default=` callables and services pass it through to Stripe at session
# creation time.
INSTITUTION_DEFAULT_CURRENCY: str = os.environ.get("INSTITUTION_DEFAULT_CURRENCY", "USD").upper()


def get_branding() -> dict:
    """Single source of truth for brand values exposed to API + templates."""
    return {
        "institution_name": INSTITUTION_NAME,
        "institution_logo_url": INSTITUTION_LOGO_URL,
        "institution_favicon_url": INSTITUTION_FAVICON_URL,
        "institution_primary_color": INSTITUTION_PRIMARY_COLOR,
        "institution_support_email": INSTITUTION_SUPPORT_EMAIL,
        "institution_footer_text": INSTITUTION_FOOTER_TEXT,
        "institution_website_url": INSTITUTION_WEBSITE_URL,
    }


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "DEPLOYMENT_MODE",
    "REGISTRATION_MODE",
    "INSTITUTION_NAME",
    "INSTITUTION_LOGO_URL",
    "INSTITUTION_FAVICON_URL",
    "INSTITUTION_PRIMARY_COLOR",
    "INSTITUTION_SUPPORT_EMAIL",
    "INSTITUTION_FOOTER_TEXT",
    "INSTITUTION_WEBSITE_URL",
    "INSTITUTION_DEFAULT_CURRENCY",
    "get_branding",
]
