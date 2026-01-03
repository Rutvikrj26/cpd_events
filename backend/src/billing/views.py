"""
Billing API views.
"""

from rest_framework import permissions, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.rbac import roles
from .models import Invoice, PaymentMethod, Subscription, StripeProduct
from .serializers import (
    BillingPortalSerializer,
    CheckoutSessionSerializer,
    InvoiceListSerializer,
    InvoiceSerializer,
    PaymentMethodCreateSerializer,
    PaymentMethodSerializer,
    SubscriptionCreateSerializer,
    SubscriptionUpdateSerializer,
    SubscriptionSerializer,
    SubscriptionStatusSerializer,
    StripeProductPublicSerializer,
)
from .services import stripe_service
from common.utils import error_response
from drf_yasg.utils import swagger_auto_schema


@roles('attendee', 'organizer', 'admin', route_name='subscriptions')
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
        subscription, _ = Subscription.objects.get_or_create(user=self.request.user, defaults={'plan': Subscription.Plan.ATTENDEE})
        return subscription

    def list(self, request, *args, **kwargs):
        """Get current subscription."""
        subscription = self.get_object()
        serializer = self.get_serializer(subscription)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """Create or upgrade subscription."""
        serializer = SubscriptionCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        result = stripe_service.create_subscription(
            user=request.user,
            plan=serializer.validated_data['plan'],
            payment_method_id=serializer.validated_data.get('payment_method_id'),
        )

        if result['success']:
            return Response(SubscriptionSerializer(result['subscription']).data, status=status.HTTP_201_CREATED)
        else:
            return error_response(result.get('error', 'Failed to create subscription'), code='SUBSCRIPTION_FAILED')

    @swagger_auto_schema(
        operation_summary="Update subscription plan",
        operation_description="Update existing subscription to a new plan. Upgrades are immediate with proration. Downgrades can be immediate or at period end.",
        request_body=SubscriptionUpdateSerializer,
        responses={200: SubscriptionSerializer, 400: '{"error": "..."}'},
    )
    def update(self, request, *args, **kwargs):
        """Update subscription plan."""
        subscription = self.get_object()
        serializer = SubscriptionUpdateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        new_plan = serializer.validated_data['plan']
        immediate = serializer.validated_data.get('immediate', True)

        result = stripe_service.update_subscription(
            subscription=subscription,
            new_plan=new_plan,
            immediate=immediate,
        )

        if result['success']:
            subscription.refresh_from_db()
            return Response(SubscriptionSerializer(subscription).data)
        else:
            return error_response(result.get('error', 'Failed to update subscription'), code='UPDATE_FAILED')

    def partial_update(self, request, *args, **kwargs):
        """Same as update for subscription."""
        return self.update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Subscription status",
        operation_description="Get minimal subscription status information.",
        responses={200: SubscriptionStatusSerializer},
    )
    @action(detail=False, methods=['get'])
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
    @action(detail=False, methods=['post'])
    def cancel(self, request):
        """Cancel subscription."""
        subscription = self.get_object()

        if subscription.status == Subscription.Status.CANCELED:
            return error_response('Subscription already canceled', code='ALREADY_CANCELED')

        reason = request.data.get('reason', '')
        immediate = request.data.get('immediate', False)

        success = stripe_service.cancel_subscription(subscription, immediate=immediate, reason=reason)

        if success:
            subscription.refresh_from_db()
            return Response(SubscriptionSerializer(subscription).data)
        else:
            return error_response('Failed to cancel subscription', code='CANCELLATION_FAILED')

    @swagger_auto_schema(
        operation_summary="Reactivate subscription",
        operation_description="Reactivate a subscription that is scheduled for cancellation.",
        responses={200: SubscriptionSerializer, 400: '{"error": "..."}'},
    )
    @action(detail=False, methods=['post'])
    def reactivate(self, request):
        """Reactivate a canceled subscription."""
        subscription = self.get_object()

        if not subscription.cancel_at_period_end:
            return error_response('Subscription is not scheduled for cancellation', code='NOT_CANCELLING')

        success = stripe_service.reactivate_subscription(subscription)

        if success:
            subscription.refresh_from_db()
            return Response(SubscriptionSerializer(subscription).data)
        else:
            return error_response('Failed to reactivate subscription', code='REACTIVATION_FAILED')

    @swagger_auto_schema(
        operation_summary="Sync subscription",
        operation_description="Force sync subscription status from Stripe (useful when webhooks are missing).",
        responses={200: SubscriptionSerializer, 400: '{"error": "..."}'},
    )
    @action(detail=False, methods=['post'])
    def sync(self, request):
        """Force sync subscription from Stripe."""
        result = stripe_service.sync_subscription(request.user)

        if result['success']:
            return Response(SubscriptionSerializer(result['subscription']).data)
        else:
            return error_response(result.get('error', 'Failed to sync subscription'), code='SYNC_FAILED')

    @swagger_auto_schema(
        operation_summary="Confirm checkout",
        operation_description="Confirm checkout session completion. Called by frontend after returning from Stripe Checkout. Atomically syncs subscription from Stripe.",
        responses={
            200: SubscriptionSerializer,
            400: '{"error": {"code": "...", "message": "..."}}',
        },
    )
    @action(detail=False, methods=['post'], url_path='confirm-checkout')
    def confirm_checkout(self, request):
        """
        Confirm checkout session completion.

        Called by frontend after returning from Stripe Checkout.
        Atomically syncs subscription from Stripe.

        Expected request body:
            {"session_id": "cs_xxx"}
        """
        session_id = request.data.get('session_id')
        if not session_id:
            return error_response('session_id is required', code='MISSING_SESSION_ID')

        result = stripe_service.confirm_checkout_session(
            user=request.user,
            session_id=session_id,
        )

        if result['success']:
            return Response(SubscriptionSerializer(result['subscription']).data)
        else:
            return error_response(result.get('error', 'Checkout confirmation failed'), code='CHECKOUT_CONFIRMATION_FAILED')


