"""
LiveKit video conferencing provider implementation.

Uses the official ``livekit-api`` (>=0.8) Python SDK, whose transport is
async-only (``LiveKitAPI`` holds an ``aiohttp.ClientSession``). The public
method surface of this class is **synchronous** — we wrap each call in
``async_to_sync`` so existing sync callers (signals, DRF request/response
cycle, cloud-tasks runner) work unchanged. Each call creates a short-lived
``LiveKitAPI`` session; this is acceptable because room/egress lifecycle
operations are low-frequency and off the request hot path.

Capabilities:
- Room management (create, delete, list participants)
- Access token generation (JWT, sync — no network call)
- Recording via Egress (room composite)
- Webhook signature verification (sync — HMAC only, no network call)
"""

import json
import logging
from datetime import datetime, timezone

from asgiref.sync import async_to_sync
from django.conf import settings

from conferencing.provider import (
    ParticipantInfo,
    RoomResult,
    VideoProvider,
    WebhookEvent,
)

logger = logging.getLogger(__name__)


def _get_livekit_api_module():
    """Lazy import of livekit-api to allow graceful degradation if missing."""
    try:
        import livekit.api as lk_api

        return lk_api
    except ImportError as exc:
        raise RuntimeError(
            "livekit-api package is not installed. Run: uv add livekit-api"
        ) from exc


