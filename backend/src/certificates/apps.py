from django.apps import AppConfig


class CertificatesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'certificates'
    verbose_name = 'Certificates'

    def ready(self):
        # Wire up the User.total_cpd_credits recompute on Certificate save/delete.
        from . import signals  # noqa: F401
