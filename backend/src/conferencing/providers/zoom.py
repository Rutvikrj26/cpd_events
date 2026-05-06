"""
Zoom video conferencing provider implementation.

Architecture:
- Authenticates against Zoom REST via Server-to-Server (S2S) OAuth.
  Single admin Zoom account owns every meeting on the platform.
  S2S apps are private to a Zoom account and don't require marketplace
  publication.
- Recording is Zoom Cloud (auto-started by meeting setting); we pull the
  artifact into our GCS bucket post-meeting via the recording.completed
  webhook (handled in conferencing/tasks.py).
- Live transcription is Zoom-native; we ingest the post-meeting VTT.
- Webhook signing follows Zoom's HMAC scheme:
    signature = "v0=" + hmac_sha256(secret_token, "v0:" + ts + ":" + body)
  CRC validation challenges (sent on subscription save) are handled in
  ``parse_webhook`` — callers should detect ``WebhookEvent.type == 'crc_challenge'``
  and respond with the plainToken/encryptedToken pair from metadata.
"""

import base64
import hashlib
import hmac
import json
import logging
import time
from typing import Any
from urllib.parse import urlencode

import requests
from django.conf import settings

from conferencing.provider import (
    ParticipantInfo,
    RegistrantInfo,
    RoomResult,
    VideoProvider,
    WebhookEvent,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# S2S OAuth token client
# ---------------------------------------------------------------------------


class _ZoomTokenClient:
    """Caches the S2S bearer token in-process.

    Zoom's S2S tokens are valid for 60 minutes. We refresh at T-5min to
    avoid serving an expired token under clock skew. The cache is
    process-local (no Redis) — every Django/Cloud-Tasks worker keeps
    its own copy. That's acceptable because token issuance is cheap and
    Zoom does not rate-limit token fetches aggressively.
    """

    _SKEW_SECONDS = 5 * 60  # refresh 5 minutes before expiry

    def __init__(self):
        self._token: str = ''
        self._expires_at: float = 0.0  # monotonic seconds

    def get(self, *, account_id: str, client_id: str, client_secret: str) -> str:
        if self._token and time.monotonic() < self._expires_at - self._SKEW_SECONDS:
            return self._token

        url = getattr(settings, 'ZOOM_OAUTH_TOKEN_URL', 'https://zoom.us/oauth/token')
        basic = base64.b64encode(f'{client_id}:{client_secret}'.encode()).decode()
        resp = requests.post(
            url,
            params={'grant_type': 'account_credentials', 'account_id': account_id},
            headers={'Authorization': f'Basic {basic}'},
            timeout=10,
        )
        resp.raise_for_status()
        body = resp.json()
        self._token = body['access_token']
        # `expires_in` is seconds (typically 3600). Anchor on monotonic
        # to avoid wall-clock issues.
        self._expires_at = time.monotonic() + int(body.get('expires_in', 3600))
        return self._token

    def invalidate(self) -> None:
        """Clear the cached token (force a refresh on next get)."""
        self._token = ''
        self._expires_at = 0.0


# Module-level singleton — VideoProvider is itself a singleton via
# get_video_provider(), but separating the token cache here makes it
# easy to swap out in tests.
_token_client = _ZoomTokenClient()


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class ZoomProvider(VideoProvider):
    """Zoom Server-to-Server OAuth implementation of VideoProvider."""

    def __init__(self):
        self._account_id = getattr(settings, 'ZOOM_ACCOUNT_ID', '') or ''
        self._client_id = getattr(settings, 'ZOOM_CLIENT_ID', '') or ''
        self._client_secret = getattr(settings, 'ZOOM_CLIENT_SECRET', '') or ''
        self._admin_user_id = getattr(settings, 'ZOOM_ADMIN_USER_ID', '') or ''
        self._webhook_secret = getattr(settings, 'ZOOM_WEBHOOK_SECRET_TOKEN', '') or ''
        self._instructor_host_mode = getattr(
            settings, 'ZOOM_INSTRUCTOR_HOST_MODE', 'alternative_host',
        )
        self._api_base = getattr(settings, 'ZOOM_API_BASE_URL', 'https://api.zoom.us/v2').rstrip('/')

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def is_configured(self) -> bool:
        return bool(
            self._account_id
            and self._client_id
            and self._client_secret
            and self._admin_user_id
        )

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _token(self) -> str:
        return _token_client.get(
            account_id=self._account_id,
            client_id=self._client_id,
            client_secret=self._client_secret,
        )

    def _headers(self) -> dict:
        return {
            'Authorization': f'Bearer {self._token()}',
            'Content-Type': 'application/json',
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
        params: dict | None = None,
        timeout: int = 15,
    ) -> requests.Response:
        url = f'{self._api_base}{path}'
        resp = requests.request(
            method,
            url,
            headers=self._headers(),
            json=json_body,
            params=params,
            timeout=timeout,
        )
        # 401 → token may have been revoked; one retry after invalidating cache.
        if resp.status_code == 401:
            _token_client.invalidate()
            resp = requests.request(
                method, url, headers=self._headers(), json=json_body,
                params=params, timeout=timeout,
            )
        return resp

    # ------------------------------------------------------------------
    # Room lifecycle
    # ------------------------------------------------------------------

    def create_room(
        self,
        name: str,
        metadata: dict | None = None,
        max_participants: int = 0,
    ) -> RoomResult:
        """Create a Zoom meeting on behalf of the admin user.

        Settings applied:
        * Auto-recording to cloud (we pull post-meeting).
        * Registration required + auto-approve (Zoom emails attendees).
        * Join-before-host on (instructors can start without admin).
        * Waiting room on (configurable per event via metadata).
        * Alternative hosts populated from ``metadata['alternative_hosts']``
          (comma-separated list of instructor emails). Caller is
          responsible for gating on Licensed-seat availability.
        """
        meta = metadata or {}
        alternative_hosts = meta.get('alternative_hosts', '') or ''
        scheduled_for = meta.get('start_time')  # ISO 8601 string, optional
        duration_minutes = int(meta.get('duration_minutes', 60))
        topic = meta.get('topic') or name[:200]

        body: dict[str, Any] = {
            'topic': topic,
            'type': 2 if not scheduled_for else 2,  # 2 = scheduled meeting
            'duration': duration_minutes,
            'settings': {
                'host_video': True,
                'participant_video': True,
                'join_before_host': True,
                'jbh_time': 0,
                'mute_upon_entry': True,
                'waiting_room': bool(meta.get('waiting_room', True)),
                'auto_recording': 'cloud',
                'approval_type': 0,  # auto-approve registration
                'registration_type': 1,  # one-time meeting
                'alternative_hosts': alternative_hosts,
                'alternative_hosts_email_notification': True,
                'email_notification': True,
                'registrants_email_notification': True,
                'registrants_confirmation_email': True,
                'meeting_authentication': False,
            },
        }
        if scheduled_for:
            body['start_time'] = scheduled_for
            body['timezone'] = meta.get('timezone', 'UTC')
        if max_participants:
            # Zoom doesn't enforce per-meeting attendee caps via API for
            # standard meetings (capacity is plan-level), but we pass it
            # through as metadata so it appears in the room settings.
            body['settings']['registration_limit'] = max_participants

        resp = self._request(
            'POST', f'/users/{self._admin_user_id}/meetings', json_body=body,
        )
        resp.raise_for_status()
        data = resp.json()
        meeting_id = str(data.get('id') or '')
        meeting_uuid = data.get('uuid') or ''
        join_url = data.get('join_url') or ''
        logger.info(
            'Zoom meeting created: id=%s uuid=%s topic=%s',
            meeting_id, meeting_uuid, topic,
        )
        return RoomResult(
            room_id=meeting_uuid,
            room_name=name,
            metadata={
                **meta,
                'zoom_meeting_id': meeting_id,
                'zoom_uuid': meeting_uuid,
                'zoom_join_url': join_url,
                'zoom_start_url': data.get('start_url') or '',
                'zoom_password': data.get('password') or '',
            },
        )

    def delete_room(self, room_name: str) -> bool:
        """Delete a Zoom meeting by numeric meeting id.

        Caller is expected to pass the numeric meeting id (stored on
        VideoRoom.zoom_meeting_id) — falling back to room_name only
        works for legacy rows that aren't ours. Failures log + return False.
        """
        # We accept either a numeric id or a room_name; the caller is
        # the conferencing layer which knows the row's zoom_meeting_id.
        meeting_id = room_name
        try:
            resp = self._request('DELETE', f'/meetings/{meeting_id}')
            if resp.status_code in (204, 200):
                logger.info('Zoom meeting deleted: %s', meeting_id)
                return True
            logger.warning(
                'Zoom delete_room non-204 response: %s %s',
                resp.status_code, resp.text[:300],
            )
            return False
        except Exception:
            logger.exception('Failed to delete Zoom meeting: %s', meeting_id)
            return False

    def list_participants(self, room_name: str) -> list[ParticipantInfo]:
        """Post-meeting participant report.

        Zoom does not expose a real-time participant list via REST for
        in-progress meetings (without the dashboard licence). This method
        only succeeds AFTER the meeting ends. For live participant state,
        rely on the participant_joined / participant_left webhooks.
        """
        meeting_id = room_name
        try:
            resp = self._request(
                'GET', f'/report/meetings/{meeting_id}/participants',
                params={'page_size': 300},
            )
            if resp.status_code != 200:
                return []
            participants = resp.json().get('participants', [])
            return [
                ParticipantInfo(
                    identity=p.get('id') or p.get('user_id') or '',
                    name=p.get('name') or '',
                    metadata={
                        'email': p.get('user_email') or '',
                        'join_time': p.get('join_time'),
                        'leave_time': p.get('leave_time'),
                        'duration': p.get('duration', 0),
                        'registrant_id': p.get('registrant_id') or '',
                    },
                )
                for p in participants
            ]
        except Exception:
            logger.exception('Failed to fetch Zoom participants for %s', meeting_id)
            return []

    # ------------------------------------------------------------------
    # Tokens / join URLs
    # ------------------------------------------------------------------

    def generate_join_token(
        self,
        room_name: str,
        participant_identity: str,
        participant_name: str,
        is_host: bool = False,
        waiting: bool = False,
    ) -> str:
        """Zoom doesn't use JWTs for client join — return an empty string.

        The actual join surface is the URL (registrant URL for
        attendees, start_url for hosts). Callers should use
        ``client_join_url`` and the registration-time per-attendee URL
        instead. Returned empty string is intentional: existing API
        responses keep their ``token`` field shape, frontend just
        ignores it for Zoom rooms.
        """
        return ''

    def client_join_url(
        self,
        room_name: str,
        *,
        token: str = '',
        registrant_join_url: str = '',
    ) -> str:
        # Per-attendee URLs are passed in by caller (Registration.zoom_registrant_join_url).
        # Generic meeting URL is on VideoRoom.zoom_join_url and reaches
        # us via the meetings layer.
        return registrant_join_url

    # ------------------------------------------------------------------
    # Participant ops (no-ops — Zoom controls these in-meeting)
    # ------------------------------------------------------------------

    def update_participant(
        self,
        room_name: str,
        identity: str,
        *,
        can_publish: bool | None = None,
        can_subscribe: bool | None = None,
        metadata: str | None = None,
    ) -> bool:
        # Zoom's REST API does not support runtime track-permission
        # changes. Host controls (mute/spotlight/promote) happen in the
        # Zoom client. We accept the call and return True so callers
        # don't fail; the host can perform the action manually.
        logger.debug(
            'Zoom.update_participant is a no-op (room=%s identity=%s)',
            room_name, identity,
        )
        return True

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def start_recording(self, room_name: str, output_path: str = '') -> str:
        """No-op: cloud recording is configured at meeting create time.

        Returns the meeting_id as the recording handle so VideoRecording
        rows still have a unique egress_id. The actual recording is
        provisioned by Zoom when the meeting starts (auto_recording=cloud).
        """
        return room_name

    def stop_recording(self, egress_id: str) -> bool:
        """No-op for cloud auto-recording."""
        return True

    def recording_output_template(self) -> str:
        # Zoom recordings are downloaded by the post-meeting task;
        # storage_path is set then. No upfront template needed.
        return ''

    # ------------------------------------------------------------------
    # Registration (Zoom-specific)
    # ------------------------------------------------------------------

    def register_attendee(
        self, room_name: str, email: str, full_name: str,
    ) -> RegistrantInfo:
        """Register an attendee on the Zoom meeting.

        ``room_name`` is treated as the numeric Zoom meeting id (the
        caller passes ``video_room.zoom_meeting_id``). On success Zoom
        emails the registrant the calendar invite + personalized join
        URL automatically.
        """
        meeting_id = room_name
        first_name, _, last_name = full_name.partition(' ')
        body = {
            'email': email,
            'first_name': first_name or full_name[:64] or 'Attendee',
            'last_name': last_name or '',
            'auto_approve': True,
        }
        resp = self._request(
            'POST', f'/meetings/{meeting_id}/registrants', json_body=body,
        )
        if resp.status_code not in (200, 201):
            logger.warning(
                'Zoom register_attendee failed (%s): %s %s',
                meeting_id, resp.status_code, resp.text[:300],
            )
            return RegistrantInfo(email=email)
        data = resp.json()
        return RegistrantInfo(
            registrant_id=str(data.get('registrant_id') or ''),
            join_url=data.get('join_url') or '',
            email=email,
        )

    # ------------------------------------------------------------------
    # Webhooks
    # ------------------------------------------------------------------

    def get_webhook_dedup_key(self, headers: dict | None) -> str:
        if not headers:
            return ''
        # Zoom delivery id header (case-insensitive). Different Zoom
        # event types use slightly different headers; we accept any.
        for key in ('x-zm-trackingid', 'X-Zm-Trackingid', 'X-ZM-TRACKINGID'):
            v = headers.get(key)
            if v:
                return v
        return ''

    def verify_webhook(self, body: bytes, auth_header: str) -> bool:
        """Verify the ``x-zm-signature`` header.

        ``auth_header`` here is the full request headers serialized as
        ``"<x-zm-request-timestamp>|<x-zm-signature>"`` — callers must
        compose it before calling. We split on ``|`` and re-derive the
        HMAC. On mismatch we return False (caller 401s).

        Note: callers that pass a bare ``x-zm-signature`` will fail
        verification; the timestamp is required for replay protection.
        """
        if not self._webhook_secret:
            logger.error('Zoom webhook verification attempted without ZOOM_WEBHOOK_SECRET_TOKEN set')
            return False
        ts, _, sig = auth_header.partition('|')
        if not ts or not sig:
            return False
        message = f'v0:{ts}:{body.decode("utf-8")}'.encode()
        expected = (
            'v0=' + hmac.new(self._webhook_secret.encode(), message, hashlib.sha256).hexdigest()
        )
        return hmac.compare_digest(expected, sig)

    def parse_webhook(self, body: bytes, auth_header: str) -> WebhookEvent:
        """Parse a Zoom webhook payload into the generic shape.

        Special case: ``endpoint.url_validation`` (CRC) — surfaced as
        ``WebhookEvent(type='crc_challenge')`` with metadata carrying
        ``plain_token`` and ``encrypted_token``. The view layer responds
        with ``{plainToken, encryptedToken}`` to complete subscription
        registration.
        """
        if not self.verify_webhook(body, auth_header):
            raise PermissionError('Zoom webhook signature invalid')

        payload = json.loads(body.decode('utf-8')) if body else {}
        event_type = payload.get('event') or ''
        obj = (payload.get('payload') or {}).get('object') or {}

        # CRC handshake (sent once when subscription is saved or refreshed).
        if event_type == 'endpoint.url_validation':
            plain = (payload.get('payload') or {}).get('plainToken') or ''
            encrypted = ''
            if plain and self._webhook_secret:
                encrypted = hmac.new(
                    self._webhook_secret.encode(),
                    plain.encode(),
                    hashlib.sha256,
                ).hexdigest()
            return WebhookEvent(
                type='crc_challenge',
                room_name='',
                metadata={'plain_token': plain, 'encrypted_token': encrypted},
            )

        # Map Zoom event types to our generic vocabulary used by tasks.py.
        type_map = {
            'meeting.started': 'room_started',
            'meeting.ended': 'room_finished',
            'meeting.participant_joined': 'participant_joined',
            'meeting.participant_left': 'participant_left',
            'recording.started': 'recording_started',
            'recording.completed': 'recording_ended',
        }

        room_id = obj.get('uuid') or ''
        meeting_numeric_id = str(obj.get('id') or '')
        room_name = obj.get('topic') or meeting_numeric_id

        participant_identity = ''
        participant_name = ''
        meta: dict = {'zoom_meeting_id': meeting_numeric_id, 'zoom_uuid': room_id}

        participant = obj.get('participant') or {}
        if participant:
            participant_identity = participant.get('user_id') or participant.get('id') or ''
            participant_name = participant.get('user_name') or ''
            meta['email'] = participant.get('email') or ''
            meta['registrant_id'] = participant.get('registrant_id') or ''
            meta['join_time'] = participant.get('join_time')
            meta['leave_time'] = participant.get('leave_time')

        if event_type == 'recording.completed':
            recording_files = obj.get('recording_files') or []
            meta['recording_files'] = recording_files
            # Surface convenience handle so tasks.py can dispatch the
            # download without re-fetching.
            meta['download_token'] = obj.get('download_access_token') or payload.get('download_token') or ''

        return WebhookEvent(
            type=type_map.get(event_type, event_type),
            room_name=room_name,
            room_id=room_id,
            participant_identity=participant_identity,
            participant_name=participant_name,
            timestamp=None,  # we anchor on receipt time in tasks.py
            metadata=meta,
        )

    # ------------------------------------------------------------------
    # Recording fetch helpers (used by conferencing/tasks.py)
    # ------------------------------------------------------------------

    def get_meeting_recordings(self, meeting_id: str) -> dict:
        """GET /meetings/{id}/recordings — returns the full payload."""
        resp = self._request('GET', f'/meetings/{meeting_id}/recordings')
        resp.raise_for_status()
        return resp.json()

    def stream_recording_file(self, download_url: str, *, download_token: str = ''):
        """Yield chunks of a recording file from Zoom Cloud.

        Zoom returns short-lived URLs that require either the S2S bearer
        token or a download_token (passed in the recording.completed
        webhook). The download_token is preferred when present because
        it scopes access to just the recording.
        """
        if download_token:
            url = download_url + ('&' if '?' in download_url else '?') + urlencode({'access_token': download_token})
            headers = {}
        else:
            url = download_url
            headers = {'Authorization': f'Bearer {self._token()}'}
        with requests.get(url, headers=headers, stream=True, timeout=300) as resp:
            resp.raise_for_status()
            for chunk in resp.iter_content(chunk_size=1 << 16):
                if chunk:
                    yield chunk

    def delete_recording(self, meeting_id: str, recording_id: str = '') -> bool:
        """Purge a recording from Zoom Cloud after we've copied it to GCS.

        If ``recording_id`` is empty, deletes ALL recordings for the
        meeting (the meeting-level endpoint). Pass an explicit
        recording_id to delete a single file.
        """
        try:
            if recording_id:
                resp = self._request(
                    'DELETE', f'/meetings/{meeting_id}/recordings/{recording_id}',
                    params={'action': 'trash'},
                )
            else:
                resp = self._request(
                    'DELETE', f'/meetings/{meeting_id}/recordings',
                    params={'action': 'trash'},
                )
            return resp.status_code in (200, 204)
        except Exception:
            logger.exception('Failed to delete Zoom recording (meeting=%s)', meeting_id)
            return False

    def fetch_admin_zak(self) -> str:
        """Fetch the admin user's ZAK token (host-impersonation join key).

        Used only when ZOOM_INSTRUCTOR_HOST_MODE='zak_proxy'. The returned
        token, appended to a join URL as ?zak=<token>, lets the holder
        join as the admin (host privileges). Tokens are short-lived.
        """
        resp = self._request(
            'GET', f'/users/{self._admin_user_id}/token', params={'type': 'zak'},
        )
        resp.raise_for_status()
        return resp.json().get('token', '')
