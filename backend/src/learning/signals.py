"""
Signals for the learning app.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Course, CourseSession
from .tasks import create_zoom_meeting_for_course, create_zoom_meeting_for_session

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Course)
def trigger_zoom_creation_for_course(sender, instance, created, **kwargs):
    """
    Trigger Zoom meeting creation when a hybrid course is created/updated
    with Zoom enabled but no meeting ID.
    """
    # Prevent infinite recursion when the task itself updates the course
    update_fields = kwargs.get('update_fields')
    if update_fields:
        # If only updating zoom-related fields, skip
        zoom_fields = {'zoom_error', 'zoom_error_at', 'zoom_meeting_id', 'zoom_meeting_uuid',
                       'zoom_meeting_url', 'zoom_start_url', 'zoom_meeting_password', 'updated_at'}
        if set(update_fields).issubset(zoom_fields):
            return

    # Check if we should create a Zoom meeting
    # 1. format is 'hybrid'
    # 2. zoom_settings has enabled=True
    # 3. zoom_meeting_id is empty (not already created)
    # 4. live_session_start is set (we need a start time)
    should_create = False

    if instance.format == Course.CourseFormat.HYBRID and not instance.zoom_meeting_id:
        zoom_settings = instance.zoom_settings or {}
        if zoom_settings.get('enabled', False) and instance.live_session_start:
            should_create = True

    if should_create:
        logger.info(f"Triggering Zoom meeting creation for course {instance.uuid}")
        create_zoom_meeting_for_course.delay(instance.id)


@receiver(post_save, sender=CourseSession)
def trigger_zoom_creation_for_session(sender, instance, created, **kwargs):
    """
    Trigger Zoom meeting creation when a CourseSession is created/updated
    with Zoom enabled but no meeting ID.
    """
    # Prevent infinite recursion when the task updates the session
    update_fields = kwargs.get('update_fields')
    if update_fields:
        zoom_fields = {'zoom_error', 'zoom_error_at', 'zoom_meeting_id', 'zoom_meeting_uuid',
                       'zoom_join_url', 'zoom_start_url', 'zoom_password', 'updated_at'}
        if set(update_fields).issubset(zoom_fields):
            return

    # Check if we should create a Zoom meeting:
    # 1. zoom_settings has enabled=True
    # 2. zoom_meeting_id is empty (not already created)
    # 3. starts_at is set (we need a start time)
    should_create = False

    zoom_settings = instance.zoom_settings or {}
    if zoom_settings.get('enabled', False) and not instance.zoom_meeting_id and instance.starts_at:
        should_create = True

    if should_create:
        logger.info(f"Triggering Zoom meeting creation for session {instance.uuid}")
        create_zoom_meeting_for_session.delay(instance.id)
