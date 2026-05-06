"""Entry point for the Accredit transcription agent.

Run via:

    uv run python -m src.main dev    # local development with hot reload
    uv run python -m src.main start  # production worker

The agent registers with the LiveKit server and waits for explicit
dispatch — the Django backend calls `LiveKitProvider.dispatch_agent`
from `_on_room_started` to spawn this agent into a specific room with
the transcript_uuid embedded in the dispatch metadata.

Lifecycle of one agent dispatch:

  1. Backend creates a Transcript row, calls dispatch_agent(metadata=uuid).
  2. LiveKit notifies this worker; `entrypoint(ctx)` runs.
  3. We extract transcript_uuid from `ctx.job.metadata`.
  4. AgentSession starts an STT pipeline on the room's audio tracks.
  5. LiveKit publishes finalised segments to the `lk.transcription`
     topic — both browsers (via `useTranscriptions()`) and our own
     agent (via the `transcription_received` event) receive them.
  6. We mirror finals to the backend ingest endpoint so the durable
     record survives the room ending.
  7. On room end, the framework cancels our coroutine; the cleanup
     block calls IngestClient.finalize() so the backend transcript
     row flips to FINALIZED.
"""

from __future__ import annotations

import asyncio
import logging

from livekit import agents
from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.agents.voice.room_io import RoomOutputOptions

from src.ingest import IngestClient, IngestSegment
from src.session import STTConfig, build_stt
from src.settings import load_settings

logger = logging.getLogger('accredit-agent')

SETTINGS = load_settings()

# One ingest client per worker process. Built lazily; the inner
# httpx.AsyncClient is created on first send.
INGEST = IngestClient(
    backend_url=SETTINGS.backend_url,
    shared_secret=SETTINGS.internal_agent_shared_secret,
)


# Agent name registered with LiveKit dispatch. Backend's
# `_maybe_provision_transcript` uses the same string.
AGENT_NAME = 'accredit-agent'


