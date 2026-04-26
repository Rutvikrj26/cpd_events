"""Tests for the ScheduledEmail model + dispatcher + helpers."""

from unittest.mock import patch

import pytest
from django.utils import timezone

from integrations.models import EmailLog, ScheduledEmail
from integrations.services import schedule_bulk_emails, schedule_email
from integrations.tasks import dispatch_scheduled_emails


@pytest.mark.django_db
class TestScheduleEmail:
    def test_creates_pending_row_with_rendered_subject(self):
        send_at = timezone.now() + timezone.timedelta(hours=1)
        row = schedule_email(
            recipient_email='alice@example.com',
            template_key='event_reminder',
            send_at=send_at,
            context={'event_title': 'My Event'},
        )
        assert row.status == ScheduledEmail.Status.PENDING
        assert row.send_at == send_at
        assert 'My Event' in row.subject

    def test_subject_falls_back_when_context_missing(self):
        row = schedule_email(
            recipient_email='a@b.com',
            template_key='event_reminder',
            send_at=timezone.now(),
            context={},
        )
        assert row.subject  # no crash, template used as-is


@pytest.mark.django_db
class TestScheduleBulk:
    def test_staggers_send_at_by_seconds(self):
        send_at = timezone.now() + timezone.timedelta(hours=1)
        recipients = [{'email': f'u{i}@ex.com', 'context': {'event_title': 'X'}} for i in range(5)]
        count = schedule_bulk_emails(
            recipients=recipients,
            template_key='event_reminder',
            send_at=send_at,
            stagger_seconds=10,
        )
        assert count == 5
        rows = list(ScheduledEmail.objects.order_by('send_at'))
        deltas = [(r.send_at - send_at).total_seconds() for r in rows]
        assert deltas == [0, 10, 20, 30, 40]

    def test_skips_rows_missing_email(self):
        count = schedule_bulk_emails(
            recipients=[{'email': ''}, {'email': 'ok@ex.com'}],
            template_key='event_reminder',
            send_at=timezone.now(),
        )
        assert count == 1


@pytest.mark.django_db
class TestDispatch:
    @patch('integrations.tasks.send_email.delay')
    def test_only_dispatches_due_rows(self, mock_delay):
        now = timezone.now()
        schedule_email(
            recipient_email='past@ex.com',
            template_key='event_reminder',
            send_at=now - timezone.timedelta(minutes=5),
            context={'event_title': 'Past'},
        )
        schedule_email(
            recipient_email='future@ex.com',
            template_key='event_reminder',
            send_at=now + timezone.timedelta(hours=1),
            context={'event_title': 'Future'},
        )
        result = dispatch_scheduled_emails()
        assert result['dispatched'] == 1
        past = ScheduledEmail.objects.get(recipient_email='past@ex.com')
        future = ScheduledEmail.objects.get(recipient_email='future@ex.com')
        assert past.status == ScheduledEmail.Status.DISPATCHED
        assert past.email_log is not None
        assert future.status == ScheduledEmail.Status.PENDING

    @patch('integrations.tasks.send_email.delay')
    def test_dispatched_row_is_idempotent(self, mock_delay):
        row = schedule_email(
            recipient_email='x@ex.com',
            template_key='event_reminder',
            send_at=timezone.now() - timezone.timedelta(minutes=1),
            context={'event_title': 'X'},
        )
        dispatch_scheduled_emails()
        dispatch_scheduled_emails()  # second run must not re-dispatch
        row.refresh_from_db()
        assert row.status == ScheduledEmail.Status.DISPATCHED
        assert EmailLog.objects.filter(recipient_email='x@ex.com').count() == 1

    @patch('integrations.tasks.send_email.delay')
    def test_cancelled_row_never_dispatched(self, mock_delay):
        row = schedule_email(
            recipient_email='c@ex.com',
            template_key='event_reminder',
            send_at=timezone.now() - timezone.timedelta(minutes=1),
            context={'event_title': 'C'},
        )
        row.cancel('changed mind')
        dispatch_scheduled_emails()
        row.refresh_from_db()
        assert row.status == ScheduledEmail.Status.CANCELLED
        assert row.email_log is None
