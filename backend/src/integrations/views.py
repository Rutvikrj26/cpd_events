"""
Integrations app views - Recordings API (C3) and Webhooks (H8).
"""

import hashlib
import hmac

from django.conf import settings
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from common.permissions import IsOrganizer
from common.rbac import roles
from common.viewsets import ReadOnlyModelViewSet
from common.utils import error_response

from . import serializers
from .tasks import process_zoom_webhook
from .models import EmailLog, RecordingView, ZoomRecording, ZoomRecordingFile, ZoomWebhookLog

# =============================================================================
# Event Recordings ViewSet (C3)
# =============================================================================


class EventRecordingFilter(filters.FilterSet):
    """Filter recordings."""

    status = filters.ChoiceFilter(choices=ZoomRecording.Status.choices)

    class Meta:
        model = ZoomRecording
        fields = ['status', 'access_level']


@roles('organizer', 'admin', route_name='event_recordings')
class EventRecordingViewSet(viewsets.ModelViewSet):
    """
    Manage recordings for an event (C3).

    Nested under events: /api/v1/events/{event_uuid}/recordings/
    """

    permission_classes = [IsAuthenticated, IsOrganizer]
    filterset_class = EventRecordingFilter
    ordering = ['-created_at']
    lookup_field = 'uuid'

    def get_queryset(self):
        event_uuid = self.kwargs.get('event_uuid')
        return (
            ZoomRecording.objects.filter(event__uuid=event_uuid, event__owner=self.request.user)
            .select_related('event')
            .prefetch_related('files')
        )

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return serializers.ZoomRecordingUpdateSerializer
        if self.action == 'list':
            return serializers.ZoomRecordingListSerializer
        return serializers.ZoomRecordingDetailSerializer

    @swagger_auto_schema(
        operation_summary="Recording analytics",
        operation_description="Get analytics for a specific recording.",
    )
    @action(detail=True, methods=['get'])
    def analytics(self, request, event_uuid=None, uuid=None):
        """Get recording analytics."""
        recording = self.get_object()

        views = recording.views.all()
        total_watch = sum(v.watch_duration_seconds or 0 for v in views)
        avg_watch = total_watch // views.count() if views.count() > 0 else 0

        # Estimate completion rate
        if recording.duration_seconds:
            completion_rates = [
                (v.watch_duration_seconds or 0) / recording.duration_seconds for v in views if v.watch_duration_seconds
            ]
            avg_completion = sum(completion_rates) / len(completion_rates) if completion_rates else 0
        else:
            avg_completion = 0

        return Response(
            {
                'total_views': recording.view_count,
                'unique_viewers': recording.unique_viewers,
                'total_watch_time_seconds': total_watch,
                'average_watch_time_seconds': avg_watch,
                'completion_rate': avg_completion,
            }
        )

    @swagger_auto_schema(
        operation_summary="Recording views",
        operation_description="Get the view log for a recording.",
        responses={200: serializers.RecordingViewLogSerializer(many=True)},
    )
    @action(detail=True, methods=['get'])
    def views(self, request, event_uuid=None, uuid=None):
        """Get view log for recording."""
        recording = self.get_object()
        views = recording.views.all().order_by('-started_at')
        serializer = serializers.RecordingViewLogSerializer(views, many=True)
        return Response(serializer.data)


# =============================================================================
# Attendee Recordings Access (C3)
# =============================================================================


