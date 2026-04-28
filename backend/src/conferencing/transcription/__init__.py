"""Transcription provider abstraction.

Mirrors the `conferencing.provider`/`conferencing.service` split for video.
A `TranscriptionProvider` constructs the LiveKit `agents.stt.STT` plugin
instance the agent worker hands to its `AgentSession`. Provider selection
happens at agent boot via `TRANSCRIPTION_PROVIDER` env var; swapping
providers is one env var change with no agent code change.

The abstraction lives in the Django backend (not the agent) because:

  - The same Protocol is referenced by the ingest validator (e.g. to
    confirm the provider name on each POSTed segment is one we know about).
  - Server-side admin tooling can query `is_configured()` to render
    "Provider not set up" notices in the org settings UI without booting
    the agent worker.

The agent worker imports this module directly (it shares the backend
codebase via the monorepo) so we have one source of truth for which STT
plugins are wired up.
"""

from conferencing.transcription.base import TranscriptionProvider, STTConfig
from conferencing.transcription.service import get_transcription_provider

__all__ = ['TranscriptionProvider', 'STTConfig', 'get_transcription_provider']
