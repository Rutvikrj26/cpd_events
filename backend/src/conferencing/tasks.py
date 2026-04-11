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

    try:
        provider.stop_recording(recording.egress_id)
    except Exception:
        logger.exception("Failed to stop recording for event %s", event_id)
        recording.status = VideoRecording.Status.ERROR
        recording.save(update_fields=['status', 'updated_at'])
        return

    recording.status = VideoRecording.Status.PROCESSING
    recording.save(update_fields=['status', 'updated_at'])


def create_video_room_for_object(content_type_id: int, object_id: int):
    """
    Create a LiveKit room for an Event, Course, or CourseSession.

    Called from signals when video is enabled on a content object.
    """
    from conferencing.models import VideoRoom
    from conferencing.service import get_video_provider

    ct = ContentType.objects.get(id=content_type_id)
    obj = ct.get_object_for_this_type(id=object_id)

    # Don't create duplicate rooms
    if VideoRoom.objects.filter(content_type=ct, object_id=object_id).exists():
        logger.info("VideoRoom already exists for %s:%s", ct.model, object_id)
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
        VideoRoom.objects.create(
            content_type=ct,
            object_id=object_id,
            room_id=result.room_id,
            room_name=result.room_name,
            provider='livekit',
        )
        logger.info("Created VideoRoom %s for %s:%s", room_name, ct.model, object_id)
    except Exception as e:
        logger.exception("Failed to create video room for %s:%s", ct.model, object_id)
        # Create a room record in error state so it can be retried
        VideoRoom.objects.create(
            content_type=ct,
            object_id=object_id,
            room_id='',
            room_name=room_name,
            provider='livekit',
            status=VideoRoom.Status.ERROR,
            error=str(e)[:2000],
            error_at=timezone.now(),
        )


def process_video_webhook(webhook_log_id: int):
    """
    Process a video webhook event.

    Handles: room_started, room_finished, participant_joined,
    participant_left, recording_ended.
    """
    from conferencing.models import VideoRecording, VideoRoom, VideoWebhookLog

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
        event_type = log.event_type
        payload = log.payload
        records_created = 0

        if event_type == 'room_started':
            video_room.mark_active()

            # Mark the linked event/course as live if applicable
            _mark_content_live(video_room)

        elif event_type == 'room_finished':
            video_room.mark_ended()

            # Mark the linked event/course as completed if applicable
            _mark_content_ended(video_room)

        elif event_type == 'participant_joined':
            records_created = _handle_participant_joined(video_room, payload)

        elif event_type == 'participant_left':
            records_created = _handle_participant_left(video_room, payload)

        elif event_type == 'recording_ended':
            _handle_recording_ended(video_room, payload)

        log.mark_completed(records_created=records_created)

    except Exception as e:
        logger.exception("Error processing video webhook %s", webhook_log_id)
        log.mark_failed(str(e), traceback.format_exc())


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
    participant = payload.get('participant', {})
    identity = participant.get('identity', '')
    name = participant.get('name', '')

    if not identity:
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

    # Create attendance record
    # Field names are zoom_* for now — will be renamed in migration
    AttendanceRecord.objects.create(
        registration=registration,
        zoom_participant_id=participant_identity,
        zoom_user_email=registration.user.email if registration.user else '',
        zoom_user_name=participant_name,
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
        zoom_participant_id=participant_identity,
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
            'zoom_participant_id': participant_identity,
            'zoom_user_email': enrollment.user.email if enrollment.user else '',
            'zoom_join_time': timezone.now(),
            'attendance_minutes': 0,
        },
    )
    if not created:
        # Re-joining: update join time for a new segment
        attendance.zoom_join_time = timezone.now()
        attendance.save(update_fields=['zoom_join_time', 'updated_at'])

    return 1 if created else 0


def _update_session_attendance(video_room, participant_identity):
    """Update course session attendance with accumulated minutes."""
    from learning.models import CourseSessionAttendance

    session = video_room.content_object
    if not session:
        return

    attendance = CourseSessionAttendance.objects.filter(
        session=session,
        zoom_participant_id=participant_identity,
    ).first()

    if attendance and attendance.zoom_join_time:
        now = timezone.now()
        segment_minutes = int((now - attendance.zoom_join_time).total_seconds() / 60)
        attendance.attendance_minutes = (attendance.attendance_minutes or 0) + segment_minutes
        attendance.zoom_leave_time = now

        # Calculate eligibility
        if session.duration_minutes and session.duration_minutes > 0:
            attendance.attendance_percent = (attendance.attendance_minutes / session.duration_minutes) * 100
            min_pct = getattr(session, 'minimum_attendance_percent', 80) or 80
            attendance.is_eligible = attendance.attendance_percent >= min_pct

        attendance.save(update_fields=[
            'attendance_minutes', 'zoom_leave_time', 'attendance_percent',
            'is_eligible', 'updated_at',
        ])


def _handle_recording_ended(video_room, payload):
    """Handle recording completion — update the VideoRecording record."""
    from conferencing.models import VideoRecording

    egress_info = payload.get('egressInfo', {})
    egress_id = egress_info.get('egressId', '')

    if not egress_id:
        return

    try:
        recording = VideoRecording.objects.get(egress_id=egress_id)
    except VideoRecording.DoesNotExist:
        # Create a new recording record if it wasn't pre-created
        recording = VideoRecording.objects.create(
            video_room=video_room,
            egress_id=egress_id,
            provider='livekit',
        )

    recording.status = VideoRecording.Status.AVAILABLE
    recording.recording_end = timezone.now()

    # Extract file info from egress results
    file_results = egress_info.get('fileResults', [])
    if file_results:
        result = file_results[0]
        recording.storage_path = result.get('filename', '')
        recording.total_size_bytes = result.get('size', 0)
        recording.duration_seconds = result.get('duration', 0) // 1_000_000_000  # nanoseconds to seconds

    recording.save(update_fields=[
        'status', 'recording_end', 'storage_path',
        'total_size_bytes', 'duration_seconds', 'updated_at',
    ])

    if recording.auto_publish:
        recording.publish()

    logger.info("Recording completed for room %s, egress_id=%s", video_room.room_name, egress_id)
