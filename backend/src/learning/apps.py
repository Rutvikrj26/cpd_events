"""Learning app configuration."""

from django.apps import AppConfig


class LearningConfig(AppConfig):
    """Configuration for the learning app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'learning'
    verbose_name = 'Learning & Assignments'
    
    def ready(self):
        """Import signals when app is ready."""
        try:
            import learning.signals  # noqa
        except ImportError:
            pass
