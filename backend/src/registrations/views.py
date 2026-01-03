"""
Registrations app views and viewsets.
"""

from django.db.models import Max
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import generics, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from common.pagination import SmallPagination
from common.permissions import IsOrganizer
from common.rbac import roles
from common.utils import error_response
from common.viewsets import ReadOnlyModelViewSet, SoftDeleteModelViewSet

from . import serializers
from .models import Registration

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


@roles('organizer', 'admin', route_name='event_registrations')
class EventRegistrationViewSet(SoftDeleteModelViewSet):
    """
    Manage registrations for an event (organizer view).

    Nested under events: /api/v1/events/{event_uuid}/registrations/
    """

    permission_classes = [IsAuthenticated, IsOrganizer]
    pagination_class = SmallPagination  # M5: Nested resource pagination
    filterset_class = RegistrationFilter
    search_fields = ['email', 'full_name', 'user__email', 'user__full_name']
    ordering_fields = ['created_at', 'status', 'attended', 'full_name']
    ordering = ['-created_at']

    def get_queryset(self):
        event_uuid = self.kwargs.get('event_uuid')
        return (
            Registration.objects.filter(event__uuid=event_uuid, event__owner=self.request.user, deleted_at__isnull=True)
            .select_related('user', 'event')
            .prefetch_related('attendance_records', 'custom_field_responses')
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
            event = Event.objects.get(uuid=event_uuid, owner=self.request.user)
        except Event.DoesNotExist:
            return error_response('Event not found.', code='NOT_FOUND', status_code=status.HTTP_404_NOT_FOUND)

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
        # Update event counts handled by signals


        return Response(
            {
                'created': len(created),
                'skipped': len(skipped),
                'skipped_emails': skipped,
            },
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        """Update attendance for single registration."""
        instance = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data['attended']:
            instance.attended = True
            if not instance.check_in_time:
                instance.check_in_time = timezone.now()
        else:
            instance.attended = False
            instance.check_in_time = None  # Clear check-in time when marked absent
        
        if 'attendance_eligible' in serializer.validated_data:
            instance.attendance_eligible = serializer.validated_data['attendance_eligible']
        instance.save()

        return Response(serializers.RegistrationDetailSerializer(instance).data)

    @swagger_auto_schema(
        operation_summary="Get waitlist",
        operation_description="Get all waitlisted registrations for this event.",
        responses={200: serializers.RegistrationListSerializer(many=True)},
    )
    @action(detail=False, methods=['get'])
    def waitlist(self, request, event_uuid=None):
        """Get waitlist registrations."""
        waitlisted = self.get_queryset().filter(status='waitlisted').order_by('waitlist_position')

        serializer = serializers.RegistrationListSerializer(waitlisted, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Promote registration",
        operation_description="Promote a waitlisted registration to confirmed status.",
        responses={200: serializers.RegistrationDetailSerializer, 400: '{"error": {"code": "NOT_WAITLISTED"}}'},
    )
    @action(detail=True, methods=['post'])
    def promote(self, request, event_uuid=None, uuid=None):
        """Promote a waitlisted registration to confirmed."""
        registration = self.get_object()

        if registration.status != 'waitlisted':
            return error_response('Registration is not waitlisted.', code='NOT_WAITLISTED')

        registration.promote_from_waitlist()
        return Response(serializers.RegistrationDetailSerializer(registration).data)

    @swagger_auto_schema(
        operation_summary="Promote next waitlisted",
        operation_description="Promote the next person in the waitlist to confirmed status.",
        responses={200: serializers.RegistrationDetailSerializer, 400: '{"error": {"code": "EMPTY_WAITLIST"}}'},
    )
    @action(detail=False, methods=['post'], url_path='promote-next')
    def promote_next(self, request, event_uuid=None):
        """Promote next person in waitlist."""
        next_in_line = self.get_queryset().filter(status='waitlisted').order_by('waitlist_position').first()

        if not next_in_line:
            return error_response('No one on waitlist.', code='EMPTY_WAITLIST')

        next_in_line.promote_from_waitlist()
        return Response(serializers.RegistrationDetailSerializer(next_in_line).data)

    @swagger_auto_schema(
        operation_summary="Override attendance",
        operation_description="Override attendance eligibility for a registration.",
        request_body=serializers.AttendanceOverrideSerializer,
        responses={200: serializers.RegistrationDetailSerializer},
    )
    @action(detail=True, methods=['post'], url_path='override-attendance')
    def override_attendance(self, request, event_uuid=None, uuid=None):
        """Override attendance eligibility for a registration."""
        registration = self.get_object()
        serializer = serializers.AttendanceOverrideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        registration.set_attendance_override(
            eligible=serializer.validated_data['eligible'], user=request.user, reason=serializer.validated_data['reason']
        )

        return Response(serializers.RegistrationDetailSerializer(registration).data)

    @swagger_auto_schema(
        operation_summary="Registration summary",
        operation_description="Get aggregate statistics for event registrations.",
    )
    @action(detail=False, methods=['get'])
    def summary(self, request, event_uuid=None):
        """Get registration summary stats."""
        qs = self.get_queryset()

        return Response(
            {
                'total': qs.count(),
                'confirmed': qs.filter(status='confirmed').count(),
                'waitlisted': qs.filter(status='waitlisted').count(),
                'cancelled': qs.filter(status='cancelled').count(),
                'attended': qs.filter(attended=True).count(),
                'attendance_eligible': qs.filter(attendance_eligible=True).count(),
                'certificate_issued': qs.filter(certificate_issued=True).count(),
            }
        )


# =============================================================================
# Public Registration
# =============================================================================


@roles('public', route_name='public_registration')
class PublicRegistrationView(generics.CreateAPIView):
    """
    POST /api/v1/public/events/{event_uuid}/register/

    Public registration endpoint (authenticated or guest).
    """

    serializer_class = serializers.RegistrationCreateSerializer
    permission_classes = [AllowAny]

    def create(self, request, event_uuid=None):
        from events.models import Event
        from .services import registration_service
        from rest_framework.exceptions import ValidationError
        import logging

        logger = logging.getLogger(__name__)

        try:
            event = Event.objects.get(uuid=event_uuid, status='published', registration_enabled=True, deleted_at__isnull=True)
        except Event.DoesNotExist:
            return error_response('Event not found or registration closed.', code='NOT_FOUND', status_code=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user if request.user.is_authenticated else None

        try:
            result = registration_service.register_participant(
                event=event, 
                data=serializer.validated_data, 
                user=user
            )

            # Map service result to API response
            reg = result['registration']
            response_data = {
                'registration_uuid': str(reg.uuid),
                'status': result['status'],
                'client_secret': result.get('client_secret'),
                'waitlist_position': getattr(reg, 'waitlist_position', None),
                'message': result.get('message', 'Registration successful.'),
            }
            return Response(response_data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            # Map validation errors to error codes
            msg = str(e.detail[0]) if isinstance(e.detail, list) else str(e)
            
            error_code = 'VALIDATION_ERROR'
            if 'capacity' in msg.lower():
                error_code = 'EVENT_FULL'
            elif 'already registered' in msg.lower():
                error_code = 'ALREADY_REGISTERED'
            
            return error_response(msg, code=error_code, status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Registration failed")
            return error_response("An unexpected error occurred.", code='INTERNAL_ERROR', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@roles('public', route_name='confirm_payment')
class ConfirmPaymentView(generics.GenericAPIView):
    """
    POST /api/v1/public/registrations/{uuid}/confirm-payment/

    Called by frontend after Stripe.js payment confirmation.
    Synchronously verifies payment status with Stripe and updates registration.
    """

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Confirm registration payment",
        operation_description="Synchronously confirms payment status with Stripe after frontend payment completion.",
        responses={
            200: '{"status": "paid", "registration_uuid": "...", "amount_paid": 99.00}',
            400: '{"error": {"code": "...", "message": "..."}}',
            404: '{"error": {"code": "NOT_FOUND", "message": "Registration not found"}}'
        },
    )
    def post(self, request, uuid=None):
        from .services import payment_confirmation_service

        # Get registration
        try:
            registration = Registration.objects.get(uuid=uuid, deleted_at__isnull=True)
        except Registration.DoesNotExist:
            return error_response('Registration not found.', code='NOT_FOUND', status_code=status.HTTP_404_NOT_FOUND)

        # Check if already paid (idempotent)
        if registration.payment_status == Registration.PaymentStatus.PAID:
            return Response({
                'status': 'paid',
                'registration_uuid': str(registration.uuid),
                'amount_paid': float(registration.amount_paid),
                'message': 'Payment already confirmed.'
            })

        # Check if payment is expected
        if registration.payment_status == Registration.PaymentStatus.NA:
            return error_response('This registration does not require payment.', code='NO_PAYMENT_REQUIRED')

        # Confirm payment with Stripe
        result = payment_confirmation_service.confirm_registration_payment(registration)

        if result['status'] == 'paid':
            return Response(result, status=status.HTTP_200_OK)
        elif result['status'] == 'processing':
            return Response(result, status=status.HTTP_202_ACCEPTED)
        elif result['status'] == 'failed':
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        else:
            return error_response(result.get('message', 'Payment confirmation failed'), code='PAYMENT_ERROR')


# =============================================================================
# Attendee ViewSet
# =============================================================================


@roles('attendee', 'organizer', 'admin', route_name='registrations')
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
        return Registration.objects.filter(user=self.request.user, deleted_at__isnull=True).select_related(
            'event', 'event__owner'
        )

    @swagger_auto_schema(
        operation_summary="Cancel registration",
        operation_description="Cancel your registration for an event.",
        request_body=serializers.RegistrationCancelSerializer,
        responses={200: '{"message": "Registration cancelled."}', 400: '{"error": {}}'},
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, uuid=None):
        """Cancel a registration."""
        registration = self.get_object()

        if registration.status == 'cancelled':
            return error_response('Already cancelled.', code='ALREADY_CANCELLED')

        if registration.event.status in ['live', 'completed', 'closed']:
            return error_response('Cannot cancel after event has started.', code='CANNOT_CANCEL')

        serializer = serializers.RegistrationCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        registration.cancel(reason=serializer.validated_data.get('reason', 'User requested cancellation'))

        return Response({'message': 'Registration cancelled.'})


# =============================================================================
# Guest Registration Linking
# =============================================================================


@roles('attendee', 'organizer', 'admin', route_name='link_registrations')
class LinkRegistrationsView(generics.GenericAPIView):
    """
    POST /api/v1/users/me/link-registrations/

    Find and link orphaned guest registrations to the current user.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        count = Registration.link_registrations_for_user(request.user)

        return Response({'linked_count': count, 'message': f'Linked {count} registration(s) to your account.'})
