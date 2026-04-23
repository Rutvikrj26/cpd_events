"""
Billing API views for institutional deployment.

Admin endpoints for configuring billing and managing plans.
Learner endpoints for viewing plans and managing subscriptions.
"""

from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers as drf_serializers

from common.rbac import roles

from .checkout import checkout_service
from .models import InstitutionBillingConfig, InstitutionPlan, Subscription


# =============================================================================
# Serializers (inline for now — move to serializers.py when needed)
# =============================================================================


class BillingConfigSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = InstitutionBillingConfig
        fields = [
            "uuid", "pricing_model",
            "default_currency", "tax_enabled", "tax_id",
            "is_stripe_configured", "created_at", "updated_at",
        ]
        read_only_fields = ["uuid", "is_stripe_configured", "created_at", "updated_at"]


class InstitutionPlanSerializer(drf_serializers.ModelSerializer):
    price_display = drf_serializers.CharField(read_only=True)

    class Meta:
        model = InstitutionPlan
        fields = [
            "uuid", "name", "description", "price_cents", "price_display",
            "billing_interval", "includes_all_courses", "max_enrollments",
            "is_active", "is_featured", "sort_order", "features_list",
            "created_at", "updated_at",
        ]
        read_only_fields = ["uuid", "price_display", "created_at", "updated_at"]


class SubscriptionSerializer(drf_serializers.ModelSerializer):
    plan_name = drf_serializers.CharField(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "uuid", "plan_name", "status", "current_period_start",
            "current_period_end", "cancel_at_period_end", "created_at",
        ]
        read_only_fields = fields


# =============================================================================
# Admin Views
# =============================================================================


@roles("admin", route_name="billing_config")
class BillingConfigView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/v1/admin/billing/config/ — Institution billing configuration."""

    serializer_class = BillingConfigSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return InstitutionBillingConfig.get_config()


@roles("admin", route_name="institution_plans")
class InstitutionPlanListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/v1/admin/billing/plans/ — Manage institution plans."""

    serializer_class = InstitutionPlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return InstitutionPlan.objects.all()


@roles("admin", route_name="institution_plan_detail")
class InstitutionPlanDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /api/v1/admin/billing/plans/{uuid}/ — Plan detail."""

    serializer_class = InstitutionPlanSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"

    def get_queryset(self):
        return InstitutionPlan.objects.all()


# =============================================================================
# Learner-Facing Views
# =============================================================================


@roles("learner", "organizer", "instructor", "admin", route_name="public_plans")
class PublicPlanListView(generics.ListAPIView):
    """GET /api/v1/billing/plans/ — List available subscription plans."""

    serializer_class = InstitutionPlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return InstitutionPlan.objects.filter(is_active=True)


class PublicPricingView(generics.ListAPIView):
    """GET /api/v1/public/pricing/ — Unauthenticated list of active plans for the public pricing page."""

    serializer_class = InstitutionPlanSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return InstitutionPlan.objects.filter(is_active=True)


@roles("learner", "organizer", "instructor", "admin", route_name="my_subscription")
class MySubscriptionView(generics.RetrieveAPIView):
    """GET /api/v1/billing/my-subscription/ — Current subscription status."""

    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            return self.request.user.subscription
        except Subscription.DoesNotExist:
            return None

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj is None:
            config = InstitutionBillingConfig.get_config()
            return Response({
                "subscription": None,
                "pricing_model": config.pricing_model,
            })
        serializer = self.get_serializer(obj)
        return Response(serializer.data)


# =============================================================================
# Checkout — subscription signup & Customer Portal
# =============================================================================


class SubscribeView(APIView):
    """POST /api/v1/billing/subscribe/

    Body: ``{"plan_uuid": "..."}``. Returns a Stripe Checkout Session URL
    for subscription signup. Webhook ``customer.subscription.created``
    creates the local ``Subscription`` row on success.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan_uuid = request.data.get("plan_uuid")
        if not plan_uuid:
            return Response({"error": "plan_uuid is required"}, status=400)
        plan = get_object_or_404(InstitutionPlan, uuid=plan_uuid, is_active=True)
        try:
            result = checkout_service.for_subscription(request.user, plan)
        except Exception as exc:
            return Response({"error": str(exc)}, status=400)
        return Response({"session_id": result.session_id, "url": result.url})


class CustomerPortalView(APIView):
    """POST /api/v1/billing/portal/

    Returns a Stripe Customer Portal URL. Portal covers cancel/resume/plan
    switch/card update/invoice history with no UI code on our side.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        return_url = request.data.get("return_url")
        try:
            result = checkout_service.for_customer_portal(request.user, return_url=return_url)
        except Exception as exc:
            return Response({"error": str(exc)}, status=400)
        return Response({"url": result.url})
