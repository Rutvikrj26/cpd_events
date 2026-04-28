"""OpenAI TranscriptionProvider — backend metadata only.

OpenAI's Realtime Whisper (`gpt-4o-mini-transcribe`) is the streaming
alternative to Deepgram in the LiveKit plugin lineup. We keep it as a
backup option for deployments that already have an OpenAI relationship
and don't want to add a second vendor for transcription.

Diarization caveat: OpenAI's Whisper-family models do NOT diarize. We
attribute by LiveKit `participant_identity` instead — each audio track
is one participant, so the agent can tag segments without a separate
diarization pass. That gives accurate speaker labels for our use case
(small medical CPD sessions, 1-5 speakers) without losing anything to
Deepgram on quality.
"""

from __future__ import annotations

from django.conf import settings

from conferencing.transcription.base import STTConfig, TranscriptionProvider


class OpenAITranscription(TranscriptionProvider):
    name = 'openai'
    # Realtime-capable Whisper variant. The `whisper-1` batch model is
    # also available but not relevant here — we provision live captures
    # at room_started, not after the recording is sealed.
    model = 'gpt-4o-mini-transcribe'

    def is_configured(self) -> bool:
        return bool(getattr(settings, 'OPENAI_API_KEY', '') or '')

    def stt(self, config: STTConfig):
        raise RuntimeError(
            "OpenAI STT is constructed by the accredit-agent service, "
            "not the Django backend."
        )

    def supports_diarization(self) -> bool:
        # No native diarization. We rely on LiveKit per-track attribution.
        return False

    def supports_streaming(self) -> bool:
        return True
