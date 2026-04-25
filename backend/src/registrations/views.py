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
from common.permissions import IsOrganizerOrAdmin
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

    permission_classes = [IsAuthenticated, IsOrganizerOrAdmin]
    pagination_class = SmallPagination  # M5: Nested resource pagination
    filterset_class = RegistrationFilter
    search_fields = ['email', 'full_name', 'user__email', 'user__full_name']
    ordering_fields = ['created_at', 'status', 'attended', 'full_name']
    ordering = ['-created_at']

    def get_queryset(self):
        event_uuid = self.kwargs.get('event_uuid')
        qs_filter = {'event__uuid': event_uuid, 'deleted_at__isnull': True}
        if not self.request.user.groups.filter(name="admin").exists():
            qs_filter['event__owner'] = self.request.user
        return (
            Registration.objects.filter(**qs_filter)
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
        """Refund a registration (paid only).

        ``automatic_tax`` handled the original charge, so Stripe reverses the
        tax transaction automatically when we issue the refund.
        """
        from billing.services import refund_payment_intent

        registration = self.get_object()
        serializer = serializers.RegistrationRefundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if registration.payment_status == Registration.PaymentStatus.REFUNDED:
            return error_response('Registration already refunded.', code='ALREADY_REFUNDED')
        if registration.payment_status != Registration.PaymentStatus.PAID or registration.amount_paid <= 0:
            return error_response('Registration is not paid.', code='NOT_PAID')
        if not registration.payment_intent_id:
            return error_response('No payment intent found for this registration.', code='NO_PAYMENT_INTENT')

        amount_cents = serializer.validated_data.get('amount_cents')
        if amount_cents is not None and amount_cents > int(registration.amount_paid * 100):
            return error_response(
                'Refund amount exceeds amount paid.',
                code='REFUND_EXCEEDS_AMOUNT',
            )

        reason = serializer.validated_data['reason']
        try:
            stripe_result = refund_payment_intent(
                registration.payment_intent_id,
                amount_cents=amount_cents,
                reason='requested_by_customer',
            )
        except Exception as exc:
            return error_response(str(exc), code='REFUND_FAILED')

        is_partial = amount_cents is not None and amount_cents < int(registration.amount_paid * 100)

        if not is_partial:
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

        try:
            from accounts.audit import log_audit_event

            log_audit_event(
                actor=request.user,
                action='registration.refunded',
                object_type='Registration',
                object_uuid=str(registration.uuid),
                metadata={
                    'event_uuid': str(registration.event.uuid),
                    'amount_cents': stripe_result.get('amount_cents'),
                    'partial': is_partial,
                    'reason': reason,
                    'stripe_refund_id': stripe_result.get('refund_id'),
                },
                request=request,
            )
        except Exception as e:
            logger.warning("Failed to audit registration refund for %s: %s", registration.uuid, e)

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
            target_list = ContactList.objects.filter(owner=organizer).order_by('created_at').first()
            if not target_list:
                target_list = ContactList.objects.create(owner=organizer, name="My Contacts")

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
        operation_description="Get attendance records not matched to any registration.",
        responses={200: serializers.UnmatchedAttendanceRecordSerializer(many=True)},
    )
    @action(detail=False, methods=['get'], url_path='unmatched-attendance')
    def unmatched_attendance(self, request, event_uuid=None):
        """Get unmatched attendance records for reconciliation."""
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
        operation_description="Manually match an unmatched attendance record to a registration.",
        request_body=serializers.AttendanceMatchSerializer,
        responses={
            200: serializers.AttendanceRecordSerializer,
            400: '{"error": {}}',
            404: '{"error": {"code": "NOT_FOUND"}}',
        },
    )
    @action(detail=False, methods=['post'], url_path='match-attendance/(?P<record_uuid>[^/.]+)')
    def match_attendance(self, request, event_uuid=None, record_uuid=None):
        """Match unmatched attendance record to a registration."""
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
            event = Event.objects.get(
                uuid=event_uuid,
                status__in=['published', 'live'],
                registration_enabled=True,
                deleted_at__isnull=True,
            )
        except Event.DoesNotExist:
            return error_response(
                'Event not found or registration closed.', code='NOT_FOUND', status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user if request.user.is_authenticated else None

        try:
            result = registration_service.register_participant(event=event, data=serializer.validated_data, user=user)

            reg = result['registration']
            response_data = {
                'registration_uuid': str(reg.uuid),
                'uuid': str(reg.uuid),
                'status': result['status'],
                'requires_payment': result.get('requires_payment', False),
                'checkout_url': result.get('checkout_url'),
                'checkout_session_id': result.get('checkout_session_id'),
                'amount': float(reg.total_amount) if reg.total_amount else None,
                'ticket_price': float(reg.amount_paid) if reg.amount_paid else None,
                'tax_amount': float(reg.tax_amount) if reg.tax_amount else None,
                'total_amount': float(reg.total_amount) if reg.total_amount else None,
                'currency': event.currency,
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


@roles('public', route_name='registration_lobby')
class RegistrationLobbyView(generics.GenericAPIView):
    """GET /api/v1/public/registrations/{uuid}/lobby/

    Public endpoint that returns the minimum info a guest registrant needs to
    render the pre-event lobby: event details + their registration metadata.
    Authenticated paths (``/events/:uuid/lobby``) load the same data via the
    standard event endpoints; this exists so a non-User registrant can still
    land on the lobby URL embedded in their reminder email.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request, uuid=None):
        from events.serializers import PublicEventDetailSerializer

        try:
            registration = Registration.objects.select_related('event').get(
                uuid=uuid, deleted_at__isnull=True
            )
        except Registration.DoesNotExist:
            return error_response(
                'Registration not found.', code='NOT_FOUND', status_code=status.HTTP_404_NOT_FOUND
            )

        event = registration.event
        if event.deleted_at is not None:
            return error_response(
                'Event no longer available.', code='EVENT_UNAVAILABLE', status_code=status.HTTP_404_NOT_FOUND
            )

        event_data = PublicEventDetailSerializer(event, context={'request': request}).data
        return Response({
            'event': event_data,
            'registration': {
                'uuid': str(registration.uuid),
                'email': registration.email,
                'full_name': registration.full_name,
                'status': registration.status,
                'payment_status': registration.payment_status,
                'attended': registration.attended,
            },
        })


@roles('public', route_name='start_checkout')
class StartCheckoutView(generics.GenericAPIView):
    """POST /api/v1/public/registrations/{uuid}/start-checkout/

    Create (or return) a Stripe Checkout Session for a PENDING paid
    registration. The frontend redirects to the returned ``url``. Fulfilment
    happens via ``checkout.session.completed``.
    """

    permission_classes = [AllowAny]

    def post(self, request, uuid=None):
        from billing.checkout import checkout_service

        try:
            registration = Registration.objects.select_related('event').get(
                uuid=uuid, deleted_at__isnull=True
            )
        except Registration.DoesNotExist:
            return error_response(
                'Registration not found.', code='NOT_FOUND', status_code=status.HTTP_404_NOT_FOUND
            )

        if registration.status == Registration.Status.WAITLISTED:
            return error_response('Registration is waitlisted.', code='WAITLISTED')
        if registration.status == Registration.Status.CANCELLED:
            return error_response('Registration is cancelled.', code='CANCELLED')
        if registration.payment_status == Registration.PaymentStatus.PAID:
            return error_response('Payment already completed.', code='ALREADY_PAID')
        if registration.status != Registration.Status.PENDING or registration.amount_paid <= 0:
            return error_response('Registration does not require payment.', code='NO_PAYMENT_REQUIRED')

        try:
            result = checkout_service.for_event_registration(registration)
        except Exception as exc:
            return error_response(str(exc), code='CHECKOUT_ERROR')

        return Response({
            'registration_uuid': str(registration.uuid),
            'session_id': result.session_id,
            'url': result.url,
            'status': registration.status,
            'amount_paid': float(registration.amount_paid),
            'currency': registration.event.currency,
        })


# =============================================================================
# Attendee ViewSet
# =============================================================================


@roles('learner', 'organizer', 'admin', route_name='registrations')
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


@roles('learner', 'organizer', 'admin', route_name='link_registrations')
class LinkRegistrationsView(generics.GenericAPIView):
    """
    POST /api/v1/users/me/link-registrations/

    Find and link orphaned guest registrations to the current user.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        count = Registration.link_registrations_for_user(request.user)

        return Response({'linked_count': count, 'message': f'Linked {count} registration(s) to your account.'})
