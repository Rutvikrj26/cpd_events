"""
Billing API views.
"""

from rest_framework import viewsets, views, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from common.permissions import IsOwner

from .models import Subscription, Invoice, PaymentMethod
from .serializers import (
    SubscriptionSerializer,
    SubscriptionStatusSerializer,
    SubscriptionCreateSerializer,
    InvoiceSerializer,
    InvoiceListSerializer,
    PaymentMethodSerializer,
    PaymentMethodCreateSerializer,
    CheckoutSessionSerializer,
    BillingPortalSerializer,
)
from .services import stripe_service


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
            user=self.request.user,
            defaults={'plan': Subscription.Plan.FREE}
        )
        return subscription
    
    def list(self, request, *args, **kwargs):
        """Get current subscription."""
        subscription = self.get_object()
        serializer = self.get_serializer(subscription)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """Create or upgrade subscription."""
        serializer = SubscriptionCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        result = stripe_service.create_subscription(
            user=request.user,
            plan=serializer.validated_data['plan'],
            payment_method_id=serializer.validated_data.get('payment_method_id')
        )
        
        if result['success']:
            return Response(
                SubscriptionSerializer(result['subscription']).data,
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(
                {'error': result.get('error', 'Failed to create subscription')},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """Get subscription status (minimal)."""
        subscription = self.get_object()
        serializer = SubscriptionStatusSerializer(subscription)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def cancel(self, request):
        """Cancel subscription."""
        subscription = self.get_object()
        
        if subscription.status == Subscription.Status.CANCELED:
            return Response(
                {'error': 'Subscription already canceled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reason = request.data.get('reason', '')
        immediate = request.data.get('immediate', False)
        
        success = stripe_service.cancel_subscription(
            subscription,
            immediate=immediate,
            reason=reason
        )
        
        if success:
            subscription.refresh_from_db()
            return Response(SubscriptionSerializer(subscription).data)
        else:
            return Response(
                {'error': 'Failed to cancel subscription'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def reactivate(self, request):
        """Reactivate a canceled subscription."""
        subscription = self.get_object()
        
        if not subscription.cancel_at_period_end:
            return Response(
                {'error': 'Subscription is not scheduled for cancellation'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success = stripe_service.reactivate_subscription(subscription)
        
        if success:
            subscription.refresh_from_db()
            return Response(SubscriptionSerializer(subscription).data)
        else:
            return Response(
                {'error': 'Failed to reactivate subscription'},
                status=status.HTTP_400_BAD_REQUEST
            )


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
            set_as_default=serializer.validated_data.get('set_as_default', True)
        )
        
        if result['success']:
            return Response(
                PaymentMethodSerializer(result['payment_method']).data,
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(
                {'error': result.get('error', 'Failed to add payment method')},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, *args, **kwargs):
        payment_method = self.get_object()
        success = stripe_service.detach_payment_method(payment_method)
        
        if success:
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(
                {'error': 'Failed to remove payment method'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, uuid=None):
        """Set payment method as default."""
        payment_method = self.get_object()
        payment_method.set_as_default()
        return Response(PaymentMethodSerializer(payment_method).data)


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
            cancel_url=serializer.validated_data['cancel_url']
        )
        
        if result['success']:
            return Response({
                'session_id': result['session_id'],
                'url': result['url']
            })
        else:
            return Response(
                {'error': result.get('error', 'Failed to create checkout session')},
                status=status.HTTP_400_BAD_REQUEST
            )


class BillingPortalView(views.APIView):
    """
    Create Stripe billing portal session.
    
    POST /billing/portal/
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = BillingPortalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        result = stripe_service.create_portal_session(
            user=request.user,
            return_url=serializer.validated_data['return_url']
        )
        
        if result['success']:
            return Response({'url': result['url']})
        else:
            return Response(
                {'error': result.get('error', 'Failed to create portal session')},
                status=status.HTTP_400_BAD_REQUEST
            )
