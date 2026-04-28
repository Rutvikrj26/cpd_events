"""Agent runtime settings — env-driven, no hierarchy.

The agent is a small, single-purpose process; it doesn't need Django's
multi-environment settings module. We keep one flat dataclass and load
env vars eagerly at import so missing config surfaces immediately at
boot, not on the first request.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Pulls .env.dev / .env from the working directory if present. Cloud
# Run injects env vars directly so this is a no-op there; locally it
# matches the backend's docker-compose env_file convention.
load_dotenv()


@dataclass(frozen=True)
class Settings:
    # ---------- LiveKit -----------------------------------------------------
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str

    # ---------- Backend -----------------------------------------------------
    # Where the agent POSTs finalised segments. Internal-network only in
    # production; localhost in dev.
    backend_url: str
    # Shared HMAC secret. The Django web service has the same value;
    # both must agree or every internal POST 401s.
    internal_agent_shared_secret: str

    # ---------- Transcription ------------------------------------------------
    # Provider name selects which STT plugin the agent constructs.
    # 'null' is the safe default — agent boots and registers, but
    # AgentSession is never started, so no audio leaves the room.
    transcription_provider: str
    # Per-provider API keys. Only one is required at a time; the others
    # can be empty. The provider factory will fail fast if its own key
    # is missing.
    # Path to a GCP service-account JSON file with the
    # `roles/speech.client` role. Cloud Speech-to-Text v2 uses ADC, so
    # we set GOOGLE_APPLICATION_CREDENTIALS in the environment and the
    # plugin's underlying google-cloud-speech client picks it up.
    google_application_credentials: str
    # Cloud Speech-to-Text v2 region. Different regions publish different
    # models — Canadian regions (the default) carry `latest_long` but
    # not `chirp_2`. See `_build_google` for the pairing rules.
    google_speech_location: str
    # Model id. `latest_long` is broadly available; `chirp_2` is the
    # best-accuracy model but only in select US/EU/Asia regions.
    google_speech_model: str
    deepgram_api_key: str
    openai_api_key: str
    assemblyai_api_key: str

    # ---------- Diagnostics --------------------------------------------------
    # Health-check port the Dockerfile probes. livekit-agents exposes
    # this via its built-in HTTP probe server.
    health_port: int


def load_settings() -> Settings:
    """Read environment variables and build a Settings instance.

    Defaults are dev-friendly (local LiveKit emulator, localhost backend).
    Production overrides via Cloud Run env vars; missing critical fields
    (e.g. shared HMAC secret) make `_validate` raise so the service
    crash-loops visibly rather than silently misbehaving.
    """
    s = Settings(
        livekit_url=os.environ.get('LIVEKIT_URL', 'ws://localhost:7880'),
        livekit_api_key=os.environ.get('LIVEKIT_API_KEY', ''),
        livekit_api_secret=os.environ.get('LIVEKIT_API_SECRET', ''),
        backend_url=os.environ.get(
            'BACKEND_INTERNAL_URL', 'http://localhost:8000'
        ).rstrip('/'),
        internal_agent_shared_secret=os.environ.get(
            'INTERNAL_AGENT_SHARED_SECRET', ''
        ),
        transcription_provider=os.environ.get(
            'TRANSCRIPTION_PROVIDER', 'null'
        ).lower(),
        google_application_credentials=os.environ.get(
            'GOOGLE_APPLICATION_CREDENTIALS', '',
        ),
        # Default `global`: Cloud Speech-to-Text v2's multi-region
        # endpoint with full feature support for `latest_long`.
        # Regional endpoints (e.g. northamerica-northeast1) work with
        # the *model availability matrix* (chirp_2 isn't there) AND a
        # narrower *streaming feature matrix* — sending the same
        # request shape to a regional endpoint that works against
        # `global` returns HTTP 501 "Operation is not implemented, or
        # supported, or enabled" because of the regional feature gap.
        # We default to `global` so captions Just Work; tenants with
        # data-residency requirements override
        # `GOOGLE_SPEECH_LOCATION=northamerica-northeast1` (and may
        # need to also drop streaming features the regional endpoint
        # doesn't accept — see _build_google in session.py).
        google_speech_location=os.environ.get(
            'GOOGLE_SPEECH_LOCATION', 'global',
        ),
        # Default `latest_long`: tuned for long-form conferencing audio
        # and fully supported in `global`. Override with
        # GOOGLE_SPEECH_MODEL=chirp_2 + a chirp_2-supported region
        # (us-central1, us-east4, europe-west4, …) when accuracy
        # matters more than geographic neutrality.
        google_speech_model=os.environ.get(
            'GOOGLE_SPEECH_MODEL', 'latest_long',
        ),
        deepgram_api_key=os.environ.get('DEEPGRAM_API_KEY', ''),
        openai_api_key=os.environ.get('OPENAI_API_KEY', ''),
        assemblyai_api_key=os.environ.get('ASSEMBLYAI_API_KEY', ''),
        health_port=int(os.environ.get('HEALTH_PORT', '8081')),
    )
    _validate(s)
    return s


def _validate(s: Settings) -> None:
    if not s.livekit_api_key or not s.livekit_api_secret:
        raise SystemExit(
            "LIVEKIT_API_KEY and LIVEKIT_API_SECRET must be set. The agent "
            "needs them to dispatch into rooms via the LiveKit Server API."
        )
    # The HMAC secret is required only when the agent actually posts to
    # the backend — provider 'null' skips ingest, so we tolerate an empty
    # secret in pure-dispatch dev mode. With any real provider, missing
    # secret means segments would silently disappear at the backend's
    # 401 wall, which is a worse failure than crash-on-boot.
    if s.transcription_provider != 'null' and not s.internal_agent_shared_secret:
        raise SystemExit(
            "INTERNAL_AGENT_SHARED_SECRET must be set when "
            "TRANSCRIPTION_PROVIDER != 'null'. Without it, every POST to "
            "the backend ingest endpoint will return 401 and segments "
            "won't persist."
        )
