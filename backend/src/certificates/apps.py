from django.apps import AppConfig


class CertificatesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "certificates"
    verbose_name = "Certificates"

    def ready(self):
        """Import signal handlers when app is ready."""
        import certificates.signals  # noqa: F401
