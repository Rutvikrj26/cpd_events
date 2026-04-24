"""Firebase Admin SDK client — lazy-initialized, used only for verifying
ID tokens produced by the frontend Firebase Web SDK (Google sign-in).

Configuration (settings.py):
    FIREBASE_PROJECT_ID         required when Firebase auth is used
    FIREBASE_CREDENTIALS_JSON   inline service-account JSON (preferred in dev)
    FIREBASE_CREDENTIALS_PATH   path to a service-account JSON file

If neither credential source is set, ``verify_id_token`` raises
``FirebaseNotConfigured`` so the caller can return a 503 instead of 500.
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_initialized = False
_init_failed: str | None = None


class FirebaseNotConfigured(Exception):
    """Raised when Firebase is required but credentials are not configured."""


def _load_credentials():
    from firebase_admin import credentials

    if settings.FIREBASE_CREDENTIALS_JSON:
        try:
            data = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
        except json.JSONDecodeError as exc:
            raise FirebaseNotConfigured(f"FIREBASE_CREDENTIALS_JSON is not valid JSON: {exc}") from exc
        return credentials.Certificate(data)

    if settings.FIREBASE_CREDENTIALS_PATH:
        return credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)

    raise FirebaseNotConfigured(
        "Firebase credentials not configured — set FIREBASE_CREDENTIALS_JSON or FIREBASE_CREDENTIALS_PATH."
    )


def _ensure_initialized() -> None:
    global _initialized, _init_failed  # noqa: PLW0603

    if _initialized:
        return
    if _init_failed:
        raise FirebaseNotConfigured(_init_failed)

    with _lock:
        if _initialized:
            return
        if _init_failed:
            raise FirebaseNotConfigured(_init_failed)

        try:
            import firebase_admin

            if firebase_admin._apps:  # already initialized elsewhere
                _initialized = True
                return

            cred = _load_credentials()
            options: dict[str, Any] = {}
            if settings.FIREBASE_PROJECT_ID:
                options["projectId"] = settings.FIREBASE_PROJECT_ID
            firebase_admin.initialize_app(cred, options or None)
            _initialized = True
            logger.info("firebase.initialized", extra={"project_id": settings.FIREBASE_PROJECT_ID or None})
        except FirebaseNotConfigured:
            raise
        except Exception as exc:
            _init_failed = f"Firebase initialization failed: {exc}"
            logger.exception("firebase.init_failed")
            raise FirebaseNotConfigured(_init_failed) from exc


def verify_id_token(id_token: str) -> dict[str, Any]:
    """Verify a Firebase ID token. Returns the decoded claims.

    Raises ``FirebaseNotConfigured`` if Firebase isn't set up, or ``ValueError``
    if the token is invalid/expired (wrapping the provider's own exception).
    """
    _ensure_initialized()

    from firebase_admin import auth as fb_auth

    try:
        return fb_auth.verify_id_token(id_token, check_revoked=True)
    except fb_auth.RevokedIdTokenError as exc:
        raise ValueError("Token has been revoked.") from exc
    except fb_auth.ExpiredIdTokenError as exc:
        raise ValueError("Token has expired.") from exc
    except fb_auth.InvalidIdTokenError as exc:
        raise ValueError(f"Invalid token: {exc}") from exc
    except Exception as exc:
        # Defensive: any other firebase error -> opaque invalid-token.
        raise ValueError("Token verification failed.") from exc
