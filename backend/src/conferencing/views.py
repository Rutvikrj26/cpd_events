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

from conferencing.models import VideoRecording, VideoRoom, VideoWebhookLog
from conferencing.serializers import (
    JoinVideoResponseSerializer,
    VideoRecordingSerializer,
    VideoRoomSerializer,
    VideoStatusSerializer,
)
from common.rbac import roles
from conferencing.service import get_video_provider

logger = logging.getLogger(__name__)


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

    output_path = getattr(
        settings,
        'LIVEKIT_RECORDING_OUTPUT_PATH_TEMPLATE',
        '/out/{room_name}-{time}.mp4',
    )

    provider = get_video_provider()
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


@roles('learner', 'organizer', 'admin', route_name='join_video')
class JoinVideoView(generics.GenericAPIView):
    """
    POST /api/v1/events/{event_uuid}/join-video/

    Generates a participant JWT token for joining the video room
    associated with an event. The user must have a confirmed registration.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, event_uuid):
        from events.models import Event

        try:
            event = Event.objects.get(uuid=event_uuid, deleted_at__isnull=True)
        except Event.DoesNotExist:
            return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)

        # Find the video room for this event
        from django.contrib.contenttypes.models import ContentType

        ct = ContentType.objects.get_for_model(Event)
        try:
            video_room = VideoRoom.objects.get(content_type=ct, object_id=event.id)
        except VideoRoom.DoesNotExist:
            return Response({'error': 'No video room for this event'}, status=status.HTTP_404_NOT_FOUND)

        is_host = is_event_host(request.user, event)

        if video_room.status == VideoRoom.Status.ENDED:
            if is_host:
                video_room.reopen()
            else:
                return Response({'error': 'Video room has ended'}, status=status.HTTP_400_BAD_REQUEST)

        if not is_host:
            from registrations.models import Registration

            has_registration = Registration.objects.filter(
                event=event,
                user=request.user,
                status__in=['confirmed', 'attended'],
                deleted_at__isnull=True,
            ).exists()
            if not has_registration:
                return Response(
                    {'error': 'You must be registered for this event'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        if is_platform_admin(request.user) and event.owner_id != request.user.id:
            logger.info(
                "admin_host_override event_uuid=%s admin_user_id=%s",
                event.uuid, request.user.id,
            )

        video_settings = event.video_settings or {}
        waiting_room_enabled = bool(video_settings.get('waiting_room_enabled', False))
        recording_default = bool(video_settings.get('recording_enabled', False))
        waiting = waiting_room_enabled and not is_host

        # Auto-start recording on first host join when the event opted in.
        # ensure_recording_started is idempotent so concurrent joins / reconnects
        # don't spawn duplicate egress processes.
        if (
            is_host
            and recording_default
            and video_room.status == VideoRoom.Status.ACTIVE
        ):
            try:
                ensure_recording_started(video_room)
            except Exception:
                logger.exception(
                    "Auto-start recording failed for event %s; host can retry manually",
                    event.uuid,
                )

        provider = get_video_provider()
        token = provider.generate_join_token(
            room_name=video_room.room_name,
            participant_identity=str(request.user.uuid),
            participant_name=request.user.full_name or request.user.email,
            is_host=is_host,
            waiting=waiting,
        )

        recording_active = VideoRecording.objects.filter(
            video_room=video_room, status=VideoRecording.Status.RECORDING
        ).exists()

        ws_url = getattr(settings, 'LIVEKIT_WS_URL', '')
        data = {
            'token': token,
            'ws_url': ws_url,
            'room_name': video_room.room_name,
            'room_uuid': str(video_room.uuid),
            'is_host': is_host,
            'waiting': waiting,
            'waiting_room_enabled': waiting_room_enabled,
            'recording_enabled_default': recording_default,
            'recording_active': recording_active,
        }
        return Response(JoinVideoResponseSerializer(data).data)


class JoinVideoGuestView(generics.GenericAPIView):
    """
    POST /api/v1/public/events/{event_uuid}/join-video/

    Issue a LiveKit token for a guest attendee using their registration UUID.
    No authentication required — the registration UUID itself is the bearer
    secret. Used by attendees who registered through the public event page
    without creating an account.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, event_uuid):
        from django.contrib.contenttypes.models import ContentType

        from events.models import Event
        from registrations.models import Registration

        registration_uuid = request.data.get('registration_uuid') if isinstance(request.data, dict) else None
        if not registration_uuid:
            return Response(
                {'error': 'registration_uuid is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            event = Event.objects.get(uuid=event_uuid, deleted_at__isnull=True)
        except Event.DoesNotExist:
            return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            registration = Registration.objects.get(
                uuid=registration_uuid,
                event=event,
                deleted_at__isnull=True,
            )
        except Registration.DoesNotExist:
            return Response(
                {'error': 'Registration not found for this event'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if registration.status not in ['confirmed', 'attended']:
            return Response(
                {'error': 'Registration is not confirmed'},
                status=status.HTTP_403_FORBIDDEN,
            )

        ct = ContentType.objects.get_for_model(Event)
        try:
            video_room = VideoRoom.objects.get(content_type=ct, object_id=event.id)
        except VideoRoom.DoesNotExist:
            return Response(
                {'error': 'No video room for this event'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if video_room.status == VideoRoom.Status.ENDED:
            return Response(
                {'error': 'Video room has ended'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        video_settings = event.video_settings or {}
        waiting_room_enabled = bool(video_settings.get('waiting_room_enabled', False))
        recording_default = bool(video_settings.get('recording_enabled', False))
        waiting = waiting_room_enabled

        provider = get_video_provider()
        token = provider.generate_join_token(
            room_name=video_room.room_name,
            participant_identity=f"guest-{registration.uuid}",
            participant_name=registration.full_name or registration.email,
            is_host=False,
            waiting=waiting,
        )

        recording_active = VideoRecording.objects.filter(
            video_room=video_room, status=VideoRecording.Status.RECORDING
        ).exists()

        ws_url = getattr(settings, 'LIVEKIT_WS_URL', '')
        data = {
            'token': token,
            'ws_url': ws_url,
            'room_name': video_room.room_name,
            'room_uuid': str(video_room.uuid),
            'is_host': False,
            'waiting': waiting,
            'waiting_room_enabled': waiting_room_enabled,
            'recording_enabled_default': recording_default,
            'recording_active': recording_active,
        }
        return Response(JoinVideoResponseSerializer(data).data)


@roles('learner', 'organizer', 'instructor', 'admin', route_name='join_course_video')
class JoinCourseSessionVideoView(generics.GenericAPIView):
    """
    POST /api/v1/courses/{course_uuid}/sessions/{session_uuid}/join-video/

    Generates a participant JWT token for joining a course session video room.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, course_uuid, session_uuid):
        from learning.models import Course, CourseSession

        try:
            course = Course.objects.get(uuid=course_uuid)
        except Course.DoesNotExist:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            session = CourseSession.objects.get(uuid=session_uuid, course=course)
        except CourseSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)

        from django.contrib.contenttypes.models import ContentType

        ct = ContentType.objects.get_for_model(CourseSession)
        try:
            video_room = VideoRoom.objects.get(content_type=ct, object_id=session.id)
        except VideoRoom.DoesNotExist:
            return Response({'error': 'No video room for this session'}, status=status.HTTP_404_NOT_FOUND)

        is_host = is_course_session_host(request.user, course)

        if video_room.status == VideoRoom.Status.ENDED:
            if is_host:
                video_room.reopen()
            else:
                return Response({'error': 'Video room has ended'}, status=status.HTTP_400_BAD_REQUEST)

        if not is_host:
            from learning.models import CourseEnrollment

            has_enrollment = CourseEnrollment.objects.filter(
                course=course,
                user=request.user,
                status='active',
            ).exists()
            if not has_enrollment:
                return Response(
                    {'error': 'You must be enrolled in this course'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        if is_platform_admin(request.user) and course.created_by_id != request.user.id:
            logger.info(
                "admin_host_override course_uuid=%s session_uuid=%s admin_user_id=%s",
                course.uuid, session.uuid, request.user.id,
            )

        provider = get_video_provider()
        token = provider.generate_join_token(
            room_name=video_room.room_name,
            participant_identity=str(request.user.uuid),
            participant_name=request.user.full_name or request.user.email,
            is_host=is_host,
        )

        recording_active = VideoRecording.objects.filter(
            video_room=video_room, status=VideoRecording.Status.RECORDING
        ).exists()

        ws_url = getattr(settings, 'LIVEKIT_WS_URL', '')
        data = {
            'token': token,
            'ws_url': ws_url,
            'room_name': video_room.room_name,
            'room_uuid': str(video_room.uuid),
            'is_host': is_host,
            'waiting': False,
            'waiting_room_enabled': False,
            'recording_enabled_default': False,
            'recording_active': recording_active,
        }
        return Response(JoinVideoResponseSerializer(data).data)


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

        response = FileResponse(open(path, 'rb'), content_type='video/mp4')
        response['Content-Disposition'] = f'inline; filename="{rec_file.file_name or os.path.basename(path)}"'
        return response


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

        # Deduplicate by generating a stable webhook_id
        webhook_id = request.META.get('HTTP_X_LIVEKIT_ID', '') or str(uuid_lib.uuid4())

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
