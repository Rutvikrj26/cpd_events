"""
Signals for auto-creating video rooms when events/courses enable video.
"""

import logging

from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _enqueue_room_creation(ct, object_id):
    """Enqueue room creation, swallowing failures so the model's save() isn't
    rolled back when the provider is unavailable.

    In production (async Cloud Tasks), ``.delay()`` only enqueues — it almost
    always succeeds, and the actual task runs later under the queue's retry
    policy. In dev sync mode, ``.delay()`` runs the task inline; if LiveKit
    is down, the task records an ERROR ``VideoRoom`` row and re-raises. We
    log and continue here so the model save survives.
    """
    from conferencing.tasks import create_video_room_for_object

    try:
        create_video_room_for_object.delay(ct.id, object_id)
    except Exception:
        logger.exception(
            "VideoRoom enqueue failed for %s:%s; continuing — backfill via "
            "`manage.py provision_video_rooms` when the provider is healthy.",
            ct.model, object_id,
        )


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
    if VideoRoom.objects.filter(content_type=ct, object_id=instance.id).exclude(status=VideoRoom.Status.ERROR).exists():
        return

    _enqueue_room_creation(ct, instance.id)


@receiver(post_save, sender='learning.CourseSession')
def handle_course_session_video(sender, instance, created, **kwargs):
    """Create a video room when a course session has video enabled.

    Skipped for in-person sessions: there's no remote stream to host. Hybrid
    sessions still provision a room because remote attendees join via video.
    """
    if instance.delivery_mode == instance.DeliveryMode.IN_PERSON:
        return

    video_settings = getattr(instance, 'video_settings', None)
    if not video_settings:
        return

    enabled = video_settings.get('enabled', False) if isinstance(video_settings, dict) else False
    if not enabled:
        return

    from conferencing.models import VideoRoom

    ct = ContentType.objects.get_for_model(instance)
    if VideoRoom.objects.filter(content_type=ct, object_id=instance.id).exclude(status=VideoRoom.Status.ERROR).exists():
        return

    _enqueue_room_creation(ct, instance.id)
