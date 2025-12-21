"""
Events app views and viewsets.
"""

from django.db.models import Q
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_yasg.utils import swagger_auto_schema

from common.pagination import SmallPagination
from common.permissions import IsOrganizer
from common.rbac import roles
from common.utils import error_response
from common.viewsets import SoftDeleteModelViewSet

from . import serializers
from .models import Event, EventCustomField

# =============================================================================
# Filters
# =============================================================================


class EventFilter(filters.FilterSet):
    """Filter events."""

    status = filters.MultipleChoiceFilter(choices=Event.Status.choices)
    event_type = filters.MultipleChoiceFilter(choices=Event.EventType.choices)
    starts_after = filters.DateTimeFilter(field_name='starts_at', lookup_expr='gte')
    starts_before = filters.DateTimeFilter(field_name='starts_at', lookup_expr='lte')
    cpd_type = filters.CharFilter()

    class Meta:
        model = Event
        fields = ['status', 'event_type', 'cpd_type']


class PublicEventFilter(filters.FilterSet):
    """Filter for public event discovery."""

    event_type = filters.MultipleChoiceFilter(choices=Event.EventType.choices)
    cpd_type = filters.CharFilter()
    starts_after = filters.DateTimeFilter(field_name='starts_at', lookup_expr='gte')
    starts_before = filters.DateTimeFilter(field_name='starts_at', lookup_expr='lte')
    search = filters.CharFilter(method='filter_search')

    class Meta:
        model = Event
        fields = ['event_type', 'cpd_type']

    def filter_search(self, queryset, name, value):
        return queryset.filter(Q(title__icontains=value) | Q(description__icontains=value))


# =============================================================================
# Organizer ViewSet
# =============================================================================


