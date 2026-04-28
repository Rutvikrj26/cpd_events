"""Factory for the configured TranscriptionProvider.

Mirrors `conferencing.service.get_video_provider` — selection by settings
flag, instances cached per-process. The cache matters because some plugin
constructors (Deepgram, AAI) eagerly validate API keys with a network
round-trip; we want one validation per process, not one per call.

Real provider modules are imported lazily so the web service doesn't
have to install `livekit-agents` and `livekit-plugins-*`. Only the
agent worker runtime needs those — for the web app, falling through to
the lazy `import` only happens if production accidentally tries to
construct a real STT instance from Django, which would surface a clean
ImportError instead of a startup crash.
"""

from __future__ import annotations

from functools import lru_cache

from django.conf import settings

from conferencing.transcription.base import TranscriptionProvider
from conferencing.transcription.null import NullTranscription


@lru_cache(maxsize=1)
def get_transcription_provider() -> TranscriptionProvider:
    """Return the singleton TranscriptionProvider configured for this process.

    Reads `TRANSCRIPTION_PROVIDER` from settings (default: 'null') and
    returns a cached instance. Unknown provider names fall back to the
    null provider with a warning, rather than crashing the process — the
    web service must remain bootable even if STT config is misconfigured.
    """
    name = (getattr(settings, 'TRANSCRIPTION_PROVIDER', 'null') or 'null').lower()

    if name == 'null':
        return NullTranscription()

    if name == 'google':
        # Lazy import to keep the agent's plugin packages out of the
        # web service's dep tree.
        from conferencing.transcription.google import GoogleTranscription
        return GoogleTranscription()

    if name == 'deepgram':
        from conferencing.transcription.deepgram import DeepgramTranscription
        return DeepgramTranscription()

    if name == 'openai':
        from conferencing.transcription.openai import OpenAITranscription
        return OpenAITranscription()

    if name == 'assemblyai':
        from conferencing.transcription.assemblyai import AssemblyAITranscription
        return AssemblyAITranscription()

    # Unknown provider: log loudly but keep the process alive.
    import logging
    logging.getLogger(__name__).error(
        "Unknown TRANSCRIPTION_PROVIDER %r; falling back to null. "
        "Valid values: null, google, deepgram, openai, assemblyai.",
        name,
    )
    return NullTranscription()
