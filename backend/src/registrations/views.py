"""
Registrations app views and viewsets.
"""

import logging
from decimal import Decimal

from django.utils import timezone
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from common.pagination import SmallPagination
from common.permissions import IsOrganizer
from common.rbac import roles
from common.utils import error_response
from common.viewsets import ReadOnlyModelViewSet, SoftDeleteModelViewSet

from . import serializers
from .models import Registration

logger = logging.getLogger(__name__)

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

    @swagger_auto_schema(
        operation_summary="Cancel registration",
        operation_description="Cancel an unpaid registration for this event.",
        request_body=serializers.RegistrationCancelSerializer,
        responses={200: serializers.RegistrationDetailSerializer, 400: '{"error": {"code": "CANNOT_CANCEL"}}'},
    )
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_registration(self, request, event_uuid=None, uuid=None):
        """Cancel a registration without refund (unpaid only)."""
        registration = self.get_object()
        serializer = serializers.RegistrationCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if registration.status == Registration.Status.CANCELLED:
            return error_response('Already cancelled.', code='ALREADY_CANCELLED')
        if registration.payment_status == Registration.PaymentStatus.PAID:
            return error_response('Paid registrations must be refunded.', code='PAID_REGISTRATION')
        if registration.payment_status == Registration.PaymentStatus.REFUNDED:
            return error_response('Registration already refunded.', code='ALREADY_REFUNDED')

        reason = serializer.validated_data.get('reason', 'Organizer cancelled registration')
        registration.cancel(reason=reason, cancelled_by=request.user)
        try:
            from promo_codes.models import PromoCodeUsage

            PromoCodeUsage.release_for_registration(registration)
        except Exception as e:
            logger.warning("Failed to release promo code usage for %s: %s", registration.uuid, e)

        return Response(serializers.RegistrationDetailSerializer(registration).data)

    @swagger_auto_schema(
        operation_summary="Refund registration",
        operation_description="Refund a paid registration and cancel the attendee.",
        request_body=serializers.RegistrationRefundSerializer,
        responses={200: serializers.RegistrationDetailSerializer, 400: '{"error": {"code": "NOT_PAID"}}'},
    )
    @action(detail=True, methods=['post'], url_path='refund')
    def refund_registration(self, request, event_uuid=None, uuid=None):
        """Refund a registration (paid only)."""
        from billing.services import stripe_payment_service

        registration = self.get_object()
        serializer = serializers.RegistrationRefundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if registration.payment_status == Registration.PaymentStatus.REFUNDED:
            return error_response('Registration already refunded.', code='ALREADY_REFUNDED')
        if registration.payment_status != Registration.PaymentStatus.PAID or registration.amount_paid <= 0:
            return error_response('Registration is not paid.', code='NOT_PAID')
        if not registration.payment_intent_id:
            return error_response('No payment intent found for this registration.', code='NO_PAYMENT_INTENT')

        refund_result = stripe_payment_service.refund_payment_intent(
            registration.payment_intent_id,
            registration=registration,
        )
        if not refund_result['success']:
            return error_response(refund_result['error'], code='REFUND_FAILED')

        reason = serializer.validated_data.get('reason', 'Organizer refunded registration')

        if registration.status != Registration.Status.CANCELLED:
            registration.cancel(reason=reason, cancelled_by=request.user)
        elif reason and not registration.cancellation_reason:
            registration.cancellation_reason = reason
            registration.save(update_fields=['cancellation_reason', 'updated_at'])

        registration.payment_status = Registration.PaymentStatus.REFUNDED
        registration.save(update_fields=['payment_status', 'updated_at'])
        try:
            from promo_codes.models import PromoCodeUsage

            PromoCodeUsage.release_for_registration(registration)
        except Exception as e:
            logger.warning("Failed to release promo code usage for %s: %s", registration.uuid, e)

        return Response(serializers.RegistrationDetailSerializer(registration).data)

    @swagger_auto_schema(
        operation_summary="Add to contacts",
        operation_description="Add this registrant to the organizer's contact list.",
        responses={200: '{"message": "Contact added.", "contact_uuid": "..."}', 400: '{"error": {}}'},
    )
    @action(detail=True, methods=['post'], url_path='add-to-contacts')
    def add_to_contacts(self, request, event_uuid=None, uuid=None):
        """Add registrant to organizer's contacts."""
        from django.utils import timezone

        from contacts.models import Contact, ContactList

        registration = self.get_object()
        organizer = request.user

        # Get target list from request or use default
        list_uuid = request.data.get('list_uuid')
        if list_uuid:
            try:
                target_list = ContactList.objects.get(uuid=list_uuid, owner=organizer)
            except ContactList.DoesNotExist:
                return error_response('Contact list not found.', code='LIST_NOT_FOUND', status_code=status.HTTP_404_NOT_FOUND)
        else:
            # Get or create default list
            target_list = ContactList.objects.filter(owner=organizer, is_default=True).first()
            if not target_list:
                target_list = ContactList.objects.filter(owner=organizer).first()
            if not target_list:
                target_list = ContactList.objects.create(owner=organizer, name="Default", is_default=True)

        # Check if contact already exists
        existing = Contact.objects.filter(contact_list__owner=organizer, email__iexact=registration.email).first()

        if existing:
            return Response(
                {
                    'message': 'Contact already exists.',
                    'contact_uuid': str(existing.uuid),
                }
            )

        # Create new contact
        contact = Contact.objects.create(
            contact_list=target_list,
            email=registration.email,
            full_name=registration.full_name,
            professional_title=registration.professional_title or '',
            organization_name=registration.organization_name or '',
            user=registration.user,
            source='registration',
            added_from_event=registration.event,
            events_invited_count=1,
            last_invited_at=timezone.now(),
        )
        target_list.update_contact_count()

        return Response(
            {
                'message': 'Contact added.',
                'contact_uuid': str(contact.uuid),
            },
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary="List unmatched attendance",
        operation_description="Get Zoom attendance records not matched to any registration.",
        responses={200: serializers.UnmatchedAttendanceRecordSerializer(many=True)},
    )
    @action(detail=False, methods=['get'], url_path='unmatched-attendance')
    def unmatched_attendance(self, request, event_uuid=None):
        """Get unmatched Zoom attendance records for reconciliation."""
        from events.models import Event

        from .models import AttendanceRecord

        try:
            event = Event.objects.get(uuid=event_uuid, owner=request.user)
        except Event.DoesNotExist:
            return error_response('Event not found.', code='NOT_FOUND', status_code=status.HTTP_404_NOT_FOUND)

        unmatched = AttendanceRecord.objects.filter(
            event=event,
            is_matched=False,
        ).order_by('-join_time')

        # Paginate results
        page = self.paginate_queryset(unmatched)
        if page is not None:
            serializer = serializers.UnmatchedAttendanceRecordSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = serializers.UnmatchedAttendanceRecordSerializer(unmatched, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Match attendance to registration",
        operation_description="Manually match an unmatched Zoom attendance record to a registration.",
        request_body=serializers.AttendanceMatchSerializer,
        responses={
            200: serializers.AttendanceRecordSerializer,
            400: '{"error": {}}',
            404: '{"error": {"code": "NOT_FOUND"}}',
        },
    )
    @action(detail=False, methods=['post'], url_path='match-attendance/(?P<record_uuid>[^/.]+)')
    def match_attendance(self, request, event_uuid=None, record_uuid=None):
        """Match unmatched Zoom attendance record to a registration."""
        from events.models import Event

        from .models import AttendanceRecord

        try:
            event = Event.objects.get(uuid=event_uuid, owner=request.user)
        except Event.DoesNotExist:
            return error_response('Event not found.', code='NOT_FOUND', status_code=status.HTTP_404_NOT_FOUND)

        try:
            record = AttendanceRecord.objects.get(uuid=record_uuid, event=event)
        except AttendanceRecord.DoesNotExist:
            return error_response('Attendance record not found.', code='NOT_FOUND', status_code=status.HTTP_404_NOT_FOUND)

        if record.is_matched:
            return error_response('Record already matched.', code='ALREADY_MATCHED')

        serializer = serializers.AttendanceMatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            registration = Registration.objects.get(
                uuid=serializer.validated_data['registration_uuid'],
                event=event,
                deleted_at__isnull=True,
            )
        except Registration.DoesNotExist:
            return error_response('Registration not found.', code='REGISTRATION_NOT_FOUND')

        # Perform the match
        record.registration = registration
        record.is_matched = True
        record.matched_at = timezone.now()
        record.matched_manually = True
        record.matched_by = request.user
        record.save(update_fields=[
            'registration', 'is_matched', 'matched_at', 'matched_manually', 'matched_by', 'updated_at'
        ])

        # Update registration attendance summary
        registration.update_attendance_summary()

        logger.info(f"Manual match: Record {record_uuid} -> Registration {registration.uuid} by {request.user.email}")

        return Response(serializers.AttendanceRecordSerializer(record).data)


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
        import logging

        from rest_framework.exceptions import ValidationError

        from events.models import Event

        from .services import registration_service

        logger = logging.getLogger(__name__)

        try:
            event = Event.objects.get(uuid=event_uuid, status='published', registration_enabled=True, deleted_at__isnull=True)
        except Event.DoesNotExist:
            return error_response(
                'Event not found or registration closed.', code='NOT_FOUND', status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user if request.user.is_authenticated else None

        try:
            result = registration_service.register_participant(event=event, data=serializer.validated_data, user=user)

            # Map service result to API response
            reg = result['registration']
            stripe_account_id = None
            if result.get('client_secret'):
                stripe_account_id = None

            response_data = {
                'registration_uuid': str(reg.uuid),
                'uuid': str(reg.uuid),
                'status': result['status'],
                'client_secret': result.get('client_secret'),
                'requires_payment': result.get('requires_payment', bool(result.get('client_secret'))),
                'amount': float(reg.total_amount) if reg.total_amount else None,
                'ticket_price': float(reg.amount_paid) if reg.amount_paid else None,
                'platform_fee': float(reg.platform_fee_amount) if reg.platform_fee_amount else None,
                'service_fee': float(reg.service_fee_amount) if reg.service_fee_amount else None,
                'processing_fee': float(reg.processing_fee_amount) if reg.processing_fee_amount else None,
                'tax_amount': float(reg.tax_amount) if reg.tax_amount else None,
                'total_amount': float(reg.total_amount) if reg.total_amount else None,
                'currency': event.currency,  # Use event's currency setting
                'stripe_account_id': stripe_account_id,
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
        except Exception:
            logger.exception("Registration failed")
            return error_response(
                "An unexpected error occurred.", code='INTERNAL_ERROR', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@roles('public', route_name='payment_intent')
class RegistrationPaymentIntentView(generics.GenericAPIView):
    """
    POST /api/v1/public/registrations/{uuid}/payment-intent/

    Returns a client_secret for completing payment on a pending registration.
    Performs a capacity check before allowing payment.
    """

    permission_classes = [AllowAny]

    def post(self, request, uuid=None):
        from billing.services import stripe_payment_service

        try:
            registration = Registration.objects.select_related('event').get(uuid=uuid, deleted_at__isnull=True)
        except Registration.DoesNotExist:
            return error_response('Registration not found.', code='NOT_FOUND', status_code=status.HTTP_404_NOT_FOUND)

        if registration.status == Registration.Status.WAITLISTED:
            return error_response('Registration is waitlisted.', code='WAITLISTED')

        if registration.status == Registration.Status.CANCELLED:
            return error_response('Registration is cancelled.', code='CANCELLED')

        if registration.payment_status == Registration.PaymentStatus.PAID:
            return error_response('Payment already completed.', code='ALREADY_PAID')

        if registration.status != Registration.Status.PENDING:
            return error_response('Registration does not require payment.', code='NO_PAYMENT_REQUIRED')

        event = registration.event
        if registration.amount_paid <= 0:
            return error_response('Registration does not require payment.', code='NO_PAYMENT_REQUIRED')
        confirmed_count = Registration.objects.filter(
            event=event,
            status=Registration.Status.CONFIRMED,
            deleted_at__isnull=True,
        ).count()
        if event.max_attendees and confirmed_count >= event.max_attendees:
            return error_response('Event is fully booked.', code='EVENT_FULL', status_code=status.HTTP_409_CONFLICT)

        if not stripe_payment_service.is_configured:
            return error_response('Payment system not configured.', code='PAYMENT_NOT_CONFIGURED')

        payee_account_id = stripe_payment_service.get_payee_account_id(event)
        if not payee_account_id:
            return error_response('Organizer payment setup incomplete.', code='PAYMENT_NOT_CONFIGURED')

        # Reuse existing payment intent if still valid
        if registration.payment_intent_id:
            intent = stripe_payment_service.retrieve_payment_intent(registration.payment_intent_id)
            if intent and intent.status == 'succeeded':
                return error_response('Payment already completed.', code='ALREADY_PAID')
            if intent and intent.status in ['requires_payment_method', 'requires_confirmation', 'requires_action']:
                return Response(
                    {
                        'registration_uuid': str(registration.uuid),
                        'uuid': str(registration.uuid),
                        'client_secret': intent.client_secret,
                        'amount': float(registration.total_amount),
                        'ticket_price': float(registration.amount_paid),
                        'platform_fee': float(registration.platform_fee_amount),
                        'service_fee': float(registration.service_fee_amount),
                        'processing_fee': float(registration.processing_fee_amount),
                        'tax_amount': float(registration.tax_amount),
                        'total_amount': float(registration.total_amount),
                        'currency': event.currency,
                        'requires_payment': True,
                        'status': registration.status,
                        'stripe_account_id': None,
                    },
                    status=status.HTTP_200_OK,
                )

        billing_country = (request.data.get('billing_country') or request.data.get('billingCountry') or '').upper().strip()
        billing_state = (request.data.get('billing_state') or request.data.get('billingState') or '').strip()
        billing_postal_code = (request.data.get('billing_postal_code') or request.data.get('billingPostalCode') or '').strip()
        billing_city = (request.data.get('billing_city') or request.data.get('billingCity') or '').strip()
        updated_fields = []

        if billing_country:
            registration.billing_country = billing_country
            updated_fields.append('billing_country')
        if billing_state:
            registration.billing_state = billing_state
            updated_fields.append('billing_state')
        if billing_postal_code:
            registration.billing_postal_code = billing_postal_code
            updated_fields.append('billing_postal_code')
        if billing_city:
            registration.billing_city = billing_city
            updated_fields.append('billing_city')

        if updated_fields:
            registration.save(update_fields=[*updated_fields, 'updated_at'])

        if not registration.billing_country or not registration.billing_postal_code:
            return error_response(
                'Billing country and postal code are required for tax calculation.',
                code='BILLING_REQUIRED',
            )

        intent_data = stripe_payment_service.create_payment_intent(
            registration,
            ticket_amount_cents=int(registration.amount_paid * 100),
        )
        if not intent_data['success']:
            return error_response(intent_data['error'], code='PAYMENT_ERROR')

        registration.payment_intent_id = intent_data['payment_intent_id']
        if intent_data.get('service_fee_cents') is not None:
            registration.platform_fee_amount = Decimal(intent_data['service_fee_cents']) / Decimal('100')
            registration.service_fee_amount = Decimal(intent_data['service_fee_cents']) / Decimal('100')
            registration.processing_fee_amount = Decimal(intent_data.get('processing_fee_cents', 0)) / Decimal('100')
            registration.tax_amount = Decimal(intent_data.get('tax_cents', 0)) / Decimal('100')
            registration.total_amount = Decimal(intent_data.get('total_amount_cents', 0)) / Decimal('100')
            registration.stripe_tax_calculation_id = intent_data.get('tax_calculation_id', '')
        registration.payment_status = Registration.PaymentStatus.PENDING
        registration.save(
            update_fields=[
                'payment_intent_id',
                'platform_fee_amount',
                'service_fee_amount',
                'processing_fee_amount',
                'tax_amount',
                'total_amount',
                'stripe_tax_calculation_id',
                'payment_status',
                'updated_at',
            ]
        )

        return Response(
            {
                'registration_uuid': str(registration.uuid),
                'uuid': str(registration.uuid),
                'client_secret': intent_data['client_secret'],
                'amount': float(registration.total_amount),
                'ticket_price': float(registration.amount_paid),
                'platform_fee': float(registration.platform_fee_amount),
                'service_fee': float(registration.service_fee_amount),
                'processing_fee': float(registration.processing_fee_amount),
                'tax_amount': float(registration.tax_amount),
                'total_amount': float(registration.total_amount),
                'currency': event.currency,
                'requires_payment': True,
                'status': registration.status,
                'stripe_account_id': None,
            },
            status=status.HTTP_200_OK,
        )


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
            404: '{"error": {"code": "NOT_FOUND", "message": "Registration not found"}}',
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
            return Response(
                {
                    'status': 'paid',
                    'registration_uuid': str(registration.uuid),
                    'amount_paid': float(registration.amount_paid),
                    'message': 'Payment already confirmed.',
                }
            )

        # Check if payment is expected
        if registration.payment_status == Registration.PaymentStatus.NA:
            return error_response('This registration does not require payment.', code='NO_PAYMENT_REQUIRED')

        # Confirm payment with Stripe
        result = payment_confirmation_service.confirm_registration_payment(registration)

        if result['status'] == 'paid':
            return Response(result, status=status.HTTP_200_OK)
        elif result['status'] == 'event_full':
            return error_response(
                result.get('message', 'Event is fully booked.'), code='EVENT_FULL', status_code=status.HTTP_409_CONFLICT
            )
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
        try:
            from promo_codes.models import PromoCodeUsage

            PromoCodeUsage.release_for_registration(registration)
        except Exception as e:
            logger.warning("Failed to release promo code usage for %s: %s", registration.uuid, e)

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
