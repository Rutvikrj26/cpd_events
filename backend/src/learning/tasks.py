"""
Cloud tasks for the learning app.
"""

import logging

from django.conf import settings
from django.utils import timezone

from common.cloud_tasks import task

logger = logging.getLogger(__name__)


# =============================================================================
# Course-flow lifecycle emails (P5)
# =============================================================================
#
# These run through ``email_service.send_log`` so they get the same prefs +
# Notification mirroring as the event flow. Each is idempotent against the
# EmailLog table — repeat invocations from webhook retries / signal storms
# are safe no-ops.


def _course_url(course) -> str:
    base = (getattr(settings, 'FRONTEND_URL', '') or '').rstrip('/')
    return f"{base}/learn/{course.uuid}"


def _module_url(course, module) -> str:
    base = (getattr(settings, 'FRONTEND_URL', '') or '').rstrip('/')
    return f"{base}/learn/{course.uuid}#module-{module.id}"


@task()
def send_enrollment_confirmation(enrollment_id: int):
    """Send the course enrollment confirmation email + create Notification.

    Idempotent: short-circuits if a COURSE_ENROLLED EmailLog already exists
    for this enrollment's user/course pair.
    """
    from accounts.models import Notification
    from integrations.models import EmailLog
    from integrations.services import email_service
    from learning.models import CourseEnrollment, CourseSession, EventModule

    try:
        enrollment = CourseEnrollment.objects.select_related('course', 'user').get(id=enrollment_id)
    except CourseEnrollment.DoesNotExist:
        logger.error("CourseEnrollment %s not found", enrollment_id)
        return False

    if not enrollment.user or not enrollment.user.email:
        return False

    # Idempotency — one confirmation per (user, course) is enough.
    already_sent = EmailLog.objects.filter(
        recipient_user=enrollment.user,
        event=None,
        email_type='course_enrolled',
        subject__icontains=enrollment.course.title,
    ).exists()
    if already_sent:
        logger.info("Enrollment %s already has confirmation EmailLog, skipping", enrollment_id)
        return True

    course = enrollment.course
    instructor_name = (
        getattr(course.created_by, 'full_name', None)
        if getattr(course, 'created_by_id', None)
        else None
    ) or ''
    module_count = EventModule.objects.filter(course_links__course=course).count() if hasattr(EventModule, 'course_links') else 0
    first_module = (
        EventModule.objects.filter(course_links__course=course)
        .order_by('course_links__order', 'order')
        .first()
        if module_count else None
    )
    upcoming_session_count = CourseSession.objects.filter(
        course=course, starts_at__gt=timezone.now(), status=CourseSession.Status.SCHEDULED,
    ).count()

    context = {
        'user_name': enrollment.user.full_name,
        'course_title': course.title,
        'instructor_name': instructor_name,
        'module_count': module_count,
        'estimated_hours': str(course.estimated_hours) if getattr(course, 'estimated_hours', 0) else '',
        'first_module_title': getattr(first_module, 'title', ''),
        'upcoming_session_count': upcoming_session_count,
        'course_url': _course_url(course),
    }

    log = EmailLog.objects.create(
        recipient_email=enrollment.user.email,
        recipient_name=enrollment.user.full_name,
        recipient_user=enrollment.user,
        email_type='course_enrolled',
        subject=f"You're enrolled in {course.title}",
    )

    email_service.send_log(log, context=context)

    # send_log only auto-mirrors when log.event is set; courses don't have an
    # event FK on EmailLog, so we explicitly create the Notification here.
    if not Notification.objects.filter(
        user=enrollment.user,
        notification_type='course_enrolled',
        metadata__course_uuid=str(course.uuid),
    ).exists():
        Notification.objects.create(
            user=enrollment.user,
            notification_type='course_enrolled',
            title=f"Enrolled in {course.title}",
            message=f"Your seat in {course.title} is confirmed.",
            action_url=_course_url(course),
            metadata={
                'course_uuid': str(course.uuid),
                'enrollment_id': enrollment.id,
                'email_log_id': log.id,
            },
        )

    return True


@task()
def send_module_released(enrollment_id: int, module_id: int):
    """Notify a learner that a course module has unlocked for them.

    Idempotent: skips if a module_released EmailLog row already exists for
    this (user, module) pair.
    """
    from accounts.models import Notification
    from integrations.models import EmailLog
    from integrations.services import email_service
    from learning.models import CourseEnrollment, EventModule

    try:
        enrollment = CourseEnrollment.objects.select_related('course', 'user').get(id=enrollment_id)
        module = EventModule.objects.get(id=module_id)
    except (CourseEnrollment.DoesNotExist, EventModule.DoesNotExist):
        logger.warning("send_module_released: enrollment %s or module %s missing", enrollment_id, module_id)
        return False

    if not enrollment.user or not enrollment.user.email:
        return False

    already_sent = EmailLog.objects.filter(
        recipient_user=enrollment.user,
        email_type='module_released',
        subject__icontains=module.title,
    ).exists()
    if already_sent:
        return True

    course = enrollment.course
    context = {
        'user_name': enrollment.user.full_name,
        'course_title': course.title,
        'module_title': module.title,
        'module_description': getattr(module, 'description', '') or '',
        'cpd_credits': str(module.cpd_credits) if getattr(module, 'cpd_credits', 0) else '',
        'cpd_type': getattr(module, 'cpd_type', '') or '',
        'progress_percent': enrollment.progress_percent,
        'module_url': _module_url(course, module),
    }
    log = EmailLog.objects.create(
        recipient_email=enrollment.user.email,
        recipient_name=enrollment.user.full_name,
        recipient_user=enrollment.user,
        email_type='module_released',
        subject=f"New module unlocked: {module.title}",
    )
    email_service.send_log(log, context=context)

    Notification.objects.create(
        user=enrollment.user,
        notification_type='module_released',
        title=f"New module: {module.title}",
        message=f"Just unlocked in {course.title}.",
        action_url=_module_url(course, module),
        metadata={
            'course_uuid': str(course.uuid),
            'module_id': module.id,
            'enrollment_id': enrollment.id,
            'email_log_id': log.id,
        },
    )
    return True


