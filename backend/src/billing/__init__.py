"""Billing app — Stripe Checkout fulfilment, refunds, disputes, reconciliation.

Single-tenant deployment: the institution owns the Stripe account; learners
pay per event/course/program. CoursePurchase is the unified receipt; refunds
flow through ``views.RefundPurchaseView``; webhooks land in ``handlers``.
"""

default_app_config = 'billing.apps.BillingConfig'
