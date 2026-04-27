"""Billing API views.

Two surfaces:

1. **Admin observability** — StripeEvents (webhook idempotency + error log),
   Disputes, Reconciliation findings.
2. **Learner-/staff-facing** — ``VerifySessionView`` (post-checkout polling
   from the frontend) and ``RefundPurchaseView`` (the canonical refund
   endpoint that replaced surface-specific actions on Registration / Course /
   Program viewsets).

The subscription-based endpoints were removed when the platform moved to
course-based institutional pricing.
"""

from __future__ import annotations

import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework import serializers as drf_serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.rbac import roles
from common.utils import error_response

from .models import CoursePurchase, Dispute, RefundRecord, StripeEvent

logger = logging.getLogger(__name__)


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

        if hours < 1 or hours > 720:
            return error_response(
                "`hours` must be a whole number between 1 and 720.",
                code="INVALID_HOURS",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            summary = reconcile(hours=hours)
        except Exception as exc:
            return error_response(str(exc), code="RECONCILE_FAILED")

        return Response(summary, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Learner-facing — verify-session (CheckoutReturn polling)
# ---------------------------------------------------------------------------


_KIND_REDIRECT = {
    "course": "/dashboard",
    "program": "/my-programs",
    "event": "/registrations",
}


def _purchase_kind(purchase: CoursePurchase) -> str:
    if purchase.course_id:
        return "course"
    if purchase.program_id:
        return "program"
    return "event"


class VerifySessionView(APIView):
    """GET /api/v1/billing/verify-session/?session_id=cs_...

    Authoritative check for post-checkout state. The frontend polls this
    after Stripe redirects back; on the first request the webhook may
    still be in flight, so we return ``202 Accepted`` until the
    ``CoursePurchase`` exists.

    Scoped to the requesting user — a leaked session id can't be probed
    by anyone other than its purchaser.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        session_id = request.query_params.get("session_id", "")
        if not session_id.startswith("cs_"):
            return error_response(
                "Invalid session id.", code="INVALID_SESSION", status_code=status.HTTP_400_BAD_REQUEST,
            )

        purchase = (
            CoursePurchase.objects
            .select_related("course", "event", "program")
            .filter(stripe_checkout_session_id=session_id, user=request.user)
            .first()
        )
        if not purchase:
            # Webhook hasn't delivered yet (or session belongs to another
            # user — same response on purpose to avoid existence oracle).
            return Response(
                {"fulfilled": False, "kind": None, "payment_status": "unknown"},
                status=status.HTTP_202_ACCEPTED,
            )

        kind = _purchase_kind(purchase)
        return Response({
            "fulfilled": purchase.status == CoursePurchase.Status.COMPLETED,
            "kind": kind,
            "payment_status": purchase.status,
            "amount_cents": purchase.amount_cents,
            "currency": purchase.currency,
            "redirect_url": _KIND_REDIRECT[kind],
        })


# ---------------------------------------------------------------------------
# Staff-facing — unified refund endpoint
# ---------------------------------------------------------------------------


class RefundPurchaseView(APIView):
    """POST /api/v1/billing/purchases/{uuid}/refund/

    Body: ``{reason: str, amount_cents?: int}``

    Single canonical refund endpoint replacing the surface-specific actions
    that used to live on RegistrationViewSet and CourseViewSet. Permission
    is delegated to the related entity's ``can_manage(user)`` check
    (course manager / program manager / event organizer / admin).

    Cascade by kind:
    - **event**: Registration.cancel(reason) + payment_status=REFUNDED;
      promo code released.
    - **course**: CourseEnrollment.status=DROPPED. Rejected with
      PROGRAM_SEEDED if the row was seeded by a program purchase — the
      learner must refund the program instead.
    - **program**: ProgramEnrollment.status=DROPPED + cascade-drop every
      seeded child CourseEnrollment.

    Refunds are issued at the Stripe layer first; local state flips only
    on Stripe success. The downstream ``charge.refunded`` webhook still
    runs (writes the ``RefundRecord`` row), but is now informational
    rather than load-bearing.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, uuid=None):
        from billing.services import refund_payment_intent

        purchase = get_object_or_404(
            CoursePurchase.objects.select_related("course", "event", "program", "user"),
            uuid=uuid,
        )

        target = purchase.course or purchase.event or purchase.program
        if target is None or not target.can_manage(request.user):
            raise PermissionDenied(
                "You do not have permission to refund this purchase."
            )

        if purchase.status == CoursePurchase.Status.REFUNDED:
            return error_response(
                "Purchase has already been refunded.",
                code="ALREADY_REFUNDED",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        if purchase.status != CoursePurchase.Status.COMPLETED:
            return error_response(
                "Purchase is not in a refundable state.",
                code="NOT_REFUNDABLE",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        if not purchase.stripe_payment_intent_id:
            return error_response(
                "Purchase has no Stripe PaymentIntent.",
                code="NO_PAYMENT_INTENT",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        reason = (request.data.get("reason") or "").strip()
        if not reason:
            raise ValidationError({"reason": "required"})

        amount_cents = request.data.get("amount_cents")
        if amount_cents is not None:
            try:
                amount_cents = int(amount_cents)
            except (TypeError, ValueError):
                raise ValidationError({"amount_cents": "must be an integer"}) from None
            if amount_cents <= 0:
                raise ValidationError({"amount_cents": "must be positive"})
            if amount_cents > purchase.amount_cents:
                return error_response(
                    "Refund amount exceeds amount paid.",
                    code="REFUND_EXCEEDS_AMOUNT",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        # Pre-validate program-seeded rejection BEFORE calling Stripe so we
        # don't issue a refund and then fail to revoke access.
        kind = _purchase_kind(purchase)
        if kind == "course":
            from learning.models import CourseEnrollment

            enrollment = CourseEnrollment.objects.filter(
                user=purchase.user, course=purchase.course,
            ).first()
            if enrollment and enrollment.from_program_enrollment_id:
                parent = enrollment.from_program_enrollment
                return Response(
                    {"error": {
                        "code": "PROGRAM_SEEDED",
                        "message": "Refund the program instead.",
                        "program_uuid": str(parent.program.uuid),
                        "program_enrollment_uuid": str(parent.uuid),
                        "program_title": parent.program.title,
                    }},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            stripe_result = refund_payment_intent(
                purchase.stripe_payment_intent_id,
                amount_cents=amount_cents,
                reason="requested_by_customer",
            )
        except Exception as exc:
            return error_response(str(exc), code="REFUND_FAILED", status_code=status.HTTP_400_BAD_REQUEST)

        is_partial = amount_cents is not None and amount_cents < purchase.amount_cents

        with transaction.atomic():
            if not is_partial:
                purchase.status = CoursePurchase.Status.REFUNDED
                purchase.save(update_fields=["status", "updated_at"])
                self._cascade_full_refund(purchase, kind, reason, request.user)

        self._audit(request, purchase, kind, stripe_result, is_partial, reason)

        return Response({
            "purchase_uuid": str(purchase.uuid),
            "kind": kind,
            "status": purchase.status,
            "stripe_refund_id": stripe_result.get("refund_id"),
            "amount_cents": stripe_result.get("amount_cents"),
            "partial": is_partial,
        })

    # ------------------------------------------------------------------

    def _cascade_full_refund(self, purchase, kind, reason, actor):
        from learning.models import CourseEnrollment, ProgramEnrollment
        from registrations.models import Registration

        if kind == "event":
            for reg in purchase.registrations.all():
                if reg.status != Registration.Status.CANCELLED:
                    reg.cancel(reason=reason, cancelled_by=actor)
                elif reason and not reg.cancellation_reason:
                    reg.cancellation_reason = reason
                    reg.save(update_fields=["cancellation_reason", "updated_at"])
                reg.payment_status = Registration.PaymentStatus.REFUNDED
                reg.save(update_fields=["payment_status", "updated_at"])
                try:
                    from promo_codes.models import PromoCodeUsage

                    PromoCodeUsage.release_for_registration(reg)
                except Exception as exc:  # pragma: no cover - defensive
                    logger.warning(
                        "billing.refund.promo_release_failed",
                        extra={"registration_uuid": str(reg.uuid), "error": str(exc)},
                    )

        elif kind == "course":
            CourseEnrollment.objects.filter(
                user=purchase.user, course=purchase.course,
            ).update(status=CourseEnrollment.Status.DROPPED)
            self._release_promo_for_purchase(purchase)

        elif kind == "program":
            program_enrollments = ProgramEnrollment.objects.filter(
                user=purchase.user, program=purchase.program,
            )
            for pe in program_enrollments:
                pe.status = ProgramEnrollment.Status.DROPPED
                pe.save(update_fields=["status", "updated_at"])
                # Cascade-drop only the rows that this program seeded — direct
                # course enrollments (from_program_enrollment IS NULL) keep
                # their access.
                CourseEnrollment.objects.filter(
                    from_program_enrollment=pe,
                ).exclude(status=CourseEnrollment.Status.DROPPED).update(
                    status=CourseEnrollment.Status.DROPPED,
                )
            self._release_promo_for_purchase(purchase)

    def _release_promo_for_purchase(self, purchase):
        try:
            from promo_codes.models import PromoCodeUsage

            PromoCodeUsage.release_for_purchase(purchase)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "billing.refund.promo_release_failed",
                extra={"purchase_uuid": str(purchase.uuid), "error": str(exc)},
            )

    def _audit(self, request, purchase, kind, stripe_result, is_partial, reason):
        try:
            from accounts.audit import log_audit_event

            log_audit_event(
                actor=request.user,
                action="purchase.refunded",
                object_type="CoursePurchase",
                object_uuid=str(purchase.uuid),
                metadata={
                    "kind": kind,
                    "amount_cents": stripe_result.get("amount_cents"),
                    "partial": is_partial,
                    "reason": reason,
                    "stripe_refund_id": stripe_result.get("refund_id"),
                },
                request=request,
            )
        except Exception as exc:  # pragma: no cover - logging should never fail tests
            logger.warning("audit log failed for purchase refund %s: %s", purchase.uuid, exc)
