"""
Async tasks for video conferencing.

These tasks handle webhook processing, room creation, and attendance tracking.
"""

import logging
import traceback
from datetime import datetime, timezone as _stdlib_tz

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from common.cloud_tasks import CloudTask

logger = logging.getLogger(__name__)


@CloudTask
def start_event_recording(event_id: int):
    """
    Start a LiveKit room-composite egress for the given event.

    Creates a ``VideoRecording`` row in ``RECORDING`` state so the frontend
    can show a "recording" badge immediately; the ``egress_ended`` webhook
    updates it to ``AVAILABLE`` with the stored file path.
    """
    from conferencing.models import VideoRecording, VideoRoom
    from conferencing.service import get_video_provider
    from events.models import Event

    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        logger.warning("start_event_recording: event %s not found", event_id)
        return

    ct = ContentType.objects.get_for_model(Event)
    video_room = VideoRoom.objects.filter(content_type=ct, object_id=event.id).first()
    if not video_room:
        logger.info("start_event_recording: no VideoRoom for event %s", event_id)
        return

    if VideoRecording.objects.filter(
        video_room=video_room,
        status__in=[VideoRecording.Status.RECORDING, VideoRecording.Status.PROCESSING],
    ).exists():
        logger.info("Recording already in flight for event %s", event_id)
        return

    provider = get_video_provider()
    if not provider.is_configured():
        logger.warning("Video provider not configured; skipping recording start")
        return

    try:
        egress_id = provider.start_recording(
            room_name=video_room.room_name,
            output_path=f"recordings/{video_room.room_name}.mp4",
        )
    except Exception:
        logger.exception("Failed to start recording for event %s", event_id)
        return

    VideoRecording.objects.create(
        video_room=video_room,
        event=event,
        egress_id=egress_id,
        provider='livekit',
        status=VideoRecording.Status.RECORDING,
        recording_start=timezone.now(),
        access_level=VideoRecording.AccessLevel.REGISTRANTS,
    )
    logger.info("Recording started for event %s (egress=%s)", event_id, egress_id)


@CloudTask
def stop_event_recording(event_id: int):
    """Stop the in-flight egress for the given event, if any."""
    from conferencing.models import VideoRecording
    from conferencing.service import get_video_provider

    recording = (
        VideoRecording.objects.filter(
            event_id=event_id,
            status=VideoRecording.Status.RECORDING,
        )
        .order_by('-created_at')
        .first()
    )
    if not recording:
        logger.info("stop_event_recording: no in-flight recording for event %s", event_id)
        return

    provider = get_video_provider()
    if not provider.is_configured():
        logger.warning("Video provider not configured; cannot stop recording")
        return

    from conferencing.state_machine import advance_recording

    try:
        provider.stop_recording(recording.egress_id)
    except Exception:
        logger.exception("Failed to stop recording for event %s", event_id)
        advance_recording(recording.id, to_status=VideoRecording.Status.ERROR)
        return

    advance_recording(recording.id, to_status=VideoRecording.Status.PROCESSING)


def process_video_webhook(webhook_log_id: int):
    """
    Process a video webhook event.

    Handles: room_started, room_finished, participant_joined,
    participant_left, recording_ended, recording_started.

    Concurrency model: all webhooks for a given room are serialized via a
    Postgres advisory transaction lock keyed on `video_room.id`. This
    eliminates races between handlers that mutate VideoRoom and
    VideoRecording state. Different rooms remain concurrent.

    Defense-in-depth: handlers also use guarded SQL UPDATEs so a row in a
    terminal state can never be regressed, even if the lock is bypassed
    (e.g. by the reconciler running a manual transition).
    """
    from django.db import transaction

    from conferencing.models import VideoRecording, VideoRoom, VideoWebhookLog
    from conferencing.state_machine import acquire_room_lock

    try:
        log = VideoWebhookLog.objects.select_related('video_room').get(id=webhook_log_id)
    except VideoWebhookLog.DoesNotExist:
        logger.error("VideoWebhookLog %s not found", webhook_log_id)
        return

    log.start_processing()
    video_room = log.video_room

    if not video_room:
        log.mark_skipped("No linked VideoRoom")
        return

    try:
        # Serialize per-room. Lock auto-releases on commit/rollback.
        with transaction.atomic():
            acquire_room_lock(video_room.id)
            # Refresh inside the lock so we see writes from any handler that
            # finished while we were waiting.
            video_room.refresh_from_db()

            event_type = log.event_type
            payload = log.payload
            records_created = 0

            if event_type == 'room_started':
                _on_room_started(video_room)

            elif event_type == 'room_finished':
                _on_room_finished(video_room)

            elif event_type == 'participant_joined':
                records_created = _handle_participant_joined(video_room, payload)

            elif event_type == 'participant_left':
                records_created = _handle_participant_left(video_room, payload)

            elif event_type == 'recording_ended':
                _handle_recording_ended(video_room, payload)

        # Mark log outside the lock so its update doesn't extend the lock
        # window unnecessarily.
        log.mark_completed(records_created=records_created)

    except Exception as e:
        logger.exception("Error processing video webhook %s", webhook_log_id)
        log.mark_failed(str(e), traceback.format_exc())


def _on_room_started(video_room):
    """Apply room_started — delegates to `_ensure_room_active`.

    The same side-effects must run if `room_started` was missed and a
    later event (participant_joined) is the first reliable signal that
    the room is up. Keeping the work in `_ensure_room_active` lets both
    paths share a single, idempotent implementation.
    """
    _ensure_room_active(video_room)


def _ensure_room_active(video_room):
    """Idempotent "room is now active" side-effects.

    Invoked from any handler that observes a live room — currently
    `room_started` (when it arrives in time) and `participant_joined`
    (always reliable because we know the VideoRoom row is linked by
    then). Webhook ordering is not guaranteed: `room_started` can arrive
    before the VideoRoom row commits and get skipped by the receiver.
    Without this backstop the entire room-start chain (mark content live,
    auto-record, provision transcript) never runs.

    Every step inside MUST be idempotent. We rely on:
      - `_mark_content_live` flipping only on `status == 'published'`
      - `start_recording_if_enabled` checking for an existing recording
      - `provision_transcript_if_enabled` early-returning when a
        transcript row already exists (which also gates the agent
        dispatch)

    This handler is the **single source of truth** for recording start
    and transcript provisioning. The HTTP API endpoints in
    `conferencing.meetings` deliberately do NOT trigger these
    side-effects — they only mint tokens. Anything that wants to know
    "has the room actually become live?" has to wait for the webhook.
    """
    from conferencing.state_machine import advance_room
    from conferencing.models import VideoRoom

    if video_room.status != VideoRoom.Status.ACTIVE:
        advanced = advance_room(
            video_room.id,
            to_status=VideoRoom.Status.ACTIVE,
            extra_fields={
                'started_at': timezone.now(),
                'error': '',
            },
        )
        if advanced:
            # Reload after the SQL UPDATE so downstream helpers see
            # fresh state (e.g. started_at populated for the recording
            # output-path template).
            video_room.refresh_from_db()

    _mark_content_live(video_room)
    start_recording_if_enabled(video_room)
    provision_transcript_if_enabled(video_room)


