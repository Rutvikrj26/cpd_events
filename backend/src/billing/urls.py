"""
URL routes for billing API.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BillingPortalView,
    BillingReconciliationView,
    CheckoutSessionView,
    InvoiceViewSet,
    PaymentMethodViewSet,
    PayoutViewSet,
    PublicPricingView,
    RefundView,
    SubscriptionViewSet,
)

router = DefaultRouter()
router.register(r'subscription', SubscriptionViewSet, basename='subscription')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'payment-methods', PaymentMethodViewSet, basename='payment-method')
router.register(r'payouts', PayoutViewSet, basename='payout')

# All billing routes
urlpatterns = [
    # ViewSet routes (subscription/, invoices/, payment-methods/)
    path('', include(router.urls)),
    # Public pricing API (no auth required)
    path('public/pricing/', PublicPricingView.as_view(), name='public-pricing'),
    # Checkout and portal
    path('billing/checkout/', CheckoutSessionView.as_view(), name='checkout'),
    path('billing/portal/', BillingPortalView.as_view(), name='portal'),
    path('registrations/<uuid:registration_uuid>/refund/', RefundView.as_view(), name='refund'),
    path('admin/reconciliation/', BillingReconciliationView.as_view(), name='billing-reconciliation'),
]
