"""STT factory — provider-keyed construction of LiveKit STT plugins.

Returns the actual `livekit.agents.stt.STT` instance the AgentSession
will run. One function per provider, behind a dispatch table; each
imports its own plugin lazily so importing this module doesn't pull
unused providers into memory.

The `STTConfig` dataclass mirrors the backend's; we duplicate it here
rather than importing from the backend to keep the agent service free
of the Django settings/import-graph cost.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.settings import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class STTConfig:
    language: str = 'en-US'
    diarize: bool = True


def build_stt(settings: Settings, config: STTConfig | None = None):
    """Construct the configured STT plugin instance.

    Returns None for `provider='null'` — caller skips AgentSession entirely.
    Raises SystemExit on misconfiguration so the worker dies loudly rather
    than silently consuming audio without producing transcripts.
    """
    cfg = config or STTConfig()
    name = settings.transcription_provider

    if name == 'null':
        logger.info("Transcription provider=null; STT disabled.")
        return None

    if name == 'google':
        return _build_google(settings, cfg)
    if name == 'deepgram':
        return _build_deepgram(settings, cfg)
    if name == 'openai':
        return _build_openai(settings, cfg)
    if name == 'assemblyai':
        return _build_assemblyai(settings, cfg)

    raise SystemExit(
        f"Unknown TRANSCRIPTION_PROVIDER={name!r}. "
        "Valid: null, google, deepgram, openai, assemblyai."
    )


def _build_google(settings: Settings, cfg: STTConfig):
    """Google Cloud Speech-to-Text v2.

    Auth uses the standard Google ADC chain: we set
    `GOOGLE_APPLICATION_CREDENTIALS` in the environment and the plugin
    reads the service-account JSON from that path. Not passing
    `credentials_file=` explicitly lets Workload Identity / GKE
    metadata-server creds work in production without code changes.

    Model + region: Cloud Speech-to-Text v2 publishes different models
    in different regions. The two choices that matter for us:

      - `latest_long`: available in every region including Canadian
        (`northamerica-northeast1`/`-northeast2`). Solid general-purpose
        long-form model. Default.
      - `chirp_2`: best accuracy, especially for clinical terminology
        and accented English. Regional-only — supported in select US,
        EU, and Asia regions but NOT Canadian ones.

    The default (`latest_long` in `northamerica-northeast1`) keeps data
    in-Canada with a model that exists there. Override
    `GOOGLE_SPEECH_MODEL=chirp_2` together with a supported region
    (`GOOGLE_SPEECH_LOCATION=us-east4` etc.) when accuracy matters more
    than data residency.
    """
    if not settings.google_application_credentials:
        raise SystemExit(
            "TRANSCRIPTION_PROVIDER=google but GOOGLE_APPLICATION_CREDENTIALS "
            "is empty. Cloud Speech-to-Text needs a service-account JSON: "
            "create a GCP project, enable the Speech-to-Text API, create a "
            "service account with the 'Cloud Speech Client' role, download "
            "the JSON, mount it into the agent container, and point "
            "GOOGLE_APPLICATION_CREDENTIALS at that path."
        )
    from livekit.plugins import google

    location = settings.google_speech_location
    model = settings.google_speech_model
    # `spoken_punctuation` is only honoured by `chirp_2` and a few other
    # newer models. Sending it for `latest_long` (or any model that
    # doesn't support it) makes Cloud Speech-to-Text v2 return HTTP 501
    # "Operation is not implemented, or supported, or enabled" and
    # crashes the AgentSession. Gate it on the model.
    spoken_punctuation = model.startswith('chirp_2')
    logger.info(
        "Using Google Cloud Speech-to-Text (model=%s location=%s spoken_punctuation=%s) "
        "with credentials %s",
        model, location, spoken_punctuation, settings.google_application_credentials,
    )
    return google.STT(
        model=model,
        location=location,
        languages=[cfg.language],
        use_streaming=True,
        spoken_punctuation=spoken_punctuation,
    )


def _build_deepgram(settings: Settings, cfg: STTConfig):
    """Deepgram Nova-3 — recommended default.

    `model='nova-3'` + `smart_format=True` gives medical-friendly
    capitalisation, punctuation, and number formatting. `diarize=True`
    enables Deepgram's native speaker labelling on top of LiveKit's
    per-track attribution; we still tag by participant_identity in
    `transcription_received` because Deepgram's speaker IDs are
    per-segment integers, not user UUIDs.
    """
    if not settings.deepgram_api_key:
        raise SystemExit(
            "TRANSCRIPTION_PROVIDER=deepgram but DEEPGRAM_API_KEY is empty."
        )
    from livekit.plugins import deepgram

    return deepgram.STT(
        model='nova-3',
        language=cfg.language,
        smart_format=True,
        diarize=cfg.diarize,
        api_key=settings.deepgram_api_key,
    )


def _build_openai(settings: Settings, cfg: STTConfig):
    """OpenAI realtime Whisper variant.

    Doesn't natively diarize; we attribute by LiveKit participant_identity
    in the agent's transcription handler (each track is one participant).
    """
    if not settings.openai_api_key:
        raise SystemExit(
            "TRANSCRIPTION_PROVIDER=openai but OPENAI_API_KEY is empty."
        )
    from livekit.plugins import openai as openai_plugin

    return openai_plugin.STT(
        model='gpt-4o-mini-transcribe',
        language=cfg.language,
        api_key=settings.openai_api_key,
    )


def _build_assemblyai(settings: Settings, cfg: STTConfig):
    """AssemblyAI Universal-2 — alternative when procurement blocks Deepgram."""
    if not settings.assemblyai_api_key:
        raise SystemExit(
            "TRANSCRIPTION_PROVIDER=assemblyai but ASSEMBLYAI_API_KEY is empty."
        )
    from livekit.plugins import assemblyai

    return assemblyai.STT(
        model='universal-2',
        language=cfg.language,
        api_key=settings.assemblyai_api_key,
    )
