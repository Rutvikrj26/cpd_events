"""No-op TranscriptionProvider — the default in dev and in deployments
that haven't set up an STT vendor.

When this provider is selected, the agent worker still gets dispatched
into the room (the dispatch mechanics are useful to verify in CI even
without a real provider), but `is_configured()` returns False so:

  - `provision_transcript_if_enabled` short-circuits before creating a
    Transcript row — there's no point persisting a record we know will
    never have segments.
  - The agent's `build_session()` skips the `AgentSession.start()` call,
    so no audio frames are forwarded anywhere.
  - The frontend doesn't get a `transcription_enabled` flag flipped on
    just because the org checked the per-event toggle, so the lobby
    doesn't promise captions that won't materialise.

The class still implements `stt()` because the Protocol requires it,
but the implementation raises — production code should always check
`is_configured()` before calling.
"""

from __future__ import annotations

from conferencing.transcription.base import STTConfig, TranscriptionProvider


class NullTranscription(TranscriptionProvider):
    name = 'null'
    model = ''

    def is_configured(self) -> bool:
        return False

    def stt(self, config: STTConfig):
        # Intentionally raises — callers must guard with is_configured().
        # If we returned a no-op stub, AgentSession would silently consume
        # audio without producing anything, masking the misconfiguration.
        raise RuntimeError(
            "NullTranscription is not configured. Set TRANSCRIPTION_PROVIDER "
            "to 'deepgram', 'openai', or 'assemblyai' and provide the "
            "matching API key env var to enable transcription."
        )

    def supports_diarization(self) -> bool:
        return False

    def supports_streaming(self) -> bool:
        return False
