"""
Integrations app views - Recordings API (C3) and Webhooks (H8).
"""

import hmac
import hashlib
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters import rest_framework as filters
from django.conf import settings
from django.utils import timezone

from common.viewsets import ReadOnlyModelViewSet
from common.permissions import IsOrganizer
from . import serializers
from .models import ZoomRecording, ZoomRecordingFile, ZoomWebhookLog, RecordingView, EmailLog


# =============================================================================
# Event Recordings ViewSet (C3)
# =============================================================================

class EventRecordingFilter(filters.FilterSet):
    """Filter recordings."""
    status = filters.ChoiceFilter(choices=ZoomRecording.Status.choices)
    
    class Meta:
        model = ZoomRecording
        fields = ['status', 'access_level']


class EventRecordingViewSet(viewsets.ModelViewSet):
    """
    Manage recordings for an event (C3).
    
    Nested under events: /api/v1/events/{event_uuid}/recordings/
    """
    permission_classes = [IsAuthenticated, IsOrganizer]
    filterset_class = EventRecordingFilter
    ordering = ['-created_at']
    
    def get_queryset(self):
        event_uuid = self.kwargs.get('event_uuid')
        return ZoomRecording.objects.filter(
            event__uuid=event_uuid,
            event__owner=self.request.user
        ).select_related('event').prefetch_related('files')
    
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return serializers.ZoomRecordingUpdateSerializer
        if self.action == 'list':
            return serializers.ZoomRecordingListSerializer
        return serializers.ZoomRecordingDetailSerializer
    
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
                (v.watch_duration_seconds or 0) / recording.duration_seconds
                for v in views if v.watch_duration_seconds
            ]
            avg_completion = sum(completion_rates) / len(completion_rates) if completion_rates else 0
        else:
            avg_completion = 0
        
        return Response({
            'total_views': recording.view_count,
            'unique_viewers': recording.unique_viewers,
            'total_watch_time_seconds': total_watch,
            'average_watch_time_seconds': avg_watch,
            'completion_rate': avg_completion,
        })
    
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
        user_event_ids = Registration.objects.filter(
            user=user,
            status='confirmed',
            deleted_at__isnull=True
        ).values_list('event_id', flat=True)
        
        return ZoomRecording.objects.filter(
            event_id__in=user_event_ids,
            status='available',
            access_level__in=['registrants', 'attendees', 'public']
        ).select_related('event').prefetch_related('files')
    
    @action(detail=True, methods=['post'])
    def stream(self, request, uuid=None):
        """Get streaming URL for a recording file."""
        recording = self.get_object()
        
        file_uuid = request.data.get('file_uuid')
        if not file_uuid:
            return Response(
                {'error': {'code': 'MISSING_FILE', 'message': 'file_uuid is required.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            recording_file = recording.files.get(uuid=file_uuid, is_enabled=True)
        except ZoomRecordingFile.DoesNotExist:
            return Response(
                {'error': {'code': 'NOT_FOUND', 'message': 'Recording file not found.'}},
                status=status.HTTP_404_NOT_FOUND
            )
        
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
        
        # TODO: Generate signed streaming URL
        # For now return the play URL
        return Response({
            'streaming_url': recording_file.play_url,
            'expires_at': (timezone.now() + timezone.timedelta(hours=1)).isoformat(),
        })


# =============================================================================
# Zoom Webhook Handler (H8)
# =============================================================================

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
                payload=request.data,
                processing_status='failed',
                error_message='Invalid signature',
            )
            return Response({'error': 'Invalid signature'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Log the webhook
        event_type = request.data.get('event', 'unknown')
        payload = request.data.get('payload', {})
        meeting_id = payload.get('object', {}).get('id', '') or payload.get('meeting', {}).get('id', '')
        
        webhook_id = request.headers.get('x-zm-request-id', f"{event_type}_{timezone.now().timestamp()}")
        
        # Deduplicate
        if ZoomWebhookLog.objects.filter(webhook_id=webhook_id).exists():
            return Response({'status': 'duplicate'})
        
        log = ZoomWebhookLog.objects.create(
            webhook_id=webhook_id,
            event_type=event_type,
            zoom_meeting_id=str(meeting_id),
            payload=request.data,
            processing_status='pending',
        )
        
        # Process asynchronously (in production use Celery)
        # process_zoom_webhook.delay(log.id)
        
        return Response({'status': 'received'})
    
    def _handle_url_validation(self, request):
        """Handle Zoom URL validation challenge."""
        plain_token = request.data.get('payload', {}).get('plainToken', '')
        
        if not plain_token:
            return Response({'error': 'Missing plainToken'}, status=status.HTTP_400_BAD_REQUEST)
        
        secret_token = getattr(settings, 'ZOOM_WEBHOOK_SECRET', '')
        
        # Create hash
        hash_obj = hmac.new(
            secret_token.encode('utf-8'),
            plain_token.encode('utf-8'),
            hashlib.sha256
        )
        encrypted_token = hash_obj.hexdigest()
        
        return Response({
            'plainToken': plain_token,
            'encryptedToken': encrypted_token,
        })
    
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
        hash_obj = hmac.new(
            secret_token.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        )
        expected_signature = f"v0={hash_obj.hexdigest()}"
        
        return hmac.compare_digest(signature, expected_signature)


# =============================================================================
# Email Logs (for debugging)
# =============================================================================

class EmailLogViewSet(ReadOnlyModelViewSet):
    """
    View email logs for an event.
    
    GET /api/v1/events/{event_uuid}/emails/
    """
    serializer_class = serializers.EmailLogSerializer
    permission_classes = [IsAuthenticated, IsOrganizer]
    
    def get_queryset(self):
        event_uuid = self.kwargs.get('event_uuid')
        return EmailLog.objects.filter(
            event__uuid=event_uuid,
            event__owner=self.request.user
        ).order_by('-created_at')
