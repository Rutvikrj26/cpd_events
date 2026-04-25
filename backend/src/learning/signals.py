"""
Signals for the learning app.

Course-flow lifecycle:
- On a new ``CourseEnrollment`` (created=True): fire enrollment confirmation
  email + Notification.
- When ``CourseEnrollment.status`` transitions to COMPLETED: fire
  course-completion summary email + Notification.

Both paths are idempotent at the task level (``EmailLog`` is the source of
truth), so retries / signal storms are safe no-ops.
"""

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(pre_save, sender='learning.CourseEnrollment')
def _capture_enrollment_state(sender, instance, **kwargs):
    """Stash old status so post_save can detect the COMPLETED transition."""
    if instance.pk is None:
        instance._old_status = None
        return
    try:
        prev = sender.objects.only('status').get(pk=instance.pk)
        instance._old_status = prev.status
    except sender.DoesNotExist:
        instance._old_status = None


@receiver(post_save, sender='learning.CourseEnrollment')
def _enrollment_lifecycle(sender, instance, created, **kwargs):
    """Fire enrollment-confirmation and course-completion tasks at the right
    moments. Wrapped in try/except so a transient task-queue failure can't
    roll back the model save (matches the same pattern in events/signals.py).
    """
    from learning.tasks import send_course_completed, send_enrollment_confirmation

    old_status = getattr(instance, '_old_status', None)

    if created and instance.status == sender.Status.ACTIVE:
        try:
            send_enrollment_confirmation.delay(instance.id)
        except Exception:
            logger.exception("Failed to enqueue enrollment confirmation for %s", instance.id)

    if (
        not created
        and instance.status == sender.Status.COMPLETED
        and old_status != sender.Status.COMPLETED
    ):
        try:
            send_course_completed.delay(instance.id)
        except Exception:
            logger.exception("Failed to enqueue course completion email for %s", instance.id)