@roles('organizer', 'admin', route_name='events')
class EventViewSet(SoftDeleteModelViewSet):
    """
    Organizer-level CRUD for events.

    GET /api/v1/events/
    POST /api/v1/events/
    GET /api/v1/events/{uuid}/
    PATCH /api/v1/events/{uuid}/
    DELETE /api/v1/events/{uuid}/
    """

    parser_classes = (MultiPartParser, FormParser, JSONParser)
    permission_classes = [IsAuthenticated, IsOrganizer]
    filterset_class = EventFilter
    search_fields = ['title', 'description']
    ordering_fields = ['starts_at', 'created_at', 'title', 'registration_count']
    ordering = ['-created_at']

    def get_queryset(self):
        return Event.objects.filter(owner=self.request.user, deleted_at__isnull=True).select_related(
            'owner', 'certificate_template'
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return serializers.EventCreateSerializer
        if self.action in ['update', 'partial_update']:
            return serializers.EventUpdateSerializer
        if self.action == 'list':
            return serializers.EventListSerializer
        return serializers.EventDetailSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @swagger_auto_schema(
        operation_summary="Publish event",
        operation_description="Publish a draft event to make it visible and open for registration.",
        responses={200: serializers.EventDetailSerializer, 400: '{"error": {"code": "INVALID_STATE"}}'},
    )
    @action(detail=True, methods=['post'])
    def publish(self, request, uuid=None):
        """Publish a draft event."""
        event = self.get_object()

        if event.status != 'draft':
            return error_response('Can only publish draft events.', code='INVALID_STATE', status_code=status.HTTP_400_BAD_REQUEST)

        event.publish()
        return Response(serializers.EventDetailSerializer(event).data)

    @swagger_auto_schema(
        operation_summary="Cancel event",
        operation_description="Cancel an event. All registrants will be notified.",
        request_body=serializers.EventStatusChangeSerializer,
        responses={200: serializers.EventDetailSerializer, 400: '{"error": {"code": "INVALID_STATE"}}'},
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, uuid=None):
        """Cancel an event."""
        event = self.get_object()
        serializer = serializers.EventStatusChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            event.cancel(reason=serializer.validated_data.get('reason', ''), cancelled_by=request.user)
        except ValueError as e:
            return error_response(str(e), code='INVALID_STATE')

        return Response(serializers.EventDetailSerializer(event).data)

    @swagger_auto_schema(
        operation_summary="Go live",
        operation_description="Mark the event as live (in progress).",
        responses={200: serializers.EventDetailSerializer, 400: '{"error": {"code": "INVALID_STATE"}}'},
    )
    @action(detail=True, methods=['post'], url_path='go-live')
    def go_live(self, request, uuid=None):
        """Start the event (mark as live)."""
        event = self.get_object()

        try:
            event.go_live()
        except ValueError as e:
            return error_response(str(e), code='INVALID_STATE')

        return Response(serializers.EventDetailSerializer(event).data)

    @swagger_auto_schema(
        operation_summary="Complete event",
        operation_description="Mark the event as completed after it has ended.",
        responses={200: serializers.EventDetailSerializer, 400: '{"error": {"code": "INVALID_STATE"}}'},
    )
    @action(detail=True, methods=['post'])
    def complete(self, request, uuid=None):
        """Mark event as completed."""
        event = self.get_object()

        try:
            event.complete()
        except ValueError as e:
            return error_response(str(e), code='INVALID_STATE')

        return Response(serializers.EventDetailSerializer(event).data)

    @swagger_auto_schema(
        operation_summary="Duplicate event",
        operation_description="Create a copy of this event with a new UUID and draft status.",
        responses={201: serializers.EventDetailSerializer},
    )
    @action(detail=True, methods=['post'])
    def duplicate(self, request, uuid=None):
        """Create a copy of this event."""
        event = self.get_object()
        new_event = event.duplicate()

        return Response(serializers.EventDetailSerializer(new_event).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        method='post',
        operation_summary="Upload featured image",
        operation_description="Upload a featured image for the event.",
        responses={200: serializers.EventDetailSerializer, 400: '{"error": {"code": "NO_FILE"}}'},
    )
    @swagger_auto_schema(
        method='delete',
        operation_summary="Delete featured image",
        operation_description="Remove the featured image from the event.",
        responses={200: serializers.EventDetailSerializer},
    )
    @action(detail=True, methods=['post', 'delete'], url_path='upload-image')
    def upload_image(self, request, uuid=None):
        """
        Upload or delete a featured image.
        POST: Upload new image.
        DELETE: Remove existing image.
        """
        event = self.get_object()

        if request.method == 'DELETE':
            event.featured_image.delete(save=False) # Delete file from storage
            event.featured_image = None
            event.save(update_fields=['featured_image', 'updated_at'])
            return Response(serializers.EventDetailSerializer(event, context={'request': request}).data)
        
        if 'image' not in request.FILES:
            return error_response('No image file provided.', code='NO_FILE', status_code=status.HTTP_400_BAD_REQUEST)
        
        image_file = request.FILES['image']
        
        # Validate file type
        valid_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if image_file.content_type not in valid_types:
            return error_response(
                f'Invalid file type. Allowed: {", ".join(valid_types)}',
                code='INVALID_TYPE',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file size (max 5MB)
        max_size = 5 * 1024 * 1024
        if image_file.size > max_size:
            return error_response(
                'File too large. Maximum size is 5MB.',
                code='FILE_TOO_LARGE',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        event.featured_image = image_file
        event.save(update_fields=['featured_image', 'updated_at'])
        
        return Response(serializers.EventDetailSerializer(event, context={'request': request}).data)

    @swagger_auto_schema(
        operation_summary="Event history",
        operation_description="Get the status change history for this event.",
        responses={200: serializers.EventStatusHistorySerializer(many=True)},
    )
    @action(detail=True, methods=['get'])
    def history(self, request, uuid=None):
        """Get status change history."""
        event = self.get_object()
        history = event.status_history.all().order_by('-created_at')
        serializer = serializers.EventStatusHistorySerializer(history, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Dashboard stats",
        operation_description="Get aggregate statistics for the organizer's events.",
    )
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get dashboard stats for organizer."""
        events = self.get_queryset()
        now = timezone.now()

        return Response(
            {
                'total_events': events.count(),
                'draft': events.filter(status='draft').count(),
                'published': events.filter(status='published').count(),
                'upcoming': events.filter(status='published', starts_at__gt=now).count(),
                'live': events.filter(status='live').count(),
                'completed': events.filter(status__in=['completed', 'closed']).count(),
                'total_registrations': sum(e.registration_count for e in events),
                'total_attendees': sum(e.attendee_count for e in events),
            }
        )


# =============================================================================
# Nested Registrations
# =============================================================================

# EventRegistrationViewSet is imported from registrations app


# =============================================================================
# Public Event Views
# =============================================================================


@roles('public', route_name='public_events')
class PublicEventListView(generics.ListAPIView):
    """
    GET /api/v1/public/events/

    Public event discovery.
    """

    serializer_class = serializers.PublicEventListSerializer
    permission_classes = [AllowAny]
    filterset_class = PublicEventFilter
    search_fields = ['title', 'description', 'owner__organizer_display_name']
    ordering_fields = ['starts_at', 'registration_count']
    ordering = ['starts_at']

    def get_queryset(self):
        return Event.objects.filter(
            status='published',
            is_public=True,
            starts_at__gte=timezone.now(),
            deleted_at__isnull=True,
        ).select_related('owner')


class PublicEventDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/public/events/{slug_or_uuid}/

    Public event detail by slug or uuid.
    """

    serializer_class = serializers.PublicEventDetailSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        """Look up event by slug first, then by uuid if slug lookup fails."""
        identifier = self.kwargs.get('identifier')
        queryset = self.get_queryset()

        # Try slug first
        obj = queryset.filter(slug=identifier).first()
        if obj:
            return obj

        # Try uuid
        try:
            import uuid
            uuid_obj = uuid.UUID(identifier)
            obj = queryset.filter(uuid=uuid_obj).first()
            if obj:
                return obj
        except (ValueError, TypeError):
            pass

        # Not found
        from django.http import Http404
        raise Http404("Event not found")

    def get_queryset(self):
        return (
            Event.objects.filter(
                status__in=['published', 'live'],
                is_public=True,
                deleted_at__isnull=True,
            )
            .select_related('owner')
            .prefetch_related('custom_fields')
        )


# =============================================================================
# Custom Fields Management
# =============================================================================


class EventCustomFieldViewSet(viewsets.ModelViewSet):
    """
    Manage custom fields for an event.

    Nested under events: /api/v1/events/{event_uuid}/custom-fields/
    """

    permission_classes = [IsAuthenticated, IsOrganizer]

    def get_queryset(self):
        event_uuid = self.kwargs.get('event_uuid')
        return EventCustomField.objects.filter(event__uuid=event_uuid, event__owner=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return serializers.EventCustomFieldCreateSerializer
        return serializers.EventCustomFieldSerializer

    def perform_create(self, serializer):
        event_uuid = self.kwargs.get('event_uuid')
        event = Event.objects.get(uuid=event_uuid, owner=self.request.user)

        # Get next position
        max_position = self.get_queryset().order_by('-position').values_list('position', flat=True).first() or 0

        serializer.save(event=event, position=max_position + 1)

    @action(detail=False, methods=['post'])
    def reorder(self, request, event_uuid=None):
        """Reorder custom fields."""
        field_order = request.data.get('order', [])  # List of UUIDs in desired order

        for position, field_uuid in enumerate(field_order):
            self.get_queryset().filter(uuid=field_uuid).update(position=position)

        return Response({'message': 'Fields reordered.'})


# =============================================================================
# Session Management (C1: Multi-Session Events API)
# =============================================================================


class EventSessionViewSet(viewsets.ModelViewSet):
    """
    Manage sessions for a multi-session event.

    Nested under events: /api/v1/events/{event_uuid}/sessions/
    """

    permission_classes = [IsAuthenticated, IsOrganizer]
    pagination_class = SmallPagination  # M5: Nested resource pagination
    lookup_field = 'uuid'

    def get_queryset(self):
        from .sessions import EventSession

        event_uuid = self.kwargs.get('event_uuid')
        return EventSession.objects.filter(event__uuid=event_uuid, event__owner=self.request.user).order_by(
            'order', 'starts_at'
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.EventSessionListSerializer
        if self.action == 'create':
            return serializers.EventSessionCreateSerializer
        if self.action in ['update', 'partial_update']:
            return serializers.EventSessionUpdateSerializer
        return serializers.EventSessionDetailSerializer

    def perform_create(self, serializer):
        event_uuid = self.kwargs.get('event_uuid')
        event = Event.objects.get(uuid=event_uuid, owner=self.request.user)

        # Get next order position
        max_order = self.get_queryset().order_by('-order').values_list('order', flat=True).first() or 0

        serializer.save(event=event, order=max_order + 1)

    @swagger_auto_schema(
        operation_summary="Reorder sessions",
        operation_description="Reorder sessions within a multi-session event by providing a list of session UUIDs in the desired order.",
        request_body=serializers.SessionReorderSerializer,
        responses={200: '{"message": "Sessions reordered."}'},
    )
    @action(detail=False, methods=['post'])
    def reorder(self, request, event_uuid=None):
        """Reorder sessions within the event."""
        reorder_serializer = serializers.SessionReorderSerializer(data=request.data)
        reorder_serializer.is_valid(raise_exception=True)

        order_list = reorder_serializer.validated_data['order']
        for order, session_uuid in enumerate(order_list):
            self.get_queryset().filter(uuid=session_uuid).update(order=order)

        return Response({'message': 'Sessions reordered.'})


class RegistrationSessionAttendanceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View session attendance for a registration.

    Nested under registrations: /api/v1/registrations/{registration_uuid}/session-attendance/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = serializers.SessionAttendanceSerializer
    lookup_field = 'uuid'

    def get_queryset(self):
        from registrations.models import Registration

        from .sessions import SessionAttendance

        registration_uuid = self.kwargs.get('registration_uuid')
        registration = Registration.objects.get(uuid=registration_uuid)

        # Check permission: owner of event or the registrant themselves
        user = self.request.user
        if registration.event.owner != user and registration.user != user:
            return SessionAttendance.objects.none()

        return (
            SessionAttendance.objects.filter(registration=registration)
            .select_related('session')
            .order_by('session__order', 'session__starts_at')
        )

    @swagger_auto_schema(
        operation_summary="Override session attendance",
        operation_description="Override attendance eligibility for a specific session. Only the event owner can perform this action.",
        request_body=serializers.SessionAttendanceOverrideSerializer,
        responses={
            200: serializers.SessionAttendanceSerializer,
            403: '{"error": "Only the event owner can override attendance."}',
        },
    )
    @action(detail=True, methods=['post'])
    def override(self, request, registration_uuid=None, uuid=None):
        """Override session attendance eligibility."""

        session_attendance = self.get_object()
        event = session_attendance.registration.event # Define event for the check

        # Only event owner can override
        if session_attendance.registration.event.owner != request.user:
             return error_response('Only the event owner can override attendance.', code='PERMISSION_DENIED', status_code=status.HTTP_403_FORBIDDEN)

        override_serializer = serializers.SessionAttendanceOverrideSerializer(data=request.data)
        override_serializer.is_valid(raise_exception=True)

        session_attendance.override_eligible = override_serializer.validated_data['eligible']
        session_attendance.override_reason = override_serializer.validated_data['reason']
        session_attendance.override_by = request.user
        session_attendance.save()

        return Response(serializers.SessionAttendanceSerializer(session_attendance).data)
