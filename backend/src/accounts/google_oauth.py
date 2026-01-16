"""
Google OAuth 2.0 helper functions for user authentication.
"""

from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = __import__('logging').getLogger(__name__)


def get_google_credentials():
    """Get Google OAuth credentials from settings."""
    client_id = settings.GOOGLE_CLIENT_ID
    client_secret = settings.GOOGLE_CLIENT_SECRET
    redirect_uri = settings.GOOGLE_REDIRECT_URI

    if not all([client_id, client_secret, redirect_uri]):
        raise ImproperlyConfigured("Google OAuth credentials are missing in settings.")

    return client_id, client_secret, redirect_uri


def get_google_auth_url(state: str | None = None):
    """
    Generate the Google OAuth authorization URL.
    
    Args:
        state: Optional state parameter for CSRF protection
    
    Returns:
        Authorization URL string
    """
    client_id, _, redirect_uri = get_google_credentials()

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "openid email profile",
        "access_type": "offline",  # Request refresh token
        "prompt": "select_account",  # Always show account picker
    }

    if state:
        params["state"] = state

    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    return f"{base_url}?{urlencode(params)}"


def exchange_code_for_token(code: str):
    """
    Exchange the authorization code for access and ID tokens.
    
    Args:
        code: Authorization code from Google
    
    Returns:
        Token data dict or None on failure
    """
    client_id, client_secret, redirect_uri = get_google_credentials()

    token_url = "https://oauth2.googleapis.com/token"

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    }

    try:
        response = requests.post(token_url, data=data, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Google token exchange failed: {e}")
        return None


def get_google_user_info(access_token: str):
    """
    Fetch the authenticated user's profile from Google.
    
    Args:
        access_token: Google access token
    
    Returns:
        User info dict or None on failure
    """
    user_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        response = requests.get(user_url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch Google user info: {e}")
        return None


def verify_google_id_token(id_token: str):
    """
    Verify and decode a Google ID token.
    
    This is an alternative to fetching user info via API.
    The ID token contains user information that can be extracted.
    
    Args:
        id_token: JWT ID token from Google
    
    Returns:
        Decoded token data or None on failure
    """
    client_id, _, _ = get_google_credentials()

    verify_url = "https://oauth2.googleapis.com/tokeninfo"
    params = {"id_token": id_token}

    try:
        response = requests.get(verify_url, params=params, timeout=10)
        response.raise_for_status()
        token_data = response.json()

        # Verify audience matches our client ID
        if token_data.get("aud") != client_id:
            logger.error("ID token audience mismatch")
            return None

        return token_data
    except requests.RequestException as e:
        logger.error(f"Failed to verify Google ID token: {e}")
        return None
