"""Billing app configuration."""

from django.apps import AppConfig


class BillingConfig(AppConfig):
    """Configuration for the billing app."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'billing'
    verbose_name = 'Billing & Subscriptions'

    def ready(self):
        """Import signals when app is ready."""
        try:
            import billing.signals  # noqa
        except ImportError:
            pass
