"""
Billing API views.
"""

from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, serializers, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.audit import log_audit_event
from billing.capability_service import capability_service
from common.utils import error_response
from registrations.models import Registration

from .models import Invoice, PaymentMethod, PayoutRequest, RefundRecord, StripePrice, StripeProduct, Subscription
from .serializers import (
    BillingPortalSerializer,
    CheckoutSessionSerializer,
    InvoiceListSerializer,
    InvoiceSerializer,
    PaymentMethodCreateSerializer,
    PaymentMethodSerializer,
    PayoutRequestSerializer,
    RefundRecordSerializer,
    RefundRequestSerializer,
    StripeProductPublicSerializer,
    SubscriptionCreateSerializer,
    SubscriptionSerializer,
    SubscriptionStatusSerializer,
    SubscriptionUpdateSerializer,
)
from .services import RefundService, stripe_connect_service, stripe_service


class SubscriptionViewSet(viewsets.GenericViewSet):
    """
    Subscription management for the authenticated user.

    GET /users/me/subscription/ - Get current subscription
    POST /users/me/subscription/ - Create/update subscription
    POST /users/me/subscription/cancel/ - Cancel subscription
    POST /users/me/subscription/reactivate/ - Reactivate subscription
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SubscriptionSerializer

    def get_object(self):
        """Get or create subscription for current user."""
        subscription, _ = Subscription.objects.get_or_create(
            user=self.request.user, defaults={"plan": Subscription.Plan.ATTENDEE}
        )
        return subscription

    def list(self, request, *args, **kwargs):
        """Get current subscription."""
        subscription = self.get_object()
        serializer = self.get_serializer(subscription)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """Create or upgrade subscription."""
        serializer = SubscriptionCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        subscription = self.get_object()
        plan = serializer.validated_data["plan"]
        billing_interval = serializer.validated_data.get("billing_interval", "month")
        if subscription.plan == plan and subscription.billing_interval == billing_interval:
            return Response(SubscriptionSerializer(subscription).data, status=status.HTTP_200_OK)

        result = stripe_service.create_subscription(
            user=request.user,
            plan=plan,
            payment_method_id=serializer.validated_data.get("payment_method_id"),
            billing_interval=billing_interval,
        )

        if result["success"]:
            try:
                log_audit_event(
                    actor=request.user,
                    action="subscription_created",
                    object_type="subscription",
                    object_uuid=str(result["subscription"].uuid),
                    metadata={"plan": result["subscription"].plan},
                    request=request,
                )
            except Exception:
                pass
            return Response(SubscriptionSerializer(result["subscription"]).data, status=status.HTTP_201_CREATED)
        else:
            return error_response(result.get("error", "Failed to create subscription"), code="SUBSCRIPTION_FAILED")

    @swagger_auto_schema(
        operation_summary="Update subscription plan",
        operation_description="Update existing subscription to a new plan. Upgrades are immediate with proration. Downgrades can be immediate or at period end.",
        request_body=SubscriptionUpdateSerializer,
        responses={200: SubscriptionSerializer, 400: '{"error": "..."}'},
    )
    def update(self, request, *args, **kwargs):
        """Update subscription plan."""
        subscription = self.get_object()
        serializer = SubscriptionUpdateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        new_plan = serializer.validated_data["plan"]
        immediate = serializer.validated_data.get("immediate", True)
        billing_interval = serializer.validated_data.get("billing_interval", "month")

        result = stripe_service.update_subscription(
            subscription=subscription,
            new_plan=new_plan,
            immediate=immediate,
            billing_interval=billing_interval,
        )

        if result["success"]:
            subscription.refresh_from_db()
            try:
                log_audit_event(
                    actor=request.user,
                    action="subscription_updated",
                    object_type="subscription",
                    object_uuid=str(subscription.uuid),
                    metadata={"plan": subscription.plan},
                    request=request,
                )
            except Exception:
                pass
            return Response(SubscriptionSerializer(subscription).data)
        else:
            return error_response(result.get("error", "Failed to update subscription"), code="UPDATE_FAILED")

    def partial_update(self, request, *args, **kwargs):
        """Same as update for subscription."""
        return self.update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Subscription status",
        operation_description="Get minimal subscription status information.",
        responses={200: SubscriptionStatusSerializer},
    )
    @action(detail=False, methods=["get"])
    def status(self, request):
        """Get subscription status (minimal)."""
        subscription = self.get_object()
        serializer = SubscriptionStatusSerializer(subscription)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary="Cancel subscription",
        operation_description="Cancel the current subscription.",
        responses={200: SubscriptionSerializer, 400: '{"error": "..."}'},
    )
    @action(detail=False, methods=["post"])
    def cancel(self, request):
        """Cancel subscription."""
        subscription = self.get_object()

        if subscription.status == Subscription.Status.CANCELED:
            return error_response("Subscription already canceled", code="ALREADY_CANCELED")

        reason = request.data.get("reason", "")
        immediate = request.data.get("immediate", False)

        success = stripe_service.cancel_subscription(subscription, immediate=immediate, reason=reason)

        if success:
            subscription.refresh_from_db()
            try:
                log_audit_event(
                    actor=request.user,
                    action="subscription_cancelled",
                    object_type="subscription",
                    object_uuid=str(subscription.uuid),
                    metadata={"plan": subscription.plan, "immediate": immediate},
                    request=request,
                )
            except Exception:
                pass
            return Response(SubscriptionSerializer(subscription).data)
        else:
            return error_response("Failed to cancel subscription", code="CANCELLATION_FAILED")

    @swagger_auto_schema(
        operation_summary="Reactivate subscription",
        operation_description="Reactivate a subscription that is scheduled for cancellation.",
        responses={200: SubscriptionSerializer, 400: '{"error": "..."}'},
    )
    @action(detail=False, methods=["post"])
    def reactivate(self, request):
        """Reactivate a canceled subscription."""
        subscription = self.get_object()

        if not subscription.cancel_at_period_end:
            return error_response("Subscription is not scheduled for cancellation", code="NOT_CANCELLING")

        success = stripe_service.reactivate_subscription(subscription)

        if success:
            subscription.refresh_from_db()
            try:
                log_audit_event(
                    actor=request.user,
                    action="subscription_reactivated",
                    object_type="subscription",
                    object_uuid=str(subscription.uuid),
                    metadata={"plan": subscription.plan},
                    request=request,
                )
            except Exception:
                pass
            return Response(SubscriptionSerializer(subscription).data)
        else:
            return error_response("Failed to reactivate subscription", code="REACTIVATION_FAILED")

    @swagger_auto_schema(
        operation_summary="Sync subscription",
        operation_description="Force sync subscription status from Stripe (useful when webhooks are missing).",
        responses={200: SubscriptionSerializer, 400: '{"error": "..."}'},
    )
    @action(detail=False, methods=["post"])
    def sync(self, request):
        """Force sync subscription from Stripe."""
        result = stripe_service.sync_subscription(request.user)

        if result["success"]:
            stripe_service.sync_payment_methods(
                user=request.user,
                customer_id=result["subscription"].stripe_customer_id,
            )
            return Response(SubscriptionSerializer(result["subscription"]).data)
        else:
            return error_response(result.get("error", "Failed to sync subscription"), code="SYNC_FAILED")

    @swagger_auto_schema(
        operation_summary="Confirm checkout",
        operation_description="Confirm checkout session completion. Called by frontend after returning from Stripe Checkout. Atomically syncs subscription from Stripe.",
        responses={
            200: SubscriptionSerializer,
            400: '{"error": {"code": "...", "message": "..."}}',
        },
    )
    @action(detail=False, methods=["post"], url_path="confirm-checkout")
    def confirm_checkout(self, request):
        """
        Confirm checkout session completion.

        Called by frontend after returning from Stripe Checkout.
        Atomically syncs subscription from Stripe.

        Expected request body:
            {"session_id": "cs_xxx"}
        """
        session_id = request.data.get("session_id")
        if not session_id:
            return error_response("session_id is required", code="MISSING_SESSION_ID")

        result = stripe_service.confirm_checkout_session(
            user=request.user,
            session_id=session_id,
        )

        if result["success"]:
            return Response(SubscriptionSerializer(result["subscription"]).data)
        else:
            return error_response(result.get("error", "Checkout confirmation failed"), code="CHECKOUT_CONFIRMATION_FAILED")


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Invoice history for the authenticated user.

    GET /users/me/invoices/ - List invoices
    GET /users/me/invoices/{uuid}/ - Invoice detail
    """

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "uuid"

    def get_queryset(self):
        return Invoice.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return InvoiceListSerializer
        return InvoiceSerializer

    def retrieve(self, request, *args, **kwargs):
        invoice = self.get_object()
        if invoice.stripe_invoice_id and stripe_service.is_configured:
            stripe_invoice = stripe_service.get_invoice(invoice.stripe_invoice_id)
            if stripe_invoice:
                invoice.invoice_pdf_url = getattr(stripe_invoice, "invoice_pdf", "") or invoice.invoice_pdf_url
                invoice.hosted_invoice_url = getattr(stripe_invoice, "hosted_invoice_url", "") or invoice.hosted_invoice_url
                invoice.save(update_fields=["invoice_pdf_url", "hosted_invoice_url", "updated_at"])
        serializer = self.get_serializer(invoice)
        return Response(serializer.data)


