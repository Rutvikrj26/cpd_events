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
        event.update_counts()

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


class PublicRegistrationView(generics.CreateAPIView):
    """
    POST /api/v1/public/events/{event_uuid}/register/

    Public registration endpoint (authenticated or guest).
    """

    serializer_class = serializers.RegistrationCreateSerializer
    permission_classes = [AllowAny]

    def create(self, request, event_uuid=None):
        from decimal import Decimal
        from events.models import Event

        try:
            event = Event.objects.get(uuid=event_uuid, status='published', registration_enabled=True, deleted_at__isnull=True)
        except Event.DoesNotExist:
            return error_response('Event not found or registration closed.', code='NOT_FOUND', status_code=status.HTTP_404_NOT_FOUND)

        if not event.is_open_for_registration:
            return error_response('Event not found or registration closed.', code='NOT_FOUND', status_code=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user if request.user.is_authenticated else None
        email = serializer.validated_data.get('email', '').lower()
        full_name = serializer.validated_data.get('full_name', '')

        if user:
            email = user.email
            full_name = full_name or user.full_name

        # Check for existing registration (by user if authenticated, by email if guest)
        if user:
            if Registration.objects.filter(event=event, user=user, deleted_at__isnull=True).exists():
                return error_response('Already registered for this event.', code='ALREADY_REGISTERED', status_code=status.HTTP_400_BAD_REQUEST)
        else:
            if Registration.objects.filter(event=event, email__iexact=email, deleted_at__isnull=True).exists():
                return error_response('Already registered for this event.', code='ALREADY_REGISTERED', status_code=status.HTTP_400_BAD_REQUEST)

        # Check capacity
        if event.max_attendees:
            confirmed_count = event.registrations.filter(status='confirmed').count()
            if confirmed_count >= event.max_attendees:
                if event.waitlist_enabled:
                    return self._add_to_waitlist(event, user, email, full_name, serializer.validated_data)
                return error_response('Event is at capacity.', code='EVENT_FULL')

        # Handle promo code validation
        promo_code_str = serializer.validated_data.get('promo_code', '').strip()
        validated_promo_code = None
        discount_amount = Decimal('0.00')
        final_price = event.price

        if promo_code_str and not event.is_free:
            from promo_codes.services import promo_code_service, PromoCodeError

            try:
                promo_code = promo_code_service.find_code(promo_code_str, event)
                if not promo_code:
                    return error_response('Invalid promo code.', code='INVALID_PROMO_CODE', status_code=status.HTTP_400_BAD_REQUEST)

                # Validate the code
                promo_code_service.validate_code(promo_code, event, email, user)

                # Calculate discount
                discount_amount = promo_code.calculate_discount(event.price)
                final_price = max(Decimal('0.00'), event.price - discount_amount)
                validated_promo_code = promo_code

            except PromoCodeError as e:
                return error_response(str(e), code='PROMO_CODE_ERROR', status_code=status.HTTP_400_BAD_REQUEST)

        # Create registration
        registration = Registration.objects.create(
            event=event,
            user=user,
            email=email,
            full_name=full_name,
            professional_title=serializer.validated_data.get('professional_title', ''),
            organization_name=serializer.validated_data.get('organization_name', ''),
            status='confirmed',  # Default to confirmed
            allow_public_verification=serializer.validated_data.get('allow_public_verification', True),
            source=Registration.Source.SELF,
            amount_paid=final_price,
        )

        # Apply promo code if validated
        if validated_promo_code:
            from promo_codes.services import promo_code_service
            promo_code_service.apply_code(validated_promo_code, registration, event.price)

        # Handle Payment if final price > 0
        client_secret = None
        payment_intent_id = None

        if final_price > 0:
            from billing.services import stripe_payment_service

            registration.payment_status = Registration.PaymentStatus.PENDING
            registration.save()

            if stripe_payment_service.is_configured:
                intent_data = stripe_payment_service.create_payment_intent(registration, amount_cents=int(final_price * 100))
                if intent_data['success']:
                    client_secret = intent_data['client_secret']
                    payment_intent_id = intent_data['payment_intent_id']

                    registration.payment_intent_id = payment_intent_id
                    registration.save(update_fields=['payment_intent_id'])
                else:
                    registration.delete()
                    return Response({'error': intent_data['error']}, status=status.HTTP_400_BAD_REQUEST)
            else:
                registration.delete()
                return Response({'error': 'Payment system not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        elif not event.is_free:
            # Event has a price but final_price is 0 (100% discount)
            registration.payment_status = Registration.PaymentStatus.NA
            registration.save(update_fields=['payment_status'])

        # Save Custom Field Responses
        custom_responses = serializer.validated_data.get('custom_field_responses', {})
        if custom_responses:
            from registrations.models import CustomFieldResponse
            import json
            
            # Helper to safely serialize list/dict
            def serialize_val(v):
                if isinstance(v, (dict, list)):
                    return json.dumps(v)
                return str(v)

            # Get valid field UUIDs for this event
            valid_fields = {str(f.uuid): f for f in event.custom_fields.all()}
            
            for field_uuid, value in custom_responses.items():
                field_obj = valid_fields.get(field_uuid)
                if field_obj:
                    CustomFieldResponse.objects.create(
                        registration=registration,
                        field=field_obj,
                        value=serialize_val(value)
                    )

        # Update event counts
        event.update_counts()

        response_data = {
            'registration_uuid': str(registration.uuid),
            'status': registration.status,
            'payment_status': registration.payment_status if hasattr(registration, 'payment_status') else 'na',
            'message': 'Successfully registered!',
        }

        # Add discount info if promo code was applied
        if validated_promo_code:
            response_data['promo_code'] = validated_promo_code.code
            response_data['original_price'] = str(event.price)
            response_data['discount_amount'] = str(discount_amount)
            response_data['final_price'] = str(final_price)

        if client_secret:
            response_data['client_secret'] = client_secret
            response_data['message'] = 'Payment required to complete registration.'

        return Response(
            response_data,
            status=status.HTTP_201_CREATED,
        )

    def _add_to_waitlist(self, event, user, email, full_name, data):
        """Add to waitlist when event is full."""
        max_position = (
            Registration.objects.filter(event=event, status='waitlisted').aggregate(Max('waitlist_position'))[
                'waitlist_position__max'
            ]
            or 0
        )

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

        # Save Custom Field Responses
        custom_responses = data.get('custom_field_responses', {})
        if custom_responses:
            from registrations.models import CustomFieldResponse
            import json
            
            # Helper to safely serialize list/dict
            def serialize_val(v):
                if isinstance(v, (dict, list)):
                    return json.dumps(v)
                return str(v)

            # Get valid field UUIDs for this event
            valid_fields = {str(f.uuid): f for f in event.custom_fields.all()}
            
            for field_uuid, value in custom_responses.items():
                field_obj = valid_fields.get(field_uuid)
                if field_obj:
                    CustomFieldResponse.objects.create(
                        registration=registration,
                        field=field_obj,
                        value=serialize_val(value)
                    )

        return Response(
            {
                'registration_uuid': str(registration.uuid),
                'status': 'waitlisted',
                'waitlist_position': registration.waitlist_position,
                'message': 'Added to waitlist.',
            },
            status=status.HTTP_201_CREATED,
        )


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


class LinkRegistrationsView(generics.GenericAPIView):
    """
    POST /api/v1/users/me/link-registrations/

    Find and link orphaned guest registrations to the current user.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        count = Registration.link_registrations_for_user(request.user)

        return Response({'linked_count': count, 'message': f'Linked {count} registration(s) to your account.'})