@roles('attendee', 'organizer', 'admin', route_name='my_recordings')
class MyRecordingsViewSet(ReadOnlyModelViewSet):
    """
    Current user's accessible recordings.

    GET /api/v1/users/me/recordings/
    GET /api/v1/users/me/recordings/{uuid}/
    """

    serializer_class = serializers.AttendeeRecordingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Get recordings where user is a confirmed registrant
        from registrations.models import Registration

        user_event_ids = Registration.objects.filter(user=user, status='confirmed', deleted_at__isnull=True).values_list(
            'event_id', flat=True
        )

        return (
            ZoomRecording.objects.filter(
                event_id__in=user_event_ids, status='available', access_level__in=['registrants', 'attendees', 'public']
            )
            .select_related('event')
            .prefetch_related('files')
        )

    @swagger_auto_schema(
        operation_summary="Stream recording",
        operation_description="Get a streaming URL for a recording file. Requires file_uuid in request body.",
        responses={200: '{"streaming_url": "..."}', 400: '{"error": {}}'},
    )
    @action(detail=True, methods=['post'])
    def stream(self, request, uuid=None):
        """Get streaming URL for a recording file."""
        recording = self.get_object()

        file_uuid = request.data.get('file_uuid')
        if not file_uuid:
            return error_response('file_uuid is required.', code='MISSING_FILE')

        try:
            recording_file = recording.files.get(uuid=file_uuid, is_enabled=True)
        except ZoomRecordingFile.DoesNotExist:
            return error_response('Recording file not found.', code='NOT_FOUND', status_code=status.HTTP_404_NOT_FOUND)

        # Track view
        RecordingView.objects.create(
            recording=recording,
            viewer=request.user,
            started_at=timezone.now(),
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )

        # Update counts
        recording.view_count = (recording.view_count or 0) + 1
        recording.save(update_fields=['view_count'])

        # Future Work: Generate signed streaming URL (e.g. CloudFront/GCP signed URLs)
        # to prevent direct access. For now, we rely on the play_url from Zoom.
        return Response(
            {
                'streaming_url': recording_file.play_url,
                'expires_at': (timezone.now() + timezone.timedelta(hours=1)).isoformat(),
            }
        )


# =============================================================================
# Zoom Webhook Handler (H8)
# =============================================================================


