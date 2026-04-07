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
from django.views import View
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
from conferencing.service import get_video_provider

logger = logging.getLogger(__name__)


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

        if video_room.status == VideoRoom.Status.ENDED:
            return Response({'error': 'Video room has ended'}, status=status.HTTP_400_BAD_REQUEST)

        # Check user has registration (or is the event owner)
        is_owner = event.owner_id == request.user.id
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

        provider = get_video_provider()
        token = provider.generate_join_token(
            room_name=video_room.room_name,
            participant_identity=str(request.user.uuid),
            participant_name=request.user.get_full_name() or request.user.email,
            is_host=is_owner,
        )

        ws_url = getattr(settings, 'LIVEKIT_WS_URL', '')
        data = {
            'token': token,
            'ws_url': ws_url,
            'room_name': video_room.room_name,
        }
        return Response(JoinVideoResponseSerializer(data).data)


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

        if video_room.status == VideoRoom.Status.ENDED:
            return Response({'error': 'Video room has ended'}, status=status.HTTP_400_BAD_REQUEST)

        # Check enrollment
        is_instructor = course.created_by_id == request.user.id
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
            participant_name=request.user.get_full_name() or request.user.email,
            is_host=is_instructor,
        )

        ws_url = getattr(settings, 'LIVEKIT_WS_URL', '')
        data = {
            'token': token,
            'ws_url': ws_url,
            'room_name': video_room.room_name,
        }
        return Response(JoinVideoResponseSerializer(data).data)


class VideoRoomViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v1/video/rooms/ — List video rooms for the authenticated user's events.
    """

    serializer_class = VideoRoomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        from django.contrib.contenttypes.models import ContentType
        from events.models import Event

        ct = ContentType.objects.get_for_model(Event)
        user_event_ids = Event.objects.filter(
            owner=self.request.user, deleted_at__isnull=True
        ).values_list('id', flat=True)

        return VideoRoom.objects.filter(
            content_type=ct, object_id__in=user_event_ids
        )

    @action(detail=True, methods=['post'])
    def start_recording(self, request, pk=None):
        room = self.get_object()
        if room.status != VideoRoom.Status.ACTIVE:
            return Response({'error': 'Room is not active'}, status=status.HTTP_400_BAD_REQUEST)

        provider = get_video_provider()
        try:
            egress_id = provider.start_recording(room.room_name)
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
    def stop_recording(self, request, pk=None):
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


class VideoRecordingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v1/video/recordings/ — List published recordings accessible to the user.
    """

    serializer_class = VideoRecordingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return VideoRecording.objects.filter(
            is_published=True,
            status=VideoRecording.Status.AVAILABLE,
        )


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
