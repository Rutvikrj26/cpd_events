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


@CloudTask
def create_video_room_for_object(content_type_id: int, object_id: int):
    """
    Create a LiveKit room for an Event, Course, or CourseSession.

    Called from signals (via ``.delay()``) when video is enabled on a content
    object. Idempotent: existing ACTIVE/SCHEDULED rooms short-circuit; an
    existing ERROR row is upgraded on retry. On provider failure the row is
    written/updated to ERROR and the exception is re-raised so the Cloud
    Tasks queue's retry policy applies in production.
    """
    from conferencing.models import VideoRoom
    from conferencing.service import get_video_provider

    ct = ContentType.objects.get(id=content_type_id)
    obj = ct.get_object_for_this_type(id=object_id)

    existing = VideoRoom.objects.filter(content_type=ct, object_id=object_id).first()
    if existing and existing.status != VideoRoom.Status.ERROR:
        logger.info("VideoRoom already exists for %s:%s (status=%s)", ct.model, object_id, existing.status)
        return

    # Generate a unique room name
    room_name = f"{ct.model}-{obj.uuid}"

    provider = get_video_provider()
    if not provider.is_configured():
        logger.warning("Video provider not configured, skipping room creation")
        return

    try:
        result = provider.create_room(
            name=room_name,
            metadata={"content_type": ct.model, "object_id": object_id},
        )
    except Exception as e:
        logger.exception("Failed to create video room for %s:%s", ct.model, object_id)
        defaults = {
            'room_id': '',
            'room_name': room_name,
            'provider': 'livekit',
            'status': VideoRoom.Status.ERROR,
            'error': str(e)[:2000],
            'error_at': timezone.now(),
        }
        VideoRoom.objects.update_or_create(
            content_type=ct, object_id=object_id, defaults=defaults
        )
        raise

    if existing:
        existing.room_id = result.room_id
        existing.room_name = result.room_name
        existing.status = VideoRoom.Status.SCHEDULED
        existing.error = ''
        existing.error_at = None
        existing.save(update_fields=['room_id', 'room_name', 'status', 'error', 'error_at', 'updated_at'])
    else:
        VideoRoom.objects.create(
            content_type=ct,
            object_id=object_id,
            room_id=result.room_id,
            room_name=result.room_name,
            provider='livekit',
        )
    logger.info("Created VideoRoom %s for %s:%s", room_name, ct.model, object_id)


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
    """
    Apply room_started: transition VideoRoom → ACTIVE, mark linked content
    live, and trigger auto-recording if the parent opted in.
    """
    from conferencing.state_machine import advance_room
    from conferencing.models import VideoRoom

    advanced = advance_room(
        video_room.id,
        to_status=VideoRoom.Status.ACTIVE,
        extra_fields={
            'started_at': timezone.now(),
            'error': '',
        },
    )
    if advanced:
        # Reload after the SQL UPDATE so downstream helpers see fresh state.
        video_room.refresh_from_db()

    _mark_content_live(video_room)
    _maybe_auto_start_recording(video_room)


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
    """Mark the linked content object as completed."""
    obj = video_room.content_object
    if obj is None:
        return

    model_name = video_room.content_type.model
    if model_name == 'event':
        if hasattr(obj, 'status') and obj.status == 'live':
            obj.status = 'completed'
            obj.save(update_fields=['status', 'updated_at'])
            logger.info("Event %s marked as completed", obj.uuid)


def _handle_participant_joined(video_room, payload):
    """Create attendance record when a participant joins."""
    import uuid as _uuid

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
    """Update attendance record when a participant leaves."""
    participant = payload.get('participant', {})
    identity = participant.get('identity', '')

    if not identity:
        return 0

    model_name = video_room.content_type.model

    if model_name == 'event':
        _update_event_attendance(video_room, identity)
    elif model_name == 'coursesession':
        _update_session_attendance(video_room, identity)

    return 0


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


def _maybe_auto_start_recording(video_room):
    """
    If the parent event/session has recording_enabled=True, kick off egress.
    Idempotent via ensure_recording_started.
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

    # Inherit auto_publish from parent event/session — overrides the row's
    # default which may have been left False at create time.
    parent = video_room.content_object
    auto_publish = False
    if parent is not None:
        from events.models import Event
        from learning.models import CourseSession

        if isinstance(parent, Event):
            settings_dict = parent.video_settings if isinstance(parent.video_settings, dict) else {}
            auto_publish = bool(settings_dict.get('auto_publish_recording', True))
        elif isinstance(parent, CourseSession):
            auto_publish = bool(getattr(parent, 'recording_auto_publish', True))

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
