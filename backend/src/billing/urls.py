"""URL routes for the billing API.

Two surfaces:

- **Admin observability** under ``/admin/billing/...`` — StripeEvent
  listing/retry, Dispute listing/detail, on-demand reconciliation.
- **Learner-/staff-facing** under ``/billing/...`` — verify-session
  (CheckoutReturn polling) and the unified purchase refund endpoint.

Stripe checkouts themselves run through the webhook endpoint at
``/api/v1/webhooks/stripe/`` (mounted from ``config/urls.py``, not here).
"""

from django.urls import path

from . import views

urlpatterns = [
    # Stripe Events (webhook idempotency table + retry)
    path(
        "admin/billing/stripe-events/",
        views.AdminStripeEventListView.as_view(),
        name="admin-stripe-events",
    ),
    path(
        "admin/billing/stripe-events/<str:event_id>/",
        views.AdminStripeEventDetailView.as_view(),
        name="admin-stripe-event-detail",
    ),
    path(
        "admin/billing/stripe-events/<str:event_id>/retry/",
        views.AdminStripeEventRetryView.as_view(),
        name="admin-stripe-event-retry",
    ),
    # Disputes
    path(
        "admin/billing/disputes/",
        views.AdminDisputeListView.as_view(),
        name="admin-disputes",
    ),
    path(
        "admin/billing/disputes/<uuid:uuid>/",
        views.AdminDisputeDetailView.as_view(),
        name="admin-dispute-detail",
    ),
    # Stripe reconciliation (admin-triggered sync drift check)
    path(
        "admin/billing/reconcile/",
        views.AdminReconcileView.as_view(),
        name="admin-reconcile",
    ),
    # Learner-/staff-facing
    path(
        "billing/verify-session/",
        views.VerifySessionView.as_view(),
        name="billing-verify-session",
    ),
    path(
        "billing/purchases/<uuid:uuid>/refund/",
        views.RefundPurchaseView.as_view(),
        name="purchase-refund",
    ),
]