class PaymentMethodViewSet(viewsets.ModelViewSet):
    """
    Payment method management.

    GET /users/me/payment-methods/ - List payment methods
    POST /users/me/payment-methods/ - Add payment method
    DELETE /users/me/payment-methods/{uuid}/ - Remove payment method
    POST /users/me/payment-methods/{uuid}/set-default/ - Set as default
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PaymentMethodSerializer
    lookup_field = "uuid"
    http_method_names = ["get", "post", "delete"]

    def get_queryset(self):
        return PaymentMethod.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = PaymentMethodCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = stripe_service.attach_payment_method(
            user=request.user,
            payment_method_id=serializer.validated_data["stripe_payment_method_id"],
            set_as_default=serializer.validated_data.get("set_as_default", True),
        )

        if result["success"]:
            try:
                log_audit_event(
                    actor=request.user,
                    action="payment_method_added",
                    object_type="payment_method",
                    object_uuid=str(result["payment_method"].uuid),
                    metadata={"brand": result["payment_method"].card_brand, "last4": result["payment_method"].card_last4},
                    request=request,
                )
            except Exception:
                pass
            return Response(PaymentMethodSerializer(result["payment_method"]).data, status=status.HTTP_201_CREATED)
        else:
            return error_response(result.get("error", "Failed to add payment method"), code="PAYMENT_METHOD_FAILED")

    def destroy(self, request, *args, **kwargs):
        payment_method = self.get_object()
        subscription = capability_service.get_subscription(request.user)
        if (
            subscription
            and subscription.status in [Subscription.Status.ACTIVE, Subscription.Status.TRIALING]
            and PaymentMethod.objects.filter(user=request.user).count() <= 1
        ):
            return error_response("Cannot delete the only payment method", code="LAST_PAYMENT_METHOD")
        success = stripe_service.detach_payment_method(payment_method)

        if success:
            try:
                log_audit_event(
                    actor=request.user,
                    action="payment_method_removed",
                    object_type="payment_method",
                    object_uuid=str(payment_method.uuid),
                    metadata={"brand": payment_method.card_brand, "last4": payment_method.card_last4},
                    request=request,
                )
            except Exception:
                pass
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return error_response("Failed to remove payment method", code="DELETE_FAILED")

    @swagger_auto_schema(
        operation_summary="Set default payment method",
        operation_description="Set this payment method as the default.",
        responses={200: PaymentMethodSerializer},
    )
    @action(detail=True, methods=["post"])
    def set_default(self, request, uuid=None):
        """Set payment method as default."""
        payment_method = self.get_object()
        payment_method.set_as_default()
        try:
            log_audit_event(
                actor=request.user,
                action="payment_method_default_set",
                object_type="payment_method",
                object_uuid=str(payment_method.uuid),
                metadata={"brand": payment_method.card_brand, "last4": payment_method.card_last4},
                request=request,
            )
        except Exception:
            pass
        return Response(PaymentMethodSerializer(payment_method).data)


class CheckoutSessionView(views.APIView):
    """
    Create Stripe checkout session.

    POST /billing/checkout/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CheckoutSessionSerializer(data=request.data)

        if not serializer.is_valid():
            logger.warning(
                "Checkout session validation failed",
                extra={
                    "errors": serializer.errors,
                    "user_uuid": str(request.user.uuid),
                    "data_keys": list(request.data.keys()),
                },
            )
        serializer.is_valid(raise_exception=True)

        result = stripe_service.create_checkout_session(
            user=request.user,
            plan=serializer.validated_data["plan"],
            success_url=serializer.validated_data["success_url"],
            cancel_url=serializer.validated_data["cancel_url"],
            billing_interval=serializer.validated_data.get("billing_interval", "month"),
        )

        if result["success"]:
            return Response({"session_id": result["session_id"], "url": result["url"]})
        else:
            return error_response(result.get("error", "Failed to create checkout session"), code="CHECKOUT_FAILED")


