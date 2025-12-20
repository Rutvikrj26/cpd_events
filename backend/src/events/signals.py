import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Event
from .tasks import create_zoom_meeting

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Event)
def trigger_zoom_creation(sender, instance, created, **kwargs):
    """
    Trigger Zoom meeting creation when event is created/updated
    with Zoom settings but no meeting ID.
    """
    # Check if we should create a Zoom meeting
    # 1. zoom_settings is present (not empty)
    # 2. zoom_meeting_id is empty (not already created)
    # 3. auto_create is true (optional explicit flag from frontend)
    #    OR just implicit presence of settings
    
    if instance.zoom_settings and not instance.zoom_meeting_id:
        # Check explicit enabled flag if present, otherwise assume implicit
        if instance.zoom_settings.get('enabled', True):
            logger.info(f"Triggering Zoom meeting creation for event {instance.uuid}")
            create_zoom_meeting.delay(instance.id)
