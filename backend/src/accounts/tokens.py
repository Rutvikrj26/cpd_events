"""Signed-token primitives shared across self-service auth flows.

Two distinct signed-token surfaces use this module:

  - ``LearningInvitation`` — organizer-issued invites (existing).
  - ``MagicLink``         — self-claim and email-link sign-in (new).

Each surface gets a distinct salt so a leaked token cannot be replayed
against a different endpoint. Verification re-fetches the row and matches
the secret column; a leaked DB column alone cannot mint valid links.

The signer's ``max_age`` is the upper bound — the row's own
``expires_at`` is the authoritative gate the views should still check.
"""

from __future__ import annotations

from typing import Optional

from django.core.signing import BadSignature, SignatureExpired, TimestampSigner


def sign_token(salt: str, uuid_str: str, secret: str) -> str:
    """Return a URL-safe signed token over ``uuid:secret`` with the given salt.

    Caller embeds the result in the link emailed to the user.
    """
    return TimestampSigner(salt=salt).sign(f"{uuid_str}:{secret}")


def verify_token(salt: str, max_age_seconds: int, uuid_str: str, token: str) -> Optional[str]:
    """Return the unsigned secret iff signature, age, and uuid all match.

    Returns ``None`` on any failure so callers can answer with a uniform
    404 (don't leak which rows exist). Caller is responsible for fetching
    the row by ``uuid_str`` and verifying the returned secret matches the
    stored column.
    """
    try:
        unsigned = TimestampSigner(salt=salt).unsign(token, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None
    try:
        signed_uuid, signed_secret = unsigned.split(':', 1)
    except ValueError:
        return None
    if signed_uuid != str(uuid_str):
        return None
    return signed_secret


# --- Salts ---------------------------------------------------------------

INVITE_TOKEN_SALT = 'learning-invitation'
MAGIC_LINK_SALT = 'magic-link'


# --- Lifetimes (upper bound; row's expires_at is the authoritative gate) -

# 30 days. Matches the LearningInvitation row's default expires_at.
INVITE_TOKEN_MAX_AGE_SECONDS = 30 * 24 * 60 * 60

# 90 days. A paid registration's claim shouldn't lock users out quickly;
# the resend-claim affordance covers anything beyond this.
MAGIC_LINK_CLAIM_MAX_AGE_SECONDS = 90 * 24 * 60 * 60

# 30 minutes. Email-link sign-in is a fresh authentication challenge —
# short-lived for safety.
MAGIC_LINK_SIGN_IN_MAX_AGE_SECONDS = 30 * 60
