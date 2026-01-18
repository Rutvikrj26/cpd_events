"""
Cloud tasks for the learning app.
"""

import logging

from django.utils import timezone

from common.cloud_tasks import task

logger = logging.getLogger(__name__)


@task()
def create_zoom_meeting_for_course(course_id: int):
    """
    Create Zoom meeting for a hybrid course.

    Args:
        course_id: ID of the Course to create meeting for
    """
    from accounts.services import zoom_service
    from learning.models import Course

    try:
        course = Course.objects.get(id=course_id)

        # Validate that we should create a meeting
        if course.format != Course.CourseFormat.HYBRID:
            logger.info(f"Course {course_id} is not hybrid, skipping Zoom creation")
            return False

        if course.zoom_meeting_id:
            logger.info(f"Course {course_id} already has Zoom meeting, skipping")
            return False

        # Create the Zoom meeting
        result = zoom_service.create_meeting_for_course(course)

        if not result.get('success'):
            error_msg = result.get('error', 'Unknown Zoom error')
            course.zoom_error = error_msg
            course.zoom_error_at = timezone.now()
            course.save(update_fields=['zoom_error', 'zoom_error_at', 'updated_at'])
            logger.error(f"Failed to create Zoom meeting for course {course_id}: {error_msg}")
            return False

        # Clear error on success
        if course.zoom_error:
            course.zoom_error = ''
            course.zoom_error_at = None
            course.save(update_fields=['zoom_error', 'zoom_error_at', 'updated_at'])

        logger.info(f"Created Zoom meeting for course {course_id}")
        return True

    except Course.DoesNotExist:
        logger.error(f"Course {course_id} not found")
        return False
    except Exception as e:
        logger.exception(f"Error creating Zoom meeting for course {course_id}: {e}")
        return False


@task()
def create_zoom_meeting_for_session(session_id: int):
    """
    Create Zoom meeting for a specific course session.

    Args:
        session_id: ID of the CourseSession to create meeting for
    """
    from accounts.services import zoom_service
    from learning.models import CourseSession

    try:
        session = CourseSession.objects.select_related('course', 'course__created_by').get(id=session_id)

        # Check if meeting already exists
        if session.zoom_meeting_id:
            logger.info(f"Session {session_id} already has Zoom meeting, skipping")
            return False

        # Check if Zoom is enabled for this session
        zoom_settings = session.zoom_settings or {}
        if not zoom_settings.get('enabled', False):
            logger.info(f"Session {session_id} does not have Zoom enabled, skipping")
            return False

        # Create the Zoom meeting
        result = zoom_service.create_meeting_for_session(session)

        if not result.get('success'):
            error_msg = result.get('error', 'Unknown Zoom error')
            session.zoom_error = error_msg
            session.zoom_error_at = timezone.now()
            session.save(update_fields=['zoom_error', 'zoom_error_at', 'updated_at'])
            logger.error(f"Failed to create Zoom meeting for session {session_id}: {error_msg}")
            return False

        # Clear error on success
        if session.zoom_error:
            session.zoom_error = ''
            session.zoom_error_at = None
            session.save(update_fields=['zoom_error', 'zoom_error_at', 'updated_at'])

        logger.info(f"Created Zoom meeting for session {session_id}")
        return True

    except CourseSession.DoesNotExist:
        logger.error(f"Session {session_id} not found")
        return False
    except Exception as e:
        logger.exception(f"Error creating Zoom meeting for session {session_id}: {e}")
        return False


@task()
def sync_session_attendance(session_id: int):
    """
    Sync Zoom attendance data for a course session.

    Args:
        session_id: ID of the CourseSession to sync attendance for
    """
    from integrations.services import attendance_matcher
    from learning.models import CourseSession

    try:
        session = CourseSession.objects.get(id=session_id)
        result = attendance_matcher.match_session_attendance(session)
        logger.info(f"Synced attendance for session {session_id}: {result}")
        return result
    except CourseSession.DoesNotExist:
        logger.error(f"Session {session_id} not found")
        return {}
