"""Services for the learning app.

Checkout / enrollment confirmation lives in ``billing.checkout`` +
``billing.handlers``. This module is now just ICS calendar generation for
course sessions — delegating low-level formatting to
``integrations.calendar`` so events and sessions emit the same canonical
RFC 5545 structure.
"""

from __future__ import annotations

import logging

from django.conf import settings

from integrations.calendar import build_vevent_lines, ics_calendar

from .models import CourseSession

logger = logging.getLogger(__name__)


def build_session_ics(session: CourseSession, user=None) -> str:
    course = session.course
    cancelled = session.status == CourseSession.Status.CANCELLED
    method = 'CANCEL' if cancelled else 'PUBLISH'
    domain = getattr(settings, 'ICS_UID_DOMAIN', 'accredit.app')

    organizer_email = getattr(course.created_by, 'email', '') if course.created_by_id else ''
    organizer_name = getattr(course.created_by, 'full_name', '') if course.created_by_id else ''
    attendee_email = getattr(user, 'email', '') if user is not None else ''
    attendee_name = getattr(user, 'full_name', '') if user is not None else ''

    vevent = build_vevent_lines(
        uid=f"course-session-{session.uuid}@{domain}",
        starts_at=session.starts_at,
        ends_at=session.ends_at,
        summary=f"{course.title} — {session.title}",
        description=session.description or course.short_description or course.title,
        organizer_name=organizer_name or '',
        organizer_email=organizer_email or '',
        attendee_name=attendee_name or '',
        attendee_email=attendee_email or '',
        cancelled=cancelled,
    )

    return ics_calendar(
        prodid='-//Accredit//CourseSession//EN',
        method=method,
        events=[vevent],
    )
