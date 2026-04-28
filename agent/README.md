# Accredit Transcription Agent

A LiveKit agent worker that joins meeting rooms, runs an STT pipeline
on participant audio, and forwards finalised transcript segments to the
Django backend.

## Architecture

This service is one of three Python deployables in the Accredit stack:

| Service | Role | Scaling |
|---|---|---|
| `backend` | Django web app — REST API + auth + business logic | HTTP request RPS |
| `accredit-agent` (this) | Joins LiveKit rooms; runs STT; forwards segments | Concurrent active rooms |
| `cpd_livekit_egress` | LiveKit's own recording compositor | Per-recording session |

Lives in its own image because:

1. `livekit-agents` and the STT plugins pull native audio deps (PyAudio,
   ffmpeg, opus codec) that triple the Django image size and slow its
   cold start.
2. Audio workloads scale on a different curve than HTTP requests — one
   long-running room consumes one worker for ~hours; the API server is
   millions of requests/second-bound. Mixing them couples scaling
   profiles in ways that hurt both.
3. Failure isolation: a misbehaving STT plugin can crash the agent
   without taking down the API.

## Local development

The agent runs in `docker-compose` alongside the backend. To bring up
the full stack:

```bash
cd cli/
docker compose up -d
```

The agent registers with the local LiveKit emulator at startup. To
verify dispatch:

```bash
docker logs cpd_agent -f
```

You should see:
```
agent dispatched: room=<room_name> job=<job_id> ...
```
when the backend dispatches the agent into a room (Step 4 onwards).

## Configuration

Environment variables are loaded once at boot (see `src/settings.py`).
For local dev, copy `.env.example` to `.env.dev` and adjust:

- `TRANSCRIPTION_PROVIDER=null` — the agent boots and joins rooms but
  doesn't run STT. Useful for verifying dispatch wiring.
- `TRANSCRIPTION_PROVIDER=deepgram` (with `DEEPGRAM_API_KEY` set) —
  the recommended default. ~300ms streaming latency, native diarization.

## Testing

```bash
uv run pytest
```

Integration tests against a real LiveKit emulator + backend live in
`tests/integration/` and require `docker compose up -d` to be running.