def _on_room_finished(video_room):
    """
    Apply room_finished: stop in-flight recordings, transition VideoRoom →
    ENDED, mark linked content completed.

    For Zoom rooms we additionally enqueue ``sync_zoom_attendance`` to
    reconcile the per-meeting attendance report with the records we
    already created from participant_joined/left webhooks. The report
    API is authoritative — it dedupes networks/rejoin segments into a
    single per-participant total — but it can lag the meeting.ended
    webhook by ~1 minute, so the task itself is tolerant of an empty
    response and idempotent on re-run.
    """
    from conferencing.state_machine import advance_room
    from conferencing.models import VideoRoom

    # Stop any in-flight recording before marking the room ended; LiveKit
    # fires room_finished when the room empties for its configured timeout
    # (or on admin force-end), so this is the correct moment to flush egress.
    _stop_active_recordings(video_room)

    advance_room(
        video_room.id,
        to_status=VideoRoom.Status.ENDED,
        extra_fields={'ended_at': timezone.now()},
    )
    video_room.refresh_from_db()
    _mark_content_ended(video_room)
    finalize_transcript(video_room)

    if video_room.provider == 'zoom' and video_room.zoom_meeting_id:
        # NOTE: CloudTask.schedule() is currently a stub (see
        # common/cloud_tasks.py), so we cannot push a delayed task to
        # absorb Zoom's ~60s report lag. The sync task itself is
        # tolerant — it logs and exits when the report is empty, and
        # is idempotent on re-run, so a manual replay (or future
        # delay-aware enqueue) catches up cleanly.
        sync_zoom_attendance.delay(video_room.zoom_meeting_id)


def _mark_content_live(video_room):
    """Mark the linked content object as live/active."""
    obj = video_room.content_object
    if obj is None:
        return

    model_name = video_room.content_type.model
    if model_name == 'event':
        if hasattr(obj, 'status') and obj.status == 'published':
            obj.status = 'live'
            obj.save(update_fields=['status', 'updated_at'])
            logger.info("Event %s marked as live", obj.uuid)


def _mark_content_ended(video_room):
    """Mark the linked content object as completed.

    Zoom-model: an Event can host many meeting sessions over its
    lifetime — host clicks Start, runs the meeting, clicks End, then
    optionally clicks Start again later in the same scheduled window.
    The Event's status is therefore *schedule-driven*, not
    *meeting-driven*: we only mark it ``completed`` once the scheduled
    end time has passed. A meeting ending mid-window (host leaves
    early, comes back, runs another session) leaves the Event in
    ``live`` so the lobby can offer "Start a new meeting" to the host
    and "Waiting for host" to attendees.
    """
    obj = video_room.content_object
    if obj is None:
        return

    model_name = video_room.content_type.model
    if model_name == 'event':
        if not getattr(obj, 'status', None) == 'live':
            return
        # `is_past` checks `starts_at + duration_minutes < now` — i.e. the
        # scheduled window has actually ended. Without this guard a 30-second
        # test-and-leave terminates the event for every other registered
        # learner in the lobby.
        if not getattr(obj, 'is_past', False):
            logger.info(
                "Event %s room ended but scheduled session still in progress; "
                "leaving event status=live (room can be reopened by host).",
                obj.uuid,
            )
            return
        obj.status = 'completed'
        obj.save(update_fields=['status', 'updated_at'])
        logger.info("Event %s marked as completed", obj.uuid)


def _handle_participant_joined(video_room, payload):
    """Create attendance record when a participant joins.

    Also acts as a backstop for `room_started` events that the receiver
    skipped because the VideoRoom row hadn't committed yet. We re-run
    the room-active side-effects here; everything inside is idempotent
    so this is safe even when room_started was processed normally.

    Provider branching:
      * LiveKit — match `participant.identity` (a UUID) → User → Registration.
      * Zoom    — match `participant.registrant_id` (preferred) or
        ``email`` → Registration. Zoom user_ids are not UUIDs, so the
        UUID guard used for LiveKit cannot apply here.
    """
    import uuid as _uuid

    # Backstop must run BEFORE attendance recording so a missed
    # room_started doesn't leave the room in 'scheduled' status — some
    # downstream attendance logic checks the room state.
    _ensure_room_active(video_room)

    if video_room.provider == 'zoom':
        return _handle_zoom_participant_joined(video_room, payload)

    participant = payload.get('participant', {})
    identity = participant.get('identity', '')
    name = participant.get('name', '')

    if not identity:
        return 0

    # Egress / ingress participants are bots, not learners. We assign user
    # identities as UUIDs at join-token generation time, so anything that
    # doesn't parse as a UUID is a service participant — skip it.
    try:
        _uuid.UUID(str(identity))
    except (ValueError, AttributeError):
        return 0

    model_name = video_room.content_type.model
    records = 0

    if model_name == 'event':
        records = _create_event_attendance(video_room, identity, name)
    elif model_name == 'coursesession':
        records = _create_session_attendance(video_room, identity, name)

    return records


def _handle_participant_left(video_room, payload):
    """Update attendance record when a participant leaves.

    Also implements the Zoom-model "auto-end when last host leaves"
    rule: if the leaving participant was a host AND the room has no
    other host-eligible participants left, we trigger a clean
    end-meeting via the LiveKit API. The empty-room timeout is the
    safety net; this just makes the common case (host clicks Leave
    instead of End) end the meeting promptly for the attendees.

    Provider branching: Zoom rooms close out attendance against a
    registrant_id/email key; the auto-end-on-last-host-leave logic is
    LiveKit-only because it depends on a real-time participant list
    that Zoom's REST API doesn't expose mid-meeting (see
    ``ZoomProvider.list_participants`` — post-meeting only).
    """
    if video_room.provider == 'zoom':
        return _handle_zoom_participant_left(video_room, payload)

    participant = payload.get('participant', {})
    identity = participant.get('identity', '')

    if not identity:
        return 0

    model_name = video_room.content_type.model

    if model_name == 'event':
        _update_event_attendance(video_room, identity)
    elif model_name == 'coursesession':
        _update_session_attendance(video_room, identity)

    _maybe_auto_end_on_last_host_leave(video_room, identity)

    return 0


# =========================================================================
# Zoom-specific participant webhook handlers
# =========================================================================
#
# Zoom delivers participant events with a different shape than LiveKit:
# the participant identity is `user_id` (not a UUID) and matching back
# to our Registration relies on `registrant_id` or `email` rather than
# a User-row lookup. The helpers below mirror the LiveKit path
# (_create_event_attendance / _update_event_attendance) but consume the
# raw Zoom webhook body and key on Zoom's identifiers.


def _zoom_participant_from_payload(payload: dict) -> tuple[dict, dict]:
    """Pluck ``(participant, object)`` from a raw Zoom webhook body.

    Zoom wraps the meeting/participant payload as
    ``payload -> object -> {id, uuid, topic, participant: {...}}``.
    This helper keeps both join and left handlers on the same shape.
    """
    obj = (payload.get('payload') or {}).get('object') or {}
    participant = obj.get('participant') or {}
    return participant, obj


def _resolve_zoom_registration(event, registrant_id: str, email: str):
    """Match a Zoom participant back to a Registration row.

    Preference order:
      1. ``zoom_registrant_id`` — exact match, only set when the
         attendee registered via Zoom's built-in flow.
      2. ``email`` — case-insensitive fallback for participants that
         joined without going through Zoom registration (e.g. an
         instructor who used the ``start_url``).

    Returns the Registration or None.
    """
    from registrations.models import Registration

    if registrant_id:
        reg = Registration.objects.filter(
            event=event,
            zoom_registrant_id=registrant_id,
            deleted_at__isnull=True,
        ).first()
        if reg:
            return reg
    if email:
        return Registration.objects.filter(
            event=event,
            email__iexact=email,
            deleted_at__isnull=True,
        ).first()
    return None