@roles('public', route_name='zoom_webhook')
class ZoomWebhookView(generics.GenericAPIView):
    """
    POST /api/v1/webhooks/zoom/

    Handle Zoom webhook events with proper signature verification (H8).
    """

    permission_classes = [AllowAny]

    def post(self, request):
        # Zoom URL validation challenge
        event = request.data.get('event')
        if event == 'endpoint.url_validation':
            return self._handle_url_validation(request)

        # Verify signature (H8)
        if not self._verify_signature(request):
            ZoomWebhookLog.objects.create(
                webhook_id=f"invalid_{timezone.now().timestamp()}",
                event_type='signature_failed',
                zoom_meeting_id='',
                event_timestamp=timezone.now(),  # Added missing timestamp
                payload=request.data,
                processing_status='failed',
                error_message='Invalid signature',
            )
            return error_response('Invalid signature', code='INVALID_SIGNATURE', status_code=status.HTTP_401_UNAUTHORIZED)

        # Log the webhook
        event_type = request.data.get('event', 'unknown')
        payload = request.data.get('payload', {})
        meeting_id = payload.get('object', {}).get('id', '') or payload.get('meeting', {}).get('id', '')

        webhook_id = request.headers.get('x-zm-request-id', f"{event_type}_{timezone.now().timestamp()}")

        # Deduplicate
        if ZoomWebhookLog.objects.filter(webhook_id=webhook_id).exists():
            return Response({'status': 'duplicate'})

        # Extract timestamp
        event_ts = request.data.get('event_ts')
        if event_ts:
            import datetime
            # Zoom sends timestamp in milliseconds
            event_timestamp = datetime.datetime.fromtimestamp(event_ts / 1000.0, tz=datetime.timezone.utc)
        else:
            event_timestamp = timezone.now()

        log = ZoomWebhookLog.objects.create(
            webhook_id=webhook_id,
            event_type=event_type,
            zoom_meeting_id=str(meeting_id),
            event_timestamp=event_timestamp,
            payload=request.data,
            processing_status='pending',
        )

        # Process asynchronously (in production use Celery)
        process_zoom_webhook.delay(log.id)

        return Response({'status': 'received'})

    def _handle_url_validation(self, request):
        """Handle Zoom URL validation challenge."""
        plain_token = request.data.get('payload', {}).get('plainToken', '')

        if not plain_token:
            return error_response('Missing plainToken', code='MISSING_TOKEN')

        secret_token = getattr(settings, 'ZOOM_WEBHOOK_SECRET', '')

        # Create hash
        hash_obj = hmac.new(secret_token.encode('utf-8'), plain_token.encode('utf-8'), hashlib.sha256)
        encrypted_token = hash_obj.hexdigest()

        return Response(
            {
                'plainToken': plain_token,
                'encryptedToken': encrypted_token,
            }
        )

    def _verify_signature(self, request):
        """Verify Zoom webhook signature (H8)."""
        signature = request.headers.get('x-zm-signature', '')
        timestamp = request.headers.get('x-zm-request-timestamp', '')

        if not signature or not timestamp:
            return False

        secret_token = getattr(settings, 'ZOOM_WEBHOOK_SECRET', '')

        if not secret_token:
            return True  # Skip verification in dev mode

        # Construct message
        import json

        message = f"v0:{timestamp}:{json.dumps(request.data, separators=(',', ':'))}"

        # Create expected signature
        hash_obj = hmac.new(secret_token.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
        expected_signature = f"v0={hash_obj.hexdigest()}"

        return hmac.compare_digest(signature, expected_signature)


# =============================================================================
# Email Logs (for debugging)
# =============================================================================


@roles('organizer', 'admin', route_name='email_logs')
class EmailLogViewSet(ReadOnlyModelViewSet):
    """
    View email logs for an event.

    GET /api/v1/events/{event_uuid}/emails/
    """

    serializer_class = serializers.EmailLogSerializer
    permission_classes = [IsAuthenticated, IsOrganizer]

    def get_queryset(self):
        event_uuid = self.kwargs.get('event_uuid')
        return EmailLog.objects.filter(event__uuid=event_uuid, event__owner=self.request.user).order_by('-created_at')


# =============================================================================
# Zoom OAuth Views (H8)
# =============================================================================


@roles('organizer', 'admin', route_name='zoom_initiate')
class ZoomInitiateView(generics.GenericAPIView):
    """
    GET /api/v1/integrations/zoom/initiate/

    Start OAuth flow. Returns authorization URL.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from accounts.services import zoom_service

        result = zoom_service.initiate_oauth(request.user)

        if result.get('success'):
            return Response({'url': result.get('authorization_url')})
        
        return error_response(result.get('error', 'Configuration error'), code='CONFIG_ERROR')


@roles('organizer', 'admin', route_name='zoom_callback')
class ZoomCallbackView(generics.GenericAPIView):
    """
    GET /api/v1/integrations/zoom/callback/

    Handle OAuth redirect from Zoom.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        code = request.query_params.get('code')
        error = request.query_params.get('error')

        if error:
            return error_response(f"Zoom authorization failed: {error}", code='AUTH_FAILED')

        if not code:
            return error_response('Missing authorization code', code='MISSING_CODE')

        from accounts.services import zoom_service

        result = zoom_service.complete_oauth(request.user, code)

        if result.get('success'):
            return Response({'status': 'connected'})
        
        return error_response(result.get('error', 'Unknown error'), code='CONNECTION_FAILED')


@roles('organizer', 'admin', route_name='zoom_status')
class ZoomStatusView(generics.RetrieveAPIView):
    """
    GET /api/v1/integrations/zoom/status/

    Check if current user has Zoom connected.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'is_connected': request.user.has_zoom_connected,
            'zoom_email': request.user.zoom_connection.zoom_email if request.user.has_zoom_connected else None
        })


@roles('organizer', 'admin', route_name='zoom_disconnect')
class ZoomDisconnectView(generics.GenericAPIView):
    """
    POST /api/v1/integrations/zoom/disconnect/

    Disconnect Zoom account.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from accounts.services import zoom_service

        if zoom_service.disconnect(request.user):
            return Response({'status': 'disconnected'})
        
        return error_response('Failed to disconnect Zoom', code='DISCONNECT_FAILED')


@roles('organizer', 'admin', route_name='zoom_meetings')
class ZoomMeetingsListView(generics.ListAPIView):
    """
    GET /api/v1/integrations/zoom/meetings/

    List all events with Zoom meetings for the current user.
    """

    permission_classes = [IsAuthenticated, IsOrganizer]
    serializer_class = serializers.ZoomMeetingListSerializer

    def get_queryset(self):
        from events.models import Event

        return (
            Event.objects.filter(
                owner=self.request.user,
                zoom_meeting_id__isnull=False,
                deleted_at__isnull=True,
            )
            .exclude(zoom_meeting_id='')
            .order_by('-starts_at')
            .values(
                'uuid',
                'title',
                'status',
                'starts_at',
                'zoom_meeting_id',
                'zoom_join_url',
                'zoom_password',
                'created_at',
            )
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        # Transform to match serializer's expected field names
        data = [
            {
                'event_uuid': item['uuid'],
                'event_title': item['title'],
                'event_status': item['status'],
                'starts_at': item['starts_at'],
                'zoom_meeting_id': item['zoom_meeting_id'],
                'zoom_join_url': item['zoom_join_url'],
                'zoom_password': item['zoom_password'],
                'event_created_at': item['created_at'],
            }
            for item in queryset
        ]
        serializer = self.get_serializer(data, many=True)
        return Response(serializer.data)

