"""TranscriptionProvider Protocol + supporting types.

Why a Protocol (and not an ABC the way `VideoProvider` does it): the agent
worker imports concrete plugin classes from `livekit.plugins.*`, which are
heavy native deps. We want the *Django* side to be able to introspect
"which provider is configured?" without importing those plugin packages —
so the contract is a structural type. Concrete implementations live in
sibling modules and are imported lazily by `service.get_transcription_provider`.

The `stt()` factory method's return type is intentionally typed as a
forward string reference (`"livekit.agents.stt.STT"`). Doing it this way
keeps `livekit-agents` out of the Django runtime dependency tree — only
the agent worker actually pulls those packages in. The web service can
load this module without crashing if `livekit-agents` isn't installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    # Imported only for type-checking — never at runtime in the web app.
    # The agent worker's runtime DOES import it, but it gets the symbol
    # from the real package rather than this conditional.
    from livekit.agents import stt as _lk_stt  # noqa: F401


@dataclass(frozen=True)
class STTConfig:
    """Per-session configuration the agent passes to `provider.stt()`.

    Kept narrow on purpose: things that belong here are signals known at
    the per-event level (language, whether to attempt diarization).
    Provider tunables (model name, API key) are environment concerns and
    stay in the provider's own settings reader.
    """

    language: str = 'en-US'
    diarize: bool = True


class TranscriptionProvider(Protocol):
    """Constructs a LiveKit STT plugin instance for an `AgentSession`.

    The Protocol is intentionally minimal — we lean on LiveKit Agents
    for the actual streaming/segment/interim-final mechanics. Our job is
    to (a) tell the caller whether this provider is wired up at all,
    (b) hand over a configured plugin instance, (c) advertise what
    features the provider supports so callers can fall back gracefully.
    """

    name: str
    """Stable identifier (e.g. 'deepgram', 'openai', 'null'). Persisted on
    `Transcript.provider` at provisioning time."""

    model: str
    """Default model identifier for the provider (e.g. 'nova-3'). Persisted
    on `Transcript.provider_model` so historical rows survive provider
    config changes."""

    def is_configured(self) -> bool:
        """True when the provider has the credentials/network needed to run.

        Used by:
          - The agent worker at boot to fail fast if env vars are missing.
          - Admin UIs to render "Provider not set up — contact support"
            without crashing.
          - Tests to skip integration cases when running offline.
        """
        ...

    def stt(self, config: STTConfig) -> '_lk_stt.STT':
        """Construct a LiveKit `STT` plugin instance ready to plug into
        `AgentSession(stt=...)`.

        Implementations live in modules that import their plugin lazily
        inside this method, so the web service can import the provider
        class without pulling LiveKit Agents into Django.
        """
        ...

    def supports_diarization(self) -> bool:
        """True when the provider exposes per-speaker labels in segments.

        Callers can short-circuit speaker UI affordances when False (we
        still attribute by LiveKit participant_identity, but cross-track
        speaker splits aren't available)."""
        ...

    def supports_streaming(self) -> bool:
        """True when the provider can emit interim segments while audio is
        still flowing.

        All provider plugins LiveKit ships today (Deepgram, OpenAI, AAI,
        Speechmatics, …) support streaming. The flag exists to leave room
        for batch-only providers (e.g. a self-hosted Whisper that only
        runs on completed files) to plug in later without breaking the
        Protocol contract."""
        ...
