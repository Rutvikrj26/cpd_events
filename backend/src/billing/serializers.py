"""
Serializers for billing API.

This module was a vestige of the multi-tenant SaaS Stripe integration. Its
module-level imports referenced models that no longer exist on the trimmed
single-tenant Subscription model (StripeProduct, StripePrice, PayoutRequest),
which would have raised ImportError on any attempt to use it.

Nothing currently imports from this module — the active views in billing/views.py
declare inline serializers. If a shared serializer is needed later for the
institutional subscription flow, add it here against the current models only
(Subscription, Invoice, PaymentMethod, RefundRecord, InstitutionPlan,
InstitutionBillingConfig, CoursePurchase).
"""
