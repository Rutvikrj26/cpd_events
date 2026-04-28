"""Deepgram TranscriptionProvider — backend metadata only.

The actual `livekit.plugins.deepgram.STT` instance is constructed on
the *agent* side (see `agent/src/session.py`); it imports the LiveKit
plugin directly. The backend never holds a Deepgram client.

What this module contributes to the backend:

  - A name/model identity that gets snapshotted onto `Transcript.provider`
    and `Transcript.provider_model` at provisioning time, so historical
    rows record which provider produced them.
  - A feature flag pair (`supports_diarization`, `supports_streaming`) the
    UI can read to gate panels at provisioning time — e.g. don't render
    the "show speaker labels" toggle if the provider can't diarize.
  - An `is_configured()` check that fails fast in admin tooling when the
    deployment selected `TRANSCRIPTION_PROVIDER=deepgram` but didn't set
    `DEEPGRAM_API_KEY`.

The `stt()` method is intentionally stub: callers on the backend should
never construct an STT instance — only the agent does that. We raise
clearly to surface the misuse in tests/admin scripts.
"""

from __future__ import annotations

from django.conf import settings

from conferencing.transcription.base import STTConfig, TranscriptionProvider


class DeepgramTranscription(TranscriptionProvider):
    name = 'deepgram'
    # Nova-3 is the current best-quality + lowest-latency tier (Mar 2026
    # general availability). Deepgram's `model='multi'` accepts ~50
    # languages without per-call config — good for the multi-language
    # CPD audience.
    model = 'nova-3'

    def is_configured(self) -> bool:
        return bool(getattr(settings, 'DEEPGRAM_API_KEY', '') or '')

    def stt(self, config: STTConfig):
        raise RuntimeError(
            "Deepgram STT is constructed by the accredit-agent service, "
            "not the Django backend. If you reached this from a test, "
            "use `null` as the provider."
        )

    def supports_diarization(self) -> bool:
        # Deepgram supports diarization in streaming via `diarize=True`.
        # The agent honours STTConfig.diarize when it constructs the plugin.
        return True

    def supports_streaming(self) -> bool:
        return True
