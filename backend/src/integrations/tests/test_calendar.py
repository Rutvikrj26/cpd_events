"""Tests for shared ICS helpers + event/session ICS builders.

Goal: every path emits canonical RFC 5545 structure (BEGIN:VCALENDAR,
METHOD, UID, DTSTART;Z-suffix, DTEND, SUMMARY, ATTENDEE) and properly
escapes/cancels.
"""

from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

import pytest

from integrations.calendar import (
    build_vevent_lines,
    google_calendar_url,
    ics_calendar,
    ics_escape,
    ics_fold_line,
    ics_format_dt,
    outlook_calendar_url,
)


class TestICSPrimitives:
    def test_format_dt_emits_utc_z_suffix(self):
        dt = datetime(2026, 4, 25, 14, 30, 0, tzinfo=dt_timezone.utc)
        assert ics_format_dt(dt) == '20260425T143000Z'

    def test_format_dt_converts_non_utc(self):
        # 14:30 in UTC+5:30 → 09:00 UTC
        from datetime import timezone as tz

        ist = tz(timedelta(hours=5, minutes=30))
        dt = datetime(2026, 4, 25, 14, 30, 0, tzinfo=ist)
        assert ics_format_dt(dt) == '20260425T090000Z'

    def test_escape_handles_special_chars(self):
        assert ics_escape("a, b; c\nd \\e") == "a\\, b\\; c\\nd \\\\e"

    def test_fold_short_line_unchanged(self):
        assert ics_fold_line("SUMMARY:short") == "SUMMARY:short"

    def test_fold_long_line_inserts_continuation(self):
        long = "DESCRIPTION:" + ("x" * 200)
        folded = ics_fold_line(long, limit=75)
        # First chunk is at most 75 octets; continuation lines start with CRLF + space.
        assert folded.startswith("DESCRIPTION:")
        assert "\r\n " in folded
        # All content preserved.
        assert folded.replace("\r\n ", "") == long


class TestVEventBuilder:
    @pytest.fixture
    def starts(self):
        return datetime(2026, 4, 25, 14, 30, 0, tzinfo=dt_timezone.utc)

    @pytest.fixture
    def ends(self, starts):
        return starts + timedelta(hours=1)

    def test_basic_vevent_emits_required_fields(self, starts, ends):
        lines = build_vevent_lines(
            uid='test-uid@example.test',
            starts_at=starts,
            ends_at=ends,
            summary='Sample',
            description='Body, with; special\nchars',
        )
        text = '\r\n'.join(lines)
        assert 'BEGIN:VEVENT' in text
        assert 'UID:test-uid@example.test' in text
        assert 'DTSTART:20260425T143000Z' in text
        assert 'DTEND:20260425T153000Z' in text
        assert 'SUMMARY:Sample' in text
        assert 'DESCRIPTION:Body\\, with\\; special\\nchars' in text
        assert 'STATUS:CONFIRMED' in text
        assert 'END:VEVENT' in text

    def test_cancelled_uses_status_and_sequence(self, starts, ends):
        lines = build_vevent_lines(
            uid='u@d',
            starts_at=starts,
            ends_at=ends,
            summary='Cancelled Event',
            cancelled=True,
        )
        text = '\r\n'.join(lines)
        assert 'STATUS:CANCELLED' in text
        assert 'SEQUENCE:1' in text

    def test_attendee_and_organizer_render(self, starts, ends):
        lines = build_vevent_lines(
            uid='u@d',
            starts_at=starts,
            ends_at=ends,
            summary='X',
            organizer_name='Alice Org',
            organizer_email='alice@org.test',
            attendee_name='Bob Attendee',
            attendee_email='bob@a.test',
        )
        text = '\r\n'.join(lines)
        assert 'ORGANIZER;CN=Alice Org:mailto:alice@org.test' in text
        assert 'ATTENDEE;CN=Bob Attendee;ROLE=REQ-PARTICIPANT;RSVP=FALSE:mailto:bob@a.test' in text


class TestICSCalendar:
    def test_calendar_wraps_events_with_method(self):
        starts = datetime(2026, 4, 25, 14, 30, 0, tzinfo=dt_timezone.utc)
        ends = starts + timedelta(hours=1)
        ev = build_vevent_lines(uid='u@d', starts_at=starts, ends_at=ends, summary='X')
        ics = ics_calendar(prodid='-//Test//EN', method='PUBLISH', events=[ev])
        assert ics.startswith('BEGIN:VCALENDAR\r\n')
        assert 'VERSION:2.0\r\n' in ics
        assert 'PRODID:-//Test//EN\r\n' in ics
        assert 'METHOD:PUBLISH\r\n' in ics
        assert 'CALSCALE:GREGORIAN\r\n' in ics
        assert ics.endswith('END:VCALENDAR\r\n')


@pytest.mark.django_db
class TestBuildEventICS:
    def test_event_ics_includes_event_data_and_attendee(self):
        from datetime import timedelta
        from django.utils import timezone

        from events.services import build_event_ics
        from factories import EventFactory

        event = EventFactory(
            published=True,
            starts_at=timezone.now() + timedelta(days=2),
            title='ICS Smoke',
            short_description='check ics output',
        )
        ics = build_event_ics(event, attendee_email='a@b.test', attendee_name='Test User')
        assert 'BEGIN:VCALENDAR' in ics
        assert 'METHOD:PUBLISH' in ics
        assert 'SUMMARY:ICS Smoke' in ics
        assert f'UID:event-{event.uuid}' in ics
        assert 'ATTENDEE;CN=Test User;ROLE=REQ-PARTICIPANT;RSVP=FALSE:mailto:a@b.test' in ics

    def test_cancelled_event_emits_method_cancel(self, db):
        from datetime import timedelta
        from django.utils import timezone

        from events.services import build_event_ics
        from factories import EventFactory

        event = EventFactory(starts_at=timezone.now() + timedelta(days=1), status='cancelled')
        ics = build_event_ics(event, attendee_email='a@b.test')
        assert 'METHOD:CANCEL' in ics
        assert 'STATUS:CANCELLED' in ics
        assert 'SEQUENCE:1' in ics


class TestCalendarDeepLinks:
    def test_google_calendar_url_has_dates_and_text(self):
        starts = datetime(2026, 4, 25, 14, 30, 0, tzinfo=dt_timezone.utc)
        ends = starts + timedelta(hours=1)
        url = google_calendar_url(summary='Event', starts_at=starts, ends_at=ends)
        assert url.startswith('https://calendar.google.com/calendar/render?')
        assert 'action=TEMPLATE' in url
        assert 'text=Event' in url
        assert 'dates=20260425T143000Z%2F20260425T153000Z' in url

    def test_outlook_calendar_url_has_iso_dates(self):
        starts = datetime(2026, 4, 25, 14, 30, 0, tzinfo=dt_timezone.utc)
        ends = starts + timedelta(hours=1)
        url = outlook_calendar_url(summary='Event', starts_at=starts, ends_at=ends)
        assert url.startswith('https://outlook.live.com/calendar/0/deeplink/compose?')
        assert 'rru=addevent' in url
