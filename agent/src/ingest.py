"""HTTP client for posting transcript segments to the Django backend.

Owns the HMAC signing scheme that pairs with `IsInternalAgent` on the
web service. One client instance per worker process — keeps a single
httpx.AsyncClient with connection pooling so per-segment posts have
~1ms overhead on top of the network RTT.

Failure mode strategy:

  - 2xx → done.
  - 4xx → log + drop. The backend has rejected the payload (validation
    error, locked-by-edit, transcript finalised). Retrying won't help
    and would only flood the logs.
  - 5xx / network → retry with exponential backoff up to a small cap
    (3 attempts). Beyond that, log loudly — the agent stays connected
    to the room (so live captions still flow to the browser) but drops
    the durable record. The post-event batch repair pass (Step 4
    follow-up) is the safety net.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Retry policy. Tuned for "the backend is briefly overloaded" not
# "the backend is down" — the latter we want to surface, not paper
# over. Max 3 attempts means a transient bump costs <1s; sustained
# outage drops the segment after ~2s.
_MAX_RETRIES = 3
_BACKOFF_BASE_SECONDS = 0.2


@dataclass(frozen=True)
class IngestSegment:
    """The agent-side shape of one segment to forward to the backend.

    Mirrors `TranscriptSegmentIngestSerializer` exactly. Speaker fields
    are optional; the backend resolves participant_identity → User on
    its own when populated.
    """

    livekit_segment_id: str
    start_ms: int
    end_ms: int
    text: str
    is_final: bool = True
    participant_identity: str = ''
    speaker_name: str = ''
    confidence: float | None = None

    def to_payload(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            'livekit_segment_id': self.livekit_segment_id,
            'start_ms': self.start_ms,
            'end_ms': self.end_ms,
            'text': self.text,
            'is_final': self.is_final,
        }
        if self.participant_identity:
            d['participant_identity'] = self.participant_identity
        if self.speaker_name:
            d['speaker_name'] = self.speaker_name
        if self.confidence is not None:
            d['confidence'] = self.confidence
        return d


class IngestClient:
    """Async HTTP client that POSTs segments to the Django backend.

    Long-lived; one instance per agent worker process. Holds a single
    httpx.AsyncClient with connection pooling and a 5s connect timeout
    so a sluggish DNS lookup doesn't stall the agent's audio loop.

    HTTP/1.1 is intentional. Segments are tiny (<1KB), traffic to the
    backend is in-region, and the connection pool is reused across
    every POST — the per-request overhead is already dominated by
    network RTT, not protocol framing. Avoids the `httpx[http2]` extra
    (`h2` package) without any meaningful latency cost.
    """

    def __init__(self, *, backend_url: str, shared_secret: str) -> None:
        self._backend_url = backend_url.rstrip('/')
        self._secret = shared_secret.encode('utf-8') if shared_secret else b''
        # Lazily constructed on first use so `IngestClient(...)` is safe
        # to call from synchronous setup code without an event loop.
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(5.0, connect=2.0),
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _sign(self, body: bytes) -> dict[str, str]:
        """Build the (timestamp, signature) header pair for one request.

        Recomputed per call so each request has its own timestamp —
        replays of an old (ts, body) tuple are rejected by the 5-min
        window in `IsInternalAgent`.
        """
        ts = int(time.time())
        msg = f'{ts}.'.encode('ascii') + body
        sig = hmac.new(self._secret, msg, hashlib.sha256).hexdigest()
        return {
            'X-Agent-Timestamp': str(ts),
            'X-Agent-Signature': sig,
            'Content-Type': 'application/json',
        }

    async def _post(self, path: str, payload: dict[str, Any]) -> bool:
        """POST with backoff. Returns True on 2xx, False on terminal failure."""
        body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        client = await self._get_client()
        for attempt in range(1, _MAX_RETRIES + 1):
            headers = self._sign(body)
            try:
                resp = await client.post(
                    f'{self._backend_url}{path}',
                    content=body,
                    headers=headers,
                )
            except httpx.RequestError as e:
                logger.warning(
                    "ingest %s attempt %d failed (network): %s",
                    path, attempt, e,
                )
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))
                continue
            if 200 <= resp.status_code < 300:
                return True
            if 400 <= resp.status_code < 500:
                # Terminal — backend has rejected this payload deliberately.
                logger.warning(
                    "ingest %s rejected by backend: %d %s",
                    path, resp.status_code, resp.text[:200],
                )
                return False
            # 5xx — backend hiccup, retry.
            logger.warning(
                "ingest %s attempt %d returned %d; will retry",
                path, attempt, resp.status_code,
            )
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))
        logger.error("ingest %s exhausted retries; segment dropped", path)
        return False

    async def post_segment(
        self, transcript_uuid: str, segment: IngestSegment,
    ) -> bool:
        return await self._post(
            f'/api/v1/internal/transcripts/{transcript_uuid}/segments/',
            segment.to_payload(),
        )

    async def finalize(
        self, transcript_uuid: str, error_message: str = '',
    ) -> bool:
        """Tell the backend the room is done.

        Idempotent on the backend — safe to call from both `room_finished`
        webhook handler (Step 4) and the agent's own shutdown path
        (whichever fires first wins; the second is a no-op).
        """
        return await self._post(
            f'/api/v1/internal/transcripts/{transcript_uuid}/finalize/',
            {'error_message': error_message} if error_message else {},
        )
