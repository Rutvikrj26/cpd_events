"""
Registrations app views and viewsets.
"""

from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters import rest_framework as filters
from django.db.models import Max

from common.viewsets import SoftDeleteModelViewSet, ReadOnlyModelViewSet
from common.permissions import IsOrganizer, IsEventOwner, IsRegistrant
from common.pagination import SmallPagination
from . import serializers
from .models import Registration, AttendanceRecord


# =============================================================================
# Filters
# =============================================================================

class RegistrationFilter(filters.FilterSet):
    """Filter registrations."""
    status = filters.ChoiceFilter(choices=Registration.Status.choices)
    attended = filters.BooleanFilter()
    certificate_issued = filters.BooleanFilter()
    attendance_eligible = filters.BooleanFilter()
    registered_after = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    registered_before = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = Registration
        fields = ['status', 'attended', 'certificate_issued', 'attendance_eligible']


# =============================================================================
# Organizer ViewSets
# =============================================================================

class EventRegistrationViewSet(SoftDeleteModelViewSet):
    """
    Manage registrations for an event (organizer view).
    
    Nested under events: /api/v1/events/{event_uuid}/registrations/
    """
    permission_classes = [IsAuthenticated, IsOrganizer]
    filterset_class = RegistrationFilter
    search_fields = ['email', 'full_name', 'user__email', 'user__full_name']
    ordering_fields = ['created_at', 'status', 'attended', 'full_name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        event_uuid = self.kwargs.get('event_uuid')
        return Registration.objects.filter(
            event__uuid=event_uuid,
            event__owner=self.request.user,
            deleted_at__isnull=True
        ).select_related('user', 'event').prefetch_related(
            'attendance_records', 'custom_field_responses'
        )
    
    def get_serializer_class(self):
        if self.action == 'create':
            return serializers.RegistrationBulkCreateSerializer
        if self.action in ['update', 'partial_update']:
            return serializers.AttendanceUpdateSerializer
        if self.action == 'list':
            return serializers.RegistrationListSerializer
        return serializers.RegistrationDetailSerializer
    
    def create(self, request, *args, **kwargs):
        """Bulk add registrations."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        event_uuid = self.kwargs.get('event_uuid')
        from events.models import Event
        
        try:
            event = Event.objects.get(uuid=event_uuid, owner=request.user)
        except Event.DoesNotExist:
            return Response(
                {'error': {'code': 'NOT_FOUND', 'message': 'Event not found.'}},
                status=status.HTTP_404_NOT_FOUND
            )
        
        created = []
        skipped = []
        
        for reg_data in serializer.validated_data['registrations']:
            email = reg_data['email'].lower()
            full_name = reg_data.get('full_name', reg_data.get('name', ''))
            
            # Check if already registered
            if Registration.objects.filter(event=event, email__iexact=email).exists():
                skipped.append(email)
                continue
            
            # Find user or create guest registration
            from accounts.models import User
            user = User.objects.filter(email__iexact=email).first()
            
            reg = Registration.objects.create(
                event=event,
                user=user,
                email=email,
                full_name=full_name if not user else user.full_name,
                professional_title=reg_data.get('professional_title', ''),
                organization_name=reg_data.get('organization_name', ''),
                status='confirmed',
                source=Registration.Source.MANUAL,
                registered_by=request.user,
            )
            created.append(reg)
        
        # Update event counts
        event.update_counts()
        
        return Response({
            'created': len(created),
            'skipped': len(skipped),
            'skipped_emails': skipped,
        }, status=status.HTTP_201_CREATED)
    
    def partial_update(self, request, *args, **kwargs):
        """Update attendance for single registration."""
        instance = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        instance.attended = serializer.validated_data['attended']
        if 'attendance_eligible' in serializer.validated_data:
            instance.attendance_eligible = serializer.validated_data['attendance_eligible']
        instance.save()
        
        return Response(serializers.RegistrationDetailSerializer(instance).data)
    
    @action(detail=False, methods=['get'])
    def waitlist(self, request, event_uuid=None):
        """Get waitlist registrations."""
        waitlisted = self.get_queryset().filter(
            status='waitlisted'
        ).order_by('waitlist_position')
        
        serializer = serializers.RegistrationListSerializer(waitlisted, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def promote(self, request, event_uuid=None, uuid=None):
        """Promote a waitlisted registration to confirmed."""
        registration = self.get_object()
        
        if registration.status != 'waitlisted':
            return Response(
                {'error': {'code': 'NOT_WAITLISTED', 'message': 'Registration is not waitlisted.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        registration.promote_from_waitlist()
        return Response(serializers.RegistrationDetailSerializer(registration).data)
    
    @action(detail=False, methods=['post'], url_path='promote-next')
    def promote_next(self, request, event_uuid=None):
        """Promote next person in waitlist."""
        next_in_line = self.get_queryset().filter(
            status='waitlisted'
        ).order_by('waitlist_position').first()
        
        if not next_in_line:
            return Response(
                {'error': {'code': 'EMPTY_WAITLIST', 'message': 'No one on waitlist.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        next_in_line.promote_from_waitlist()
        return Response(serializers.RegistrationDetailSerializer(next_in_line).data)
    
    @action(detail=True, methods=['post'], url_path='override-attendance')
    def override_attendance(self, request, event_uuid=None, uuid=None):
        """Override attendance eligibility for a registration."""
        registration = self.get_object()
        serializer = serializers.AttendanceOverrideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        registration.set_attendance_override(
            eligible=serializer.validated_data['eligible'],
            user=request.user,
            reason=serializer.validated_data['reason']
        )
        
        return Response(serializers.RegistrationDetailSerializer(registration).data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request, event_uuid=None):
        """Get registration summary stats."""
        qs = self.get_queryset()
        
        return Response({
            'total': qs.count(),
            'confirmed': qs.filter(status='confirmed').count(),
            'waitlisted': qs.filter(status='waitlisted').count(),
            'cancelled': qs.filter(status='cancelled').count(),
            'attended': qs.filter(attended=True).count(),
            'attendance_eligible': qs.filter(attendance_eligible=True).count(),
            'certificate_issued': qs.filter(certificate_issued=True).count(),
        })


# =============================================================================
# Public Registration
# =============================================================================

class PublicRegistrationView(generics.CreateAPIView):
    """
    POST /api/v1/public/events/{event_uuid}/register/
    
    Public registration endpoint (authenticated or guest).
    """
    serializer_class = serializers.RegistrationCreateSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, event_uuid=None):
        from events.models import Event
        
        try:
            event = Event.objects.get(
                uuid=event_uuid,
                status='published',
                registration_enabled=True,
                deleted_at__isnull=True
            )
        except Event.DoesNotExist:
            return Response(
                {'error': {'code': 'NOT_FOUND', 'message': 'Event not found or registration closed.'}},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user if request.user.is_authenticated else None
        email = serializer.validated_data.get('email', '').lower()
        full_name = serializer.validated_data.get('full_name', '')
        
        # Use user's info if authenticated
        if user:
            email = user.email
            full_name = full_name or user.full_name
        
        # Check for existing registration
        if Registration.objects.filter(event=event, email__iexact=email).exists():
            return Response(
                {'error': {'code': 'ALREADY_REGISTERED', 'message': 'Already registered for this event.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check capacity
        if event.capacity:
            confirmed_count = event.registrations.filter(status='confirmed').count()
            if confirmed_count >= event.capacity:
                if event.waitlist_enabled:
                    return self._add_to_waitlist(event, user, email, full_name, serializer.validated_data)
                else:
                    return Response(
                        {'error': {'code': 'EVENT_FULL', 'message': 'Event is at capacity.'}},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        
        # Create registration
        registration = Registration.objects.create(
            event=event,
            user=user,
            email=email,
            full_name=full_name,
            professional_title=serializer.validated_data.get('professional_title', ''),
            organization_name=serializer.validated_data.get('organization_name', ''),
            status='confirmed',
            allow_public_verification=serializer.validated_data.get('allow_public_verification', True),
            source=Registration.Source.SELF,
        )
        
        # Update event counts
        event.update_counts()
        
        return Response({
            'registration_uuid': str(registration.uuid),
            'status': registration.status,
            'message': 'Successfully registered!',
        }, status=status.HTTP_201_CREATED)
    
    def _add_to_waitlist(self, event, user, email, full_name, data):
        """Add to waitlist when event is full."""
        max_position = Registration.objects.filter(
            event=event, status='waitlisted'
        ).aggregate(Max('waitlist_position'))['waitlist_position__max'] or 0
        
        registration = Registration.objects.create(
            event=event,
            user=user,
            email=email,
            full_name=full_name,
            professional_title=data.get('professional_title', ''),
            organization_name=data.get('organization_name', ''),
            status='waitlisted',
            waitlist_position=max_position + 1,
            allow_public_verification=data.get('allow_public_verification', True),
            source=Registration.Source.SELF,
        )
        
        return Response({
            'registration_uuid': str(registration.uuid),
            'status': 'waitlisted',
            'waitlist_position': registration.waitlist_position,
            'message': 'Added to waitlist.',
        }, status=status.HTTP_201_CREATED)


# =============================================================================
# Attendee ViewSet
# =============================================================================

class MyRegistrationViewSet(ReadOnlyModelViewSet):
    """
    Current user's registrations.
    
    GET /api/v1/users/me/registrations/
    GET /api/v1/users/me/registrations/{uuid}/
    POST /api/v1/users/me/registrations/{uuid}/cancel/
    """
    serializer_class = serializers.MyRegistrationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Registration.objects.filter(
            user=self.request.user,
            deleted_at__isnull=True
        ).select_related('event', 'event__owner')
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, uuid=None):
        """Cancel a registration."""
        registration = self.get_object()
        
        if registration.status == 'cancelled':
            return Response(
                {'error': {'code': 'ALREADY_CANCELLED', 'message': 'Already cancelled.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if registration.event.status in ['live', 'completed', 'closed']:
            return Response(
                {'error': {'code': 'CANNOT_CANCEL', 'message': 'Cannot cancel after event has started.'}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = serializers.RegistrationCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        registration.cancel(reason=serializer.validated_data.get('reason', 'User requested cancellation'))
        
        return Response({'message': 'Registration cancelled.'})


# =============================================================================
# Guest Registration Linking
# =============================================================================

class LinkRegistrationsView(generics.GenericAPIView):
    """
    POST /api/v1/users/me/link-registrations/
    
    Find and link orphaned guest registrations to the current user.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        count = Registration.link_registrations_for_user(request.user)
        
        return Response({
            'linked_count': count,
            'message': f'Linked {count} registration(s) to your account.'
        })
