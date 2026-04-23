"""Stripe client initialisation.

One place to pin the API version and wire the key from settings. Import
``get_stripe()`` rather than ``import stripe`` directly so the version pin
and key are always applied consistently.
"""

from __future__ import annotations

import logging

from django.conf import settings

logger = logging.getLogger(__name__)

# Pin the Stripe API version so upgrades are intentional. Bump deliberately,
# with a test pass, and not in response to a warning.
STRIPE_API_VERSION = "2024-06-20"


def get_stripe():
    """Return the ``stripe`` module with ``api_key`` and ``api_version`` set.

    Callers should always go through this helper so nothing in the codebase
    relies on the global module-level defaults picking up env vars correctly.
    """
    import stripe

    stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", None) or ""
    stripe.api_version = STRIPE_API_VERSION
    # 2 automatic retries cover transient network blips. The library backs
    # off exponentially and respects idempotency keys we pass, which is
    # why every mutating call must pass one.
    stripe.max_network_retries = 2
    return stripe


def webhook_secret() -> str:
    return getattr(settings, "STRIPE_WEBHOOK_SECRET", "") or ""
