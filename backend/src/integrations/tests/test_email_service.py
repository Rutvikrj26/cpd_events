from unittest.mock import MagicMock, patch

import pytest

from integrations.models import EmailLog
from integrations.services import EmailService


@pytest.mark.django_db
class TestEmailService:
    @patch('django.core.mail.EmailMultiAlternatives')
    def test_send_email_success(self, mock_emm):
        """Test successful email sending."""
        mock_emm.return_value = MagicMock(send=MagicMock(return_value=1))

        service = EmailService()
        recipient = 'test@example.com'
        template = 'registration_confirmation'
        context = {'user_name': 'Test User', 'event_title': 'Test Event'}

        success = service.send_email(template, recipient, context)

        assert success is True
        mock_emm.assert_called_once()
        mock_emm.return_value.send.assert_called_once()

        # Verify EmailLog created with correct status
        log = EmailLog.objects.last()
        assert log.recipient_email == recipient
        assert log.email_type == template
        assert log.status == 'sent'
        assert log.sent_at is not None

    @patch('django.core.mail.EmailMultiAlternatives')
    def test_send_email_failure(self, mock_emm):
        """Backend raise → row marked failed."""
        instance = MagicMock()
        instance.send.side_effect = Exception("SMTP Error")
        mock_emm.return_value = instance

        service = EmailService()
        recipient = 'test@example.com'
        template = 'registration_confirmation'
        context = {'user_name': 'Test User', 'event_title': 'Test Event'}

        success = service.send_email(template, recipient, context)

        assert success is False

        log = EmailLog.objects.last()
        assert log is not None
        assert log.recipient_email == recipient
        assert log.status == 'failed'
        assert log.sent_at is None

    @patch('django.core.mail.EmailMultiAlternatives')
    def test_simple_html_fallback(self, mock_emm):
        """Test fallback to simple HTML if template missing."""
        mock_emm.return_value = MagicMock(send=MagicMock(return_value=1))

        service = EmailService()
        recipient = 'test@example.com'
        template = 'non_existent_template'
        context = {'special_key': 'special_value'}

        success = service.send_email(template, recipient, context)

        assert success is True
        # The HTML body is attached as the alternative
        attach_calls = mock_emm.return_value.attach_alternative.call_args_list
        assert any('special_key: special_value' in (call.args[0] if call.args else '') for call in attach_calls)

    @patch('django.core.mail.EmailMultiAlternatives')
    def test_attachments_passed_through(self, mock_emm):
        """``.ics`` (and other) attachments reach the underlying message."""
        mock_emm.return_value = MagicMock(send=MagicMock(return_value=1))

        service = EmailService()
        ics = "BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n"
        attachments = [('event.ics', ics, 'text/calendar; method=PUBLISH; charset=utf-8')]

        service.send_email(
            'registration_confirmation', 'a@b.test',
            {'user_name': 'A', 'event_title': 'Foo'},
            attachments=attachments,
        )

        # Message.attach() called for each attachment
        attach_calls = mock_emm.return_value.attach.call_args_list
        assert len(attach_calls) == 1
        args, _ = attach_calls[0]
        assert args[0] == 'event.ics'
        assert args[1] == ics
        assert args[2].startswith('text/calendar')


@pytest.mark.django_db
class TestSendLog:
    @patch('django.core.mail.EmailMultiAlternatives')
    def test_send_log_renders_template_against_log_relations(self, mock_emm):
        mock_emm.return_value = MagicMock(send=MagicMock(return_value=1))

        from datetime import timedelta
        from django.utils import timezone

        from factories import EventFactory, RegistrationFactory

        event = EventFactory(
            published=True,
            starts_at=timezone.now() + timedelta(days=1),
            title='SendLog Smoke',
        )
        reg = RegistrationFactory(event=event, status='confirmed')

        log = EmailLog.objects.create(
            recipient_email=reg.email,
            recipient_name=reg.full_name,
            email_type='event_reminder',
            subject='Reminder: SendLog Smoke',
            event=event,
            registration=reg,
        )

        service = EmailService()
        ok = service.send_log(log, context={'user_name': reg.full_name, 'event_title': event.title, 'event_date': 'Tomorrow', 'join_url': 'http://x.test/lobby', 'offset_minutes': 0})

        assert ok is True
        log.refresh_from_db()
        assert log.status == 'sent'
        # Template rendered (we passed user_name + event_title which the template uses)
        attach_calls = mock_emm.return_value.attach_alternative.call_args_list
        rendered = attach_calls[0].args[0]
        assert 'SendLog Smoke' in rendered
