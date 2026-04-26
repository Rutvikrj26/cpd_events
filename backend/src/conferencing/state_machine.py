"""
State-machine helpers for VideoRoom and VideoRecording.

Webhook handlers should never write status fields directly. Instead, they
call `advance(...)` which performs an atomic SQL guarded UPDATE:

    UPDATE video_recordings
       SET status = <to>, ...extra fields...
     WHERE id = <pk> AND status IN (<allowed predecessors>)

Returns True if the transition fired, False if the row had already moved
past the target state (idempotent re-delivery / concurrent-handler win).

Combined with the per-room advisory lock in the webhook dispatcher, this
gives us two layers of correctness:

  1. Lock — only one webhook for a given room is processed at a time. No
     concurrent state mutation.
  2. State-machine guards — even if a handler is invoked outside the lock
     (reconciler, manual API, future code path), it cannot regress a
     terminal state.
"""

from __future__ import annotations

import logging
from typing import Iterable, Optional

from django.db import connection, transaction
from django.utils import timezone

from conferencing.models import VideoRecording, VideoRoom

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# VideoRecording — allowed transitions.
#
# Terminal: AVAILABLE, ERROR, DELETED. No transitions out of terminal states.
# ---------------------------------------------------------------------------

RECORDING_TRANSITIONS: dict[str, set[str]] = {
    # to_status: set of allowed from_statuses
    VideoRecording.Status.PROCESSING: {VideoRecording.Status.RECORDING},
    VideoRecording.Status.AVAILABLE: {
        VideoRecording.Status.RECORDING,
        VideoRecording.Status.PROCESSING,
    },
    VideoRecording.Status.ERROR: {
        VideoRecording.Status.RECORDING,
        VideoRecording.Status.PROCESSING,
    },
}


def advance_recording(
    recording_id: int,
    *,
    to_status: str,
    extra_fields: Optional[dict] = None,
) -> bool:
    """
    Atomically transition a VideoRecording row to `to_status` if its current
    status is one of the allowed predecessors. Returns True on transition.

    The UPDATE is one SQL statement so there is no Python read-then-write
    window. Concurrent calls for the same row are safe: one wins, the other
    no-ops.
    """
    if to_status not in RECORDING_TRANSITIONS:
        raise ValueError(f"Unknown VideoRecording target status: {to_status!r}")

    allowed_from = RECORDING_TRANSITIONS[to_status]

    update_fields: dict = {
        'status': to_status,
        'updated_at': timezone.now(),
    }
    if extra_fields:
        update_fields.update(extra_fields)

    rows = (
        VideoRecording.objects
        .filter(pk=recording_id, status__in=list(allowed_from))
        .update(**update_fields)
    )
    if rows == 0:
        logger.info(
            "advance_recording id=%s no-op (already past %s)",
            recording_id, to_status,
        )
    return rows > 0


# ---------------------------------------------------------------------------
# VideoRoom — allowed transitions.
# ---------------------------------------------------------------------------

ROOM_TRANSITIONS: dict[str, set[str]] = {
    VideoRoom.Status.ACTIVE: {VideoRoom.Status.SCHEDULED, VideoRoom.Status.ENDED},
    VideoRoom.Status.ENDED: {VideoRoom.Status.SCHEDULED, VideoRoom.Status.ACTIVE},
    VideoRoom.Status.SCHEDULED: {VideoRoom.Status.ENDED},
    VideoRoom.Status.ERROR: {
        VideoRoom.Status.SCHEDULED,
        VideoRoom.Status.ACTIVE,
        VideoRoom.Status.ENDED,
    },
}


def advance_room(
    room_id: int,
    *,
    to_status: str,
    extra_fields: Optional[dict] = None,
) -> bool:
    """
    Atomically transition a VideoRoom row to `to_status` if its current
    status is one of the allowed predecessors. Returns True on transition.
    """
    if to_status not in ROOM_TRANSITIONS:
        raise ValueError(f"Unknown VideoRoom target status: {to_status!r}")

    allowed_from = ROOM_TRANSITIONS[to_status]

    update_fields: dict = {
        'status': to_status,
        'updated_at': timezone.now(),
    }
    if extra_fields:
        update_fields.update(extra_fields)

    rows = (
        VideoRoom.objects
        .filter(pk=room_id, status__in=list(allowed_from))
        .update(**update_fields)
    )
    return rows > 0


# ---------------------------------------------------------------------------
# Per-room advisory lock.
#
# Used by the webhook dispatcher to serialize all webhook handlers for a
# given room. Postgres advisory locks are session-scoped; we use the
# transaction-bound variant so the lock auto-releases on commit/rollback.
#
# Key derivation: `pg_advisory_xact_lock(BIGINT)` takes a single 64-bit int.
# We hash the room.id with a fixed namespace so different lock domains
# (rooms, recordings, …) can't collide if we add more locks later.
# ---------------------------------------------------------------------------

_ROOM_LOCK_NAMESPACE = 0x_5664_726F_6F6D_0001  # 'Vdroom\0\1' — distinct from anything else


def acquire_room_lock(room_id: int) -> None:
    """
    Acquire a Postgres transaction-scoped advisory lock keyed on the room id.
    Must be called inside an open transaction. The lock releases automatically
    on COMMIT/ROLLBACK.

    No-op on non-Postgres backends (e.g. SQLite in tests).
    """
    if not transaction.get_autocommit():
        # We're inside a transaction — proceed.
        pass

    vendor = connection.vendor
    if vendor != 'postgresql':
        # SQLite (test) and others: rely on state-machine guards for correctness.
        return

    # Two-int form: namespace + room_id, masked to int32 each. Bigint hash
    # keys would also work; this form makes lock ownership easier to audit.
    with connection.cursor() as cur:
        cur.execute(
            "SELECT pg_advisory_xact_lock(%s, %s)",
            [_ROOM_LOCK_NAMESPACE & 0x7FFFFFFF, room_id & 0x7FFFFFFF],
        )
