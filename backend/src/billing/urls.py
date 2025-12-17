"""
URL routes for billing API.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BillingPortalView,
    CheckoutSessionView,
    InvoiceViewSet,
    PaymentMethodViewSet,
    SubscriptionViewSet,
)

router = DefaultRouter()
router.register(r'subscription', SubscriptionViewSet, basename='subscription')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'payment-methods', PaymentMethodViewSet, basename='payment-method')

# User nested routes - these will be added to accounts/urls.py
user_billing_patterns = [
    path('', include(router.urls)),
]

# Top-level billing routes
urlpatterns = [
    path('billing/checkout/', CheckoutSessionView.as_view(), name='checkout'),
    path('billing/portal/', BillingPortalView.as_view(), name='portal'),
]
