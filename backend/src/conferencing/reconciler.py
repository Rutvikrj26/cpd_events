"""
Stale-state reconciler for video conferencing.

LiveKit webhooks can be missed (provider downtime, network blips, container
restarts). This module scrubs DB rows whose state has been wedged for too
long, so organizers don't see ghost "recording in progress" indicators or
ACTIVE rooms that are actually long gone.

Run via Celery beat (registered in config/celery.py).
"""

import logging
from datetime import timedelta

from django.utils import timezone

from common.cloud_tasks import CloudTask
from conferencing.models import VideoRecording, VideoRoom

logger = logging.getLogger(__name__)


# Tolerances. Conservative — better to leave a row alone for an extra few
# minutes than nuke a healthy session because of a slow webhook.
ROOM_ACTIVE_GRACE = timedelta(hours=2)
RECORDING_RECORDING_GRACE = timedelta(hours=1)
RECORDING_PROCESSING_GRACE = timedelta(minutes=30)


@CloudTask
def reconcile_stale_video_state():
    """
    Scrub VideoRoom and VideoRecording rows whose status is wedged.

    Strategy: time-based, not API-based. We don't poll LiveKit because the
    egress container might be down (which is exactly when reconciliation
    matters). If a row hasn't received a webhook in N hours, we treat its
    egress as dead and finalize the row.
    """
    now = timezone.now()
    rooms_marked = _reconcile_rooms(now)
    recordings_marked = _reconcile_recordings(now)

    if rooms_marked or recordings_marked:
        logger.info(
            "reconcile_stale_video_state: rooms=%d recordings=%d",
            rooms_marked, recordings_marked,
        )
    return {'rooms': rooms_marked, 'recordings': recordings_marked}


def _reconcile_rooms(now) -> int:
    """ACTIVE rooms older than the grace window get force-ended."""
    cutoff = now - ROOM_ACTIVE_GRACE
    qs = VideoRoom.objects.filter(
        status=VideoRoom.Status.ACTIVE,
        started_at__lt=cutoff,
    )
    count = 0
    for room in qs:
        logger.warning(
            "Reconciler force-ending stale ACTIVE room %s (started %s)",
            room.room_name, room.started_at,
        )
        room.mark_ended()
        count += 1
    return count


def _reconcile_recordings(now) -> int:
    """
    RECORDING/PROCESSING recordings stuck past their grace window get marked
    ERROR with a note, so the UI can surface "this recording failed" instead
    of an indefinite spinner.
    """
    count = 0

    recording_cutoff = now - RECORDING_RECORDING_GRACE
    stuck_recording = VideoRecording.objects.filter(
        status=VideoRecording.Status.RECORDING,
        updated_at__lt=recording_cutoff,
    )
    for rec in stuck_recording:
        logger.warning(
            "Reconciler marking stale RECORDING %s as ERROR (last update %s)",
            rec.uuid, rec.updated_at,
        )
        rec.status = VideoRecording.Status.ERROR
        rec.recording_end = rec.recording_end or now
        rec.save(update_fields=['status', 'recording_end', 'updated_at'])
        count += 1

    processing_cutoff = now - RECORDING_PROCESSING_GRACE
    stuck_processing = VideoRecording.objects.filter(
        status=VideoRecording.Status.PROCESSING,
        updated_at__lt=processing_cutoff,
    )
    for rec in stuck_processing:
        logger.warning(
            "Reconciler marking stale PROCESSING %s as ERROR (last update %s)",
            rec.uuid, rec.updated_at,
        )
        rec.status = VideoRecording.Status.ERROR
        rec.save(update_fields=['status', 'updated_at'])
        count += 1

    return count
