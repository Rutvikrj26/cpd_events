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


@roles('learner', 'educator', 'course_manager', 'admin', route_name='video_status')
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


@roles('learner', 'educator', 'admin', route_name='join_video')
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

        is_owner = event.owner_id == request.user.id

        if video_room.status == VideoRoom.Status.ENDED:
            if is_owner:
                video_room.reopen()
            else:
                return Response({'error': 'Video room has ended'}, status=status.HTTP_400_BAD_REQUEST)

        if not is_owner:
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

        video_settings = event.video_settings or {}
        waiting_room_enabled = bool(video_settings.get('waiting_room_enabled', False))
        recording_default = bool(video_settings.get('recording_enabled', False))
        waiting = waiting_room_enabled and not is_owner

        provider = get_video_provider()
        token = provider.generate_join_token(
            room_name=video_room.room_name,
            participant_identity=str(request.user.uuid),
            participant_name=request.user.full_name or request.user.email,
            is_host=is_owner,
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
            'is_host': is_owner,
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


@roles('learner', 'educator', 'course_manager', 'instructor', 'admin', route_name='join_course_video')
class JoinCourseSessionVideoView(generics.GenericAPIView):
    """
    POST /api/v1/courses/{course_uuid}/sessions/{session_uuid}/join-video/

    Generates a participant JWT token for joining a course session video room.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, course_uuid, session_uuid):
        from learning.models import Course, CourseSession

        try:
            course = Course.objects.get(uuid=course_uuid, deleted_at__isnull=True)
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

        is_instructor = course.created_by_id == request.user.id

        if video_room.status == VideoRoom.Status.ENDED:
            if is_instructor:
                video_room.reopen()
            else:
                return Response({'error': 'Video room has ended'}, status=status.HTTP_400_BAD_REQUEST)

        if not is_instructor:
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

        provider = get_video_provider()
        token = provider.generate_join_token(
            room_name=video_room.room_name,
            participant_identity=str(request.user.uuid),
            participant_name=request.user.full_name or request.user.email,
            is_host=is_instructor,
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
            'is_host': is_instructor,
            'waiting': False,
            'waiting_room_enabled': False,
            'recording_enabled_default': False,
            'recording_active': recording_active,
        }
        return Response(JoinVideoResponseSerializer(data).data)


@roles('educator', 'admin', route_name='video_rooms')
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
            return VideoRoom.objects.filter(content_type__in=[event_ct, session_ct])

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

        return VideoRoom.objects.filter(
            Q(content_type=event_ct, object_id__in=user_event_ids)
            | Q(content_type=session_ct, object_id__in=user_session_ids)
        )

    @action(detail=True, methods=['post'])
    def start_recording(self, request, pk=None, uuid=None):
        room = self.get_object()
        if room.status != VideoRoom.Status.ACTIVE:
            return Response({'error': 'Room is not active'}, status=status.HTTP_400_BAD_REQUEST)

        # Give each recording a predictable path on the egress container's
        # mounted volume so we can surface it to users after processing.
        # LiveKit's {room_id} / {time} template variables are expanded by
        # the egress service at recording start.
        output_path = getattr(
            settings,
            'LIVEKIT_RECORDING_OUTPUT_PATH_TEMPLATE',
            '/out/{room_name}-{time}.mp4',
        )

        provider = get_video_provider()
        try:
            egress_id = provider.start_recording(room.room_name, output_path=output_path)
            VideoRecording.objects.create(
                video_room=room,
                egress_id=egress_id,
                recording_start=timezone.now(),
                status=VideoRecording.Status.RECORDING,
            )
            return Response({'egress_id': egress_id, 'status': 'recording'})
        except Exception as e:
            logger.exception("Failed to start recording for room %s", room.room_name)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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


@roles('educator', 'admin', route_name='video_recordings')
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

    def get_queryset(self):
        qs = VideoRecording.objects.filter(
            is_published=True,
            status=VideoRecording.Status.AVAILABLE,
        )
        user = self.request.user
        if user.groups.filter(name="admin").exists():
            return qs

        from django.db.models import Q
        from events.models import Event
        from learning.models import Course, CourseEnrollment, CourseSession

        user_event_ids = Event.objects.filter(
            owner=user, deleted_at__isnull=True
        ).values_list('id', flat=True)

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
            | Q(course_session_id__in=accessible_session_ids)
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

        # Match to VideoRoom
        try:
            video_room = VideoRoom.objects.get(room_name=event.room_name)
            log.video_room = video_room
            log.save(update_fields=['video_room', 'updated_at'])
        except VideoRoom.DoesNotExist:
            log.mark_skipped(f"No VideoRoom found for room_name={event.room_name}")
            return JsonResponse({'status': 'skipped'})

        # Dispatch async processing
        from conferencing.tasks import process_video_webhook

        process_video_webhook(log.id)

        return JsonResponse({'status': 'ok'})
