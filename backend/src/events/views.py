"""
Events app views and viewsets.
"""

from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters import rest_framework as filters
from django.utils import timezone

from common.viewsets import SoftDeleteModelViewSet, ReadOnlyModelViewSet
from common.permissions import IsOrganizer, IsOwner
from common.pagination import SmallPagination
from . import serializers
from .models import Event, EventStatusHistory, EventCustomField


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
        return queryset.filter(
            Q(title__icontains=value) | Q(description__icontains=value)
        )


# =============================================================================
# Organizer ViewSet
# =============================================================================

class EventViewSet(SoftDeleteModelViewSet):
    """
    Organizer-level CRUD for events.
    
    GET /api/v1/events/
    POST /api/v1/events/
    GET /api/v1/events/{uuid}/
    PATCH /api/v1/events/{uuid}/
    DELETE /api/v1/events/{uuid}/
    """
    permission_classes = [IsAuthenticated, IsOrganizer]
    filterset_class = EventFilter
    search_fields = ['title', 'description']
    ordering_fields = ['starts_at', 'created_at', 'title', 'registration_count']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Event.objects.filter(
            owner=self.request.user,
            deleted_at__isnull=True
        ).select_related('owner', 'certificate_template')
    
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
    
    @action(detail=True, methods=['post'])
    def publish(self, request, uuid=None):
        """Publish a draft event."""
        event = self.get_object()
        
        if event.status != 'draft':
            return Response(
                {'error': {'code': 'INVALID_STATE', 'message': 'Can only publish draft events.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        event.publish()
        return Response(serializers.EventDetailSerializer(event).data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, uuid=None):
        """Cancel an event."""
        event = self.get_object()
        serializer = serializers.EventStatusChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            event.cancel(
                reason=serializer.validated_data.get('reason', ''),
                cancelled_by=request.user
            )
        except ValueError as e:
            return Response(
                {'error': {'code': 'INVALID_STATE', 'message': str(e)}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(serializers.EventDetailSerializer(event).data)
    
    @action(detail=True, methods=['post'], url_path='go-live')
    def go_live(self, request, uuid=None):
        """Start the event (mark as live)."""
        event = self.get_object()
        
        try:
            event.go_live()
        except ValueError as e:
            return Response(
                {'error': {'code': 'INVALID_STATE', 'message': str(e)}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(serializers.EventDetailSerializer(event).data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, uuid=None):
        """Mark event as completed."""
        event = self.get_object()
        
        try:
            event.complete()
        except ValueError as e:
            return Response(
                {'error': {'code': 'INVALID_STATE', 'message': str(e)}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(serializers.EventDetailSerializer(event).data)
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, uuid=None):
        """Create a copy of this event."""
        event = self.get_object()
        new_event = event.duplicate()
        
        return Response(
            serializers.EventDetailSerializer(new_event).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['get'])
    def history(self, request, uuid=None):
        """Get status change history."""
        event = self.get_object()
        history = event.status_history.all().order_by('-created_at')
        serializer = serializers.EventStatusHistorySerializer(history, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get dashboard stats for organizer."""
        events = self.get_queryset()
        now = timezone.now()
        
        return Response({
            'total_events': events.count(),
            'draft': events.filter(status='draft').count(),
            'published': events.filter(status='published').count(),
            'upcoming': events.filter(status='published', starts_at__gt=now).count(),
            'live': events.filter(status='live').count(),
            'completed': events.filter(status__in=['completed', 'closed']).count(),
            'total_registrations': sum(e.registration_count for e in events),
            'total_attendees': sum(e.attendee_count for e in events),
        })


# =============================================================================
# Nested Registrations
# =============================================================================

# EventRegistrationViewSet is imported from registrations app


# =============================================================================
# Public Event Views
# =============================================================================

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
    GET /api/v1/public/events/{slug}/
    
    Public event detail by slug.
    """
    serializer_class = serializers.PublicEventDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'
    
    def get_queryset(self):
        return Event.objects.filter(
            status__in=['published', 'live'],
            is_public=True,
            deleted_at__isnull=True,
        ).select_related('owner').prefetch_related('custom_fields')


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
        return EventCustomField.objects.filter(
            event__uuid=event_uuid,
            event__owner=self.request.user
        )
    
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
