from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = __import__("logging").getLogger(__name__)


def get_zoom_credentials():
    client_id = settings.ZOOM_CLIENT_ID
    client_secret = settings.ZOOM_CLIENT_SECRET
    redirect_uri = settings.ZOOM_REDIRECT_URI

    if not all([client_id, client_secret, redirect_uri]):
        raise ImproperlyConfigured("Zoom credentials are missing in settings.")

    return client_id, client_secret, redirect_uri


def get_zoom_auth_url():
    """
    Generate the Zoom OAuth authorization URL.
    """
    client_id, _, redirect_uri = get_zoom_credentials()

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
    }

    # Base URL for Zoom OAuth
    base_url = "https://zoom.us/oauth/authorize"
    return f"{base_url}?{urlencode(params)}"


def exchange_code_for_token(code):
    """
    Exchange the authorization code for an access token.
    """
    client_id, client_secret, redirect_uri = get_zoom_credentials()

    token_url = "https://zoom.us/oauth/token"

    # Zoom requires Basic Auth with client_id:client_secret for this endpoint
    # OR client_id/client_secret in params. Let's use params + auth header is safest mostly
    # But checking Zoom docs: POST /oauth/token with query params or form data.
    # Usually Basic Auth header is preferred.

    auth = (client_id, client_secret)
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }

    response = requests.post(token_url, auth=auth, data=data, timeout=30)

    if not response.ok:
        logger.error(f"Zoom token exchange failed: {response.text}")
        return None

    return response.json()


def get_zoom_user_info(access_token):
    """
    Fetch the authenticated user's profile from Zoom.
    """
    user_url = "https://api.zoom.us/v2/users/me"
    headers = {"Authorization": f"Bearer {access_token}"}

    response = requests.get(user_url, headers=headers, timeout=30)

    if not response.ok:
        logger.error(f"Failed to fetch Zoom user info: {response.text}")
        return None

    return response.json()
