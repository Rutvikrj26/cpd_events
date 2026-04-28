"""Permissions specific to the conferencing app.

`IsInternalAgent` gates the agent-only endpoints (segment ingest +
transcript finalize). The agent is the `accredit-agent` Cloud Run
service; we authenticate it via HMAC-SHA256 of `(timestamp + body)`
signed with `INTERNAL_AGENT_SHARED_SECRET`. The same secret lives in
the agent service's env vars; both sides hold it but neither side
exposes it on the public API.

Why HMAC and not a JWT or service-account token:
  - The agent runs in our own infra and shouldn't need to mint a JWT
    against the public auth endpoint just to talk to a sibling service.
  - A static API key would also work but doesn't bind to the request
    body — replayed payloads with a stolen key could overwrite segments.
  - HMAC binds the signature to the exact bytes posted, with a short
    timestamp window to defeat replay. Same pattern LiveKit uses for
    its own webhook verification, so agents-and-webhooks share an
    auth idiom.
"""

from __future__ import annotations

import hmac
import hashlib
import logging
import time

from django.conf import settings
from rest_framework import permissions

logger = logging.getLogger(__name__)

# Replay window in seconds. 5 minutes is generous for clock skew between
# the agent and web service while still defeating opportunistic replay.
_MAX_TIMESTAMP_SKEW_SECONDS = 300


class IsInternalAgent(permissions.BasePermission):
    """Allow only requests signed by the accredit-agent shared secret.

    The agent must include two headers on every request:

      X-Agent-Timestamp: <unix epoch seconds, integer>
      X-Agent-Signature: <hex-encoded HMAC-SHA256 of "{timestamp}.{body}">

    Where the secret is `settings.INTERNAL_AGENT_SHARED_SECRET`. We use
    `hmac.compare_digest` for constant-time comparison and reject any
    request whose timestamp is more than 5 minutes in the past or future.
    """

    message = 'Invalid or missing agent signature.'

    def has_permission(self, request, view) -> bool:
        secret = getattr(settings, 'INTERNAL_AGENT_SHARED_SECRET', '') or ''
        if not secret:
            # Fail closed when the secret isn't configured — better to
            # 403 every internal request than to silently allow them.
            logger.warning(
                "Rejecting internal-agent request: "
                "INTERNAL_AGENT_SHARED_SECRET is not set."
            )
            return False

        timestamp = request.META.get('HTTP_X_AGENT_TIMESTAMP', '')
        signature = request.META.get('HTTP_X_AGENT_SIGNATURE', '')
        if not timestamp or not signature:
            return False

        try:
            ts = int(timestamp)
        except (TypeError, ValueError):
            return False

        # Replay-window check first — cheaper than the HMAC and short-
        # circuits stale requests before we touch the secret.
        now = int(time.time())
        if abs(now - ts) > _MAX_TIMESTAMP_SKEW_SECONDS:
            return False

        # `request.body` reads the raw bytes; DRF caches it after the
        # first call so this doesn't break downstream parsing.
        body = request.body or b''
        msg = f'{ts}.'.encode('ascii') + body
        expected = hmac.new(
            secret.encode('utf-8'), msg, hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)
