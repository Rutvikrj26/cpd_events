"""
Abstract video conferencing provider interface.

All video providers must implement this interface. Currently only LiveKit
is shipped, but the abstraction keeps the door open for alternatives.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RoomResult:
    """Result of creating a video room."""

    room_id: str
    room_name: str
    metadata: dict = field(default_factory=dict)


@dataclass
class ParticipantInfo:
    """Information about a participant in a video room."""

    identity: str
    name: str
    joined_at: datetime | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class WebhookEvent:
    """Parsed webhook event from the video provider."""

    type: str  # room_started, room_finished, participant_joined, participant_left, egress_ended
    room_name: str
    room_id: str = ""
    participant_identity: str = ""
    participant_name: str = ""
    timestamp: datetime | None = None
    metadata: dict = field(default_factory=dict)


class VideoProvider(ABC):
    """Abstract base class for video conferencing providers."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the provider has all required settings."""

    @abstractmethod
    def create_room(
        self,
        name: str,
        metadata: dict | None = None,
        max_participants: int = 0,
    ) -> RoomResult:
        """Create a video room. Returns RoomResult with room_id and room_name."""

    @abstractmethod
    def delete_room(self, room_name: str) -> bool:
        """Delete a video room. Returns True if deleted."""

    @abstractmethod
    def generate_join_token(
        self,
        room_name: str,
        participant_identity: str,
        participant_name: str,
        is_host: bool = False,
    ) -> str:
        """Generate a join token for a participant. Returns JWT string."""

    @abstractmethod
    def list_participants(self, room_name: str) -> list[ParticipantInfo]:
        """List current participants in a room."""

    @abstractmethod
    def start_recording(self, room_name: str, output_path: str = "") -> str:
        """Start recording a room. Returns egress_id."""

    @abstractmethod
    def stop_recording(self, egress_id: str) -> bool:
        """Stop a recording. Returns True if stopped."""

    @abstractmethod
    def verify_webhook(self, body: bytes, auth_header: str) -> bool:
        """Verify webhook signature. Returns True if valid."""

    @abstractmethod
    def parse_webhook(self, body: bytes, auth_header: str) -> WebhookEvent:
        """Parse and verify a webhook payload. Returns WebhookEvent."""