@roles('attendee', 'organizer', 'admin', route_name='invoices')
class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Invoice history for the authenticated user.

    GET /users/me/invoices/ - List invoices
    GET /users/me/invoices/{uuid}/ - Invoice detail
    """

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'

    def get_queryset(self):
        return Invoice.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'list':
            return InvoiceListSerializer
        return InvoiceSerializer


@roles('attendee', 'organizer', 'admin', route_name='payment_methods')
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
    lookup_field = 'uuid'
    http_method_names = ['get', 'post', 'delete']

    def get_queryset(self):
        return PaymentMethod.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = PaymentMethodCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = stripe_service.attach_payment_method(
            user=request.user,
            payment_method_id=serializer.validated_data['stripe_payment_method_id'],
            set_as_default=serializer.validated_data.get('set_as_default', True),
        )

        if result['success']:
            return Response(PaymentMethodSerializer(result['payment_method']).data, status=status.HTTP_201_CREATED)
        else:
            return error_response(result.get('error', 'Failed to add payment method'), code='PAYMENT_METHOD_FAILED')

    def destroy(self, request, *args, **kwargs):
        payment_method = self.get_object()
        success = stripe_service.detach_payment_method(payment_method)

        if success:
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return error_response('Failed to remove payment method', code='DELETE_FAILED')

    @swagger_auto_schema(
        operation_summary="Set default payment method",
        operation_description="Set this payment method as the default.",
        responses={200: PaymentMethodSerializer},
    )
    @action(detail=True, methods=['post'])
    def set_default(self, request, uuid=None):
        """Set payment method as default."""
        payment_method = self.get_object()
        payment_method.set_as_default()
        return Response(PaymentMethodSerializer(payment_method).data)


@roles('attendee', 'organizer', 'admin', route_name='checkout_session')
class CheckoutSessionView(views.APIView):
    """
    Create Stripe checkout session.

    POST /billing/checkout/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CheckoutSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = stripe_service.create_checkout_session(
            user=request.user,
            plan=serializer.validated_data['plan'],
            success_url=serializer.validated_data['success_url'],
            cancel_url=serializer.validated_data['cancel_url'],
        )

        if result['success']:
            return Response({'session_id': result['session_id'], 'url': result['url']})
        else:
            return error_response(result.get('error', 'Failed to create checkout session'), code='CHECKOUT_FAILED')


@roles('attendee', 'organizer', 'admin', route_name='billing_portal')
class BillingPortalView(views.APIView):
    """
    Create Stripe billing portal session.

    POST /billing/portal/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = BillingPortalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = stripe_service.create_portal_session(user=request.user, return_url=serializer.validated_data['return_url'])

        if result['success']:
            return Response({'url': result['url']})
        else:
            return error_response(result.get('error', 'Failed to create portal session'), code='PORTAL_FAILED')





@roles('public', route_name='public_pricing')
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
        from django.db.models import Case, When, IntegerField

        # Only return active products, ordered by price (low to high)
        # Custom ordering: professional (lower price) first, then organization
        # Exclude 'attendee' (free tier) and legacy plans
        products = StripeProduct.objects.filter(
            is_active=True,
            plan__in=['professional', 'organization']
        ).prefetch_related('prices').annotate(
            plan_order=Case(
                When(plan='professional', then=1),
                When(plan='organization', then=2),
                default=3,
                output_field=IntegerField(),
            )
        ).order_by('plan_order')

        serializer = StripeProductPublicSerializer(products, many=True)
        return Response(serializer.data)
