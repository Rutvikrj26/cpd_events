"""
Billing API views for institutional deployment.

Admin endpoints for configuring billing and managing plans.
Learner endpoints for viewing plans and managing subscriptions.
"""

from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import serializers as drf_serializers

from common.rbac import roles

from .models import InstitutionBillingConfig, InstitutionPlan, Subscription


# =============================================================================
# Serializers (inline for now — move to serializers.py when needed)
# =============================================================================


class BillingConfigSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = InstitutionBillingConfig
        fields = [
            "uuid", "pricing_model", "stripe_publishable_key",
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


@roles("learner", "educator", "course_manager", "admin", route_name="public_plans")
class PublicPlanListView(generics.ListAPIView):
    """GET /api/v1/billing/plans/ — List available subscription plans."""

    serializer_class = InstitutionPlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return InstitutionPlan.objects.filter(is_active=True)


@roles("learner", "educator", "course_manager", "admin", route_name="my_subscription")
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
