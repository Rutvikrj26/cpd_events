from django.apps import AppConfig


class ConferencingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'conferencing'
    verbose_name = 'Video Conferencing'

    def ready(self):
        import conferencing.signals  # noqa: F401
