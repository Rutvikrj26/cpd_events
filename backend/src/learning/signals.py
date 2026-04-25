"""
Signals for the learning app.

Course-flow lifecycle:
- On a new ``CourseEnrollment`` (created=True): fire enrollment confirmation
  email + Notification.
- When ``CourseEnrollment.status`` transitions to COMPLETED: fire
  course-completion summary email + Notification.

Both paths are idempotent at the task level (``EmailLog`` is the source of
truth), so retries / signal storms are safe no-ops.

Course-structure change handling:
- When a ``CourseModule`` is added or removed on a published course, every
  ACTIVE enrollee's ``progress_percent`` becomes stale on read-only surfaces
  (My Learning cards, organizer dashboards). The CourseModule signal below
  recomputes each affected enrollee inline so the next list-view read
  returns fresh values without depending on the player's request-time
  recompute path.
"""

import logging

from django.db.models.signals import post_delete, post_save, pre_save
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


def _recompute_enrollees_for_course(course_id):
    """Refresh progress_percent + modules_completed for every ACTIVE enrollee
    in a course whose structure just changed. update_progress() is a no-op
    for COMPLETED enrollments (historical fact) so they're skipped naturally.
    """
    from learning.models import Course, CourseEnrollment

    if not course_id:
        return
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        return

    # Refresh denormalised module_count first so course list views see it
    # immediately on next read.
    try:
        course.update_counts()
    except Exception:
        logger.exception("Failed to refresh course counts on structure change for course=%s", course_id)

    qs = CourseEnrollment.objects.filter(
        course=course, status=CourseEnrollment.Status.ACTIVE
    )
    for enrollment in qs.iterator():
        try:
            enrollment.update_progress()
        except Exception:
            logger.exception("Failed to recompute progress for enrollment=%s", enrollment.id)


@receiver(pre_save, sender='learning.CourseSession')
def _capture_session_state(sender, instance, **kwargs):
    """Stash the prior status so post_save can detect the CANCELLED transition."""
    if instance.pk is None:
        instance._old_status = None
        return
    try:
        prev = sender.objects.only('status').get(pk=instance.pk)
        instance._old_status = prev.status
    except sender.DoesNotExist:
        instance._old_status = None


@receiver(post_save, sender='learning.CourseSession')
def _session_cancellation_cascade(sender, instance, created, **kwargs):
    """When a session flips to CANCELLED, the completion denominator shrinks
    for every active enrollee. Recompute and notify (D2 in
    docs/design/hybrid-course-experience.md). Attendance rows are preserved
    in the audit log; only the recompute path filters them.
    """
    if created:
        return
    old = getattr(instance, '_old_status', None)
    if instance.status != sender.Status.CANCELLED or old == sender.Status.CANCELLED:
        return

    _recompute_enrollees_for_course(instance.course_id)

    from learning.models import CourseEnrollment
    from learning.tasks import send_session_cancelled

    enrollee_ids = list(
        CourseEnrollment.objects.filter(
            course_id=instance.course_id,
            status=CourseEnrollment.Status.ACTIVE,
        ).values_list('id', flat=True)
    )
    for enr_id in enrollee_ids:
        try:
            send_session_cancelled.delay(enr_id, instance.id)
        except Exception:
            logger.exception(
                "Failed to enqueue session-cancelled email for enrollment=%s session=%s",
                enr_id, instance.id,
            )


@receiver(post_save, sender='learning.CourseModule')
def _coursemodule_added_or_changed(sender, instance, **kwargs):
    """Module added/edited on a course → invalidate every active enrollee."""
    _recompute_enrollees_for_course(instance.course_id)


@receiver(post_delete, sender='learning.CourseModule')
def _coursemodule_removed(sender, instance, **kwargs):
    """Module removed from a course → recompute remaining required-work
    totals for every active enrollee."""
    _recompute_enrollees_for_course(instance.course_id)


def _recompute_for_event_module(event_module):
    """Resolve EventModule → owning course (via CourseModule join), then
    recompute. Used by ModuleContent/Assignment signal handlers, since
    those models are scoped to EventModule rather than directly to a course.
    """
    if event_module is None:
        return
    from learning.models import CourseModule

    course_ids = list(
        CourseModule.objects.filter(module=event_module).values_list("course_id", flat=True)
    )
    for cid in course_ids:
        _recompute_enrollees_for_course(cid)


@receiver(post_save, sender='learning.ModuleContent')
def _modulecontent_added_or_changed(sender, instance, **kwargs):
    """New content (or required-flag flip) changes the denominator for
    every active enrollee in this module's course(s)."""
    _recompute_for_event_module(instance.module)


@receiver(post_delete, sender='learning.ModuleContent')
def _modulecontent_removed(sender, instance, **kwargs):
    _recompute_for_event_module(instance.module)


@receiver(post_save, sender='learning.Assignment')
def _assignment_added_or_changed(sender, instance, **kwargs):
    """Assignments contribute to the progress denominator alongside
    required content (see ``_module_requirement_progress``)."""
    _recompute_for_event_module(instance.module)


@receiver(post_delete, sender='learning.Assignment')
def _assignment_removed(sender, instance, **kwargs):
    _recompute_for_event_module(instance.module)


@receiver(post_save, sender='learning.ContentProgress')
def _contentprogress_cascade_to_module(sender, instance, **kwargs):
    """Cascade ContentProgress changes up to ModuleProgress.

    Without this, code paths that create ContentProgress directly (seeds,
    admin tools, future bulk imports) would leave ModuleProgress.status
    stale at "not_started", and Module.is_available_for would lock every
    subsequent module behind it. The API view path already calls
    update_from_content explicitly; this signal makes the cascade
    automatic for all writers.
    """
    if instance.course_enrollment_id is None:
        return  # event-registration progress uses a different rollup path

    from learning.models import CourseModule, ModuleProgress

    try:
        course_module = CourseModule.objects.select_related("module").get(
            course=instance.course_enrollment.course,
            module=instance.content.module,
        )
    except CourseModule.DoesNotExist:
        return

    mp, _ = ModuleProgress.objects.get_or_create(
        course_enrollment=instance.course_enrollment,
        module=course_module.module,
    )
    try:
        mp.update_from_content()
    except Exception:
        logger.exception(
            "Cascade ContentProgress→ModuleProgress failed for content=%s enrollment=%s",
            instance.content_id, instance.course_enrollment_id,
        )
