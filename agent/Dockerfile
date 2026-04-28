# Multi-stage build for the Accredit transcription agent.
#
# Why a separate image (not multi-app in the backend image):
#   - livekit-agents brings native audio deps (PyAudio, ffmpeg, opus,
#     websocket extras) that triple the backend's image size.
#   - The agent has different runtime characteristics (long-lived async
#     loop, audio-stream-heavy) and scales independently in Cloud Run.
#   - Cold-start latency matters for "first session of the day" UX —
#     a slimmer image starts faster.

FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Audio + websocket deps for livekit-agents and STT plugins. ffmpeg is
# what egress fingerprinting uses too — same family of native deps,
# kept tight.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libsndfile1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

FROM base AS dependencies
COPY pyproject.toml ./
# Use uv's built-in lockfile generation if no uv.lock yet — first build
# creates it. Subsequent builds will respect the committed lock.
RUN uv sync --no-install-project --no-dev || uv lock && uv sync --no-install-project --no-dev

FROM dependencies AS development
COPY . .
# Watch the src/ directory and reload on change (livekit-agents has
# `dev` mode with hot reload; matches Django's runserver UX).
CMD ["uv", "run", "python", "-m", "src.main", "dev"]

FROM base AS production
RUN groupadd -r agent && useradd -r -g agent agent
COPY --from=dependencies /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
COPY --chown=agent:agent . .
USER agent
# Cloud Run health check — the agent worker exposes a HTTP probe via
# livekit-agents' built-in health server.
EXPOSE 8081
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8081/health || exit 1
CMD ["python", "-m", "src.main", "start"]