class BillingPortalView(views.APIView):
    """
    Create Stripe billing portal session.

    POST /billing/portal/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = BillingPortalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = stripe_service.create_portal_session(user=request.user, return_url=serializer.validated_data["return_url"])

        if result["success"]:
            return Response({"url": result["url"]})
        else:
            return error_response(result.get("error", "Failed to create portal session"), code="PORTAL_FAILED")


class PublicPricingView(views.APIView):
    """
    Public API to fetch current pricing from database.

    GET /api/public/pricing/

    Returns all active products with their prices configured in Django Admin.
    No authentication required - this is for displaying pricing on public pages.
    """

    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_summary="Get current pricing",
        operation_description="Fetches all active pricing products and prices from database (configured via Django Admin)",
        responses={200: StripeProductPublicSerializer(many=True)},
    )
    def get(self, request):
        """Get all active pricing products."""
        from django.db.models import Case, IntegerField, Prefetch, When

        # Only return active products, ordered by price (low to high)
        # Custom ordering: organizer, lms, then pro
        # Exclude 'attendee' (free tier) and legacy plans
        products = (
            StripeProduct.objects.filter(is_active=True, plan__in=["organizer", "lms", "pro"])
            .prefetch_related(Prefetch("prices", queryset=StripePrice.objects.filter(is_active=True)))
            .annotate(
                plan_order=Case(
                    When(plan="organizer", then=1),
                    When(plan="lms", then=2),
                    When(plan="pro", then=3),
                    default=3,
                    output_field=IntegerField(),
                )
            )
            .order_by("plan_order")
        )

        serializer = StripeProductPublicSerializer(products, many=True)
        return Response(serializer.data)


class RefundView(views.APIView):
    """
    Process a refund for a registration.

    POST /registrations/{uuid}/refund/
    """

    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Process refund",
        operation_description="Refund a registration (full or partial).",
        request_body=serializers.Serializer(),  # Define a proper serializer for request body validation if needed
        responses={200: RefundRecordSerializer, 400: '{"error": "..."}'},
    )
    def post(self, request, registration_uuid):
        try:
            registration = Registration.objects.get(uuid=registration_uuid)
        except Registration.DoesNotExist:
            return error_response("Registration not found", code="NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND)

        # Permission check: Only admin or event owner can refund
        is_admin = request.user.role == "admin" or request.user.is_superuser
        is_owner = registration.event.owner == request.user

        if not (is_admin or is_owner):
            return error_response("Permission denied", code="PERMISSION_DENIED", status_code=status.HTTP_403_FORBIDDEN)

        amount_cents = request.data.get("amount_cents")  # Optional, defaults to full
        reason = request.data.get("reason", "requested_by_customer")

        refund_service = RefundService()
        result = refund_service.process_refund(
            registration=registration, amount_cents=amount_cents, reason=reason, processed_by=request.user
        )

        if result["success"]:
            # Return the created refund record
            refund_record = RefundRecord.objects.filter(stripe_refund_id=result["refund_id"]).first()
            try:
                log_audit_event(
                    actor=request.user,
                    action="refund_processed",
                    object_type="registration",
                    object_uuid=str(registration.uuid),
                    metadata={"refund_id": result["refund_id"]},
                    request=request,
                )
            except Exception:
                pass
            return Response(RefundRecordSerializer(refund_record).data)
        else:
            return error_response(result.get("error", "Refund failed"), code="REFUND_FAILED")


class PayoutViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Payout management for organizers.

    GET /payouts/ - List payout history
    POST /payouts/request/ - Request manual payout
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PayoutRequestSerializer

    def get_queryset(self):
        return PayoutRequest.objects.filter(user=self.request.user).order_by("-created_at")

    @swagger_auto_schema(
        operation_summary="Request payout",
        operation_description="Initiate a manual payout to the external bank account.",
        request_body=serializers.Serializer(),  # Define schema for amount
        responses={200: PayoutRequestSerializer, 400: '{"error": "..."}'},
    )
    @action(detail=False, methods=["post"])
    def request(self, request):
        amount_cents = request.data.get("amount_cents")
        if not amount_cents:
            return error_response("Amount is required", code="MISSING_AMOUNT")

        currency = request.data.get("currency", "usd")

        result = stripe_connect_service.create_payout(user=request.user, amount_cents=int(amount_cents), currency=currency)

        if result["success"]:
            # Return the created payout request
            # We filter by stripe_payout_id to get the record created in service
            payout = PayoutRequest.objects.get(stripe_payout_id=result["payout_id"])
            return Response(PayoutRequestSerializer(payout).data)
        else:
            return error_response(result.get("error", "Payout failed"), code="PAYOUT_FAILED")

    @action(detail=False, methods=["get"])
    def balance(self, request):
        """Get available balance for payout."""
        balance = stripe_connect_service.get_available_balance(request.user)
        return Response({"available_cents": balance, "currency": "usd"})


class RegistrationRefundView(views.APIView):
    """
    Process refund for a registration.

    POST /api/v1/registrations/{uuid}/refund/

    Body:
        amount_cents (optional): Amount to refund in cents (omit for full refund)
        reason (optional): Refund reason ('requested_by_customer', 'duplicate', 'fraudulent')
        description (optional): Optional notes
    """

    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Refund registration",
        operation_description="Process a refund for a paid event registration. Full or partial refunds supported.",
        request_body=RefundRequestSerializer,
        responses={
            200: RefundRecordSerializer,
            400: '{"error": {"code": "...", "message": "..."}}',
            403: '{"error": {"code": "FORBIDDEN", "message": "..."}}',
            404: '{"error": {"code": "NOT_FOUND", "message": "..."}}',
        },
    )
    def post(self, request, uuid):
        """Process refund for registration."""

        from registrations.models import Registration

        # Validate input
        serializer = RefundRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get registration
        try:
            registration = Registration.objects.select_for_update().get(uuid=uuid, deleted_at__isnull=True)
        except Registration.DoesNotExist:
            return error_response("Registration not found", code="NOT_FOUND", status_code=404)

        # Check ownership (event owner or org admin)
        event = registration.event
        is_owner = event.owner_id == request.user.id
        # Check permissions
        is_owner = event.owner == request.user

        if not (is_owner or request.user.is_staff):
            return error_response("You do not have permission to refund this registration", code="FORBIDDEN", status_code=403)

        # Check refund eligibility
        if registration.payment_status in [Registration.PaymentStatus.NA, Registration.PaymentStatus.REFUNDED]:
            return error_response("This registration is not eligible for refund", code="NOT_ELIGIBLE")

        if registration.payment_status != Registration.PaymentStatus.PAID:
            return error_response("Can only refund paid registrations", code="NOT_PAID")

        # Check refund window (optional - you can add time limits here)
        # Example: No refunds after event has started
        # if registration.event.starts_at and registration.event.starts_at < timezone.now():
        #     return error_response('Cannot refund after event has started', code='EVENT_STARTED')

        # Process refund
        refund_service = RefundService()
        result = refund_service.process_refund(
            registration=registration,
            amount_cents=serializer.validated_data.get("amount_cents"),
            reason=serializer.validated_data.get("reason", "requested_by_customer"),
            processed_by=request.user,
        )

        if result["success"]:
            # Get the created refund record
            refund_record = RefundRecord.objects.filter(stripe_refund_id=result["refund_id"]).first()

            # Log audit event
            try:
                log_audit_event(
                    actor=request.user,
                    action="refund_processed",
                    object_type="registration",
                    object_uuid=str(registration.uuid),
                    metadata={
                        "refund_id": result["refund_id"],
                        "amount_cents": serializer.validated_data.get("amount_cents"),
                        "reason": serializer.validated_data.get("reason"),
                    },
                    request=request,
                )
            except Exception:
                pass

            return Response(
                RefundRecordSerializer(refund_record).data if refund_record else {"refund_id": result["refund_id"]},
                status=status.HTTP_200_OK,
            )
        else:
            return error_response(result.get("error", "Refund failed"), code="REFUND_FAILED")


class BillingReconciliationView(views.APIView):
    """Admin reconciliation snapshot for Stripe vs database payments."""

    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from billing.reconciliation import reconcile_payment_intents

        days = int(request.query_params.get("days", 30))
        limit = int(request.query_params.get("limit", 200))

        result = reconcile_payment_intents(days=days, limit=limit)
        if not result.get("success"):
            return error_response(result.get("error", "Reconciliation failed"), code="RECONCILIATION_FAILED")

        return Response(result)
