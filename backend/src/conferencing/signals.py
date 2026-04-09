"""
Signals for auto-creating video rooms when events/courses enable video.
"""

import logging

from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='events.Event')
def handle_event_video(sender, instance, created, **kwargs):
    """Create a video room when an event has video enabled."""
    video_settings = getattr(instance, 'video_settings', None)
    if not video_settings:
        return

    enabled = video_settings.get('enabled', False) if isinstance(video_settings, dict) else False
    if not enabled:
        return

    from conferencing.models import VideoRoom

    ct = ContentType.objects.get_for_model(instance)
    if VideoRoom.objects.filter(content_type=ct, object_id=instance.id).exists():
        return

    from conferencing.tasks import create_video_room_for_object

    create_video_room_for_object(ct.id, instance.id)


@receiver(post_save, sender='learning.CourseSession')
def handle_course_session_video(sender, instance, created, **kwargs):
    """Create a video room when a course session has video enabled."""
    video_settings = getattr(instance, 'video_settings', None)
    if not video_settings:
        return

    enabled = video_settings.get('enabled', False) if isinstance(video_settings, dict) else False
    if not enabled:
        return

    from conferencing.models import VideoRoom

    ct = ContentType.objects.get_for_model(instance)
    if VideoRoom.objects.filter(content_type=ct, object_id=instance.id).exists():
        return

    from conferencing.tasks import create_video_room_for_object

    create_video_room_for_object(ct.id, instance.id)
