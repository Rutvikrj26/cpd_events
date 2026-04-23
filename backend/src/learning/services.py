"""Services for the learning app.

Checkout / enrollment confirmation lives in ``billing.checkout`` +
``billing.handlers``. This module is now just ICS calendar generation for
course sessions.
"""

from __future__ import annotations

import logging
from datetime import timezone as dt_timezone

from django.conf import settings
from django.utils import timezone

from .models import CourseSession

logger = logging.getLogger(__name__)


def _ics_format(dt) -> str:
    return dt.astimezone(dt_timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _ics_escape(text: str) -> str:
    return (
        (text or '')
        .replace('\\', '\\\\')
        .replace(';', '\\;')
        .replace(',', '\\,')
        .replace('\n', '\\n')
    )


def build_session_ics(session: CourseSession, user=None) -> str:
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
        'PRODID:-//Accredit//CourseSession//EN',
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
        lines.append(
            f'ORGANIZER;CN={_ics_escape(course.created_by.full_name or "")}:mailto:{organizer_email}'
        )
    if user is not None and getattr(user, 'email', None):
        lines.append(
            f'ATTENDEE;CN={_ics_escape(user.full_name or "")};RSVP=FALSE:mailto:{user.email}'
        )
    lines.extend(['END:VEVENT', 'END:VCALENDAR'])
    return '\r\n'.join(lines) + '\r\n'
