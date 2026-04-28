"""AssemblyAI TranscriptionProvider — backend metadata only.

Third option in the lineup. AssemblyAI's diarization is competitive with
Deepgram's and they offer a `Universal-2` realtime model. Kept here so a
deployment can swap to it via env var without code changes — useful if
a customer's procurement/SOC-2 process is already cleared on AssemblyAI
but not Deepgram.
"""

from __future__ import annotations

from django.conf import settings

from conferencing.transcription.base import STTConfig, TranscriptionProvider


class AssemblyAITranscription(TranscriptionProvider):
    name = 'assemblyai'
    model = 'universal-2'

    def is_configured(self) -> bool:
        return bool(getattr(settings, 'ASSEMBLYAI_API_KEY', '') or '')

    def stt(self, config: STTConfig):
        raise RuntimeError(
            "AssemblyAI STT is constructed by the accredit-agent service, "
            "not the Django backend."
        )

    def supports_diarization(self) -> bool:
        return True

    def supports_streaming(self) -> bool:
        return True
