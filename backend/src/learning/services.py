"""
Services for the learning app.
"""

import logging
from datetime import timezone as dt_timezone
from typing import Any

from django.conf import settings
from django.db import OperationalError, transaction
from django.utils import timezone

from billing.services import StripeService

from .models import Course, CourseEnrollment, CourseSession

logger = logging.getLogger(__name__)


def _ics_format(dt) -> str:
    """Format a datetime as a UTC ICS timestamp (YYYYMMDDTHHMMSSZ)."""
    return dt.astimezone(dt_timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _ics_escape(text: str) -> str:
    """Escape commas, semicolons, and newlines per RFC 5545."""
    return (
        (text or '')
        .replace('\\', '\\\\')
        .replace(';', '\\;')
        .replace(',', '\\,')
        .replace('\n', '\\n')
    )


def build_session_ics(session: CourseSession, user=None) -> str:
    """
    Build an RFC-5545 VCALENDAR string for a single CourseSession.

    Cancelled sessions emit METHOD:CANCEL so calendar clients remove them.
    """
    course = session.course
    starts = session.starts_at
    ends = session.ends_at
    method = 'CANCEL' if session.status == CourseSession.Status.CANCELLED else 'PUBLISH'
    sequence = 1 if session.status == CourseSession.Status.CANCELLED else 0
    domain = getattr(settings, 'ICS_UID_DOMAIN', 'accredit.app')
    summary = _ics_escape(f"{course.title} — {session.title}")
    description = _ics_escape(session.description or course.short_description or course.title)
    organizer_email = getattr(course.created_by, 'email', '') if course.created_by_id else ''

    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        f'PRODID:-//Accredit//CourseSession//EN',
        f'METHOD:{method}',
        'BEGIN:VEVENT',
        f'UID:course-session-{session.uuid}@{domain}',
        f'DTSTAMP:{_ics_format(timezone.now())}',
        f'DTSTART:{_ics_format(starts)}',
        f'DTEND:{_ics_format(ends)}',
        f'SUMMARY:{summary}',
        f'DESCRIPTION:{description}',
        f'SEQUENCE:{sequence}',
        f'STATUS:{"CANCELLED" if method == "CANCEL" else "CONFIRMED"}',
    ]
    if organizer_email:
        lines.append(f'ORGANIZER;CN={_ics_escape(course.created_by.full_name or "")}:mailto:{organizer_email}')
    if user is not None and getattr(user, 'email', None):
        lines.append(f'ATTENDEE;CN={_ics_escape(user.full_name or "")};RSVP=FALSE:mailto:{user.email}')
    lines.extend(['END:VEVENT', 'END:VCALENDAR'])
    return '\r\n'.join(lines) + '\r\n'


class CourseService:
    """Service for managing course operations."""

    def __init__(self):
        self.stripe_service = StripeService()

    def confirm_enrollment(self, user, session_id: str) -> dict[str, Any]:
        """
        Confirm a course enrollment from a Stripe checkout session.
        
        Args:
            user: The user checking out
            session_id: The Stripe Checkout Session ID
            
        Returns:
            dict with success/error and enrollment data
        """
        # 1. Verify session with Stripe
        session_result = self.stripe_service.retrieve_checkout_session(session_id)
        if not session_result.get('success'):
            return {'success': False, 'error': session_result.get('error')}

        session = session_result['session']

        # Verify payment status
        if session.payment_status != 'paid':
             return {'success': False, 'error': 'Payment not completed', 'code': 'PAYMENT_NOT_COMPLETED'}

        # Extract course ID from metadata
        course_uuid = session.metadata.get('course_uuid')
        if not course_uuid:
            return {'success': False, 'error': 'No course ID in session metadata'}

        try:
            course = Course.objects.get(uuid=course_uuid)
        except Course.DoesNotExist:
             return {'success': False, 'error': 'Course not found'}

        # 2. Create/Activate Enrollment (with retry for locking)
        import time

        max_retries = 3
        enrollment = None

        for attempt in range(max_retries):
            try:
                with transaction.atomic():
                    # Create or update enrollment
                    enrollment, created = CourseEnrollment.objects.get_or_create(
                        course=course,
                        user=user,
                        defaults={
                            'status': CourseEnrollment.Status.ACTIVE,
                            'enrolled_at': timezone.now(),
                            'access_type': CourseEnrollment.AccessType.LIFETIME,
                            'stripe_checkout_session_id': session_id,
                        }
                    )

                    # If it existed but was inactive/pending payment, activate it
                    if not created and enrollment.status != CourseEnrollment.Status.ACTIVE:
                        enrollment.status = CourseEnrollment.Status.ACTIVE
                        if not enrollment.enrolled_at:
                            enrollment.enrolled_at = timezone.now()
                        enrollment.stripe_checkout_session_id = session_id
                        enrollment.save(update_fields=['status', 'enrolled_at', 'stripe_checkout_session_id', 'updated_at'])

                # Success - break loop
                break

            except OperationalError as e:
                # Retry on SQLite database locked error
                if 'locked' in str(e).lower() and attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                logger.error(f"Database locked confirming course enrollment: {e}")
                return {'success': False, 'error': 'System busy, please try again'}

            except Exception as e:
                logger.error(f"Failed to confirm course enrollment: {e}")
                return {'success': False, 'error': str(e)}
        else:
            # Loop finished without breaking = failed all retries
            return {'success': False, 'error': 'Failed to confirm enrollment after retries'}

        return {'success': True, 'enrollment': enrollment}
