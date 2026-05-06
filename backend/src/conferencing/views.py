"""
Video conferencing API views.

Provides endpoints for:
- Video status check
- Joining video rooms (token generation)
- Video room management
- Recording access
- Webhook receiver
"""

import json
import logging
import traceback
import uuid as uuid_lib

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from conferencing.models import (
    Transcript,
    TranscriptSegment,
    VideoRecording,
    VideoRoom,
    VideoWebhookLog,
)
from conferencing.serializers import (
    JoinVideoResponseSerializer,
    TranscriptSegmentEditSerializer,
    TranscriptSegmentHistorySerializer,
    TranscriptSegmentIngestSerializer,
    TranscriptSegmentReadSerializer,
    TranscriptSerializer,
    VideoRecordingSerializer,
    VideoRoomSerializer,
    VideoStatusSerializer,
)
from common.rbac import roles
from conferencing.permissions import IsInternalAgent
from conferencing.service import get_video_provider

logger = logging.getLogger(__name__)


def _serve_video_with_range(request, path, *, file_name, content_type):
    """
    Serve a local file with HTTP Range support so the browser can seek.

    Without this, `<video>.seekable` returns `[[0, 0]]` and any attempt to
    set `currentTime` silently fails — the browser refuses to seek when
    the response lacks `Accept-Ranges: bytes`. The default Django
    `FileResponse` does not parse Range headers; we hand-roll a 206
    Partial Content response when the client sends one and otherwise
    return the whole file with `Accept-Ranges: bytes` advertised so the
    next request can range-request.

    Why a streaming generator (not `read()`): recordings can be hundreds
    of MB. Reading the slice into memory blocks the worker and explodes
    RSS. The 8KB chunk loop keeps memory bounded regardless of file or
    range size.
    """
    import os
    import re

    from django.http import FileResponse, StreamingHttpResponse

    file_size = os.path.getsize(path)
    range_header = request.META.get('HTTP_RANGE', '').strip()

    # Common headers — set on every response so the client knows seeking
    # is supported even on the initial full-file fetch.
    common_headers = {
        'Accept-Ranges': 'bytes',
        'Content-Disposition': f'inline; filename="{file_name}"',
        'Cache-Control': 'private, max-age=300',
    }

    if not range_header:
        response = FileResponse(open(path, 'rb'), content_type=content_type)
        for k, v in common_headers.items():
            response[k] = v
        response['Content-Length'] = str(file_size)
        return response

    # Parse `bytes=START-END` (END optional). Multiple ranges are valid
    # per RFC 7233 but rare in practice; we only handle the single-range
    # case. Malformed headers fall through to a 416.
    match = re.fullmatch(r'bytes=(\d*)-(\d*)', range_header)
    if not match:
        response = FileResponse(open(path, 'rb'), content_type=content_type)
        for k, v in common_headers.items():
            response[k] = v
        response['Content-Length'] = str(file_size)
        return response

    start_str, end_str = match.group(1), match.group(2)
    if start_str == '' and end_str == '':
        # `bytes=-` is invalid.
        response = StreamingHttpResponse(status=416)
        response['Content-Range'] = f'bytes */{file_size}'
        return response

    if start_str == '':
        # Suffix range: `bytes=-N` means the final N bytes.
        suffix = int(end_str)
        if suffix == 0:
            response = StreamingHttpResponse(status=416)
            response['Content-Range'] = f'bytes */{file_size}'
            return response
        start = max(0, file_size - suffix)
        end = file_size - 1
    else:
        start = int(start_str)
        end = int(end_str) if end_str else file_size - 1

    # Validate.
    if start >= file_size or end >= file_size or start > end:
        response = StreamingHttpResponse(status=416)
        response['Content-Range'] = f'bytes */{file_size}'
        return response

    length = end - start + 1
    chunk_size = 8 * 1024  # 8 KiB

    def stream():
        with open(path, 'rb') as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(chunk_size, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    response = StreamingHttpResponse(stream(), status=206, content_type=content_type)
    response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
    response['Content-Length'] = str(length)
    for k, v in common_headers.items():
        response[k] = v
    return response


def is_platform_admin(user) -> bool:
    """True if the user belongs to the platform-wide 'admin' group."""
    return bool(user and user.is_authenticated and user.groups.filter(name='admin').exists())


def is_event_host(user, event) -> bool:
    """
    Host of an event = the owner, a User linked to any Speaker on the event,
    or a platform admin (support override).
    """
    if not user or not user.is_authenticated:
        return False
    if event.owner_id == user.id:
        return True
    if is_platform_admin(user):
        return True
    # Speaker.owner is a User FK; Event.speakers is M2M to Speaker.
    return event.speakers.filter(owner_id=user.id).exists()


def ensure_recording_started(video_room) -> tuple['VideoRecording', bool]:
    """
    Idempotently ensure an active VideoRecording exists for the given room.

    Returns (recording, created). If a recording is already RECORDING or
    PROCESSING, returns it untouched (created=False). Otherwise starts a new
    LiveKit egress, creates a VideoRecording row, and returns (row, True).

    Raises on egress-provider failure; callers translate to 5xx.
    """
    existing = VideoRecording.objects.filter(
        video_room=video_room,
        status__in=[VideoRecording.Status.RECORDING, VideoRecording.Status.PROCESSING],
    ).first()
    if existing:
        return existing, False

    provider = get_video_provider()
    output_path = provider.recording_output_template() or '/out/{room_name}-{time}.mp4'
    egress_id = provider.start_recording(video_room.room_name, output_path=output_path)

    # Link the recording to the parent event/course_session so listing
    # endpoints (which filter by event__uuid / course_session__uuid) can
    # surface it. Without this the row is orphaned and never reaches the UI.
    create_kwargs = {
        'video_room': video_room,
        'egress_id': egress_id,
        'recording_start': timezone.now(),
        'status': VideoRecording.Status.RECORDING,
    }
    parent = video_room.content_object
    if parent is not None:
        from events.models import Event
        from learning.models import CourseSession

        if isinstance(parent, Event):
            create_kwargs['event'] = parent
        elif isinstance(parent, CourseSession):
            create_kwargs['course_session'] = parent

    recording = VideoRecording.objects.create(**create_kwargs)
    return recording, True


def is_course_session_host(user, course) -> bool:
    """
    Host of a course session = the course creator, an active CourseStaff
    member of the course, or a platform admin.
    """
    if not user or not user.is_authenticated:
        return False
    if course.created_by_id == user.id:
        return True
    if is_platform_admin(user):
        return True
    return course.staff_assignments.filter(user_id=user.id).exists()


@roles('learner', 'organizer', 'instructor', 'admin', route_name='video_status')
class VideoStatusView(generics.GenericAPIView):
    """GET /api/v1/video/status/ — Check if video conferencing is configured."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        provider = get_video_provider()
        data = {
            'configured': provider.is_configured(),
            'provider': getattr(settings, 'VIDEO_PROVIDER', 'livekit'),
        }
        return Response(VideoStatusSerializer(data).data)


# NOTE: The legacy `JoinVideoView` / `JoinVideoGuestView` /
# `JoinCourseSessionVideoView` were deleted as part of the Zoom-model
# redesign. Their replacements live in `conferencing/meetings.py`:
#
#   POST /events/{uuid}/meetings/start/   — host creates a fresh room
#   POST /events/{uuid}/meetings/join/    — attendee/host joins the active room
#   GET  /events/{uuid}/meetings/active/  — lobby polling
#   POST /video/rooms/{uuid}/end/         — host ends meeting for everyone
#
# (Same endpoints mirrored under `/courses/{course_uuid}/sessions/...`
# and `/public/events/...` for course sessions and unauthenticated guests.)



@roles('organizer', 'admin', route_name='video_rooms')
class VideoRoomViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v1/video/rooms/ — List video rooms for the authenticated user's
    events and course sessions.
    """

    serializer_class = VideoRoomSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'

    def get_queryset(self):
        from django.contrib.contenttypes.models import ContentType
        from django.db.models import Q
        from events.models import Event
        from learning.models import Course, CourseSession

        event_ct = ContentType.objects.get_for_model(Event)
        session_ct = ContentType.objects.get_for_model(CourseSession)

        if self.request.user.groups.filter(name="admin").exists():
            qs = VideoRoom.objects.filter(content_type__in=[event_ct, session_ct])
        else:
            user_event_ids = Event.objects.filter(
                owner=self.request.user, deleted_at__isnull=True
            ).values_list('id', flat=True)

            staff_course_ids = Course.objects.filter(
                Q(created_by=self.request.user)
                | Q(staff_assignments__user=self.request.user)
            ).values_list('id', flat=True).distinct()
            user_session_ids = CourseSession.objects.filter(
                course_id__in=staff_course_ids,
            ).values_list('id', flat=True)

            qs = VideoRoom.objects.filter(
                Q(content_type=event_ct, object_id__in=user_event_ids)
                | Q(content_type=session_ct, object_id__in=user_session_ids)
            )

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        # When the caller asks for "active" rooms, exclude rooms whose underlying
        # Event or CourseSession has already ended chronologically. The
        # LiveKit-side `status` field can lag (or stay ACTIVE indefinitely if
        # egress crashes), so we cross-check against the schedule.
        # Filtered in Python: SQLite cannot multiply int * timedelta in SQL,
        # and the active-room set is small (typically < 100 rows).
        if status_param == VideoRoom.Status.ACTIVE:
            ended_event_ids = [
                e.id for e in Event.objects.filter(deleted_at__isnull=True)
                                            .only('id', 'starts_at', 'duration_minutes')
                if e.is_past
            ]
            ended_session_ids = [
                s.id for s in CourseSession.objects
                                            .only('id', 'starts_at', 'duration_minutes')
                if s.is_past
            ]
            if ended_event_ids:
                qs = qs.exclude(content_type=event_ct, object_id__in=ended_event_ids)
            if ended_session_ids:
                qs = qs.exclude(content_type=session_ct, object_id__in=ended_session_ids)

        return qs.order_by('-started_at', '-created_at')

    @action(detail=True, methods=['post'])
    def start_recording(self, request, pk=None, uuid=None):
        room = self.get_object()
        if room.status != VideoRoom.Status.ACTIVE:
            return Response({'error': 'Room is not active'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            recording, created = ensure_recording_started(room)
        except Exception as e:
            logger.exception("Failed to start recording for room %s", room.room_name)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'egress_id': recording.egress_id,
            'status': recording.status,
            'created': created,
        })

    @action(detail=True, methods=['post'])
    def stop_recording(self, request, pk=None, uuid=None):
        room = self.get_object()
        active_recording = VideoRecording.objects.filter(
            video_room=room, status=VideoRecording.Status.RECORDING
        ).first()

        if not active_recording:
            return Response({'error': 'No active recording'}, status=status.HTTP_400_BAD_REQUEST)

        provider = get_video_provider()
        if provider.stop_recording(active_recording.egress_id):
            active_recording.status = VideoRecording.Status.PROCESSING
            active_recording.recording_end = timezone.now()
            active_recording.save(update_fields=['status', 'recording_end', 'updated_at'])
            return Response({'status': 'stopping'})

        return Response({'error': 'Failed to stop recording'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def admit_participant(self, request, pk=None, uuid=None):
        """Grant publish + subscribe permissions to a waiting participant.

        Body: {"identity": "<participant-identity>"}
        """
        room = self.get_object()
        identity = (request.data or {}).get('identity') if isinstance(request.data, dict) else None
        if not identity:
            return Response({'error': 'identity is required'}, status=status.HTTP_400_BAD_REQUEST)

        provider = get_video_provider()
        ok = provider.update_participant(
            room.room_name, identity, can_publish=True, can_subscribe=True
        )
        if ok:
            return Response({'status': 'admitted', 'identity': identity})
        return Response(
            {'error': 'Failed to admit participant'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    @action(detail=True, methods=['post'])
    def deny_participant(self, request, pk=None, uuid=None):
        """Revoke publish + subscribe permissions from a participant.

        Body: {"identity": "<participant-identity>"}
        """
        room = self.get_object()
        identity = (request.data or {}).get('identity') if isinstance(request.data, dict) else None
        if not identity:
            return Response({'error': 'identity is required'}, status=status.HTTP_400_BAD_REQUEST)

        provider = get_video_provider()
        ok = provider.update_participant(
            room.room_name, identity, can_publish=False, can_subscribe=False
        )
        if ok:
            return Response({'status': 'denied', 'identity': identity})
        return Response(
            {'error': 'Failed to update participant'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@roles('learner', 'instructor', 'organizer', 'admin', route_name='video_recordings')
class VideoRecordingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v1/video/recordings/ — List published recordings accessible to the user.

    Scope:
    - Admins see all published+available recordings.
    - Event owners see recordings for their own events.
    - Course staff see recordings for sessions of courses they own/staff.
    - Enrolled learners see recordings for sessions of courses they are
      actively enrolled in.
    """

    serializer_class = VideoRecordingSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'

    def get_queryset(self):
        # Hosts of an event/course can opt into seeing unpublished + non-AVAILABLE
        # rows by passing ?manage=true. Used by the EventManagement recording panel
        # to show RECORDING/PROCESSING/AVAILABLE/ERROR states with a publish toggle.
        manage_mode = self.request.query_params.get('manage') == 'true'

        if manage_mode:
            qs = VideoRecording.objects.all()
        else:
            qs = VideoRecording.objects.filter(
                is_published=True,
                status=VideoRecording.Status.AVAILABLE,
            )

        # Optional ?event_uuid=<uuid> filter for the EventRecordingPage.
        event_uuid = self.request.query_params.get('event_uuid')
        if event_uuid:
            qs = qs.filter(event__uuid=event_uuid)

        # Symmetric ?course_session_uuid= filter for the CourseSessionRecordingPage.
        course_session_uuid = self.request.query_params.get('course_session_uuid')
        if course_session_uuid:
            qs = qs.filter(course_session__uuid=course_session_uuid)

        user = self.request.user
        if user.groups.filter(name="admin").exists():
            return qs

        from django.db.models import Q
        from events.models import Event
        from learning.models import Course, CourseEnrollment, CourseSession
        from registrations.models import Registration

        user_event_ids = Event.objects.filter(
            owner=user, deleted_at__isnull=True
        ).values_list('id', flat=True)
        # Learners who registered for an event get access to its recording.
        registered_event_ids = Registration.objects.filter(
            user=user,
            status__in=[Registration.Status.CONFIRMED],
            deleted_at__isnull=True,
        ).values_list('event_id', flat=True)

        staff_course_ids = Course.objects.filter(
            Q(created_by=user) | Q(staff_assignments__user=user)
        ).values_list('id', flat=True).distinct()
        enrolled_course_ids = CourseEnrollment.objects.filter(
            user=user,
            status__in=[CourseEnrollment.Status.ACTIVE, CourseEnrollment.Status.COMPLETED],
        ).values_list('course_id', flat=True)
        accessible_session_ids = CourseSession.objects.filter(
            course_id__in=list(staff_course_ids) + list(enrolled_course_ids),
        ).values_list('id', flat=True)

        return qs.filter(
            Q(event_id__in=user_event_ids)
            | Q(event_id__in=registered_event_ids)
            | Q(course_session_id__in=accessible_session_ids)
        )

    def _user_can_access_recording(self, recording, user) -> bool:
        """
        Hosts/admins can stream their recordings even before publish; everyone
        else needs is_published=True AND status=AVAILABLE (handled by
        get_queryset's listing filter).
        """
        if user.groups.filter(name='admin').exists():
            return True
        if recording.event_id and is_event_host(user, recording.event):
            return True
        if recording.course_session_id and is_course_session_host(
            user, recording.course_session.course
        ):
            return True
        # Non-hosts: defer to the same gating used by listing.
        return self.get_queryset().filter(pk=recording.pk).exists()

    def _require_host(self, recording):
        """Raise 403 unless the request user is a host of the parent event/session."""
        from rest_framework.exceptions import PermissionDenied

        user = self.request.user
        if user.groups.filter(name='admin').exists():
            return
        if recording.event_id and is_event_host(user, recording.event):
            return
        if recording.course_session_id and is_course_session_host(
            user, recording.course_session.course
        ):
            return
        raise PermissionDenied('Only event/course hosts can publish recordings.')

    @action(detail=True, methods=['post'])
    def publish(self, request, uuid=None):
        """Mark a recording published (visible to attendees/learners)."""
        recording = VideoRecording.objects.filter(uuid=uuid).first()
        if not recording:
            return Response({'error': 'Recording not found'}, status=status.HTTP_404_NOT_FOUND)
        self._require_host(recording)
        if recording.status != VideoRecording.Status.AVAILABLE:
            return Response(
                {'error': f'Cannot publish recording in status={recording.status}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        recording.publish()
        return Response(VideoRecordingSerializer(recording).data)

    @action(detail=True, methods=['post'])
    def unpublish(self, request, uuid=None):
        """Hide a published recording from attendees/learners."""
        recording = VideoRecording.objects.filter(uuid=uuid).first()
        if not recording:
            return Response({'error': 'Recording not found'}, status=status.HTTP_404_NOT_FOUND)
        self._require_host(recording)
        recording.unpublish()
        return Response(VideoRecordingSerializer(recording).data)

    @action(
        detail=True,
        methods=['get'],
        url_path=r'files/(?P<file_uuid>[^/.]+)/stream',
        permission_classes=[permissions.AllowAny],
        authentication_classes=[],
    )
    def stream(self, request, uuid=None, file_uuid=None):
        """
        GET /api/v1/video/recordings/{uuid}/files/{file_uuid}/stream/?t=<token>

        Streams a recording file off the local recordings volume. The volume
        path is configurable via RECORDING_STORAGE_DIR; in cloud-run the same
        path is the mount-point of a GCS-fuse / S3 bucket — no code change.

        Authorization model: this endpoint is hit by the browser's <video>
        element, which can't attach the SPA's JWT Authorization header. We
        require a short-lived `t=` query token instead — generated by the
        recording listing serializer for users who have access. Tokens are
        scoped to the file_uuid and signed with Django's TimestampSigner.
        """
        import os

        from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
        from django.http import FileResponse, Http404

        from conferencing.models import VideoRecordingFile

        # Look up parent recording across the unfiltered table — host preview
        # is allowed via `_user_can_access_recording` even for unpublished rows.
        try:
            recording = VideoRecording.objects.get(uuid=uuid)
        except VideoRecording.DoesNotExist:
            raise Http404('Recording not found')

        # Verify the signed token. Falls back to header-based auth in case
        # the request comes from curl / a server-to-server client.
        token = request.query_params.get('t', '')
        token_ok = False
        if token:
            signer = TimestampSigner(salt='video-recording-stream')
            try:
                signed_file_uuid = signer.unsign(token, max_age=6 * 60 * 60)
                token_ok = signed_file_uuid == str(file_uuid)
            except (BadSignature, SignatureExpired):
                token_ok = False

        if not token_ok:
            # Fallback: an authenticated user with row-level access still works
            # for non-browser clients (admin curl, integration tests).
            from rest_framework.authentication import SessionAuthentication
            try:
                from rest_framework_simplejwt.authentication import JWTAuthentication
            except ImportError:  # pragma: no cover — JWT pkg may differ
                JWTAuthentication = None

            user = None
            if JWTAuthentication:
                try:
                    auth_result = JWTAuthentication().authenticate(request)
                    if auth_result:
                        user = auth_result[0]
                except Exception:
                    user = None
            if user is None:
                try:
                    auth_result = SessionAuthentication().authenticate(request)
                    if auth_result:
                        user = auth_result[0]
                except Exception:
                    user = None

            if not user or not user.is_authenticated:
                return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
            request.user = user
            if not self._user_can_access_recording(recording, user):
                return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        try:
            rec_file = VideoRecordingFile.objects.get(uuid=file_uuid, recording=recording)
        except VideoRecordingFile.DoesNotExist:
            raise Http404('File not found')

        storage_dir = getattr(settings, 'RECORDING_STORAGE_DIR', '/recordings')
        # storage_path on the parent VideoRecording is the absolute (or
        # template-rooted) filename egress wrote. Prefer it when present;
        # otherwise reconstruct from the file row's basename.
        candidate_paths = []
        if recording.storage_path:
            candidate_paths.append(recording.storage_path)
            candidate_paths.append(os.path.join(storage_dir, os.path.basename(recording.storage_path)))
        if rec_file.file_name:
            candidate_paths.append(os.path.join(storage_dir, rec_file.file_name))

        path = next((p for p in candidate_paths if p and os.path.exists(p)), None)
        if path is None:
            logger.warning(
                "stream: file not found on disk for recording %s (tried %s)",
                recording.uuid, candidate_paths,
            )
            raise Http404('Recording file unavailable on disk')

        return _serve_video_with_range(
            request,
            path,
            file_name=rec_file.file_name or os.path.basename(path),
            content_type='video/mp4',
        )


@method_decorator(csrf_exempt, name='dispatch')
class VideoWebhookView(View):
    """
    POST /api/v1/webhooks/video/

    Receives webhook events from the video provider (LiveKit).
    Verifies signature, logs the event, and dispatches async processing.
    """

    http_method_names = ['post']

    def post(self, request):
        body = request.body
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        provider = get_video_provider()

        # Verify signature
        if not provider.verify_webhook(body, auth_header):
            logger.warning("Video webhook signature verification failed")
            return JsonResponse({'error': 'Invalid signature'}, status=401)

        # Parse the event
        try:
            event = provider.parse_webhook(body, auth_header)
        except Exception:
            logger.exception("Failed to parse video webhook")
            return JsonResponse({'error': 'Parse error'}, status=400)

        # Deduplicate by extracting the provider's per-delivery ID from
        # request headers. LiveKit uses ``X-LiveKit-Id``; Zoom emits
        # ``x-zm-trackingid``. Provider-agnostic — falls back to a fresh
        # UUID if the header is absent (no dedup, but processing
        # continues).
        webhook_id = (
            provider.get_webhook_dedup_key(dict(request.headers))
            or str(uuid_lib.uuid4())
        )

        if VideoWebhookLog.objects.filter(webhook_id=webhook_id).exists():
            return JsonResponse({'status': 'duplicate'})

        # Log the webhook
        log = VideoWebhookLog.objects.create(
            webhook_id=webhook_id,
            event_type=event.type,
            event_timestamp=event.timestamp or timezone.now(),
            provider='livekit',
            room_name=event.room_name,
            room_id=event.room_id,
            payload=json.loads(body.decode('utf-8')) if body else {},
            headers={'authorization': auth_header[:50] + '...' if auth_header else ''},
        )

        # Match to VideoRoom. Egress events (recording_started/ended) don't
        # carry the room field, so fall back to looking up via egress_id →
        # VideoRecording.video_room.
        video_room = None
        if event.room_name:
            video_room = VideoRoom.objects.filter(room_name=event.room_name).first()
        if video_room is None:
            egress_id = (event.metadata or {}).get('egress_id')
            if egress_id:
                rec = VideoRecording.objects.filter(egress_id=egress_id).select_related('video_room').first()
                if rec:
                    video_room = rec.video_room
                    log.room_name = video_room.room_name

        if video_room is None:
            log.mark_skipped(
                f"No VideoRoom found for room_name={event.room_name} egress_id={(event.metadata or {}).get('egress_id', '')}"
            )
            return JsonResponse({'status': 'skipped'})

        log.video_room = video_room
        log.save(update_fields=['video_room', 'room_name', 'updated_at'])

        # Dispatch async processing
        from conferencing.tasks import process_video_webhook

        process_video_webhook(log.id)

        return JsonResponse({'status': 'ok'})


# =============================================================================
# Transcripts
# =============================================================================
#
# Endpoint surface:
#
#   Internal (agent-only, HMAC-authenticated):
#     POST /api/v1/internal/transcripts/{uuid}/segments/   ingest one segment
#     POST /api/v1/internal/transcripts/{uuid}/finalize/   transcript end-of-stream
#
#   Public (recording audience, IsAuthenticated + recording-access):
#     GET  /api/v1/video/recordings/{uuid}/transcript/        (full transcript)
#     GET  /api/v1/video/recordings/{uuid}/transcript/search/  (q=foo, GIN-backed)
#     GET  /api/v1/video/recordings/{uuid}/transcript/export/  (?format=vtt|srt|txt)
#
# Edit + history endpoints land in Step 7. Defining the URL contract here
# keeps the read shape stable for the agent + frontend to build against.


def _resolve_recording_for_user(recording_uuid: str, user) -> VideoRecording | None:
    """Returns the recording IFF `user` is allowed to view its transcript.

    Read access mirrors the existing recording-list scope (see
    `VideoRecordingViewSet.get_queryset`):

      - Admins: all recordings.
      - Event owners: recordings for events they own.
      - Confirmed registrants: recordings for events they registered for.
      - Course staff: recordings for sessions of courses they own/staff.
      - Active/completed enrollees: recordings for sessions of those courses.

    Returns None when no row matches — callers map to 404 (not 403) to
    avoid leaking the existence of recordings the user can't see.
    """
    from django.db.models import Q

    from events.models import Event
    from learning.models import Course, CourseEnrollment, CourseSession
    from registrations.models import Registration

    qs = VideoRecording.objects.filter(uuid=recording_uuid)

    if not user or not user.is_authenticated:
        return None
    if user.groups.filter(name='admin').exists():
        return qs.first()

    user_event_ids = Event.objects.filter(
        owner=user, deleted_at__isnull=True,
    ).values_list('id', flat=True)
    registered_event_ids = Registration.objects.filter(
        user=user,
        status=Registration.Status.CONFIRMED,
        deleted_at__isnull=True,
    ).values_list('event_id', flat=True)

    staff_course_ids = Course.objects.filter(
        Q(created_by=user) | Q(staff_assignments__user=user)
    ).values_list('id', flat=True).distinct()
    enrolled_course_ids = CourseEnrollment.objects.filter(
        user=user,
        status__in=[CourseEnrollment.Status.ACTIVE, CourseEnrollment.Status.COMPLETED],
    ).values_list('course_id', flat=True)
    accessible_session_ids = CourseSession.objects.filter(
        course_id__in=list(staff_course_ids) + list(enrolled_course_ids),
    ).values_list('id', flat=True)

    qs = qs.filter(
        Q(event_id__in=user_event_ids)
        | Q(event_id__in=registered_event_ids)
        | Q(course_session_id__in=accessible_session_ids)
    )
    return qs.first()


def _accounts_user_for_identity(identity: str):
    """LiveKit participant_identity is the user's uuid (we set it at JWT
    issuance in conferencing.meetings._build_join_response). Resolve
    it back to a User for the FK.

    Returns None for service participants (egress/ingress bots) whose
    identities aren't UUIDs — those don't get speaker rows."""
    if not identity:
        return None
    try:
        from accounts.models import User
        return User.objects.filter(uuid=identity).first()
    except (ValueError, Exception):
        return None


@method_decorator(csrf_exempt, name='dispatch')
class TranscriptIngestView(generics.GenericAPIView):
    """POST /api/v1/internal/transcripts/{uuid}/segments/ — agent-only.

    Idempotent on `(transcript, provider_segment_id, source='live')`. The
    agent re-publishes a segment with the same `lk.segment_id` until it's
    finalised (LiveKit's normal interim-then-final flow); we update the
    same row in place so the segment count reflects logical segments, not
    revisions.

    Once an organiser edits a live segment (Step 7), the live row's text
    becomes immutable — further re-publishes from the agent are dropped
    by checking `replaced_by` before update. This protects edits from
    being reverted by late-arriving agent traffic.
    """

    permission_classes = [IsInternalAgent]
    serializer_class = TranscriptSegmentIngestSerializer

    def post(self, request, transcript_uuid):
        try:
            transcript = Transcript.objects.get(uuid=transcript_uuid)
        except Transcript.DoesNotExist:
            return Response(
                {'error': 'Transcript not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if transcript.status == Transcript.Status.FINALIZED:
            # Late segments after finalization are dropped silently.
            # The agent might post one or two stragglers as it shuts
            # down; we don't want to 4xx and pollute its retry logic.
            return Response({'status': 'ignored', 'reason': 'finalized'})

        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        # Speaker attribution is an *invariant* of a provider_segment_id —
        # LiveKit guarantees the segment maps to one participant for its
        # whole lifetime, so we capture the speaker on first insert and
        # never overwrite it on revisions. This protects against agents
        # that drop `participant_identity` from the revise payload (they
        # only resend changing fields), which would otherwise blank the
        # snapshot when the row is updated.
        existing = TranscriptSegment.objects.filter(
            transcript=transcript,
            provider_segment_id=data['provider_segment_id'],
            source=TranscriptSegment.Source.LIVE,
        ).first()

        if existing is not None:
            if existing.replaced_by_id is not None:
                # Live row already superseded by an organiser edit — drop
                # the agent's update so the human-corrected text wins.
                return Response({'status': 'locked'})
            # Mutable fields only on revise — keep speaker attribution.
            existing.start_ms = data['start_ms']
            existing.end_ms = data['end_ms']
            existing.text = data['text']
            existing.is_final = data.get('is_final', True)
            if data.get('confidence') is not None:
                existing.confidence = data['confidence']
            existing.save()
            return Response(
                {'status': 'updated', 'uuid': str(existing.uuid)},
                status=status.HTTP_200_OK,
            )

        # First-time insert — resolve speaker.
        speaker_user = _accounts_user_for_identity(
            data.get('participant_identity', '')
        )
        seg = TranscriptSegment.objects.create(
            transcript=transcript,
            provider_segment_id=data['provider_segment_id'],
            source=TranscriptSegment.Source.LIVE,
            start_ms=data['start_ms'],
            end_ms=data['end_ms'],
            text=data['text'],
            is_final=data.get('is_final', True),
            participant_identity=data.get('participant_identity', ''),
            speaker_user=speaker_user,
            speaker_name_snapshot=(
                data.get('speaker_name', '')
                or (speaker_user.full_name if speaker_user else '')
            ),
            confidence=data.get('confidence'),
        )

        return Response(
            {'status': 'created', 'uuid': str(seg.uuid)},
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_exempt, name='dispatch')
class TranscriptFinalizeView(generics.GenericAPIView):
    """POST /api/v1/internal/transcripts/{uuid}/finalize/ — agent-only.

    Idempotent. Sets `status=FINALIZED`, populates `word_count` and
    `finalized_at`. Optional body: {"error_message": "..."} to flip to
    ERROR when the agent crashes mid-stream and drains its buffer
    before exiting.
    """

    permission_classes = [IsInternalAgent]

    def post(self, request, transcript_uuid):
        try:
            transcript = Transcript.objects.get(uuid=transcript_uuid)
        except Transcript.DoesNotExist:
            return Response(
                {'error': 'Transcript not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        error_message = (request.data or {}).get('error_message', '') or ''
        target_status = (
            Transcript.Status.ERROR if error_message
            else Transcript.Status.FINALIZED
        )

        # Idempotent: re-finalize is allowed (agent may retry on network
        # blip during shutdown) but doesn't reset finalized_at.
        if transcript.status != target_status:
            transcript.status = target_status
            transcript.error_message = error_message
            if not transcript.finalized_at:
                transcript.finalized_at = timezone.now()
            # Recompute word_count from the current (un-replaced) segments
            # so edits that landed before finalization are reflected.
            current = transcript.segments.filter(replaced_by__isnull=True)
            transcript.word_count = sum(
                len(s.text.split()) for s in current.only('text')
            )
            transcript.save(update_fields=[
                'status', 'error_message', 'finalized_at',
                'word_count', 'updated_at',
            ])

        return Response({
            'status': transcript.status,
            'word_count': transcript.word_count,
            'finalized_at': (
                transcript.finalized_at.isoformat()
                if transcript.finalized_at else None
            ),
        })


class RecordingTranscriptView(generics.GenericAPIView):
    """GET /api/v1/video/recordings/{uuid}/transcript/

    Returns the recording's transcript with all current (non-superseded)
    segments. 404 when no transcript exists or the user lacks access to
    the parent recording (we don't 403 to avoid leaking which recordings
    have transcripts to unauthorised viewers).
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TranscriptSerializer

    def get(self, request, recording_uuid):
        recording = _resolve_recording_for_user(recording_uuid, request.user)
        if recording is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        try:
            transcript = recording.video_room.transcript
        except (AttributeError, Transcript.DoesNotExist):
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(TranscriptSerializer(transcript).data)


class RecordingTranscriptSearchView(generics.GenericAPIView):
    """GET /api/v1/video/recordings/{uuid}/transcript/search/?q=foo

    Trigram-matched search over the current segments of a transcript.
    Returns segments in chronological order (start_ms asc) — relevance
    ranking would be jarring for a player-synced transcript where users
    expect to scrub by time.

    On non-Postgres backends (sqlite test runs), falls back to ILIKE.
    The fallback is ~200x slower for large transcripts but exists so
    the test suite doesn't have to mock the search endpoint.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, recording_uuid):
        q = (request.query_params.get('q') or '').strip()
        if not q:
            return Response({'results': []})

        recording = _resolve_recording_for_user(recording_uuid, request.user)
        if recording is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        try:
            transcript = recording.video_room.transcript
        except (AttributeError, Transcript.DoesNotExist):
            return Response(status=status.HTTP_404_NOT_FOUND)

        from django.db import connection

        qs = transcript.segments.filter(
            replaced_by__isnull=True,
        ).order_by('start_ms')

        if connection.vendor == 'postgresql':
            # The trgm GIN index lights up for `text % q` (similarity) but
            # users expect substring matches in a transcript search box, so
            # we use `ILIKE` which trgm also accelerates when the index is
            # `gin_trgm_ops`. Patterns of length < 3 don't benefit from the
            # GIN; that's a per-character matter not a correctness issue.
            qs = qs.filter(text__icontains=q)
        else:
            qs = qs.filter(text__icontains=q)

        # Cap at 200 matches to keep payload small — the UI lists matches
        # for navigation, not as a search-results page.
        qs = qs[:200]
        return Response({
            'q': q,
            'results': TranscriptSegmentReadSerializer(qs, many=True).data,
        })


class RecordingTranscriptExportView(generics.GenericAPIView):
    """GET /api/v1/video/recordings/{uuid}/transcript/export/?as=vtt|srt|txt

    Renders the transcript in the requested subtitle/text format. Defaults
    to `vtt` (WebVTT, native to HTML5 `<track>` and the most useful for
    organiser workflows that download → upload-as-captions to a video host).

    The query param is `as=` rather than `format=` because DRF reserves
    `?format=` for renderer/content-negotiation — a value DRF doesn't know
    about (e.g. `format=vtt`) makes the framework 404 the request before
    the view runs.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, recording_uuid):
        fmt = (request.query_params.get('as') or 'vtt').lower()
        if fmt not in ('vtt', 'srt', 'txt'):
            return Response(
                {'error': "as= must be one of: vtt, srt, txt"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        recording = _resolve_recording_for_user(recording_uuid, request.user)
        if recording is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        try:
            transcript = recording.video_room.transcript
        except (AttributeError, Transcript.DoesNotExist):
            return Response(status=status.HTTP_404_NOT_FOUND)

        segments = list(
            transcript.segments
            .filter(replaced_by__isnull=True)
            .order_by('start_ms')
        )

        if fmt == 'vtt':
            body = _render_vtt(segments)
            content_type = 'text/vtt; charset=utf-8'
        elif fmt == 'srt':
            body = _render_srt(segments)
            content_type = 'application/x-subrip; charset=utf-8'
        else:
            body = _render_txt(segments)
            content_type = 'text/plain; charset=utf-8'

        from django.http import HttpResponse
        resp = HttpResponse(body, content_type=content_type)
        resp['Content-Disposition'] = (
            f'attachment; filename="transcript-{recording.uuid}.{fmt}"'
        )
        return resp


# ---------- Subtitle / text renderers --------------------------------------


def _format_vtt_timestamp(ms: int) -> str:
    """WebVTT time format: HH:MM:SS.mmm (dot-separated milliseconds)."""
    s, ms_ = divmod(max(ms, 0), 1000)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f'{h:02d}:{m:02d}:{s:02d}.{ms_:03d}'


def _format_srt_timestamp(ms: int) -> str:
    """SubRip time format: HH:MM:SS,mmm (comma-separated milliseconds)."""
    return _format_vtt_timestamp(ms).replace('.', ',', 1)


def _render_vtt(segments) -> str:
    lines = ['WEBVTT', '']
    for seg in segments:
        cue = (
            f'{_format_vtt_timestamp(seg.start_ms)} --> '
            f'{_format_vtt_timestamp(seg.end_ms)}'
        )
        speaker = seg.speaker_name_snapshot
        text = f'<v {speaker}>{seg.text}' if speaker else seg.text
        lines += [cue, text, '']
    return '\n'.join(lines)


def _render_srt(segments) -> str:
    chunks = []
    for i, seg in enumerate(segments, start=1):
        cue = (
            f'{_format_srt_timestamp(seg.start_ms)} --> '
            f'{_format_srt_timestamp(seg.end_ms)}'
        )
        speaker = seg.speaker_name_snapshot
        text = f'{speaker}: {seg.text}' if speaker else seg.text
        chunks.append(f'{i}\n{cue}\n{text}\n')
    return '\n'.join(chunks)


def _render_txt(segments) -> str:
    """Plain text with speaker prefixes; collapses consecutive segments
    from the same speaker into a single paragraph for readability."""
    lines = []
    last_speaker = None
    for seg in segments:
        speaker = seg.speaker_name_snapshot
        if speaker and speaker != last_speaker:
            lines.append(f'\n{speaker}:')
            last_speaker = speaker
        lines.append(seg.text)
    return '\n'.join(lines).strip() + '\n'


# =============================================================================
# Transcript edit + audit trail (organisers only)
# =============================================================================
#
# Edit semantics (append-only with chained `replaced_by`):
#
#   Initial state:
#     SEG_1[source=live, text="hello world", replaced_by=NULL]   ← current
#
#   After organiser edits to "hello, world":
#     SEG_1[source=live, text="hello world", replaced_by=SEG_2]
#     SEG_2[source=edit, text="hello, world", replaced_by=NULL]  ← current
#
#   Default queries filter `replaced_by__isnull=True` so callers see SEG_2.
#   The history endpoint walks the chain backward (`replaces` reverse FK)
#   to expose the full provenance for compliance review.
#
# Edit ingest from the live agent: once a segment has been superseded by
# an edit (i.e. it has a non-null `replaced_by`), the live ingest path
# in `TranscriptIngestView` short-circuits with `{status: 'locked'}` —
# preventing late-arriving agent traffic from reverting a human correction.


def _user_can_edit_transcript(user, transcript) -> bool:
    """Edit gate: same predicate as the lobby's host check.

    A user can edit a transcript when they own the parent event (or are
    a course staff member, or a platform admin). We re-use `is_event_host`
    rather than redefining the rule because keeping the two in sync is
    the whole point of having a server-computed `is_current_user_host`
    on event detail.
    """
    if not user or not user.is_authenticated:
        return False

    # Walk: transcript → video_room → content_object (Event or
    # CourseSession). For events, the existing helper does the work.
    video_room = transcript.video_room
    obj = video_room.content_object
    if obj is None:
        return False

    from events.models import Event
    if isinstance(obj, Event):
        return is_event_host(user, obj)

    # CourseSession: edit = course staff. Mirrors the recording-list scope.
    from learning.models import Course, CourseSession
    if isinstance(obj, CourseSession):
        if user.groups.filter(name='admin').exists():
            return True
        return Course.objects.filter(
            id=obj.course_id,
        ).filter(
            models.Q(created_by=user) | models.Q(staff_assignments__user=user),
        ).exists()

    return False


# `models` is referenced inside _user_can_edit_transcript via Q; ensure
# the symbol resolves regardless of import order.
from django.db import models  # noqa: E402


class TranscriptSegmentEditView(generics.GenericAPIView):
    """PATCH /api/v1/transcripts/{transcript_uuid}/segments/{segment_uuid}/

    Organiser-only edit endpoint. Creates a NEW segment row with
    `source='edit'`, copies the timing + speaker attribution from the
    superseded row (those fields are immutable for compliance — the
    audit trail records exactly what STT said vs what was changed),
    and chains `replaced_by` so default reads see the new version.

    Rejects edits on a transcript that's still STREAMING — the agent
    might re-publish the same segment_id with a revision before the
    edit lands, racing the human correction. Forcing FINALIZED before
    edit is the simplest invariant; it's also when most edits happen
    in practice (organiser reviews after the session).
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TranscriptSegmentEditSerializer

    def patch(self, request, transcript_uuid, segment_uuid):
        try:
            transcript = Transcript.objects.get(uuid=transcript_uuid)
        except Transcript.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not _user_can_edit_transcript(request.user, transcript):
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            current = transcript.segments.get(
                uuid=segment_uuid, replaced_by__isnull=True,
            )
        except TranscriptSegment.DoesNotExist:
            # Either the uuid is wrong, or this segment was already
            # superseded by another edit. We don't disambiguate to keep
            # the API simple — the UI re-fetches the transcript on
            # error so the next edit lands on the latest version.
            return Response(status=status.HTTP_404_NOT_FOUND)

        if transcript.status == Transcript.Status.STREAMING:
            return Response(
                {'error': 'Cannot edit segments while transcription is still in progress.'},
                status=status.HTTP_409_CONFLICT,
            )

        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        new_text = ser.validated_data['text']

        # Atomic: create new + update old in a transaction so a half-
        # written edit chain is impossible.
        from django.db import transaction
        with transaction.atomic():
            new_segment = TranscriptSegment.objects.create(
                transcript=transcript,
                # Inherit immutable fields from the superseded version.
                start_ms=current.start_ms,
                end_ms=current.end_ms,
                participant_identity=current.participant_identity,
                speaker_user=current.speaker_user,
                speaker_name_snapshot=current.speaker_name_snapshot,
                confidence=current.confidence,
                provider_segment_id=current.provider_segment_id,
                # New content + provenance.
                text=new_text,
                is_final=True,
                source=TranscriptSegment.Source.EDIT,
                edited_by=request.user,
                edited_at=timezone.now(),
            )
            current.replaced_by = new_segment
            current.save(update_fields=['replaced_by', 'updated_at'])

        return Response(
            TranscriptSegmentReadSerializer(new_segment).data,
            status=status.HTTP_200_OK,
        )


class TranscriptSegmentHistoryView(generics.GenericAPIView):
    """GET /api/v1/transcripts/{transcript_uuid}/segments/{segment_uuid}/history/

    Returns the full version chain for a segment in chronological order
    (oldest first). Organisers only — non-organisers always get 404.

    The query walks `provider_segment_id` rather than the FK chain because
    a chain of N edits produces N+1 rows that all share the same
    `provider_segment_id`; one indexed query is faster than recursing
    via `replaces` relations.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, transcript_uuid, segment_uuid):
        try:
            transcript = Transcript.objects.get(uuid=transcript_uuid)
        except Transcript.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not _user_can_edit_transcript(request.user, transcript):
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Resolve the segment uuid to its provider_segment_id (the chain key).
        anchor = transcript.segments.filter(uuid=segment_uuid).first()
        if anchor is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not anchor.provider_segment_id:
            # Edge: a manually-created segment with no chain. Just return
            # the row itself rather than trying to chain.
            return Response({
                'segments': [TranscriptSegmentHistorySerializer(anchor).data],
            })

        chain = transcript.segments.filter(
            provider_segment_id=anchor.provider_segment_id,
        ).order_by('created_at')

        return Response({
            'segments': TranscriptSegmentHistorySerializer(chain, many=True).data,
        })
