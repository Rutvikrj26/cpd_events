"""
Billing signals (intentionally inert in single-tenant deployments).

Subscriptions are managed at the institutional level and created explicitly
via checkout, not auto-created per user on signup. The former SaaS path that
seeded an ATTENDEE subscription on user creation is gone along with the
Subscription.Plan enum it depended on.
"""
