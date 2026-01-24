"""
Events app views and viewsets.
"""

import logging

from django.db.models import Q
from django.utils import timezone
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated, SAFE_METHODS
from rest_framework.response import Response

from common.pagination import SmallPagination
from common.permissions import CanCreateEvents, IsOrganizerOrCourseManager
from common.utils import error_response
from common.viewsets import SoftDeleteModelViewSet

logger = logging.getLogger(__name__)

from . import serializers
from .models import Event, EventCustomField, Speaker

# =============================================================================
# Access Helpers
# =============================================================================


def _event_access_q(user, prefix: str = "") -> Q:
    """Simple filter: user owns the event."""
    owner_key = f"{prefix}owner"
    return Q(**{owner_key: user})


def _user_can_manage_event(user, event) -> bool:
    """Check if user can manage event (owner only)."""
    return event.owner_id == user.id


# =============================================================================
# Filters
# =============================================================================


class EventFilter(filters.FilterSet):
    """Filter events."""

    status = filters.MultipleChoiceFilter(choices=Event.Status.choices)
    event_type = filters.MultipleChoiceFilter(choices=Event.EventType.choices)
    starts_after = filters.DateTimeFilter(field_name="starts_at", lookup_expr="gte")
    starts_before = filters.DateTimeFilter(field_name="starts_at", lookup_expr="lte")
    cpd_type = filters.CharFilter()

    class Meta:
        model = Event
        fields = ["status", "event_type", "cpd_type"]


class PublicEventFilter(filters.FilterSet):
    """Filter for public event discovery."""

    event_type = filters.MultipleChoiceFilter(choices=Event.EventType.choices)
    cpd_type = filters.CharFilter()
    starts_after = filters.DateTimeFilter(field_name="starts_at", lookup_expr="gte")
    starts_before = filters.DateTimeFilter(field_name="starts_at", lookup_expr="lte")
    search = filters.CharFilter(method="filter_search")

    class Meta:
        model = Event
        fields = ["event_type", "cpd_type"]

    def filter_search(self, queryset, name, value):
        return queryset.filter(Q(title__icontains=value) | Q(description__icontains=value))


# =============================================================================
# Organizer ViewSet
# =============================================================================


