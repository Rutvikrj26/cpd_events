from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'common'
    verbose_name = 'Common'

    def ready(self):
        """Import views to register @roles decorators in ROUTE_REGISTRY."""
        # Import all views that use @roles decorator to populate the registry
        try:
            import accounts.views  # noqa: F401
            import billing.views  # noqa: F401
            import certificates.views  # noqa: F401
            import contacts.views  # noqa: F401
            import events.views  # noqa: F401
            import feedback.views  # noqa: F401
            import integrations.views  # noqa: F401
            import learning.views  # noqa: F401
            import organizations.views  # noqa: F401
            import promo_codes.views  # noqa: F401
            import registrations.views  # noqa: F401
        except ImportError:
            pass  # Apps not yet loaded