def _handle_zoom_participant_joined(video_room, payload) -> int:
    """Zoom-shaped ``participant_joined`` — create an AttendanceRecord.

    Creates one open record per ``(event, participant_id, join_time)``.
    De-dups on a re-delivered webhook so re-running with the same
    payload is a no-op.
    """
    from registrations.models import AttendanceRecord

    if video_room.content_type.model != 'event':
        # Course-session attendance for Zoom isn't wired yet — log so
        # the gap is visible if the path ever fires.
        logger.info(
            "Zoom participant_joined for non-event content (%s); skipping",
            video_room.content_type.model,
        )
        return 0

    event = video_room.content_object
    if not event:
        return 0

    participant, _obj = _zoom_participant_from_payload(payload)
    user_id = participant.get('user_id') or participant.get('id') or ''
    name = participant.get('user_name') or ''
    email = (participant.get('email') or '').strip()
    registrant_id = participant.get('registrant_id') or ''
    join_time_raw = participant.get('join_time')

    # The participant_id stored on AttendanceRecord must match the key
    # used to upsert in sync_zoom_attendance, otherwise the report-pass
    # leaves stale webhook rows behind. ``registrant_id`` is the
    # canonical key when present; we fall back to ``user_id`` only
    # when Zoom didn't surface a registrant (e.g. an instructor that
    # joined via the start_url).
    participant_id = registrant_id or user_id
    if not participant_id and not email:
        return 0

    join_time = _parse_zoom_timestamp(join_time_raw) or timezone.now()

    registration = _resolve_zoom_registration(event, registrant_id, email)

    # De-dup webhook re-delivery: same participant_id + join_time is
    # the same join event.
    if AttendanceRecord.objects.filter(
        event=event,
        participant_id=participant_id,
        join_time=join_time,
    ).exists():
        return 0

    resolved_email = (registration.email if registration else email) or ''

    AttendanceRecord.objects.create(
        event=event,
        registration=registration,
        participant_id=participant_id,
        external_user_id=user_id,
        participant_email=resolved_email.lower(),
        participant_name=name,
        join_time=join_time,
        is_matched=bool(registration),
        matched_at=timezone.now() if registration else None,
    )
    return 1


def _handle_zoom_participant_left(video_room, payload) -> int:
    """Zoom-shaped ``participant_left`` — close the open AttendanceRecord.

    Looks up the most-recent open (``leave_time IS NULL``) record for
    the same participant and calls ``record.participant_left(...)`` so
    duration + registration summary recompute via the model helpers.
    """
    from registrations.models import AttendanceRecord

    if video_room.content_type.model != 'event':
        return 0

    event = video_room.content_object
    if not event:
        return 0

    participant, _obj = _zoom_participant_from_payload(payload)
    user_id = participant.get('user_id') or participant.get('id') or ''
    registrant_id = participant.get('registrant_id') or ''
    email = (participant.get('email') or '').strip()
    leave_time_raw = participant.get('leave_time')
    leave_time = _parse_zoom_timestamp(leave_time_raw) or timezone.now()

    participant_id = registrant_id or user_id
    if not participant_id and not email:
        return 0

    qs = AttendanceRecord.objects.filter(event=event, leave_time__isnull=True)
    record = None
    if participant_id:
        record = qs.filter(participant_id=participant_id).order_by('-join_time').first()
    if record is None and email:
        # Fallback: rare case where the join keyed on registrant_id
        # but the leave event omits it (or vice versa). Match on
        # email so we don't leak open records.
        record = qs.filter(participant_email__iexact=email).order_by('-join_time').first()

    if record is None:
        return 0

    record.participant_left(leave_time=leave_time)
    return 0


def _parse_zoom_timestamp(value):
    """Parse an ISO-8601 timestamp from a Zoom payload.

    Zoom emits ``2024-01-01T12:34:56Z`` style strings for
    ``join_time``/``leave_time``. ``django.utils.dateparse.parse_datetime``
    handles those in standard form; on failure we return None and the
    caller falls back to ``timezone.now()``.
    """
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        from django.utils.dateparse import parse_datetime
        parsed = parse_datetime(str(value))
        if parsed is not None and timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, _stdlib_tz.utc)
        return parsed
    except (ValueError, TypeError):
        return None


