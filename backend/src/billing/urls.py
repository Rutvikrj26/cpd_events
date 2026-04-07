"""
URL routes for billing API.

Institutional billing endpoints:
- Admin: configure billing, manage plans
- Learner: view plans, subscribe, manage subscription
"""

from django.urls import path

from . import views

urlpatterns = [
    # Admin billing configuration
    path('admin/billing/config/', views.BillingConfigView.as_view(), name='billing-config'),
    path('admin/billing/plans/', views.InstitutionPlanListCreateView.as_view(), name='institution-plans'),
    path('admin/billing/plans/<uuid:uuid>/', views.InstitutionPlanDetailView.as_view(), name='institution-plan-detail'),

    # Learner-facing
    path('billing/plans/', views.PublicPlanListView.as_view(), name='public-plans'),
    path('billing/my-subscription/', views.MySubscriptionView.as_view(), name='my-subscription'),
]
