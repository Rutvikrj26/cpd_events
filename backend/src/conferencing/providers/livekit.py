"""
LiveKit video conferencing provider implementation.

Uses the official livekit-api Python SDK for:
- Room management (create, delete, list participants)
- Access token generation (JWT-based participant auth)
- Webhook verification and parsing
- Recording via Egress service
"""

import logging
from datetime import datetime, timezone

from django.conf import settings

from conferencing.provider import (
    ParticipantInfo,
    RoomResult,
    VideoProvider,
    WebhookEvent,
)

logger = logging.getLogger(__name__)


def _get_livekit_api():
    """Lazy import of livekit-api to allow graceful degradation."""
    try:
        import livekit.api as lk_api

        return lk_api
    except ImportError:
        raise RuntimeError(
            "livekit-api package is not installed. Run: pip install livekit-api"
        )


class LiveKitProvider(VideoProvider):
    """LiveKit implementation of the VideoProvider interface."""

    def __init__(self):
        self._api_key = getattr(settings, 'LIVEKIT_API_KEY', '') or ''
        self._api_secret = getattr(settings, 'LIVEKIT_API_SECRET', '') or ''
        self._host = getattr(settings, 'LIVEKIT_HOST', '') or ''
        self._ws_url = getattr(settings, 'LIVEKIT_WS_URL', '') or ''

    def is_configured(self) -> bool:
        return bool(self._api_key and self._api_secret and self._host)

    def create_room(
        self,
        name: str,
        metadata: dict | None = None,
        max_participants: int = 0,
    ) -> RoomResult:
        lk = _get_livekit_api()
        import json

        room_service = lk.RoomServiceClient(
            self._host, self._api_key, self._api_secret
        )
        room = room_service.create_room(
            lk.CreateRoomRequest(
                name=name,
                metadata=json.dumps(metadata) if metadata else "",
                max_participants=max_participants,
            )
        )
        logger.info("LiveKit room created: %s (sid=%s)", room.name, room.sid)
        return RoomResult(
            room_id=room.sid,
            room_name=room.name,
            metadata=metadata or {},
        )

    def delete_room(self, room_name: str) -> bool:
        lk = _get_livekit_api()
        room_service = lk.RoomServiceClient(
            self._host, self._api_key, self._api_secret
        )
        try:
            room_service.delete_room(lk.DeleteRoomRequest(room=room_name))
            logger.info("LiveKit room deleted: %s", room_name)
            return True
        except Exception:
            logger.exception("Failed to delete LiveKit room: %s", room_name)
            return False

    def generate_join_token(
        self,
        room_name: str,
        participant_identity: str,
        participant_name: str,
        is_host: bool = False,
    ) -> str:
        lk = _get_livekit_api()
        token = (
            lk.AccessToken(self._api_key, self._api_secret)
            .with_identity(participant_identity)
            .with_name(participant_name)
            .with_grants(
                lk.VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                    room_admin=is_host,
                )
            )
        )
        jwt_str = token.to_jwt()
        logger.debug(
            "Generated join token for %s in room %s (host=%s)",
            participant_identity,
            room_name,
            is_host,
        )
        return jwt_str

    def list_participants(self, room_name: str) -> list[ParticipantInfo]:
        lk = _get_livekit_api()
        room_service = lk.RoomServiceClient(
            self._host, self._api_key, self._api_secret
        )
        response = room_service.list_participants(
            lk.ListParticipantsRequest(room=room_name)
        )
        return [
            ParticipantInfo(
                identity=p.identity,
                name=p.name,
                joined_at=datetime.fromtimestamp(p.joined_at, tz=timezone.utc) if p.joined_at else None,
            )
            for p in response.participants
        ]

    def start_recording(self, room_name: str, output_path: str = "") -> str:
        lk = _get_livekit_api()
        egress_service = lk.EgressServiceClient(
            self._host, self._api_key, self._api_secret
        )
        file_output = lk.EncodedFileOutput(
            file_type=lk.EncodedFileType.MP4,
        )
        if output_path:
            file_output.filepath = output_path

        response = egress_service.start_room_composite_egress(
            lk.RoomCompositeEgressRequest(
                room_name=room_name,
                file_outputs=[file_output],
            )
        )
        logger.info("Recording started for room %s, egress_id=%s", room_name, response.egress_id)
        return response.egress_id

    def stop_recording(self, egress_id: str) -> bool:
        lk = _get_livekit_api()
        egress_service = lk.EgressServiceClient(
            self._host, self._api_key, self._api_secret
        )
        try:
            egress_service.stop_egress(lk.StopEgressRequest(egress_id=egress_id))
            logger.info("Recording stopped: egress_id=%s", egress_id)
            return True
        except Exception:
            logger.exception("Failed to stop recording: egress_id=%s", egress_id)
            return False

    def verify_webhook(self, body: bytes, auth_header: str) -> bool:
        lk = _get_livekit_api()
        try:
            receiver = lk.WebhookReceiver(self._api_key, self._api_secret)
            receiver.receive(body.decode('utf-8'), auth_header)
            return True
        except Exception:
            return False

    def parse_webhook(self, body: bytes, auth_header: str) -> WebhookEvent:
        lk = _get_livekit_api()
        receiver = lk.WebhookReceiver(self._api_key, self._api_secret)
        event = receiver.receive(body.decode('utf-8'), auth_header)

        # Map LiveKit event types to our generic types
        event_type = event.event or ""
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

        metadata = {}
        if event.egress_info:
            metadata["egress_id"] = event.egress_info.egress_id
            metadata["status"] = str(event.egress_info.status)

        return WebhookEvent(
            type=type_map.get(event_type, event_type),
            room_name=room_name,
            room_id=room_id,
            participant_identity=participant_identity,
            participant_name=participant_name,
            timestamp=datetime.fromtimestamp(event.created_at, tz=timezone.utc) if event.created_at else None,
            metadata=metadata,
        )
