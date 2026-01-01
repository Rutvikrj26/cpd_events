"""Organizations app configuration."""

from django.apps import AppConfig


class OrganizationsConfig(AppConfig):
    """Configuration for the organizations app."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'organizations'
    verbose_name = 'Organizations'

    def ready(self):
        """Import signals when app is ready."""
        try:
            import organizations.signals  # noqa: F401
        except ImportError:
            pass

