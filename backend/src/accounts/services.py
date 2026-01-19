"""
Zoom OAuth service for accounts.
"""

import logging
from typing import Any

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class ZoomService:
    """
    Service for Zoom OAuth integration.

    Handles:
    - OAuth initiation
    - Token exchange
    - Token refresh
    - Disconnection
    """

    BASE_URL = "https://zoom.us/oauth"
    API_URL = "https://api.zoom.us/v2"

    @property
    def client_id(self) -> str | None:
        return getattr(settings, "ZOOM_CLIENT_ID", None)

    @property
    def client_secret(self) -> str | None:
        return getattr(settings, "ZOOM_CLIENT_SECRET", None)

    @property
    def redirect_uri(self) -> str | None:
        return getattr(settings, "ZOOM_REDIRECT_URI", None)

    @property
    def is_configured(self) -> bool:
        """Check if Zoom is properly configured."""
        return bool(self.client_id and self.client_secret and self.redirect_uri)

    def get_authorization_url(self, state: str) -> str:
        """
        Get Zoom OAuth authorization URL.

        Args:
            state: CSRF state token

        Returns:
            Authorization URL
        """
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
        }

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.BASE_URL}/authorize?{query}"

    def initiate_oauth(self, user) -> dict[str, Any]:
        """
        Initiate Zoom OAuth flow for a user.

        Returns:
            Dict with authorization_url and state
        """
        # Unconditional debug logging
        logger.error(f"DEBUG ZOOM CONFIG CHECK: configured={self.is_configured}")
        logger.error(f"DEBUG CLIENT_ID: '{self.client_id}' (Type: {type(self.client_id)})")
        logger.error(f"DEBUG REDIRECT_URI: '{self.redirect_uri}' (Type: {type(self.redirect_uri)})")

        if not self.is_configured:
            return {"success": False, "error": "Zoom is not configured"}

        # Generate and save state
        from common.utils import generate_verification_code

        state = generate_verification_code(32)

        # Store state in user session or cache
        # For simplicity, we'll use a simple pattern here
        # In production, use Redis or session

        auth_url = self.get_authorization_url(state)

        return {"success": True, "authorization_url": auth_url, "state": state}

    def complete_oauth(self, user, code: str) -> dict[str, Any]:
        """
        Complete OAuth flow by exchanging code for tokens.

        Args:
            user: User to connect Zoom to
            code: Authorization code from Zoom

        Returns:
            Dict with success status and connection
        """
        from accounts.models import ZoomConnection

        if not self.is_configured:
            return {"success": False, "error": "Zoom is not configured"}

        try:
            # Exchange code for tokens
            token_url = f"{self.BASE_URL}/token"

            auth = (self.client_id, self.client_secret)
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
            }

            response = requests.post(token_url, auth=auth, data=data, timeout=30)

            if response.status_code != 200:
                logger.error(f"Zoom token exchange failed: {response.text}")
                return {"success": False, "error": "Failed to exchange authorization code"}

            token_data = response.json()

            # Get user info from Zoom
            user_info = self._get_zoom_user_info(token_data["access_token"])
            if not user_info:
                return {"success": False, "error": "Failed to get Zoom user info"}

            # Create or update connection
            connection, created = ZoomConnection.objects.update_or_create(
                user=user,
                defaults={
                    "access_token": token_data["access_token"],
                    "refresh_token": token_data["refresh_token"],
                    "token_expires_at": timezone.now() + timezone.timedelta(seconds=token_data.get("expires_in", 3600)),
                    "zoom_user_id": user_info.get("id", ""),
                    "zoom_account_id": user_info.get("account_id", ""),
                    "zoom_email": user_info.get("email", ""),
                    "scopes": token_data.get("scope", ""),
                    "is_active": True,
                    "error_count": 0,
                    "last_error": "",
                },
            )

            return {"success": True, "connection": connection, "created": created}

        except requests.RequestException as e:
            logger.error(f"Zoom OAuth request failed: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Zoom OAuth failed: {e}")
            return {"success": False, "error": str(e)}

    def refresh_tokens(self, connection) -> bool:
        """
        Refresh expired tokens.

        Args:
            connection: ZoomConnection to refresh

        Returns:
            True if successful
        """
        if not self.is_configured:
            return False

        try:
            token_url = f"{self.BASE_URL}/token"

            auth = (self.client_id, self.client_secret)
            data = {
                "grant_type": "refresh_token",
                "refresh_token": connection.refresh_token,
            }

            response = requests.post(token_url, auth=auth, data=data, timeout=30)

            if response.status_code != 200:
                logger.error(f"Zoom token refresh failed: {response.text}")
                connection.record_error(f"Token refresh failed: {response.text}")
                return False

            token_data = response.json()

            connection.update_tokens(
                access_token=token_data["access_token"],
                refresh_token=token_data["refresh_token"],
                expires_in=token_data.get("expires_in", 3600),
            )

            return True

        except Exception as e:
            logger.error(f"Zoom token refresh failed: {e}")
            connection.record_error(str(e))
            return False

    def disconnect(self, user) -> bool:
        """
        Disconnect Zoom from user account.

        Args:
            user: User to disconnect

        Returns:
            True if successful
        """
        from accounts.models import ZoomConnection

        try:
            connection = ZoomConnection.objects.get(user=user)

            # Optionally revoke token at Zoom
            if connection.access_token:
                try:
                    self._revoke_token(connection.access_token)
                except Exception:
                    pass  # Continue even if revoke fails

            connection.disconnect()
            return True

        except ZoomConnection.DoesNotExist:
            return True  # Already disconnected
        except Exception as e:
            logger.error(f"Zoom disconnect failed: {e}")
            return False

    def _get_zoom_user_info(self, access_token: str) -> dict | None:
        """Get Zoom user info."""
        try:
            response = requests.get(f"{self.API_URL}/users/me", headers={"Authorization": f"Bearer {access_token}"}, timeout=30)

            if response.status_code == 200:
                return response.json()

            logger.error(f"Failed to get Zoom user info: {response.text}")
            return None

        except Exception as e:
            logger.error(f"Zoom user info request failed: {e}")
            return None

    def _revoke_token(self, access_token: str):
        """Revoke OAuth token at Zoom."""
        try:
            requests.post(
                f"{self.BASE_URL}/revoke", auth=(self.client_id, self.client_secret), data={"token": access_token}, timeout=30
            )
        except Exception as e:
            logger.error(f"Token revoke failed: {e}")

    def get_access_token(self, connection) -> str | None:
        """
        Get valid access token, refreshing if needed.

        Args:
            connection: ZoomConnection

        Returns:
            Valid access token or None
        """
        if not connection.is_active:
            return None

        if connection.needs_refresh and not self.refresh_tokens(connection):
            return None

        connection.record_usage()
        return connection.access_token

    def create_meeting(self, event) -> dict[str, Any]:
        """
        Create a Zoom meeting for an event.

        Args:
            event: Event instance

        Returns:
            Dict with success status and meeting details
        """
        from accounts.models import ZoomConnection
        from common.utils import generate_verification_code

        try:
            # 1. Get Zoom connection for event owner
            connection = ZoomConnection.objects.get(user=event.owner, is_active=True)

            # 2. Get valid access token
            access_token = self.get_access_token(connection)
            if not access_token:
                return {"success": False, "error": "Could not get valid Zoom access token"}

            # 3. Construct payload
            # Zoom API: POST /users/me/meetings

            # Password (required for most accounts)
            password = event.zoom_password or generate_verification_code(8)

            payload = {
                "topic": event.title,
                "type": 2,  # Scheduled meeting
                "start_time": event.starts_at.isoformat(),
                "duration": event.duration_minutes,
                "timezone": event.timezone,
                "password": password,
                "agenda": event.short_description or event.title,
                "approval_type": 0,  # Auto-approve registrants
                "registration_type": 1,  # Register once for all occurrences
                "settings": {
                    "host_video": True,
                    "participant_video": False,
                    "join_before_host": False,
                    "mute_upon_entry": True,
                    "waiting_room": True,
                    "auto_recording": "cloud" if event.recording_enabled else "none",
                    # 'registrants_email_notification': True # We handle emails ourselves
                },
            }

            # Apply any custom zoom_settings provided in event model
            if event.zoom_settings:
                payload["settings"].update(event.zoom_settings)

            # 4. Make request using helper with retry logic
            path = "users/me/meetings"
            result = self._make_zoom_request("POST", path, connection, payload)

            if not result["success"]:
                error_msg = f"Zoom API error: {result.get('status_code')}"
                try:
                    error_detail = result.get("data") or {}
                    if not error_detail and result.get("text"):
                        import json

                        error_detail = json.loads(result["text"])

                    if "message" in error_detail:
                        error_msg = f"Zoom: {error_detail['message']}"
                except Exception:
                    pass
                return {"success": False, "error": error_msg}

            data = result["data"]

            # 5. Update event
            event.zoom_meeting_id = str(data.get("id", ""))
            event.zoom_meeting_uuid = data.get("uuid", "")
            event.zoom_join_url = data.get("join_url", "")
            event.zoom_start_url = data.get("start_url", "")
            event.zoom_password = data.get("password", password)

            event.save(
                update_fields=[
                    "zoom_meeting_id",
                    "zoom_meeting_uuid",
                    "zoom_join_url",
                    "zoom_start_url",
                    "zoom_password",
                    "updated_at",
                ]
            )

            connection.record_usage()

            return {"success": True, "meeting": data}

        except ZoomConnection.DoesNotExist:
            return {"success": False, "error": "User does not have connected Zoom account"}
        except Exception as e:
            logger.error(f"Create meeting failed: {e}")
            return {"success": False, "error": str(e)}

    def create_meeting_for_course(self, course) -> dict[str, Any]:
        """
        Create a Zoom meeting for a hybrid course.

        Args:
            course: Course instance

        Returns:
            Dict with success status and meeting details
        """
        from accounts.models import ZoomConnection
        from common.utils import generate_verification_code

        try:
            # Use owner for courses
            owner = course.owner
            if not owner:
                return {"success": False, "error": "Course has no creator/owner"}

            # 1. Get Zoom connection for course owner
            connection = ZoomConnection.objects.get(user=owner, is_active=True)

            # 2. Get valid access token
            access_token = self.get_access_token(connection)
            if not access_token:
                return {"success": False, "error": "Could not get valid Zoom access token"}

            # 3. Validate required fields
            if not course.live_session_start:
                return {"success": False, "error": "Course has no live session start time"}

            # Calculate duration from live_session_start and live_session_end
            duration = 60  # Default 60 minutes
            if course.live_session_end:
                delta = course.live_session_end - course.live_session_start
                duration = max(30, int(delta.total_seconds() / 60))  # Minimum 30 minutes

            # Password (required for most accounts)
            password = course.zoom_meeting_password or generate_verification_code(8)

            payload = {
                "topic": course.title,
                "type": 2,  # Scheduled meeting
                "start_time": course.live_session_start.isoformat(),
                "duration": duration,
                "timezone": course.live_session_timezone or "UTC",
                "password": password,
                "agenda": course.short_description or course.title,
                "approval_type": 0,  # Auto-approve registrants
                "registration_type": 1,  # Register once for all occurrences
                "settings": {
                    "host_video": True,
                    "participant_video": False,
                    "join_before_host": False,
                    "mute_upon_entry": True,
                    "waiting_room": True,
                    "auto_recording": "none",
                },
            }

            # Apply any custom zoom_settings provided in course model
            zoom_settings = course.zoom_settings or {}
            # Remove 'enabled' key as it's not a Zoom API setting
            settings_to_apply = {k: v for k, v in zoom_settings.items() if k != "enabled"}
            if settings_to_apply:
                payload["settings"].update(settings_to_apply)

            # 4. Make request using helper with retry logic
            path = "users/me/meetings"
            result = self._make_zoom_request("POST", path, connection, payload)

            if not result["success"]:
                error_msg = f"Zoom API error: {result.get('status_code')}"
                try:
                    error_detail = result.get("data") or {}
                    if not error_detail and result.get("text"):
                        import json

                        error_detail = json.loads(result["text"])

                    if "message" in error_detail:
                        error_msg = f"Zoom: {error_detail['message']}"
                except Exception:
                    pass
                return {"success": False, "error": error_msg}

            data = result["data"]

            # 5. Update course
            course.zoom_meeting_id = str(data.get("id", ""))
            course.zoom_meeting_uuid = data.get("uuid", "")
            course.zoom_meeting_url = data.get("join_url", "")
            course.zoom_start_url = data.get("start_url", "")
            course.zoom_meeting_password = data.get("password", password)

            course.save(
                update_fields=[
                    "zoom_meeting_id",
                    "zoom_meeting_uuid",
                    "zoom_meeting_url",
                    "zoom_start_url",
                    "zoom_meeting_password",
                    "updated_at",
                ]
            )

            connection.record_usage()

            return {"success": True, "meeting": data}

        except ZoomConnection.DoesNotExist:
            return {"success": False, "error": "Course creator does not have connected Zoom account"}
        except Exception as e:
            logger.error(f"Create meeting for course failed: {e}")
            return {"success": False, "error": str(e)}

    def create_meeting_for_session(self, session) -> dict[str, Any]:
        """
        Create a Zoom meeting for a specific course session.

        Args:
            session: CourseSession instance

        Returns:
            Dict with success status and meeting details
        """
        from accounts.models import ZoomConnection
        from common.utils import generate_verification_code

        try:
            course = session.course
            owner = course.owner
            if not owner:
                return {"success": False, "error": "Course has no creator/owner"}

            # 1. Get Zoom connection for course owner
            connection = ZoomConnection.objects.get(user=owner, is_active=True)

            # 2. Get valid access token
            access_token = self.get_access_token(connection)
            if not access_token:
                return {"success": False, "error": "Could not get valid Zoom access token"}

            # 3. Validate required fields
            if not session.starts_at:
                return {"success": False, "error": "Session has no start time"}

            # Password
            password = session.zoom_password or generate_verification_code(8)

            payload = {
                "topic": f"{course.title} - {session.title}",
                "type": 2,  # Scheduled meeting
                "start_time": session.starts_at.isoformat(),
                "duration": session.duration_minutes or 60,
                "timezone": session.timezone or "UTC",
                "password": password,
                "agenda": session.description or session.title,
                "approval_type": 0,  # Auto-approve registrants
                "registration_type": 1,
                "settings": {
                    "host_video": True,
                    "participant_video": False,
                    "join_before_host": False,
                    "mute_upon_entry": True,
                    "waiting_room": True,
                    "auto_recording": "none",
                },
            }

            # Apply any custom zoom_settings from session
            zoom_settings = session.zoom_settings or {}
            settings_to_apply = {k: v for k, v in zoom_settings.items() if k != "enabled"}
            if settings_to_apply:
                payload["settings"].update(settings_to_apply)

            # 4. Make request
            path = "users/me/meetings"
            result = self._make_zoom_request("POST", path, connection, payload)

            if not result["success"]:
                error_msg = f"Zoom API error: {result.get('status_code')}"
                try:
                    error_detail = result.get("data") or {}
                    if not error_detail and result.get("text"):
                        import json

                        error_detail = json.loads(result["text"])
                    if "message" in error_detail:
                        error_msg = f"Zoom: {error_detail['message']}"
                except Exception:
                    pass
                return {"success": False, "error": error_msg}

            data = result["data"]

            # 5. Update session
            session.zoom_meeting_id = str(data.get("id", ""))
            session.zoom_meeting_uuid = data.get("uuid", "")
            session.zoom_join_url = data.get("join_url", "")
            session.zoom_start_url = data.get("start_url", "")
            session.zoom_password = data.get("password", password)

            session.save(
                update_fields=[
                    "zoom_meeting_id",
                    "zoom_meeting_uuid",
                    "zoom_join_url",
                    "zoom_start_url",
                    "zoom_password",
                    "updated_at",
                ]
            )

            connection.record_usage()
            return {"success": True, "meeting": data}

        except ZoomConnection.DoesNotExist:
            return {"success": False, "error": "Course creator does not have connected Zoom account"}
        except Exception as e:
            logger.error(f"Create meeting for session failed: {e}")
            return {"success": False, "error": str(e)}

    def _make_zoom_request(
        self,
        method: str,
        path: str,
        connection,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        retry_on_401: bool = True,
    ) -> dict[str, Any]:
        """
        Make an authenticated request to Zoom API with automatic 401 retry.
        """
        access_token = self.get_access_token(connection)
        if not access_token:
            return {"success": False, "error": "Could not get valid Zoom access token"}

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        url = f"{self.API_URL}/{path.lstrip('/')}"

        try:
            if method.upper() == "POST":
                response = requests.post(url, headers=headers, json=payload, params=params, timeout=30)
            elif method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=30)
            else:
                return {"success": False, "error": f"Unsupported method: {method}"}

            if response.status_code == 401 and retry_on_401:
                logger.warning("Zoom API returned 401. Forcing token refresh and retrying.")
                if self.refresh_tokens(connection):
                    return self._make_zoom_request(method, path, connection, payload, params=params, retry_on_401=False)

            is_success = response.status_code in [200, 201]
            result = {
                "success": is_success,
                "status_code": response.status_code,
                "data": {},
                "text": response.text,
            }

            if is_success:
                result["data"] = response.json()
            else:
                # Extract error message from Zoom API response
                try:
                    error_data = response.json()
                    result["data"] = error_data
                    result["error"] = error_data.get("message", response.text)
                    logger.warning(f"Zoom API {method} {path} failed: {response.status_code} - {error_data}")
                except Exception:
                    result["error"] = response.text or f"Zoom API returned status {response.status_code}"
                    logger.warning(f"Zoom API {method} {path} failed: {response.status_code} - {response.text}")

            return result
        except Exception as e:
            logger.error(f"Zoom request failed: {e}")
            return {"success": False, "error": str(e)}

    def add_meeting_registrant(self, event, email: str, first_name: str, last_name: str) -> dict[str, Any]:
        """
        Add a registrant to a Zoom meeting.

        Args:
            event: Event instance with zoom_meeting_id
            email: Registrant email
            first_name: Registrant first name
            last_name: Registrant last name

        Returns:
            {
                'success': bool,
                'join_url': str (if success),
                'registrant_id': str (if success),
                'error': str (if failure)
            }
        """
        from accounts.models import ZoomConnection

        try:
            if not event.zoom_meeting_id:
                return {"success": False, "error": "Event has no Zoom meeting"}

            connection = ZoomConnection.objects.get(user=event.owner, is_active=True)
            access_token = self.get_access_token(connection)

            if not access_token:
                return {"success": False, "error": "Could not get Zoom access token"}

            payload = {
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "auto_approve": True,
            }

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            response = requests.post(
                f"{self.API_URL}/meetings/{event.zoom_meeting_id}/registrants", headers=headers, json=payload, timeout=30
            )

            if response.status_code not in [201, 200]:
                logger.error(f"Zoom add registrant failed: {response.status_code} - {response.text}")
                return {"success": False, "error": f"Zoom API error: {response.status_code}"}

            data = response.json()
            connection.record_usage()

            logger.info(f"Added registrant {email} to Zoom meeting {event.zoom_meeting_id}")

            return {
                "success": True,
                "join_url": data.get("join_url", ""),
                "registrant_id": data.get("id", ""),
            }

        except ZoomConnection.DoesNotExist:
            return {"success": False, "error": "No Zoom connection for event owner"}
        except Exception as e:
            logger.error(f"Add meeting registrant failed: {e}")
            return {"success": False, "error": str(e)}

    def get_past_meeting_participants(self, user, meeting_id: str) -> dict[str, Any]:
        """
        Get participants for a past meeting using the Reports API.

        Requires scope: report:read:list_meeting_participants:admin
        (or classic scope: report:read:admin)
        """
        from accounts.models import ZoomConnection

        try:
            connection = ZoomConnection.objects.get(user=user, is_active=True)

            # Use report/meetings endpoint - works for all account types with proper scope
            path = f"report/meetings/{meeting_id}/participants"
            result = self._make_zoom_request("GET", path, connection, params={"page_size": 300})

            return result

        except ZoomConnection.DoesNotExist:
            return {"success": False, "error": "No Zoom connection for user"}
        except Exception as e:
            logger.error(f"Get meeting participants failed: {e}")
            return {"success": False, "error": str(e)}


# Singleton instance
zoom_service = ZoomService()
