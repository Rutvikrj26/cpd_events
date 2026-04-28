"""Google Cloud Speech-to-Text v2 — backend metadata only.

The agent constructs the actual `livekit.plugins.google.STT` instance
with the `chirp_2` model. This module just snapshots the provider
identity onto Transcript rows so historical reads know which family
generated the segments.

Auth on the agent uses the standard Google ADC chain: a service-
account JSON file path supplied via `GOOGLE_APPLICATION_CREDENTIALS`.
"""

from __future__ import annotations

from django.conf import settings

from conferencing.transcription.base import STTConfig, TranscriptionProvider


class GoogleTranscription(TranscriptionProvider):
    name = 'google'
    model = 'chirp_2'

    def is_configured(self) -> bool:
        return bool(getattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS', '') or '')

    def stt(self, config: STTConfig):
        raise RuntimeError(
            "Google STT is constructed by the accredit-agent service, "
            "not the Django backend."
        )

    def supports_diarization(self) -> bool:
        # chirp_2 supports diarization natively. We still attribute by
        # LiveKit participant_identity in the agent — per-track is more
        # reliable than audio-based diarization for small sessions.
        return True

    def supports_streaming(self) -> bool:
        return True
