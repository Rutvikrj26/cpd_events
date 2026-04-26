"""Shared RFC 5545 (iCalendar) helpers.

Used by both ``events.services.build_event_ics`` and
``learning.services.build_session_ics`` so both paths emit identical
canonical structure. Times are emitted in UTC (``Z``-suffixed) for
broadest client compatibility — Outlook, Google Calendar, and Apple
Calendar all handle UTC reliably without needing VTIMEZONE blocks.

Helpers:
    ics_format_dt(dt) → "YYYYMMDDTHHMMSSZ"
    ics_escape(text) → escaped per RFC 5545 §3.3.11
    ics_fold_line(line) → soft-fold lines >75 octets (RFC 5545 §3.1)
    ics_calendar(events, prodid, method) → assemble final VCALENDAR string

Plus a builder for "Add to Google" / "Add to Outlook" deep links so the
email partial and frontend can share one source of truth.
"""

from __future__ import annotations

from datetime import datetime
from datetime import timezone as dt_timezone
from typing import Iterable
from urllib.parse import urlencode

from django.utils import timezone


def ics_format_dt(dt: datetime) -> str:
    """RFC 5545 UTC datetime form: YYYYMMDDTHHMMSSZ."""
    return dt.astimezone(dt_timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def ics_escape(text: str) -> str:
    """Escape per RFC 5545 §3.3.11 (TEXT value type)."""
    return (
        (text or '')
        .replace('\\', '\\\\')
        .replace(';', '\\;')
        .replace(',', '\\,')
        .replace('\n', '\\n')
    )


def ics_fold_line(line: str, limit: int = 75) -> str:
    """RFC 5545 §3.1 — fold lines longer than 75 octets.

    Continuation lines start with a single SPACE (0x20). We measure octets
    in UTF-8 since iCalendar is octet-oriented.
    """
    encoded = line.encode('utf-8')
    if len(encoded) <= limit:
        return line
    chunks = []
    while len(encoded) > limit:
        # Walk back to a UTF-8 char boundary if needed.
        cut = limit
        while cut > 0 and (encoded[cut] & 0xC0) == 0x80:
            cut -= 1
        chunks.append(encoded[:cut].decode('utf-8'))
        encoded = encoded[cut:]
    chunks.append(encoded.decode('utf-8'))
    return chunks[0] + ''.join('\r\n ' + c for c in chunks[1:])


def ics_calendar(
    *,
    prodid: str,
    method: str,
    events: Iterable[list[str]],
) -> str:
    """Assemble a VCALENDAR string from already-built VEVENT line lists."""
    out: list[str] = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        f'PRODID:{prodid}',
        f'METHOD:{method}',
        'CALSCALE:GREGORIAN',
    ]
    for ev_lines in events:
        out.extend(ev_lines)
    out.append('END:VCALENDAR')
    return '\r\n'.join(ics_fold_line(line) for line in out) + '\r\n'


def build_vevent_lines(
    *,
    uid: str,
    starts_at: datetime,
    ends_at: datetime,
    summary: str,
    description: str = '',
    location: str = '',
    url: str = '',
    organizer_name: str = '',
    organizer_email: str = '',
    attendee_name: str = '',
    attendee_email: str = '',
    cancelled: bool = False,
    sequence: int = 0,
) -> list[str]:
    """Build the VEVENT block as a list of unfolded lines."""
    status = 'CANCELLED' if cancelled else 'CONFIRMED'
    seq = max(sequence, 1) if cancelled else sequence

    lines = [
        'BEGIN:VEVENT',
        f'UID:{uid}',
        f'DTSTAMP:{ics_format_dt(timezone.now())}',
        f'DTSTART:{ics_format_dt(starts_at)}',
        f'DTEND:{ics_format_dt(ends_at)}',
        f'SUMMARY:{ics_escape(summary)}',
        f'SEQUENCE:{seq}',
        f'STATUS:{status}',
    ]
    if description:
        lines.append(f'DESCRIPTION:{ics_escape(description)}')
    if location:
        lines.append(f'LOCATION:{ics_escape(location)}')
    if url:
        lines.append(f'URL:{url}')
    if organizer_email:
        organizer_cn = ics_escape(organizer_name or '')
        lines.append(f'ORGANIZER;CN={organizer_cn}:mailto:{organizer_email}')
    if attendee_email:
        attendee_cn = ics_escape(attendee_name or '')
        lines.append(
            f'ATTENDEE;CN={attendee_cn};ROLE=REQ-PARTICIPANT;RSVP=FALSE:mailto:{attendee_email}'
        )
    lines.append('END:VEVENT')
    return lines


# =============================================================================
# Add-to-calendar deep links (used in email partials and frontend)
# =============================================================================


def google_calendar_url(
    *,
    summary: str,
    starts_at: datetime,
    ends_at: datetime,
    description: str = '',
    location: str = '',
) -> str:
    """https://calendar.google.com/calendar/render?action=TEMPLATE&...

    Times are passed in UTC compact form per Google's documented format.
    """
    fmt = '%Y%m%dT%H%M%SZ'
    params = {
        'action': 'TEMPLATE',
        'text': summary,
        'dates': f"{starts_at.astimezone(dt_timezone.utc).strftime(fmt)}/"
                 f"{ends_at.astimezone(dt_timezone.utc).strftime(fmt)}",
    }
    if description:
        params['details'] = description
    if location:
        params['location'] = location
    return 'https://calendar.google.com/calendar/render?' + urlencode(params)


def outlook_calendar_url(
    *,
    summary: str,
    starts_at: datetime,
    ends_at: datetime,
    description: str = '',
    location: str = '',
) -> str:
    """https://outlook.office.com/calendar/0/deeplink/compose?... (Microsoft 365)."""
    params = {
        'path': '/calendar/action/compose',
        'rru': 'addevent',
        'subject': summary,
        'startdt': starts_at.astimezone(dt_timezone.utc).isoformat(),
        'enddt': ends_at.astimezone(dt_timezone.utc).isoformat(),
    }
    if description:
        params['body'] = description
    if location:
        params['location'] = location
    return 'https://outlook.live.com/calendar/0/deeplink/compose?' + urlencode(params)