@task()
def send_course_completed(enrollment_id: int):
    """Send course-completion summary email + Notification.

    Idempotent: short-circuits if a course_completed EmailLog already exists
    for this enrollment.
    """
    from accounts.models import Notification
    from integrations.models import EmailLog
    from integrations.services import email_service
    from learning.models import CourseEnrollment

    try:
        enrollment = CourseEnrollment.objects.select_related('course', 'user').get(id=enrollment_id)
    except CourseEnrollment.DoesNotExist:
        logger.error("CourseEnrollment %s not found", enrollment_id)
        return False

    if enrollment.status != CourseEnrollment.Status.COMPLETED:
        logger.info("Enrollment %s not completed, skipping", enrollment_id)
        return False

    if not enrollment.user or not enrollment.user.email:
        return False

    already_sent = EmailLog.objects.filter(
        recipient_user=enrollment.user,
        email_type='course_completed',
        subject__icontains=enrollment.course.title,
    ).exists()
    if already_sent:
        return True

    course = enrollment.course
    completed_at_str = enrollment.completed_at.strftime('%B %d, %Y') if enrollment.completed_at else ''

    # Locate the issued certificate (if any) for a verification link.
    cert_url = ''
    try:
        from certificates.models import Certificate

        cert = Certificate.objects.filter(course_enrollment=enrollment).order_by('-issued_at').first()
        if cert:
            cert_url = getattr(cert, 'verification_url', '') or ''
    except Exception:
        pass

    context = {
        'user_name': enrollment.user.full_name,
        'course_title': course.title,
        'final_score': enrollment.current_score,
        'completed_at': completed_at_str,
        'cpd_credits': str(getattr(course, 'cpd_credit_value', 0)) if getattr(course, 'cpd_credit_value', 0) else '',
        'cpd_type': getattr(course, 'cpd_credit_type', '') or '',
        'certificate_url': cert_url,
    }

    log = EmailLog.objects.create(
        recipient_email=enrollment.user.email,
        recipient_name=enrollment.user.full_name,
        recipient_user=enrollment.user,
        email_type='course_completed',
        subject=f"Course complete: {course.title}",
    )
    email_service.send_log(log, context=context)

    Notification.objects.create(
        user=enrollment.user,
        notification_type='course_completed',
        title=f"Course complete: {course.title}",
        message='Your certificate is ready' if cert_url else 'Nice work!',
        action_url=cert_url or _course_url(course),
        metadata={
            'course_uuid': str(course.uuid),
            'enrollment_id': enrollment.id,
            'email_log_id': log.id,
        },
    )
    return True


@task()
def send_session_cancelled(enrollment_id: int, session_id: int):
    """Notify a learner that a course session was cancelled and that their
    completion requirements were recomputed (D2 in
    docs/design/hybrid-course-experience.md).

    Idempotent: skips if a session_cancelled EmailLog already exists for this
    (user, session) pair.
    """
    from accounts.models import Notification
    from integrations.models import EmailLog
    from integrations.services import email_service

    from .models import CourseEnrollment, CourseSession

    try:
        enrollment = CourseEnrollment.objects.select_related('course', 'user').get(id=enrollment_id)
        session = CourseSession.objects.get(id=session_id)
    except (CourseEnrollment.DoesNotExist, CourseSession.DoesNotExist):
        logger.warning(
            "send_session_cancelled: enrollment %s or session %s missing",
            enrollment_id, session_id,
        )
        return False

    if not enrollment.user or not enrollment.user.email:
        return False

    already_sent = EmailLog.objects.filter(
        recipient_user=enrollment.user,
        email_type='session_cancelled',
        subject__icontains=session.title,
    ).exists()
    if already_sent:
        return True

    log = EmailLog.objects.create(
        recipient_email=enrollment.user.email,
        recipient_name=enrollment.user.full_name,
        recipient_user=enrollment.user,
        email_type='session_cancelled',
        subject=f"Session cancelled: {session.title}",
    )

    email_service.send_log(log, context={
        'user_name': enrollment.user.full_name,
        'course_title': enrollment.course.title,
        'session_title': session.title,
        'cancellation_reason': session.cancelled_reason or '',
        'course_url': _course_url(enrollment.course),
    })

    Notification.objects.create(
        user=enrollment.user,
        notification_type='session_cancelled',
        title=f"Session cancelled: {session.title}",
        message=(
            f"{session.title} in {enrollment.course.title} was cancelled. "
            "Your completion requirements have been updated."
        ),
        action_url=_course_url(enrollment.course),
        metadata={
            'course_uuid': str(enrollment.course.uuid),
            'session_uuid': str(session.uuid),
            'enrollment_id': enrollment.id,
            'email_log_id': log.id,
        },
    )
    return True


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