async def entrypoint(ctx: JobContext) -> None:
    """One invocation per dispatched room."""
    import time

    # Captured once per session; every forwarded segment computes its
    # start_ms / end_ms as a delta from this anchor. The DB column is
    # a 32-bit IntegerField (max ~2.1 billion ms ≈ 24 days), which
    # accommodates any plausible session length but overflows if we
    # send wall-clock epoch ms (~1.7e12) directly. monotonic() is
    # immune to wall-clock jumps mid-session.
    session_started_at = time.monotonic()

    job = ctx.job
    room = ctx.room
    transcript_uuid = (job.metadata or '').strip()

    if not transcript_uuid:
        logger.error(
            "agent dispatched without metadata (transcript_uuid). "
            "room=%s job=%s — refusing to run; backend should always "
            "set metadata=str(transcript.uuid).",
            room.name, job.id,
        )
        return

    logger.info(
        "agent dispatched: room=%s job=%s transcript_uuid=%s provider=%s",
        room.name, job.id, transcript_uuid, SETTINGS.transcription_provider,
    )

    # Audio-only subscription: we don't render video, only transcribe.
    # Skipping video tracks saves bandwidth + decoder cost on the agent
    # worker.
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    stt = build_stt(SETTINGS, STTConfig(language='en-US', diarize=True))
    if stt is None:
        logger.info(
            "STT disabled (provider=null) — agent will idle in room. "
            "Set TRANSCRIPTION_PROVIDER + key to enable real captioning."
        )
        await asyncio.Event().wait()
        return

    session = AgentSession(stt=stt)

    # AgentSession.start() requires an Agent — even when we only want
    # transcription with no LLM/TTS leg. We pass an empty-instruction
    # Agent so the framework's bookkeeping (telemetry spans, run id)
    # gets a valid handle without engaging any LLM behaviour. The STT
    # plugin attached to the session is the only thing that runs.
    transcription_agent = Agent(instructions='')

    # `sync_transcription` defaults to True, which means the session
    # holds STT finalised segments and only emits them aligned with
    # the agent's TTS audio output. We have NO TTS output (transcription-
    # only worker), so by default finals never get published — the
    # synchronizer waits forever for audio that doesn't exist. Setting
    # it explicitly False makes transcription emit as soon as STT
    # produces it. This was the missing piece behind "0 segments,
    # 0 words" finalisations even when STT was healthy.
    room_output = RoomOutputOptions(
        transcription_enabled=True,
        audio_enabled=False,
        sync_transcription=False,
    )

    # Two listeners for resilience:
    #
    # 1. `session.on('user_input_transcribed')` — direct STT final hook.
    #    Fires the moment the STT plugin produces a finalised segment,
    #    regardless of whether the session also publishes it to the
    #    room. This is the authoritative ingest path for the backend.
    #
    # 2. `room.on('transcription_received')` — listens to the same
    #    `lk.transcription` text-stream channel that browsers consume
    #    via `useTranscriptions()`. We log here for parity diagnostics
    #    (does what the agent emits match what attendees see?) but do
    #    NOT double-write to the backend — that would create duplicate
    #    rows on every segment.
    # Coalescing buffer for outbound segments. STT can emit several
    # finals back-to-back (especially right after a long silence), and
    # firing one HTTP POST per final hammers the Django ingest endpoint
    # → one INSERT per POST → fan-out load on the DB. We accumulate
    # segments here and drain them in a single batch every
    # SEGMENT_FLUSH_INTERVAL seconds. Backend's
    # `update_or_create((transcript, provider_segment_id))` makes the
    # batched POSTs idempotent — duplicates become no-ops if the
    # connection retries.
    SEGMENT_FLUSH_INTERVAL = 1.0  # seconds; max one drain per second
    pending_segments: list[IngestSegment] = []

    @session.on('user_input_transcribed')
    def _on_user_transcribed(ev):
        # ev is a UserInputTranscribedEvent: {transcript, is_final, speaker_id, ...}
        if not getattr(ev, 'is_final', True):
            return
        text = getattr(ev, 'transcript', '') or ''
        if not text.strip():
            return
        speaker_id = getattr(ev, 'speaker_id', None) or ''
        # ms-since-session-start, fits comfortably in INTEGER. We use a
        # single point estimate (start_ms == end_ms) because the
        # `user_input_transcribed` event doesn't carry duration; the
        # post-event panel orders by start_ms which is sufficient.
        elapsed_ms = int((time.monotonic() - session_started_at) * 1000)
        pending_segments.append(IngestSegment(
            provider_segment_id=f'sess-{elapsed_ms}-{abs(hash(text)) % 10_000_000:07d}',
            start_ms=elapsed_ms,
            end_ms=elapsed_ms,
            text=text,
            is_final=True,
            participant_identity=speaker_id or '',
            speaker_name='',
            confidence=None,
        ))

    async def _flush_loop():
        """Drain pending_segments at most once per second.

        Sequential POSTs (not parallel) so the backend sees a steady,
        bounded request stream rather than spikes. If the worker
        shuts down we cancel this task; the `finally` block in
        entrypoint awaits one last drain so segments accumulated in
        the final second still land.
        """
        try:
            while True:
                await asyncio.sleep(SEGMENT_FLUSH_INTERVAL)
                if not pending_segments:
                    continue
                # Snapshot then clear: any segments arriving during the
                # flush itself land in the next tick's window.
                batch = pending_segments[:]
                del pending_segments[:]
                for seg in batch:
                    try:
                        await INGEST.post_segment(transcript_uuid, seg)
                    except Exception:
                        logger.exception(
                            "segment ingest POST failed; dropping (text=%r)",
                            seg.text[:80],
                        )
        except asyncio.CancelledError:
            # Final drain on shutdown — best-effort, swallow errors so
            # the cancellation propagates promptly.
            if pending_segments:
                batch = pending_segments[:]
                del pending_segments[:]
                for seg in batch:
                    try:
                        await INGEST.post_segment(transcript_uuid, seg)
                    except Exception:
                        logger.warning("final-flush segment dropped: %r", seg.text[:80])
            raise

    flush_task = asyncio.create_task(_flush_loop())

    @ctx.room.on('transcription_received')
    def _on_segments(segments, participant, _publication):
        # Diagnostic only: log that captions are reaching the room
        # (i.e. browsers will see them). Don't forward — the
        # `user_input_transcribed` listener above is the canonical ingest.
        for seg in segments:
            if seg.final:
                logger.debug(
                    "captions on the wire: text=%r participant=%s",
                    seg.text[:80] if seg.text else '',
                    participant.identity if participant else '?',
                )

    @ctx.room.on('participant_disconnected')
    def _on_leave(p):
        logger.debug("participant left: identity=%s", p.identity)

    try:
        await session.start(
            transcription_agent,
            room=ctx.room,
            room_output_options=room_output,
        )
        # Block until the room ends. AgentSession.start returns once
        # the session is up; the framework cancels this coroutine when
        # the job completes.
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        # Normal shutdown path — room ended.
        raise
    except Exception as e:
        logger.exception("agent session crashed in room %s", room.name)
        # Tell the backend the transcript ended in error so the UI
        # surfaces "transcript may be incomplete" rather than spinning
        # on STREAMING forever.
        await INGEST.finalize(transcript_uuid, error_message=str(e)[:500])
        raise
    finally:
        # Drain any remaining segments before the transcript gets
        # marked finalized. Cancelling the flush task triggers its
        # CancelledError handler, which does one last sequential
        # drain. Awaiting the task ensures we don't race finalize
        # against a half-flushed buffer.
        flush_task.cancel()
        try:
            await flush_task
        except (asyncio.CancelledError, Exception):
            pass

        # Best-effort finalize. The backend webhook handler also calls
        # finalize on room_finished; both are idempotent so racing
        # them is fine.
        try:
            await INGEST.finalize(transcript_uuid)
        except Exception:
            logger.exception(
                "finalize failed for transcript %s; backend webhook is the "
                "fallback", transcript_uuid,
            )


async def _forward_segment(
    *,
    transcript_uuid: str,
    seg,                            # livekit.rtc.TranscriptionSegment
    participant_identity: str,
    participant_name: str,
) -> None:
    """Convert a LiveKit segment to the backend's wire format and POST it.

    Wrapped in its own coroutine so the room event handler returns
    immediately — long-tail latency in the backend doesn't stall the
    next segment's dispatch.
    """
    try:
        # LiveKit's segment has start_time/end_time as nanoseconds since
        # the room start. We send milliseconds (matches start_ms/end_ms
        # on the backend model).
        start_ms = int(getattr(seg, 'start_time', 0) // 1_000_000)
        end_ms = int(getattr(seg, 'end_time', 0) // 1_000_000)
        if end_ms < start_ms:
            end_ms = start_ms

        # Confidence isn't on the segment in all plugin versions; default
        # to None so backend stores NULL rather than guessing.
        confidence = getattr(seg, 'confidence', None)

        await INGEST.post_segment(
            transcript_uuid,
            IngestSegment(
                provider_segment_id=seg.id or '',
                start_ms=start_ms,
                end_ms=end_ms,
                text=seg.text or '',
                is_final=True,
                participant_identity=participant_identity,
                speaker_name=participant_name,
                confidence=confidence,
            ),
        )
    except Exception:
        # Don't let one failed POST kill the whole agent.
        logger.exception("forwarding segment failed; dropping")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    )
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name=AGENT_NAME,
        ),
    )


if __name__ == '__main__':
    main()
