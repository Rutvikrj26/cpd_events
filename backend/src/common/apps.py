from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'common'
    verbose_name = 'Common'

    def ready(self):
        """Import views to register @roles decorators in ROUTE_REGISTRY."""
        # Import views that use @roles decorator to populate the registry
        try:
            import events.views  # noqa: F401
            import registrations.views  # noqa: F401
        except ImportError:
            pass  # Apps not yet loaded