@CloudTask
def sync_zoom_attendance(meeting_id: str):
    """Reconcile AttendanceRecords for a Zoom meeting against the report API.

    Triggered from ``_on_room_finished`` once Zoom signals
    ``meeting.ended``. Zoom's ``/report/meetings/{id}/participants``
    endpoint is the authoritative source for per-participant totals —
    it dedupes rejoin segments into a single (join_time, leave_time,
    duration) tuple per participant. Webhook-derived AttendanceRecords
    capture each segment in real time; this task replaces them with
    the report's authoritative roll-up so denormalised attendance
    summaries (``Registration.total_attendance_minutes`` etc.) are
    correct even when webhooks dropped or arrived out of order.

    Idempotency: re-running on the same ``meeting_id`` produces the
    same final state. For each report participant we delete any
    existing AttendanceRecords keyed on the same ``participant_id``
    and re-insert the report's row, then call
    ``Registration.update_attendance_summary()`` so the denormalised
    fields reflect the single deduped record.

    Tolerance: the Zoom report can lag the meeting.ended webhook by
    ~60 seconds. ``CloudTask.schedule()`` is currently a stub so we
    cannot defer enqueue; instead we tolerate an empty report (just
    log + exit) so a future replay can fill it in.
    """
    from conferencing.models import VideoRoom
    from conferencing.service import get_video_provider
    from registrations.models import AttendanceRecord

    if not meeting_id:
        return

    video_room = (
        VideoRoom.objects
        .filter(zoom_meeting_id=str(meeting_id), provider='zoom')
        .order_by('-created_at')
        .first()
    )
    if video_room is None:
        logger.info("sync_zoom_attendance: no Zoom VideoRoom for meeting %s", meeting_id)
        return

    if video_room.content_type.model != 'event':
        # Not currently wired for course sessions over Zoom.
        return

    event = video_room.content_object
    if event is None:
        return

    provider = get_video_provider()
    if not provider.is_configured():
        logger.warning(
            "sync_zoom_attendance: provider not configured; skipping meeting %s",
            meeting_id,
        )
        return

    try:
        participants = provider.list_participants(meeting_id)
    except Exception:
        logger.exception(
            "sync_zoom_attendance: list_participants raised for meeting %s", meeting_id,
        )
        return

    if not participants:
        # Report API hasn't materialised yet (typical 30–90s lag), or
        # the meeting genuinely had no joiners. Either way, nothing to
        # reconcile this pass — webhook records remain authoritative.
        logger.info(
            "sync_zoom_attendance: empty report for meeting %s; leaving "
            "webhook-derived records in place",
            meeting_id,
        )
        return

    affected_registrations: set[int] = set()
    rows_written = 0

    for p in participants:
        meta = p.metadata or {}
        registrant_id = (meta.get('registrant_id') or '').strip()
        email = (meta.get('email') or '').strip()
        # Zoom report exposes the participant's user_id in `identity`;
        # we still prefer registrant_id as the upsert key so the row
        # collapses with whatever the participant_joined webhook
        # wrote.
        user_id = p.identity or ''
        participant_id = registrant_id or user_id
        if not participant_id and not email:
            continue

        join_time = _parse_zoom_timestamp(meta.get('join_time'))
        leave_time = _parse_zoom_timestamp(meta.get('leave_time'))
        duration_raw = meta.get('duration') or 0
        try:
            # Zoom reports duration in seconds.
            duration_seconds = int(duration_raw)
        except (TypeError, ValueError):
            duration_seconds = 0
        duration_minutes = max(0, duration_seconds // 60)

        registration = _resolve_zoom_registration(event, registrant_id, email)

        # Replace per-participant: delete prior records and insert the
        # report's authoritative row. Scope tightly so an email-only
        # participant (rare: empty registrant_id AND empty user_id)
        # doesn't wipe other email-only rows on the same event.
        if participant_id:
            AttendanceRecord.objects.filter(
                event=event, participant_id=participant_id,
            ).delete()
        elif email:
            AttendanceRecord.objects.filter(
                event=event,
                participant_id='',
                participant_email__iexact=email,
            ).delete()

        record_join = join_time or timezone.now()
        record = AttendanceRecord.objects.create(
            event=event,
            registration=registration,
            participant_id=participant_id,
            external_user_id=user_id,
            participant_email=((registration.email if registration else email) or '').lower(),
            participant_name=p.name or '',
            join_time=record_join,
            leave_time=leave_time,
            is_matched=bool(registration),
            matched_at=timezone.now() if registration else None,
        )
        # Zoom's report gives one row per participant where `duration`
        # is the **sum across rejoins** but `join_time`/`leave_time`
        # are first-join / last-leave. Wall-clock `(leave - join)` is
        # therefore inflated for any rejoiner. AttendanceRecord.save()
        # auto-derives duration_minutes from those timestamps when
        # leave_time is set, which would clobber the authoritative
        # value — bypass with a queryset .update().
        AttendanceRecord.objects.filter(pk=record.pk).update(
            duration_minutes=duration_minutes,
        )
        rows_written += 1

        if registration is not None:
            affected_registrations.add(registration.id)

    # Recompute denormalised summaries once per registration. Pull
    # fresh objects to avoid stale field values from the webhook pass.
    if affected_registrations:
        from registrations.models import Registration

        for reg in Registration.objects.filter(id__in=affected_registrations):
            reg.update_attendance_summary()

    logger.info(
        "sync_zoom_attendance: meeting=%s reconciled %d participants "
        "(%d registrations updated)",
        meeting_id, rows_written, len(affected_registrations),
    )


def _maybe_auto_end_on_last_host_leave(video_room, leaving_identity):
    """If the host that just left was the last host in the room, end the
    meeting so attendees aren't stranded.

    Cheap to evaluate: checks the host predicate for the leaving
    participant first, and only then queries LiveKit for the remaining
    participants. Most leaves are non-hosts, so this is a single
    is_event_host call → False → return.
    """
    # Only ACTIVE rooms can be auto-ended. SCHEDULED rooms haven't
    # really started; ENDED is already terminal.
    if video_room.status != video_room.Status.ACTIVE:
        return

    parent = video_room.content_object
    if parent is None:
        return

    leaving_user = _resolve_user_for_identity(leaving_identity)
    if leaving_user is None:
        return

    if not _is_host_for_room(leaving_user, video_room, parent):
        return

    from conferencing.service import get_video_provider
    provider = get_video_provider()
    if not provider.is_configured():
        return

    try:
        remaining = provider.list_participants(video_room.room_name)
    except Exception:
        logger.exception(
            "list_participants failed for %s; skipping auto-end check",
            video_room.room_name,
        )
        return

    for p in remaining:
        if p.identity == leaving_identity:
            # LiveKit is sometimes still listing the leaver mid-disconnect.
            continue
        other_user = _resolve_user_for_identity(p.identity)
        if other_user is not None and _is_host_for_room(other_user, video_room, parent):
            # At least one other host is still present; meeting continues.
            return

    logger.info(
        "Last host %s left room %s; ending meeting",
        leaving_identity, video_room.room_name,
    )
    try:
        provider.delete_room(video_room.room_name)
    except Exception:
        logger.exception(
            "delete_room failed in last-host auto-end for %s; relying on "
            "empty-room timeout to fire room_finished",
            video_room.room_name,
        )


def _resolve_user_for_identity(identity: str):
    """Map a LiveKit participant.identity → User (or None for guests/agents).

    Authenticated users get identity = str(user.uuid); guests get
    identity = "guest-{registration_uuid}"; the transcription agent
    gets identity = "accredit-agent-…". Only the first form maps to a
    User row, which is what host detection cares about.
    """
    import uuid as _uuid
    from accounts.models import User
    try:
        u = _uuid.UUID(str(identity))
    except (ValueError, AttributeError):
        return None
    try:
        return User.objects.get(uuid=u)
    except User.DoesNotExist:
        return None


def _is_host_for_room(user, video_room, parent) -> bool:
    """Check the right host predicate for the room's content object."""
    from conferencing.views import is_course_session_host, is_event_host
    from events.models import Event
    from learning.models import CourseSession

    if isinstance(parent, Event):
        return is_event_host(user, parent)
    if isinstance(parent, CourseSession):
        return is_course_session_host(user, parent.course)
    return False


def _create_event_attendance(video_room, participant_identity, participant_name):
    """Create an AttendanceRecord for an event participant."""
    from registrations.models import AttendanceRecord, Registration

    event = video_room.content_object
    if not event:
        return 0

    # Find registration by user UUID
    try:
        registration = Registration.objects.get(
            event=event,
            user__uuid=participant_identity,
            deleted_at__isnull=True,
        )
    except Registration.DoesNotExist:
        logger.info("No registration found for participant %s in event %s", participant_identity, event.uuid)
        return 0

    AttendanceRecord.objects.create(
        event=event,
        registration=registration,
        participant_id=participant_identity,
        participant_email=registration.user.email if registration.user else '',
        participant_name=participant_name,
        join_time=timezone.now(),
        is_matched=True,
    )
    return 1


def _update_event_attendance(video_room, participant_identity):
    """Update AttendanceRecord with leave time when participant leaves."""
    from registrations.models import AttendanceRecord

    event = video_room.content_object
    if not event:
        return

    # Find the open attendance record
    record = AttendanceRecord.objects.filter(
        registration__event=event,
        participant_id=participant_identity,
        leave_time__isnull=True,
    ).order_by('-join_time').first()

    if record:
        record.leave_time = timezone.now()
        if record.join_time:
            record.duration_minutes = int((record.leave_time - record.join_time).total_seconds() / 60)
        record.save(update_fields=['leave_time', 'duration_minutes', 'updated_at'])


def _create_session_attendance(video_room, participant_identity, participant_name):
    """Create attendance for a course session participant."""
    from learning.models import CourseEnrollment, CourseSessionAttendance

    session = video_room.content_object
    if not session:
        return 0

    # Find enrollment by user UUID
    try:
        enrollment = CourseEnrollment.objects.get(
            course=session.course,
            user__uuid=participant_identity,
            status='active',
        )
    except CourseEnrollment.DoesNotExist:
        logger.info("No enrollment found for participant %s in course session %s", participant_identity, session.uuid)
        return 0

    attendance, created = CourseSessionAttendance.objects.get_or_create(
        session=session,
        enrollment=enrollment,
        defaults={
            'participant_id': participant_identity,
            'participant_email': enrollment.user.email if enrollment.user else '',
            'join_time': timezone.now(),
            'attendance_minutes': 0,
        },
    )
    if not created:
        # Re-joining: update join time for a new segment
        attendance.join_time = timezone.now()
        attendance.save(update_fields=['join_time', 'updated_at'])

    return 1 if created else 0


def _update_session_attendance(video_room, participant_identity):
    """Update course session attendance with accumulated minutes."""
    from learning.models import CourseSessionAttendance

    session = video_room.content_object
    if not session:
        return

    attendance = CourseSessionAttendance.objects.filter(
        session=session,
        participant_id=participant_identity,
    ).first()

    if attendance and attendance.join_time:
        now = timezone.now()
        segment_minutes = int((now - attendance.join_time).total_seconds() / 60)
        attendance.attendance_minutes = (attendance.attendance_minutes or 0) + segment_minutes
        attendance.leave_time = now
        attendance.calculate_eligibility()

        attendance.save(update_fields=[
            'attendance_minutes', 'leave_time',
            'is_eligible', 'updated_at',
        ])
        attendance.enrollment.update_progress()


def start_recording_if_enabled(video_room):
    """
    If the parent event/session has recording_enabled=True, kick off
    LiveKit egress for the room. Single source of truth for recording
    auto-start; called from `_ensure_room_active` (which itself is
    invoked from the room_started + participant_joined webhooks).
    Idempotent via ensure_recording_started.

    NOT called from the HTTP API. The room must actually be ACTIVE
    (a participant publishing media) before egress can produce
    content; calling this synchronously from `StartMeetingView`
    historically created duplicate egresses against an empty room.
    """
    parent = video_room.content_object
    if parent is None:
        return

    from events.models import Event
    from learning.models import CourseSession

    if isinstance(parent, Event):
        recording_enabled = bool(
            (parent.video_settings or {}).get('recording_enabled', False)
        )
    elif isinstance(parent, CourseSession):
        recording_enabled = bool(
            getattr(parent, 'recording_enabled', False)
            or getattr(parent, 'auto_record', False)
        )
    else:
        return

    if not recording_enabled:
        return

    try:
        from conferencing.views import ensure_recording_started
        ensure_recording_started(video_room)
    except Exception:
        logger.exception(
            "Auto-start recording failed in room_started handler for %s", video_room.room_name,
        )


def _stop_active_recordings(video_room):
    """
    Issue stop_recording for any VideoRecording row still in RECORDING for
    this room and guard-transition them to PROCESSING. The egress_ended
    webhook (or the reconciler) finalizes them to AVAILABLE/ERROR.

    Idempotent: re-delivery of room_finished or rows that already moved past
    RECORDING are no-ops.
    """
    from conferencing.models import VideoRecording
    from conferencing.service import get_video_provider
    from conferencing.state_machine import advance_recording

    actives = list(
        VideoRecording.objects
        .filter(video_room=video_room, status=VideoRecording.Status.RECORDING)
        .only('id', 'egress_id')
    )
    if not actives:
        return

    provider = get_video_provider()
    for rec in actives:
        try:
            provider.stop_recording(rec.egress_id)
        except Exception:
            logger.exception(
                "Failed to stop egress %s during room_finished", rec.egress_id,
            )
        # Guarded: only flip if the row is still RECORDING. If
        # recording_ended already moved it to AVAILABLE/ERROR, no-op.
        advance_recording(
            rec.id,
            to_status=VideoRecording.Status.PROCESSING,
            extra_fields={'recording_end': timezone.now()},
        )


def _handle_recording_ended(video_room, payload):
    """
    Handle recording completion. Atomically transitions the row to its
    terminal state (AVAILABLE or ERROR) using the state machine, populates
    file rows, and (if eligible) auto-publishes.

    Idempotent: re-delivery of egress_ended for an already-finalized row is
    a no-op for the status transition; file rows use update_or_create.

    Zoom branch: cloud recordings are produced server-side by Zoom, so
    "recording_ended" arrives as ``recording.completed`` (mapped via
    ZoomProvider.parse_webhook). We don't have an egress to finalize —
    instead we enqueue the post-meeting downloader. The LiveKit branch
    below stays unchanged.
    """
    import os

    from conferencing.models import VideoRecording, VideoRecordingFile
    from conferencing.state_machine import advance_recording

    if (video_room.provider or '').lower() == 'zoom':
        meeting_id = (
            video_room.zoom_meeting_id
            or str(((payload.get('payload') or {}).get('object') or {}).get('id') or '')
        )
        if not meeting_id:
            logger.warning(
                "recording_ended for Zoom room %s but no zoom_meeting_id available",
                video_room.room_name,
            )
            return
        download_zoom_recording.delay(meeting_id)
        return

    egress_info = payload.get('egressInfo', {})
    egress_id = egress_info.get('egressId', '')

    if not egress_id:
        return

    from events.models import Event
    from learning.models import CourseSession

    owner = video_room.content_object
    parent_event = owner if isinstance(owner, Event) else None
    parent_session = owner if isinstance(owner, CourseSession) else None

    try:
        recording = VideoRecording.objects.get(egress_id=egress_id)
    except VideoRecording.DoesNotExist:
        # Late-arriving egress_ended for a row that was never pre-created.
        defaults = {'video_room': video_room, 'egress_id': egress_id, 'provider': 'livekit'}
        if parent_event:
            defaults['event'] = parent_event
        elif parent_session:
            defaults['course_session'] = parent_session
        recording = VideoRecording.objects.create(**defaults)
    else:
        # Existing row may have been created by ensure_recording_started before
        # the orphan-fix landed. Backfill the parent link if missing so the
        # listing endpoint surfaces it.
        backfill = {}
        if parent_event and recording.event_id is None:
            backfill['event'] = parent_event
        if parent_session and recording.course_session_id is None:
            backfill['course_session'] = parent_session
        if backfill:
            for k, v in backfill.items():
                setattr(recording, k, v)
            recording.save(update_fields=list(backfill.keys()) + ['updated_at'])

    # LiveKit reports the terminal egress state. EGRESS_COMPLETE → AVAILABLE,
    # anything else (ABORTED / FAILED / LIMIT_REACHED) → ERROR.
    egress_status = str(egress_info.get('status', '') or '').upper()
    target_status = (
        VideoRecording.Status.AVAILABLE
        if (not egress_status or egress_status == 'EGRESS_COMPLETE')
        else VideoRecording.Status.ERROR
    )

    # Aggregate file results before the state transition so the metadata
    # lands together. file_rows are created independently — append-only.
    file_results = egress_info.get('fileResults', [])
    total_size = 0
    total_duration_ns = 0
    primary_filename = ''

    for result in file_results:
        filename = result.get('filename', '')
        size = int(result.get('size', 0) or 0)
        duration_ns = int(result.get('duration', 0) or 0)
        total_size += size
        total_duration_ns += duration_ns
        if not primary_filename and filename:
            primary_filename = filename

        base_name = os.path.basename(filename) if filename else ''
        ext = os.path.splitext(base_name)[1] if base_name else ''
        VideoRecordingFile.objects.update_or_create(
            recording=recording,
            file_name=base_name,
            defaults={
                'file_type': VideoRecordingFile.FileType.VIDEO,
                'file_extension': ext,
                'file_size_bytes': size,
                'storage_url': '',  # Filled after recording.uuid is final.
            },
        )

    # Inherit auto_publish from parent event/session.
    #
    # Default is **False** (opt-in): if the event organizer / instructor
    # didn't explicitly turn on auto-publish in the event settings, the
    # recording stays unpublished and they must publish it manually after
    # review. This protects against accidentally exposing raw,
    # un-reviewed footage (e.g. a session that ran over with off-topic
    # discussion, or had a participant request to be removed). Flip the
    # `auto_publish_recording` setting in the event wizard to opt in.
    parent = video_room.content_object
    auto_publish = False
    if parent is not None:
        from events.models import Event
        from learning.models import CourseSession

        if isinstance(parent, Event):
            settings_dict = parent.video_settings if isinstance(parent.video_settings, dict) else {}
            auto_publish = bool(settings_dict.get('auto_publish_recording', False))
        elif isinstance(parent, CourseSession):
            auto_publish = bool(getattr(parent, 'recording_auto_publish', False))

    # Single guarded transition: only fires if status is still RECORDING or
    # PROCESSING. If a concurrent handler already wrote a terminal state,
    # this is a no-op and we leave well alone.
    advanced = advance_recording(
        recording.id,
        to_status=target_status,
        extra_fields={
            'recording_end': timezone.now(),
            'storage_path': primary_filename,
            'total_size_bytes': total_size,
            'duration_seconds': total_duration_ns // 1_000_000_000 if total_duration_ns else 0,
            'auto_publish': auto_publish,
        },
    )

    if advanced:
        # Reload after the SQL UPDATE so we serialize the right data downstream.
        recording.refresh_from_db()

    # Populate streaming URLs on the file rows (independent of status).
    for f in recording.files.all():
        if not f.storage_url:
            f.storage_url = f'/api/v1/video/recordings/{recording.uuid}/files/{f.uuid}/stream/'
            f.save(update_fields=['storage_url', 'updated_at'])

    # Auto-publish only if (a) eligible and (b) we won the race — i.e. our
    # advance moved the row to AVAILABLE. If a concurrent handler already
    # finalized the row, that handler decides publish state, not us.
    if advanced and recording.auto_publish and recording.status == VideoRecording.Status.AVAILABLE:
        recording.publish()

    logger.info(
        "Recording finalized: room=%s egress=%s status=%s advanced=%s",
        video_room.room_name, egress_id, recording.status, advanced,
    )


# =========================================================================
# Zoom recording ingestion
# =========================================================================
#
# Zoom Cloud auto-records every meeting (set at create_room time). When the
# meeting ends and Zoom finishes processing, it fires recording.completed.
# That webhook lands in `_handle_recording_ended` above, which enqueues
# `download_zoom_recording` — this task pulls every artifact (video / audio /
# chat / transcript VTT) into our GCS bucket, materialises VideoRecording +
# VideoRecordingFile rows, parses the VTT into TranscriptSegment rows, and
# (per setting) trashes the Zoom Cloud copy to keep the admin quota clean.
#
# Idempotency contract: re-running on the same meeting_id is safe.
# - VideoRecording is upserted on egress_id=meeting_id (unique).
# - VideoRecordingFile rows use update_or_create on (recording, file_name).
# - TranscriptSegment uses bulk_create(ignore_conflicts=True) keyed on the
#   partial unique constraint (transcript, provider_segment_id, source).


_ZOOM_FILE_TYPE_MAP = {
    'MP4': 'video',
    'M4A': 'audio',
    'CHAT': 'chat',
    'TRANSCRIPT': 'transcript',
    'CC': 'transcript',
    'CAPTIONS': 'transcript',
}


@CloudTask
def download_zoom_recording(meeting_id: str, webhook_log_id: int | None = None):
    """
    Pull a Zoom Cloud recording into GCS and finalize the VideoRecording.

    Looks up the VideoRoom by ``zoom_meeting_id``, fetches the recording
    manifest from Zoom, streams every file into ``default_storage`` under
    ``{RECORDING_STORAGE_DIR}/zoom/{meeting_id}/{file_id}.{ext}``, materialises
    VideoRecording + VideoRecordingFile rows, parses VTT transcripts into
    TranscriptSegment rows, and (per ``ZOOM_PURGE_AFTER_DOWNLOAD``) trashes
    the Zoom Cloud copy. Idempotent on ``meeting_id``.
    """
    import tempfile

    from django.conf import settings
    from django.core.files import File
    from django.core.files.storage import default_storage

    from conferencing.models import (
        VideoRecording,
        VideoRecordingFile,
        VideoRoom,
    )
    from conferencing.providers.zoom import ZoomProvider
    from conferencing.state_machine import advance_recording

    meeting_id = str(meeting_id)

    video_room = VideoRoom.objects.filter(zoom_meeting_id=meeting_id).first()
    if video_room is None:
        logger.warning(
            "download_zoom_recording: no VideoRoom for zoom_meeting_id=%s", meeting_id,
        )
        return

    provider = ZoomProvider()
    if not provider.is_configured():
        logger.warning(
            "download_zoom_recording: ZoomProvider not configured; skipping (meeting=%s)",
            meeting_id,
        )
        return

    # Resolve event/course_session link off the parent.
    from events.models import Event
    from learning.models import CourseSession
    parent = video_room.content_object
    parent_event = parent if isinstance(parent, Event) else None
    parent_session = parent if isinstance(parent, CourseSession) else None

    # Upsert the parent VideoRecording row. egress_id == meeting_id is the
    # idempotency key; provider='zoom'. Default status on insert is RECORDING
    # (the model default); we advance it through the state machine below.
    recording, created = VideoRecording.objects.get_or_create(
        egress_id=meeting_id,
        defaults={
            'video_room': video_room,
            'provider': 'zoom',
            'event': parent_event,
            'course_session': parent_session,
            'recording_start': timezone.now(),
            'access_level': VideoRecording.AccessLevel.REGISTRANTS,
        },
    )
    if not created:
        # Backfill parent links if missing (mirrors the LiveKit branch).
        backfill = {}
        if parent_event and recording.event_id is None:
            backfill['event'] = parent_event
        if parent_session and recording.course_session_id is None:
            backfill['course_session'] = parent_session
        if backfill:
            for k, v in backfill.items():
                setattr(recording, k, v)
            recording.save(update_fields=list(backfill.keys()) + ['updated_at'])

    # RECORDING → PROCESSING (no-op if already past).
    advance_recording(recording.id, to_status=VideoRecording.Status.PROCESSING)
    recording.refresh_from_db()

    try:
        manifest = provider.get_meeting_recordings(meeting_id)
    except Exception:
        logger.exception(
            "download_zoom_recording: get_meeting_recordings failed (meeting=%s)",
            meeting_id,
        )
        advance_recording(recording.id, to_status=VideoRecording.Status.ERROR)
        return

    download_token = manifest.get('download_access_token') or ''
    files = manifest.get('recording_files') or []

    storage_dir = getattr(settings, 'RECORDING_STORAGE_DIR', '/recordings').rstrip('/')

    primary_video_path = ''
    total_size = 0
    earliest_start = None
    latest_end = None
    transcript_payloads: list[tuple[str, bytes]] = []  # (file_id, vtt_bytes)

    try:
        for f in files:
            file_type_raw = (f.get('file_type') or '').upper()
            if file_type_raw == 'TIMELINE':
                continue
            mapped_type = _ZOOM_FILE_TYPE_MAP.get(file_type_raw)
            if not mapped_type:
                logger.info(
                    "download_zoom_recording: skipping unknown Zoom file_type=%s (meeting=%s)",
                    file_type_raw, meeting_id,
                )
                continue

            file_id = str(f.get('id') or '')
            ext = (f.get('file_extension') or file_type_raw).lower().lstrip('.')
            if not file_id:
                logger.warning(
                    "download_zoom_recording: file with empty id, skipping (meeting=%s type=%s)",
                    meeting_id, file_type_raw,
                )
                continue
            # `file_name` carries the path relative to RECORDING_STORAGE_DIR so
            # the streaming endpoint's fallback (`os.path.join(storage_dir,
            # rec_file.file_name)`) finds non-primary artifacts (audio / chat
            # / transcript). The video file's full path also lives on
            # `recording.storage_path` for the primary lookup.
            file_name = f"zoom/{meeting_id}/{file_id}.{ext}"
            storage_path = f"{storage_dir}/{file_name}"
            download_url = f.get('download_url') or ''
            if not download_url:
                logger.warning(
                    "download_zoom_recording: file %s has no download_url (meeting=%s)",
                    file_id, meeting_id,
                )
                continue

            # Stream into a temp file, then hand to default_storage. Avoids
            # holding the whole MP4 in memory.
            written = 0
            transcript_buffer = bytearray() if mapped_type == 'transcript' else None
            with tempfile.NamedTemporaryFile(delete=True) as tmp:
                for chunk in provider.stream_recording_file(
                    download_url, download_token=download_token,
                ):
                    tmp.write(chunk)
                    written += len(chunk)
                    if transcript_buffer is not None:
                        transcript_buffer.extend(chunk)
                tmp.flush()
                tmp.seek(0)

                # Replace any prior copy at this path so re-runs don't leave
                # `_1`-suffixed duplicates behind.
                if default_storage.exists(storage_path):
                    default_storage.delete(storage_path)
                saved_path = default_storage.save(storage_path, File(tmp))

            # Track timing across the bundle.
            rs = f.get('recording_start')
            re_ = f.get('recording_end')
            if rs:
                earliest_start = rs if earliest_start is None or rs < earliest_start else earliest_start
            if re_:
                latest_end = re_ if latest_end is None or re_ > latest_end else latest_end

            VideoRecordingFile.objects.update_or_create(
                recording=recording,
                file_name=file_name,
                defaults={
                    'file_type': mapped_type,
                    'file_extension': f'.{ext}' if ext else '',
                    'file_size_bytes': written,
                    'storage_url': saved_path,
                },
            )
            total_size += written

            if mapped_type == 'video' and not primary_video_path:
                primary_video_path = saved_path

            if transcript_buffer is not None:
                transcript_payloads.append((file_id, bytes(transcript_buffer)))

    except Exception:
        logger.exception(
            "download_zoom_recording: file ingest failed (meeting=%s)", meeting_id,
        )
        advance_recording(recording.id, to_status=VideoRecording.Status.ERROR)
        return

    # Compute duration from the recording_start/recording_end timestamps Zoom
    # supplies on the manifest (ISO 8601 strings). Fall back to 0 if unparseable.
    duration_seconds = 0
    try:
        from datetime import datetime
        if earliest_start and latest_end:
            s = datetime.fromisoformat(earliest_start.replace('Z', '+00:00'))
            e = datetime.fromisoformat(latest_end.replace('Z', '+00:00'))
            duration_seconds = max(0, int((e - s).total_seconds()))
    except Exception:
        duration_seconds = 0

    # Inherit auto_publish from parent (mirrors LiveKit branch).
    auto_publish = False
    if isinstance(parent, Event):
        settings_dict = parent.video_settings if isinstance(parent.video_settings, dict) else {}
        auto_publish = bool(settings_dict.get('auto_publish_recording', False))
    elif isinstance(parent, CourseSession):
        auto_publish = bool(getattr(parent, 'recording_auto_publish', False))

    extra: dict = {
        'recording_end': timezone.now(),
        'storage_path': primary_video_path or recording.storage_path,
        'total_size_bytes': total_size,
        'duration_seconds': duration_seconds or recording.duration_seconds,
        'auto_publish': auto_publish,
    }
    advanced = advance_recording(
        recording.id,
        to_status=VideoRecording.Status.AVAILABLE,
        extra_fields=extra,
    )

    if advanced:
        recording.refresh_from_db()

    # Rewrite file storage_url to the streaming endpoint so the frontend uses
    # the same shape as LiveKit recordings (same playback/download path).
    for vf in recording.files.all():
        target = f'/api/v1/video/recordings/{recording.uuid}/files/{vf.uuid}/stream/'
        if vf.storage_url != target:
            vf.storage_url = target
            vf.save(update_fields=['storage_url', 'updated_at'])

    # Parse any VTT transcripts now that file rows + recording exist.
    if transcript_payloads:
        transcript = _ensure_zoom_transcript(video_room)
        for file_id, vtt_bytes in transcript_payloads:
            try:
                _parse_zoom_vtt_into_transcript(transcript, vtt_bytes, file_id)
            except Exception:
                logger.exception(
                    "download_zoom_recording: VTT parse failed (meeting=%s file=%s)",
                    meeting_id, file_id,
                )

    if advanced and recording.auto_publish and recording.status == VideoRecording.Status.AVAILABLE:
        recording.publish()

    # Storage hygiene: trash the Zoom Cloud copy now that we own the bytes.
    if getattr(settings, 'ZOOM_PURGE_AFTER_DOWNLOAD', False):
        try:
            ok = provider.delete_recording(meeting_id)
            if not ok:
                logger.warning(
                    "download_zoom_recording: Zoom purge returned non-success (meeting=%s)",
                    meeting_id,
                )
        except Exception:
            logger.warning(
                "download_zoom_recording: Zoom purge raised; ignoring (meeting=%s)",
                meeting_id, exc_info=True,
            )

    logger.info(
        "download_zoom_recording done: meeting=%s files=%d bytes=%d advanced=%s",
        meeting_id, len(files), total_size, advanced,
    )


def _ensure_zoom_transcript(video_room):
    """Return the Transcript for ``video_room``, creating one if missing.

    The streaming pipeline normally provisions the Transcript at
    room-started time. Zoom rooms whose ``transcription_enabled`` was
    off (or whose provision step was skipped) won't have one — we
    create a minimal row here so VTT cues have somewhere to live.
    """
    from conferencing.models import Transcript

    transcript, _ = Transcript.objects.get_or_create(
        video_room=video_room,
        defaults={
            'provider': 'zoom',
            'language_code': 'en-US',
            'started_at': timezone.now(),
        },
    )
    return transcript


def _parse_zoom_vtt_into_transcript(transcript, vtt_bytes: bytes, file_id: str):
    """Parse a Zoom VTT payload into TranscriptSegment rows.

    VTT format: ``WEBVTT`` header, blank line, then cues:

        [optional cue id]
        HH:MM:SS.mmm --> HH:MM:SS.mmm [optional settings]
        cue body line 1
        cue body line 2
        <blank line>

    Bulk-creates with ``ignore_conflicts=True`` so re-running the task is
    idempotent against the partial unique constraint
    ``(transcript, provider_segment_id, source='live')``.
    """
    from conferencing.models import Transcript, TranscriptSegment

    text = vtt_bytes.decode('utf-8-sig', errors='replace').replace('\r\n', '\n').replace('\r', '\n')

    # Strip the WEBVTT header block (everything up to the first blank line).
    if text.lstrip().startswith('WEBVTT'):
        idx = text.find('\n\n')
        if idx == -1:
            return  # Header only, no cues.
        text = text[idx + 2:]

    cues = [c for c in text.split('\n\n') if c.strip()]

    rows: list[TranscriptSegment] = []
    cue_index = 0

    for cue in cues:
        lines = [ln for ln in cue.split('\n') if ln.strip()]
        if not lines:
            continue

        # Skip NOTE/STYLE/REGION blocks.
        if lines[0].startswith(('NOTE', 'STYLE', 'REGION')):
            continue

        # First line might be a cue identifier (no `-->`); skip past it if so.
        timing_line = None
        body_start = 0
        for i, ln in enumerate(lines):
            if '-->' in ln:
                timing_line = ln
                body_start = i + 1
                break
        if timing_line is None:
            continue

        # Trim cue settings ("00:01:25.789 align:start position:50%") off the
        # end of the second timestamp.
        try:
            left, _, right = timing_line.partition('-->')
            start_str = left.strip()
            end_str = right.strip().split()[0]
            start_ms = _vtt_timestamp_to_ms(start_str)
            end_ms = _vtt_timestamp_to_ms(end_str)
        except Exception:
            continue

        body = '\n'.join(lines[body_start:]).strip()
        if not body:
            continue

        rows.append(TranscriptSegment(
            transcript=transcript,
            start_ms=start_ms,
            end_ms=end_ms,
            text=body,
            is_final=True,
            source=TranscriptSegment.Source.LIVE,
            provider_segment_id=f"{file_id}:{cue_index:05d}",
        ))
        cue_index += 1

    if rows:
        TranscriptSegment.objects.bulk_create(rows, ignore_conflicts=True)

    # Recompute word_count from the DB so we count the real (post-conflict)
    # segment set, not the rows we just tried to insert.
    current = transcript.segments.filter(replaced_by__isnull=True).only('text')
    word_count = sum(len(s.text.split()) for s in current)
    transcript.status = Transcript.Status.FINALIZED
    transcript.finalized_at = timezone.now()
    transcript.word_count = word_count
    transcript.save(update_fields=['status', 'finalized_at', 'word_count', 'updated_at'])


def _vtt_timestamp_to_ms(stamp: str) -> int:
    """Convert ``HH:MM:SS.mmm`` or ``MM:SS.mmm`` to integer milliseconds."""
    parts = stamp.split(':')
    if len(parts) == 3:
        h, m, rest = parts
    elif len(parts) == 2:
        h, m, rest = '0', parts[0], parts[1]
    else:
        raise ValueError(f"Unparseable VTT timestamp: {stamp!r}")
    if '.' in rest:
        s, ms = rest.split('.', 1)
    else:
        s, ms = rest, '0'
    # Pad/truncate ms to 3 digits.
    ms = (ms + '000')[:3]
    total = int(h) * 3600_000 + int(m) * 60_000 + int(s) * 1000 + int(ms)
    return total


@CloudTask
def start_course_session_recording(session_id: int):
    """Start a LiveKit room-composite egress for the given course session."""
    from conferencing.models import VideoRecording, VideoRoom
    from conferencing.service import get_video_provider
    from learning.models import CourseSession

    try:
        session = CourseSession.objects.get(id=session_id)
    except CourseSession.DoesNotExist:
        logger.warning("start_course_session_recording: session %s not found", session_id)
        return

    ct = ContentType.objects.get_for_model(CourseSession)
    video_room = VideoRoom.objects.filter(content_type=ct, object_id=session.id).first()
    if not video_room:
        logger.info("start_course_session_recording: no VideoRoom for session %s", session_id)
        return

    if VideoRecording.objects.filter(
        video_room=video_room,
        status__in=[VideoRecording.Status.RECORDING, VideoRecording.Status.PROCESSING],
    ).exists():
        logger.info("Recording already in flight for session %s", session_id)
        return

    provider = get_video_provider()
    if not provider.is_configured():
        logger.warning("Video provider not configured; skipping recording start")
        return

    try:
        egress_id = provider.start_recording(
            room_name=video_room.room_name,
            output_path=f"recordings/{video_room.room_name}.mp4",
        )
    except Exception:
        logger.exception("Failed to start recording for session %s", session_id)
        return

    VideoRecording.objects.create(
        video_room=video_room,
        course_session=session,
        egress_id=egress_id,
        provider='livekit',
        status=VideoRecording.Status.RECORDING,
        recording_start=timezone.now(),
        access_level=VideoRecording.AccessLevel.REGISTRANTS,
        auto_publish=session.recording_auto_publish,
    )
    logger.info("Recording started for course session %s (egress=%s)", session_id, egress_id)


@CloudTask
def stop_course_session_recording(session_id: int):
    """Stop the in-flight egress for the given course session, if any."""
    from conferencing.models import VideoRecording
    from conferencing.service import get_video_provider

    recording = (
        VideoRecording.objects.filter(
            course_session_id=session_id,
            status=VideoRecording.Status.RECORDING,
        )
        .order_by('-created_at')
        .first()
    )
    if not recording:
        logger.info("stop_course_session_recording: no in-flight recording for session %s", session_id)
        return

    provider = get_video_provider()
    if not provider.is_configured():
        logger.warning("Video provider not configured; cannot stop recording")
        return

    from conferencing.state_machine import advance_recording

    try:
        provider.stop_recording(recording.egress_id)
    except Exception:
        logger.exception("Failed to stop recording for session %s", session_id)
        advance_recording(recording.id, to_status=VideoRecording.Status.ERROR)
        return

    advance_recording(recording.id, to_status=VideoRecording.Status.PROCESSING)


# =========================================================================
# Transcripts — provisioning + finalisation hooks
# =========================================================================
#
# Wired into _on_room_started / _on_room_finished above. The two functions
# below are deliberately defensive: any failure (provider misconfigured,
# agent dispatch fails, LiveKit unreachable) logs a warning and returns
# silently. Transcription is non-critical — the meeting itself must
# proceed even when captions can't.


def _content_object_video_settings(video_room) -> dict:
    """Pull `video_settings` JSON off the linked Event/CourseSession."""
    obj = video_room.content_object
    if obj is None:
        return {}
    return getattr(obj, 'video_settings', None) or {}


def provision_transcript_if_enabled(video_room):
    """Create a Transcript row + dispatch the agent into the room.

    Runs at room_started time. Three guard conditions, in order:

      1. The event/session must opt-in via `video_settings.transcription_enabled`.
      2. The configured `TranscriptionProvider` must be `is_configured()`.
         A null provider (or a real provider missing its API key) → skip
         gracefully without creating a Transcript row that would never
         get segments.
      3. The agent dispatch must succeed. If it fails, the Transcript row
         IS still created (so the post-event panel can show "transcript
         provisioning failed" rather than "no transcript") but flipped
         to ERROR so the UI doesn't show streaming forever.
    """
    settings = _content_object_video_settings(video_room)
    if not settings.get('transcription_enabled', False):
        return

    from conferencing.models import Transcript
    from conferencing.transcription import get_transcription_provider

    provider = get_transcription_provider()
    if not provider.is_configured():
        logger.info(
            "transcription_enabled=True for room %s but provider %r is not "
            "configured (missing API key?); skipping provision",
            video_room.room_name, provider.name,
        )
        return

    # The Transcript row is the idempotency key. First call creates +
    # dispatches; subsequent calls (room_started arriving after the
    # participant_joined backstop, or duplicate webhook delivery) find
    # the existing row and return without re-dispatching. We never
    # want the agent dispatched twice for the same room — even though
    # LiveKit's CreateAgentDispatch is internally idempotent, an extra
    # network round-trip on every webhook is wasted work and noisy
    # logs.
    #
    # Zoom-model: each meeting session has its own VideoRoom row, so
    # the OneToOneField from Transcript → VideoRoom is exactly right;
    # the "stale transcript blocks new dispatch" race that haunted the
    # old reopen flow can no longer happen.
    transcript, created = Transcript.objects.get_or_create(
        video_room=video_room,
        defaults={
            'provider': provider.name,
            'provider_model': provider.model,
            'language_code': settings.get('transcription_language', 'en-US'),
            'started_at': timezone.now(),
        },
    )
    if not created:
        # Already provisioned for this room — dispatch already ran in
        # the call that created the row. Nothing to do.
        return

    logger.info(
        "Provisioned transcript %s for room %s (provider=%s)",
        transcript.uuid, video_room.room_name, provider.name,
    )

    # Dispatch the agent. Metadata = transcript_uuid so the agent can
    # tag every segment to the right transcript without needing to look
    # it up via room_name → video_room → transcript at every event.
    from conferencing.service import get_video_provider
    vp = get_video_provider()
    try:
        dispatch_id = vp.dispatch_agent(
            room_name=video_room.room_name,
            agent_name='accredit-agent',
            metadata=str(transcript.uuid),
        )
    except Exception:
        logger.exception(
            "agent dispatch raised for room %s",
            video_room.room_name,
        )
        dispatch_id = None

    if dispatch_id is None:
        # Mark the transcript ERROR so the UI shows a useful state
        # ("transcript unavailable") rather than spinning on STREAMING.
        # The agent CAN recover later (see Step 4 follow-up: batch repair)
        # but this is the right state for "no live captions".
        transcript.status = Transcript.Status.ERROR
        transcript.error_message = (
            'Failed to dispatch transcription agent into the room. '
            'Live captions will not be available; a post-event batch '
            'transcription pass may still produce a transcript.'
        )
        transcript.save(update_fields=['status', 'error_message', 'updated_at'])


def finalize_transcript(video_room):
    """Tell the transcript its source room is done.

    Mirrors the agent's own finalize call (the agent posts to the same
    endpoint when it leaves the room). Whichever fires first wins; the
    second is a no-op because the endpoint is idempotent.

    Why fire from the webhook AT ALL when the agent already does it:
      - The agent might crash before its shutdown hook runs (OOM, OS
        signal). Calling from the webhook handler is our backstop — we
        always observe room_finished, even when the agent doesn't.
    """
    from conferencing.models import Transcript

    try:
        transcript = video_room.transcript
    except Transcript.DoesNotExist:
        return

    if transcript.status == Transcript.Status.STREAMING:
        # Recompute word_count from the current (un-replaced) segments.
        # The DB query is cheap because the segments are already indexed
        # on (transcript, replaced_by) implicitly via FK + the partial
        # constraint, and a finalising room has at most a few thousand
        # segments at the upper bound.
        current = transcript.segments.filter(replaced_by__isnull=True)
        transcript.status = Transcript.Status.FINALIZED
        transcript.finalized_at = timezone.now()
        transcript.word_count = sum(
            len(s.text.split()) for s in current.only('text')
        )
        transcript.save(update_fields=[
            'status', 'finalized_at', 'word_count', 'updated_at',
        ])
        logger.info(
            "Finalized transcript %s for room %s (%d segments, %d words)",
            transcript.uuid, video_room.room_name,
            current.count(), transcript.word_count,
        )
