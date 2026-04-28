"""
Async tasks for video conferencing.

These tasks handle webhook processing, room creation, and attendance tracking.
"""

import logging
import traceback

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
    """
    import uuid as _uuid

    # Backstop must run BEFORE attendance recording so a missed
    # room_started doesn't leave the room in 'scheduled' status — some
    # downstream attendance logic checks the room state.
    _ensure_room_active(video_room)

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
    """
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
    """
    import os

    from conferencing.models import VideoRecording, VideoRecordingFile
    from conferencing.state_machine import advance_recording

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
