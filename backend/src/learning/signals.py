"""
Learning signals for progress tracking.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ContentProgress, ModuleProgress


@receiver(post_save, sender=ContentProgress)
def update_module_progress_on_content_complete(sender, instance, **kwargs):
    """Update module progress when content is completed."""
    if instance.status == 'completed':
        module_prog, created = ModuleProgress.objects.get_or_create(
            registration=instance.registration, module=instance.content.module
        )
        module_prog.update_from_content()
