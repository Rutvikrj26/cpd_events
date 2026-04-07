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

# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "DEPLOYMENT_MODE",
    "REGISTRATION_MODE",
    "INSTITUTION_NAME",
    "INSTITUTION_LOGO_URL",
]