class LiveKitProvider(VideoProvider):
    """LiveKit implementation of the ``VideoProvider`` interface."""

    def __init__(self):
        self._api_key = getattr(settings, 'LIVEKIT_API_KEY', '') or ''
        self._api_secret = getattr(settings, 'LIVEKIT_API_SECRET', '') or ''
        self._host = getattr(settings, 'LIVEKIT_HOST', '') or ''
        self._ws_url = getattr(settings, 'LIVEKIT_WS_URL', '') or ''

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def is_configured(self) -> bool:
        return bool(self._api_key and self._api_secret and self._host)

    # ------------------------------------------------------------------
    # Async implementations
    # ------------------------------------------------------------------

    async def _create_api(self):
        lk = _get_livekit_api_module()
        return lk.LiveKitAPI(self._host, self._api_key, self._api_secret)

    async def _create_room_async(self, name: str, metadata, max_participants: int):
        lk = _get_livekit_api_module()
        api = await self._create_api()
        try:
            room = await api.room.create_room(
                lk.CreateRoomRequest(
                    name=name,
                    metadata=json.dumps(metadata) if metadata else "",
                    max_participants=max_participants,
                )
            )
            return room
        finally:
            await api.aclose()

    async def _delete_room_async(self, room_name: str) -> bool:
        lk = _get_livekit_api_module()
        api = await self._create_api()
        try:
            await api.room.delete_room(lk.DeleteRoomRequest(room=room_name))
            return True
        except Exception:
            logger.exception("Failed to delete LiveKit room: %s", room_name)
            return False
        finally:
            await api.aclose()

    async def _list_participants_async(self, room_name: str):
        lk = _get_livekit_api_module()
        api = await self._create_api()
        try:
            response = await api.room.list_participants(
                lk.ListParticipantsRequest(room=room_name)
            )
            return list(response.participants)
        finally:
            await api.aclose()

    async def _start_recording_async(self, room_name: str, output_path: str):
        lk = _get_livekit_api_module()
        api = await self._create_api()
        try:
            file_output = lk.EncodedFileOutput(file_type=lk.EncodedFileType.MP4)
            if output_path:
                file_output.filepath = output_path
            response = await api.egress.start_room_composite_egress(
                lk.RoomCompositeEgressRequest(
                    room_name=room_name,
                    file_outputs=[file_output],
                )
            )
            return response.egress_id
        finally:
            await api.aclose()

    async def _stop_recording_async(self, egress_id: str) -> bool:
        lk = _get_livekit_api_module()
        api = await self._create_api()
        try:
            await api.egress.stop_egress(lk.StopEgressRequest(egress_id=egress_id))
            return True
        except Exception:
            logger.exception("Failed to stop recording: egress_id=%s", egress_id)
            return False
        finally:
            await api.aclose()

    async def _dispatch_agent_async(
        self, room_name: str, agent_name: str, metadata: str,
    ) -> str | None:
        """Tell LiveKit to dispatch a registered agent into a specific room.

        Returns the dispatch_id on success, None on failure (logged).
        Idempotent on the LiveKit side — re-dispatching a known agent
        into a room it's already in is a no-op. We tolerate failures
        (logged as warnings) because transcription is non-critical
        relative to the room itself; the meeting should proceed even
        if captions don't.
        """
        lk = _get_livekit_api_module()
        api = await self._create_api()
        try:
            response = await api.agent_dispatch.create_dispatch(
                lk.CreateAgentDispatchRequest(
                    agent_name=agent_name,
                    room=room_name,
                    metadata=metadata,
                )
            )
            return response.id
        except Exception:
            logger.exception(
                "Failed to dispatch agent %s into room %s",
                agent_name, room_name,
            )
            return None
        finally:
            await api.aclose()

    # ------------------------------------------------------------------
    # Sync façade
    # ------------------------------------------------------------------

    def create_room(
        self,
        name: str,
        metadata: dict | None = None,
        max_participants: int = 0,
    ) -> RoomResult:
        room = async_to_sync(self._create_room_async)(name, metadata or {}, max_participants)
        logger.info("LiveKit room created: %s (sid=%s)", room.name, room.sid)
        return RoomResult(
            room_id=room.sid,
            room_name=room.name,
            metadata=metadata or {},
        )

    def delete_room(self, room_name: str) -> bool:
        ok = async_to_sync(self._delete_room_async)(room_name)
        if ok:
            logger.info("LiveKit room deleted: %s", room_name)
        return ok

    def dispatch_agent(
        self, room_name: str, agent_name: str, metadata: str = '',
    ) -> str | None:
        """Sync façade for `_dispatch_agent_async`. Returns the dispatch
        id on success, None on failure (already logged)."""
        return async_to_sync(self._dispatch_agent_async)(
            room_name, agent_name, metadata,
        )

    def list_participants(self, room_name: str) -> list[ParticipantInfo]:
        participants = async_to_sync(self._list_participants_async)(room_name)
        return [
            ParticipantInfo(
                identity=p.identity,
                name=p.name,
                joined_at=(
                    datetime.fromtimestamp(p.joined_at, tz=timezone.utc)
                    if p.joined_at
                    else None
                ),
            )
            for p in participants
        ]

    def start_recording(self, room_name: str, output_path: str = "") -> str:
        egress_id = async_to_sync(self._start_recording_async)(room_name, output_path)
        logger.info(
            "Recording started for room %s, egress_id=%s", room_name, egress_id
        )
        return egress_id

    def stop_recording(self, egress_id: str) -> bool:
        ok = async_to_sync(self._stop_recording_async)(egress_id)
        if ok:
            logger.info("Recording stopped: egress_id=%s", egress_id)
        return ok

    # ------------------------------------------------------------------
    # Sync-only operations (no network I/O to LiveKit server)
    # ------------------------------------------------------------------

    def generate_join_token(
        self,
        room_name: str,
        participant_identity: str,
        participant_name: str,
        is_host: bool = False,
        waiting: bool = False,
    ) -> str:
        import json

        lk = _get_livekit_api_module()
        # Waiting participants still join the room (so hosts can see & admit
        # them) but cannot publish or subscribe until upgraded.
        can_publish = True if is_host else (not waiting)
        can_subscribe = True if is_host else (not waiting)
        # Stamp `is_host` into the participant metadata so other clients can
        # see it (e.g. for the "you're the last host" leave-confirmation
        # check). LiveKit propagates `participant.metadata` to every other
        # participant in the room as a JSON string. Anything beyond
        # `is_host` is presentation-layer only — auth still flows through
        # the JWT grants above.
        metadata = json.dumps({'is_host': bool(is_host)})
        token = (
            lk.AccessToken(self._api_key, self._api_secret)
            .with_identity(participant_identity)
            .with_name(participant_name)
            .with_metadata(metadata)
            .with_grants(
                lk.VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=can_publish,
                    can_subscribe=can_subscribe,
                    room_admin=is_host,
                )
            )
        )
        jwt_str = token.to_jwt()
        logger.debug(
            "Generated join token for %s in room %s (host=%s, waiting=%s)",
            participant_identity,
            room_name,
            is_host,
            waiting,
        )
        return jwt_str

    async def _update_participant_async(
        self,
        room_name: str,
        identity: str,
        can_publish: bool | None,
        can_subscribe: bool | None,
        metadata: str | None,
    ) -> bool:
        lk = _get_livekit_api_module()
        api = await self._create_api()
        try:
            kwargs: dict = {"room": room_name, "identity": identity}
            if metadata is not None:
                kwargs["metadata"] = metadata
            if can_publish is not None or can_subscribe is not None:
                perm_kwargs: dict = {}
                if can_publish is not None:
                    perm_kwargs["can_publish"] = can_publish
                    perm_kwargs["can_publish_data"] = can_publish
                if can_subscribe is not None:
                    perm_kwargs["can_subscribe"] = can_subscribe
                kwargs["permission"] = lk.ParticipantPermission(**perm_kwargs)
            await api.room.update_participant(lk.UpdateParticipantRequest(**kwargs))
            return True
        except Exception:
            logger.exception(
                "Failed to update participant %s in room %s", identity, room_name
            )
            return False
        finally:
            await api.aclose()

    def update_participant(
        self,
        room_name: str,
        identity: str,
        *,
        can_publish: bool | None = None,
        can_subscribe: bool | None = None,
        metadata: str | None = None,
    ) -> bool:
        return async_to_sync(self._update_participant_async)(
            room_name, identity, can_publish, can_subscribe, metadata
        )

    # ------------------------------------------------------------------
    # Provider-extension overrides (defaults from VideoProvider)
    # ------------------------------------------------------------------

    def get_webhook_dedup_key(self, headers: dict | None) -> str:
        """LiveKit's webhook delivery ID is in the ``X-LiveKit-Id`` header."""
        if not headers:
            return ""
        return headers.get('X-LiveKit-Id') or headers.get('x-livekit-id') or ""

    def client_join_url(
        self,
        room_name: str,
        *,
        token: str = "",
        registrant_join_url: str = "",
    ) -> str:
        """LiveKit clients connect to the WebSocket URL; the JWT carries the room."""
        return self._ws_url

    def recording_output_template(self) -> str:
        return getattr(settings, 'LIVEKIT_RECORDING_OUTPUT_PATH_TEMPLATE', '') or ''

    def verify_webhook(self, body: bytes, auth_header: str) -> bool:
        lk = _get_livekit_api_module()
        try:
            receiver = lk.WebhookReceiver(lk.TokenVerifier(self._api_key, self._api_secret))
            receiver.receive(body.decode('utf-8'), auth_header)
            return True
        except Exception:
            logger.exception("LiveKit webhook verification failed")
            return False

    def parse_webhook(self, body: bytes, auth_header: str) -> WebhookEvent:
        lk = _get_livekit_api_module()
        receiver = lk.WebhookReceiver(lk.TokenVerifier(self._api_key, self._api_secret))
        event = receiver.receive(body.decode('utf-8'), auth_header)

        type_map = {
            "room_started": "room_started",
            "room_finished": "room_finished",
            "participant_joined": "participant_joined",
            "participant_left": "participant_left",
            "egress_started": "recording_started",
            "egress_ended": "recording_ended",
        }

        participant_identity = ""
        participant_name = ""
        if event.participant:
            participant_identity = event.participant.identity or ""
            participant_name = event.participant.name or ""

        room_name = ""
        room_id = ""
        if event.room:
            room_name = event.room.name or ""
            room_id = event.room.sid or ""

        metadata: dict = {}
        if getattr(event, 'egress_info', None):
            metadata["egress_id"] = event.egress_info.egress_id
            metadata["status"] = str(event.egress_info.status)
            # Try to surface the final file location when available.
            file_results = getattr(event.egress_info, 'file_results', None) or []
            if file_results:
                first = file_results[0]
                metadata["file_url"] = getattr(first, 'location', '') or ''
                metadata["size_bytes"] = getattr(first, 'size', 0) or 0
                metadata["duration_ms"] = getattr(first, 'duration', 0) or 0

        return WebhookEvent(
            type=type_map.get(event.event or "", event.event or ""),
            room_name=room_name,
            room_id=room_id,
            participant_identity=participant_identity,
            participant_name=participant_name,
            timestamp=(
                datetime.fromtimestamp(event.created_at, tz=timezone.utc)
                if event.created_at
                else None
            ),
            metadata=metadata,
        )
