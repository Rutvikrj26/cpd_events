"""Billing API views.

The subscription-based endpoints were removed when the platform moved to
course-based institutional pricing. What remains is admin-only
observability on the Stripe side: StripeEvents (webhook idempotency +
error log), Disputes, and Reconciliation findings.
"""

from __future__ import annotations

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers as drf_serializers

from common.rbac import roles
from common.utils import error_response

from .models import Dispute, StripeEvent


# ---------------------------------------------------------------------------
# Serializers (inline — small, admin-only)
# ---------------------------------------------------------------------------


class StripeEventSerializer(drf_serializers.ModelSerializer):
    """Listing view — excludes the full payload for speed."""

    class Meta:
        model = StripeEvent
        fields = [
            "event_id",
            "event_type",
            "received_at",
            "processed_at",
            "error",
        ]
        read_only_fields = fields


class StripeEventDetailSerializer(drf_serializers.ModelSerializer):
    """Detail view — includes payload for debugging."""

    class Meta:
        model = StripeEvent
        fields = [
            "event_id",
            "event_type",
            "received_at",
            "processed_at",
            "error",
            "payload",
        ]
        read_only_fields = fields


class DisputeSerializer(drf_serializers.ModelSerializer):
    registration_uuid = drf_serializers.SerializerMethodField()
    course_purchase_uuid = drf_serializers.SerializerMethodField()
    amount_display = drf_serializers.SerializerMethodField()

    class Meta:
        model = Dispute
        fields = [
            "uuid",
            "stripe_dispute_id",
            "stripe_charge_id",
            "stripe_payment_intent_id",
            "status",
            "reason",
            "amount_cents",
            "currency",
            "amount_display",
            "evidence_due_by",
            "submitted_at",
            "closed_at",
            "outcome",
            "created_at",
            "updated_at",
            "registration_uuid",
            "course_purchase_uuid",
        ]
        read_only_fields = fields

    def get_registration_uuid(self, obj):
        return str(obj.registration.uuid) if obj.registration_id else None

    def get_course_purchase_uuid(self, obj):
        return str(obj.course_purchase.uuid) if obj.course_purchase_id else None

    def get_amount_display(self, obj):
        return f"{obj.amount_cents / 100:.2f} {obj.currency.upper()}"


# ---------------------------------------------------------------------------
# StripeEvent — webhook observability
# ---------------------------------------------------------------------------


@roles("admin", route_name="admin_stripe_events")
class AdminStripeEventListView(generics.ListAPIView):
    """GET /api/v1/admin/billing/stripe-events/

    Query params:
      - ``errored=1`` — only rows with non-empty error
      - ``unprocessed=1`` — only rows where processed_at is NULL
      - ``type=<str>`` — filter by event_type exact match
    """

    serializer_class = StripeEventSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # admin audit list; keep it flat

    def get_queryset(self):
        qs = StripeEvent.objects.order_by("-received_at")
        if self.request.query_params.get("errored"):
            qs = qs.exclude(error="")
        if self.request.query_params.get("unprocessed"):
            qs = qs.filter(processed_at__isnull=True)
        event_type = self.request.query_params.get("type")
        if event_type:
            qs = qs.filter(event_type=event_type)
        return qs[:200]


@roles("admin", route_name="admin_stripe_event_detail")
class AdminStripeEventDetailView(generics.RetrieveAPIView):
    """GET /api/v1/admin/billing/stripe-events/{event_id}/"""

    serializer_class = StripeEventDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "event_id"

    def get_queryset(self):
        return StripeEvent.objects.all()


@roles("admin", route_name="admin_stripe_event_retry")
class AdminStripeEventRetryView(APIView):
    """POST /api/v1/admin/billing/stripe-events/{event_id}/retry/

    Re-enqueues the event for processing. The worker is idempotent via
    ``processed_at``; this action clears ``processed_at`` and ``error`` so
    a retry actually runs the handler chain.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, event_id=None):
        from billing.tasks import process_stripe_event

        try:
            ev = StripeEvent.objects.get(pk=event_id)
        except StripeEvent.DoesNotExist:
            return error_response("Event not found.", code="NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND)

        ev.processed_at = None
        ev.error = ""
        ev.save(update_fields=["processed_at", "error"])

        try:
            process_stripe_event.delay(ev.event_id)
        except Exception as exc:
            return error_response(str(exc), code="RETRY_FAILED")

        ev.refresh_from_db()
        return Response(StripeEventDetailSerializer(ev).data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Disputes — in-app admin surface (replaces needing Django admin)
# ---------------------------------------------------------------------------


@roles("admin", route_name="admin_disputes")
class AdminDisputeListView(generics.ListAPIView):
    """GET /api/v1/admin/billing/disputes/

    Query params:
      - ``open=1`` — only open disputes (NEEDS_RESPONSE / UNDER_REVIEW)
    """

    serializer_class = DisputeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        qs = Dispute.objects.order_by("evidence_due_by", "-created_at")
        if self.request.query_params.get("open"):
            qs = qs.filter(
                status__in=[
                    Dispute.Status.NEEDS_RESPONSE,
                    Dispute.Status.UNDER_REVIEW,
                    Dispute.Status.WARNING_NEEDS_RESPONSE,
                    Dispute.Status.WARNING_UNDER_REVIEW,
                ]
            )
        return qs


@roles("admin", route_name="admin_dispute_detail")
class AdminDisputeDetailView(generics.RetrieveAPIView):
    """GET /api/v1/admin/billing/disputes/{uuid}/"""

    serializer_class = DisputeSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"
    queryset = Dispute.objects.all()


# ---------------------------------------------------------------------------
# Reconciliation — on-demand drift check against Stripe
# ---------------------------------------------------------------------------


@roles("admin", route_name="admin_reconcile")
class AdminReconcileView(APIView):
    """POST /api/v1/admin/billing/reconcile/

    Runs a drift-check against Stripe for the last N hours (default 72)
    and returns any local/remote mismatches. This is a synchronous call
    and can take a few seconds. Gated to admins only.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from billing.reconciliation import reconcile

        try:
            hours = int(request.data.get("hours") or 72)
        except (TypeError, ValueError):
            hours = 72

        try:
            summary = reconcile(hours=hours)
        except Exception as exc:
            return error_response(str(exc), code="RECONCILE_FAILED")

        return Response(summary, status=status.HTTP_200_OK)
