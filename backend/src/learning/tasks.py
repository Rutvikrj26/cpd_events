"""
Cloud tasks for the learning app.
"""

import logging

from django.utils import timezone

from common.cloud_tasks import task

logger = logging.getLogger(__name__)


@task()
def send_course_session_reminders(hours_before: int = 24):
    """Send reminders for upcoming course sessions in a window."""
    from integrations.services import email_service

    from .models import CourseEnrollment, CourseSession

    now = timezone.now()
    target_time = now + timezone.timedelta(hours=hours_before)

    sessions = CourseSession.objects.filter(
        status=CourseSession.Status.SCHEDULED,
        is_published=True,
        starts_at__gt=now,
        starts_at__lte=target_time + timezone.timedelta(minutes=30),
    ).select_related('course')

    count = 0
    for session in sessions:
        enrollments = CourseEnrollment.objects.filter(
            course=session.course,
            status=CourseEnrollment.Status.ACTIVE,
        ).select_related('user')

        for enrollment in enrollments:
            if not enrollment.user or not enrollment.user.email:
                continue
            email_service.send_email(
                template='course_session_reminder',
                recipient=enrollment.user.email,
                context={
                    'user_name': enrollment.user.full_name,
                    'course_title': session.course.title,
                    'session_title': session.title,
                    'session_date': session.starts_at.strftime('%B %d, %Y at %I:%M %p'),
                    'duration_minutes': session.duration_minutes,
                },
                subject=f"Reminder: {session.course.title} — {session.title}",
            )
            count += 1

    logger.info("Sent %d course-session reminders", count)
    return count


@task()
def notify_course_session_cancelled(session_id: int):
    """Notify enrolled learners when a course session is cancelled."""
    from integrations.services import email_service

    from .models import CourseEnrollment, CourseSession

    try:
        session = CourseSession.objects.select_related('course').get(id=session_id)
    except CourseSession.DoesNotExist:
        logger.warning("CourseSession %s not found for cancel notification", session_id)
        return 0

    if session.status != CourseSession.Status.CANCELLED:
        logger.warning("CourseSession %s not in cancelled state, skipping", session_id)
        return 0

    enrollments = CourseEnrollment.objects.filter(
        course=session.course,
        status=CourseEnrollment.Status.ACTIVE,
    ).select_related('user')

    count = 0
    for enrollment in enrollments:
        if not enrollment.user or not enrollment.user.email:
            continue
        email_service.send_email(
            template='course_session_update',
            recipient=enrollment.user.email,
            context={
                'user_name': enrollment.user.full_name,
                'course_title': session.course.title,
                'session_title': session.title,
                'reason': session.cancelled_reason or 'No reason provided.',
            },
            subject=f"Cancelled: {session.course.title} — {session.title}",
        )
        count += 1

    logger.info("Sent %d cancellation notifications for session %s", count, session_id)
    return count