class EventViewSet(SoftDeleteModelViewSet):
    """
    Organizer-level CRUD for events.

    GET /api/v1/events/ - Requires authentication (organizer/course manager)
    POST /api/v1/events/ - Requires authentication and event creation capability
    GET /api/v1/events/{uuid}/ - Requires authentication (organizer/course manager)
    PATCH /api/v1/events/{uuid}/ - Requires authentication and ownership
    DELETE /api/v1/events/{uuid}/ - Requires authentication and ownership

    Note: This endpoint is for event organizers only. Attendees should use
    the public event endpoints for discovery.
    """

    parser_classes = (MultiPartParser, FormParser, JSONParser)
    permission_classes = [IsAuthenticated, IsOrganizerOrCourseManager]
    filterset_class = EventFilter
    search_fields = ["title", "description"]
    ordering_fields = ["starts_at", "created_at", "title", "registration_count"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            Event.objects.filter(_event_access_q(self.request.user), deleted_at__isnull=True)
            .select_related("owner", "certificate_template")
            .distinct()
        )

    def get_permissions(self):
        # All actions require authentication and organizer/course manager role
        if self.request.method in SAFE_METHODS:
            return [IsAuthenticated(), IsOrganizerOrCourseManager()]
        return [IsAuthenticated(), CanCreateEvents()]

    def get_serializer_class(self):
        if self.action == "create":
            return serializers.EventCreateSerializer
        if self.action in ["update", "partial_update"]:
            return serializers.EventUpdateSerializer
        if self.action == "list":
            return serializers.EventListSerializer
        return serializers.EventDetailSerializer

    def perform_create(self, serializer):
        from rest_framework.exceptions import ValidationError

        from .services import event_service

        try:
            event = event_service.create_event(user=self.request.user, data=serializer.validated_data)
            serializer.instance = event
        except ValidationError as e:
            raise e
        except Exception as e:
            # Re-raise known exceptions as is, wrap others if needed
            raise e

    @swagger_auto_schema(
        operation_summary="Publish event",
        operation_description="Publish a draft event to make it visible and open for registration.",
        responses={200: serializers.EventDetailSerializer, 400: '{"error": {"code": "INVALID_STATE"}}'},
    )
    @action(detail=True, methods=["post"])
    def publish(self, request, uuid=None):
        """Publish a draft event."""
        event = self.get_object()

        if event.status != "draft":
            return error_response(
                "Can only publish draft events.", code="INVALID_STATE", status_code=status.HTTP_400_BAD_REQUEST
            )

        event.publish(user=request.user)
        return Response(serializers.EventDetailSerializer(event).data)

    @swagger_auto_schema(
        operation_summary="Unpublish event",
        operation_description="Revert a published event to draft status. Restricted if event has started.",
        responses={200: serializers.EventDetailSerializer, 400: '{"error": {"code": "INVALID_STATE"}}'},
    )
    @action(detail=True, methods=["post"])
    def unpublish(self, request, uuid=None):
        """Revert event to draft."""
        event = self.get_object()

        if event.starts_at <= timezone.now():
            return error_response(
                "Cannot revert to draft after event has started.", code="INVALID_STATE", status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            event.unpublish(user=request.user)
        except ValueError as e:
            return error_response(str(e), code="INVALID_STATE")

        return Response(serializers.EventDetailSerializer(event).data)

    @swagger_auto_schema(
        operation_summary="Cancel event",
        operation_description="Cancel an event. All registrants will be notified.",
        request_body=serializers.EventStatusChangeSerializer,
        responses={200: serializers.EventDetailSerializer, 400: '{"error": {"code": "INVALID_STATE"}}'},
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, uuid=None):
        """Cancel an event."""
        event = self.get_object()
        serializer = serializers.EventStatusChangeSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data or {}
        try:
            event.cancel(reason=data.get("reason", ""), user=request.user)
        except ValueError as e:
            return error_response(str(e), code="INVALID_STATE")

        return Response(serializers.EventDetailSerializer(event).data)

    @swagger_auto_schema(
        operation_summary="Go live",
        operation_description="Mark the event as live (in progress).",
        responses={200: serializers.EventDetailSerializer, 400: '{"error": {"code": "INVALID_STATE"}}'},
    )
    @action(detail=True, methods=["post"])
    def go_live(self, request, uuid=None):
        """Start the event (mark as live)."""
        event = self.get_object()

        try:
            event.start(user=request.user)
        except ValueError as e:
            return error_response(str(e), code="INVALID_STATE")

        return Response(serializers.EventDetailSerializer(event).data)

    @swagger_auto_schema(
        operation_summary="Complete event",
        operation_description="Mark the event as completed after it has ended.",
        responses={200: serializers.EventDetailSerializer, 400: '{"error": {"code": "INVALID_STATE"}}'},
    )
    @action(detail=True, methods=["post"])
    def complete(self, request, uuid=None):
        """Mark event as completed."""
        event = self.get_object()

        try:
            event.complete()
        except ValueError as e:
            return error_response(str(e), code="INVALID_STATE")

        return Response(serializers.EventDetailSerializer(event).data)

    @swagger_auto_schema(
        operation_summary="Duplicate event",
        operation_description="Create a copy of this event with a new UUID and draft status.",
        responses={201: serializers.EventDetailSerializer},
    )
    @action(detail=True, methods=["post"])
    def duplicate(self, request, uuid=None):
        """Create a copy of this event."""
        event = self.get_object()
        new_event = event.duplicate()
        new_event.save()

        return Response(serializers.EventDetailSerializer(new_event).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        method="post",
        operation_summary="Upload featured image",
        operation_description="Upload a featured image for the event.",
        responses={200: serializers.EventDetailSerializer, 400: '{"error": {"code": "NO_FILE"}}'},
    )
    @swagger_auto_schema(
        method="delete",
        operation_summary="Delete featured image",
        operation_description="Remove the featured image from the event.",
        responses={200: serializers.EventDetailSerializer},
    )
    @action(detail=True, methods=["post", "delete"], url_path="upload-image")
    def upload_image(self, request, uuid=None):
        """
        Upload or delete a featured image.
        POST: Upload new image.
        DELETE: Remove existing image.
        """
        event = self.get_object()

        if request.method == "DELETE":
            event.featured_image.delete(save=False)  # Delete file from storage
            event.featured_image = None
            event.save(update_fields=["featured_image", "updated_at"])
            return Response(serializers.EventDetailSerializer(event, context={"request": request}).data)

        if "image" not in request.FILES:
            return error_response("No image file provided.", code="NO_FILE", status_code=status.HTTP_400_BAD_REQUEST)

        image_file = request.FILES["image"]

        # Validate file type
        valid_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
        if image_file.content_type not in valid_types:
            return error_response(
                f"Invalid file type. Allowed: {', '.join(valid_types)}",
                code="INVALID_TYPE",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Validate file size (max 5MB)
        max_size = 5 * 1024 * 1024
        if image_file.size > max_size:
            return error_response(
                "File too large. Maximum size is 5MB.", code="FILE_TOO_LARGE", status_code=status.HTTP_400_BAD_REQUEST
            )

        event.featured_image = image_file
        event.save(update_fields=["featured_image", "updated_at"])

        return Response(serializers.EventDetailSerializer(event, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def sync_attendance(self, request, uuid=None):
        """Trigger background sync of attendance."""
        from .tasks import sync_zoom_attendance

        event = self.get_object()
        if not event.zoom_meeting_id:
            return error_response("Event has no Zoom meeting linked.", code="NO_ZOOM", status_code=400)

        task = sync_zoom_attendance.delay(event.id)
        # task might be a dict if CLOUD_TASKS_SYNC=True or in emulator mode
        task_id = getattr(task, "id", None) or (task.get("id") if isinstance(task, dict) else None)
        # fallback to name if it's a CloudTasks response from create_task
        if not task_id and hasattr(task, "name"):
            task_id = task.name

        return Response({"task_id": task_id, "status": "queued"})

    @action(detail=True, methods=["get"])
    def unmatched_participants(self, request, uuid=None):
        """
        Get Zoom participants that are not yet matched to any registration.
        Uses local AttendanceRecord data populated via Zoom webhooks.
        """
        event = self.get_object()
        if not event.zoom_meeting_id:
            return error_response("Event has no Zoom meeting linked.", code="NO_ZOOM", status_code=400)

        from django.db.models import Max, Sum
        from django.db.models.functions import Coalesce

        from registrations.models import AttendanceRecord

        try:
            # Prefer unmatched attendance records from webhook data when present
            unmatched_records = (
                AttendanceRecord.objects.filter(event=event, is_matched=False)
                .exclude(zoom_user_email="")
                .values("zoom_user_email", "zoom_user_name")
                .annotate(first_join=Max("join_time"), total_duration=Coalesce(Sum("duration_minutes"), 0))
                .order_by("-first_join")
            )

            if unmatched_records.exists():
                unmatched = [
                    {
                        "user_email": record["zoom_user_email"],
                        "user_name": record["zoom_user_name"] or "Unknown",
                        "join_time": record["first_join"].isoformat() if record["first_join"] else None,
                        "duration": record["total_duration"] or 0,
                    }
                    for record in unmatched_records
                ]
                return Response(unmatched)

            # Fallback: fetch participants from Zoom and filter out matched emails
            from accounts.services import zoom_service

            zoom_result = zoom_service.get_past_meeting_participants(event.owner, event.zoom_meeting_id)
            if not zoom_result.get("success"):
                return Response([])

            participants = zoom_result.get("data", {}).get("participants", [])
            matched_emails = set(
                AttendanceRecord.objects.filter(event=event, is_matched=True)
                .exclude(zoom_user_email="")
                .values_list("zoom_user_email", flat=True)
            )

            unmatched = []
            for participant in participants:
                email = participant.get("user_email") or ""
                if not email or email in matched_emails:
                    continue
                unmatched.append(
                    {
                        "user_email": email,
                        "user_name": participant.get("name") or "Unknown",
                        "join_time": participant.get("join_time"),
                        "duration": participant.get("duration") or 0,
                    }
                )

            return Response(unmatched)

        except Exception as e:
            logger.error(f"Error in unmatched_participants: {e}")
            return error_response(str(e), code="INTERNAL_ERROR", status_code=500)

    @action(detail=True, methods=["post"])
    def match_participant(self, request, uuid=None):
        """Manually match a participant to a registration."""
        from django.shortcuts import get_object_or_404

        from registrations.models import AttendanceRecord, Registration

        from .serializers import MatchParticipantSerializer

        event = self.get_object()
        serializer = MatchParticipantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        if not data:
            return error_response("Invalid data provided.", code="INVALID_DATA")

        registration_uuid = data.get("registration_uuid")
        registration = get_object_or_404(Registration, uuid=registration_uuid, event=event)

        # Create or update attendance record
        # For events, we track AttendanceRecord which sums up to Registration
        record, created = AttendanceRecord.objects.update_or_create(
            event=event,
            registration=registration,
            zoom_user_email=data.get("zoom_user_email"),
            defaults={
                "zoom_user_name": data.get("zoom_user_name"),
                "join_time": data.get("zoom_join_time") or timezone.now(),
                "duration_minutes": data.get("attendance_minutes", 0),
                "is_matched": True,
                "matched_at": timezone.now(),
                "matched_manually": True,
                "matched_by": request.user,
            },
        )

        # Trigger registration summary update
        registration.update_attendance_summary()

        # update denormalized counts on event
        event.update_counts()

        return Response({"status": "matched"})

    @swagger_auto_schema(
        operation_summary="Event history",
        operation_description="Get the status change history for this event.",
        responses={200: serializers.EventStatusHistorySerializer(many=True)},
    )
    @action(detail=True, methods=["get"])
    def history(self, request, uuid=None):
        """Get status change history."""
        event = self.get_object()
        history = event.status_history.all().order_by("-created_at")
        serializer = serializers.EventStatusHistorySerializer(history, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Dashboard stats",
        operation_description="Get aggregate statistics for the organizer's events.",
    )
    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        """Get dashboard stats for organizer."""
        events = self.get_queryset()
        now = timezone.now()

        return Response(
            {
                "total_events": events.count(),
                "draft": events.filter(status="draft").count(),
                "published": events.filter(status="published").count(),
                "upcoming": events.filter(status="published", starts_at__gt=now).count(),
                "live": events.filter(status="live").count(),
                "completed": events.filter(status__in=["completed", "closed"]).count(),
                "total_registrations": sum(e.registration_count for e in events),
                "total_attendees": sum(e.attendee_count for e in events),
            }
        )

    @swagger_auto_schema(
        operation_summary="Reports & analytics",
        operation_description="Get report summary and trends for organizer events.",
    )
    @action(detail=False, methods=["get"])
    def reports(self, request):
        from datetime import timedelta

        from django.db.models import Avg, Count, Sum
        from django.db.models.functions import TruncDate

        from feedback.models import EventFeedback
        from registrations.models import Registration

        events = self.get_queryset()
        now = timezone.now()
        period = request.query_params.get("period", "last-30-days")

        from datetime import datetime

        if period == "last-7-days":
            start = now - timedelta(days=7)
        elif period == "last-90-days":
            start = now - timedelta(days=90)
        elif period == "this-year":
            start = timezone.make_aware(datetime(now.year, 1, 1))
        else:
            start = now - timedelta(days=30)

        registrations = Registration.objects.filter(
            event__in=events,
            created_at__gte=start,
            created_at__lte=now,
            deleted_at__isnull=True,
        )

        paid_regs = registrations.filter(payment_status=Registration.PaymentStatus.PAID)
        total_revenue = paid_regs.aggregate(total=Sum("total_amount"))["total"] or 0

        event_counts = events.values("currency").annotate(count=Count("id")).order_by("-count")
        primary_currency = event_counts[0]["currency"] if event_counts else "USD"

        trends = []
        for row in (
            registrations.annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(
                registrations=Count("id"),
                revenue=Sum("total_amount"),
            )
            .order_by("day")
        ):
            trends.append(
                {
                    "date": row["day"].isoformat() if row["day"] else None,
                    "registrations": row["registrations"],
                    "revenue_cents": int((row["revenue"] or 0) * 100),
                }
            )

        ticket_breakdown = [
            {
                "label": "Paid",
                "count": paid_regs.count(),
            },
            {
                "label": "Free",
                "count": registrations.filter(payment_status=Registration.PaymentStatus.NA).count(),
            },
            {
                "label": "Refunded",
                "count": registrations.filter(payment_status=Registration.PaymentStatus.REFUNDED).count(),
            },
        ]

        avg_rating = EventFeedback.objects.filter(
            event__in=events,
            created_at__gte=start,
            created_at__lte=now,
        ).aggregate(avg=Avg("rating"))["avg"]

        recent_transactions = [
            {
                "registration_uuid": str(reg.uuid),
                "event_title": reg.event.title if reg.event else "",
                "amount_cents": int((reg.total_amount or 0) * 100),
                "currency": reg.event.currency if reg.event else primary_currency,
                "created_at": reg.created_at.isoformat(),
            }
            for reg in paid_regs.select_related("event").order_by("-created_at")[:5]
        ]

        return Response(
            {
                "summary": {
                    "total_revenue_cents": int(total_revenue * 100),
                    "total_attendees": registrations.filter(status=Registration.Status.CONFIRMED).count(),
                    "events_hosted": events.filter(starts_at__gte=start, starts_at__lte=now).count(),
                    "avg_rating": round(avg_rating, 2) if avg_rating else None,
                    "currency": primary_currency,
                },
                "trends": trends,
                "ticket_breakdown": ticket_breakdown,
                "recent_transactions": recent_transactions,
            }
        )


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
    search_fields = ["title", "description", "owner__first_name", "owner__last_name", "owner__organization_name"]
    ordering_fields = ["starts_at", "registration_count"]
    ordering = ["-starts_at"]

    def get_queryset(self):
        return Event.objects.filter(
            status__in=["published", "live", "completed"],
            is_public=True,
            deleted_at__isnull=True,
        ).select_related("owner")


class PublicEventDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/public/events/{slug_or_uuid}/

    Public event detail by slug or uuid.
    """

    serializer_class = serializers.PublicEventDetailSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        """Look up event by slug first, then by uuid if slug lookup fails."""
        identifier = self.kwargs.get("identifier")
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
        # Allow owners to see their events regardless of status
        user = self.request.user
        queryset = Event.objects.select_related("owner").prefetch_related("custom_fields")

        if user.is_authenticated:
            # If user is authenticated, they can see published/live/completed public events OR any event they own
            return queryset.filter(
                Q(status__in=["published", "live", "completed"], is_public=True, deleted_at__isnull=True)
                | Q(owner=user, deleted_at__isnull=True)
            ).distinct()

        # Public users only see published/live/completed public events
        return queryset.filter(
            status__in=["published", "live", "completed"],
            is_public=True,
            deleted_at__isnull=True,
        )


# =============================================================================
# Custom Fields Management
# =============================================================================


class EventCustomFieldViewSet(viewsets.ModelViewSet):
    """
    Manage custom fields for an event.

    Nested under events: /api/v1/events/{event_uuid}/custom-fields/
    """

    permission_classes = [IsAuthenticated, CanCreateEvents]
    lookup_field = "uuid"

    def get_queryset(self):
        event_uuid = self.kwargs.get("event_uuid")
        return EventCustomField.objects.filter(
            event__uuid=event_uuid,
        ).filter(_event_access_q(self.request.user, prefix="event__"))

    def get_serializer_class(self):
        if self.action == "create":
            return serializers.EventCustomFieldCreateSerializer
        return serializers.EventCustomFieldSerializer

    def perform_create(self, serializer):
        from django.shortcuts import get_object_or_404

        event_uuid = self.kwargs.get("event_uuid")
        event = get_object_or_404(
            Event.objects.filter(_event_access_q(self.request.user)),
            uuid=event_uuid,
        )

        # Get next order position
        max_order = self.get_queryset().order_by("-order").values_list("order", flat=True).first() or 0

        serializer.save(event=event, order=max_order + 1)

    @action(detail=False, methods=["post"])
    def reorder(self, request, event_uuid=None):
        """Reorder custom fields."""
        field_order = request.data.get("order", [])  # List of UUIDs in desired order

        for order, field_uuid in enumerate(field_order):
            self.get_queryset().filter(uuid=field_uuid).update(order=order)

        return Response({"message": "Fields reordered."})


# =============================================================================
# Session Management (C1: Multi-Session Events API)
# =============================================================================


class EventSessionViewSet(viewsets.ModelViewSet):
    """
    Manage sessions for a multi-session event.

    Nested under events: /api/v1/events/{event_uuid}/sessions/
    """

    permission_classes = [IsAuthenticated, CanCreateEvents]
    pagination_class = SmallPagination  # M5: Nested resource pagination
    lookup_field = "uuid"

    def get_queryset(self):
        from .models import EventSession

        event_uuid = self.kwargs.get("event_uuid")
        return (
            EventSession.objects.filter(
                event__uuid=event_uuid,
            )
            .filter(_event_access_q(self.request.user, prefix="event__"))
            .order_by("order", "starts_at")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return serializers.EventSessionListSerializer
        if self.action == "create":
            return serializers.EventSessionCreateSerializer
        if self.action in ["update", "partial_update"]:
            return serializers.EventSessionUpdateSerializer
        return serializers.EventSessionDetailSerializer

    def perform_create(self, serializer):
        from django.shortcuts import get_object_or_404

        event_uuid = self.kwargs.get("event_uuid")
        event = get_object_or_404(
            Event.objects.filter(_event_access_q(self.request.user)),
            uuid=event_uuid,
        )

        # Get next order position
        max_order = self.get_queryset().order_by("-order").values_list("order", flat=True).first() or 0

        serializer.save(event=event, order=max_order + 1)

    @swagger_auto_schema(
        operation_summary="Reorder sessions",
        operation_description="Reorder sessions within a multi-session event by providing a list of session UUIDs in the desired order.",
        request_body=serializers.SessionReorderSerializer,
        responses={200: '{"message": "Sessions reordered."}'},
    )
    @action(detail=False, methods=["post"])
    def reorder(self, request, event_uuid=None):
        """Reorder sessions within the event."""
        from django.shortcuts import get_object_or_404

        # Validate event ownership
        get_object_or_404(
            Event.objects.filter(_event_access_q(self.request.user)),
            uuid=event_uuid,
        )

        reorder_serializer = serializers.SessionReorderSerializer(data=request.data)
        reorder_serializer.is_valid(raise_exception=True)

        data = reorder_serializer.validated_data or {}
        order_list = data.get("order", [])
        for order, session_uuid in enumerate(order_list):
            self.get_queryset().filter(uuid=session_uuid).update(order=order)

        return Response({"message": "Sessions reordered."})


class RegistrationSessionAttendanceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View session attendance for a registration.

    Nested under registrations: /api/v1/registrations/{registration_uuid}/session-attendance/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = serializers.SessionAttendanceSerializer
    lookup_field = "uuid"

    def get_queryset(self):
        from registrations.models import Registration

        from .models import SessionAttendance

        registration_uuid = self.kwargs.get("registration_uuid")
        registration = Registration.objects.get(uuid=registration_uuid)

        # Check permission: owner/admin of event or the registrant themselves
        user = self.request.user
        if registration.user != user and not _user_can_manage_event(user, registration.event):
            return SessionAttendance.objects.none()

        return (
            SessionAttendance.objects.filter(registration=registration)
            .select_related("session")
            .order_by("session__order", "session__starts_at")
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
    @action(detail=True, methods=["post"])
    def override(self, request, registration_uuid=None, uuid=None):
        """Override session attendance eligibility."""

        session_attendance = self.get_object()
        event = session_attendance.registration.event  # Define event for the check

        if not _user_can_manage_event(request.user, event):
            return error_response(
                "Only the event owner or org admin can override attendance.",
                code="PERMISSION_DENIED",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        override_serializer = serializers.SessionAttendanceOverrideSerializer(data=request.data)
        override_serializer.is_valid(raise_exception=True)

        data = override_serializer.validated_data or {}
        session_attendance.override_eligible = data.get("eligible")
        session_attendance.override_reason = data.get("reason")
        session_attendance.override_by = request.user
        session_attendance.save()

        return Response(serializers.SessionAttendanceSerializer(session_attendance).data)


class SpeakerViewSet(SoftDeleteModelViewSet):
    """
    CRUD for speakers.
    """

    permission_classes = [IsAuthenticated, CanCreateEvents]
    queryset = Speaker.objects.all()
    serializer_class = serializers.SpeakerSerializer
    search_fields = ["name", "bio"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        return Speaker.objects.filter(
            Q(owner=self.request.user),
            deleted_at__isnull=True,
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
