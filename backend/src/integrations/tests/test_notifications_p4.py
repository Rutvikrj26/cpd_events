"""P4 — pref-gating + Notification mirroring on email send."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from accounts.models import Notification
from integrations.models import EmailLog
from integrations.services import EmailService, user_allows_email


@pytest.mark.django_db
class TestUserAllowsEmail:
    def test_transactional_always_allowed(self, db):
        from factories import UserFactory

        user = UserFactory(notify_event_reminders=False)
        # Transactional templates ignore prefs.
        for tpl in ('registration_confirmation', 'password_reset', 'payment_failed', 'invitation'):
            assert user_allows_email(user, tpl) is True

    def test_anonymous_recipient_always_allowed(self, db):
        assert user_allows_email(None, 'event_reminder') is True

    def test_pref_gates_event_reminder(self, db):
        from factories import UserFactory

        user_off = UserFactory(notify_event_reminders=False)
        user_on = UserFactory(notify_event_reminders=True)
        assert user_allows_email(user_off, 'event_reminder') is False
        assert user_allows_email(user_on, 'event_reminder') is True

    def test_pref_gates_badge_email(self, db):
        from factories import UserFactory

        user_off = UserFactory(notify_badges=False)
        assert user_allows_email(user_off, 'badge_issued') is False


@pytest.mark.django_db
class TestSendLogPrefGating:
    @patch('django.core.mail.EmailMultiAlternatives')
    def test_pref_off_creates_notification_but_skips_email(self, mock_emm, db):
        mock_emm.return_value = MagicMock(send=MagicMock(return_value=1))
        from factories import EventFactory, RegistrationFactory, UserFactory

        user = UserFactory(notify_event_reminders=False)
        event = EventFactory(published=True, starts_at=timezone.now() + timedelta(days=1))
        reg = RegistrationFactory(event=event, user=user, email=user.email)
        log = EmailLog.objects.create(
            recipient_email=user.email,
            recipient_name=user.full_name,
            recipient_user=user,
            email_type='event_reminder',
            subject='Reminder',
            event=event,
            registration=reg,
        )

        service = EmailService()
        # Use offset > 60 so the refinement keeps the 24h type.
        ok = service.send_log(log, context={'event_title': event.title, 'offset_minutes': 1440})

        assert ok is True
        # The actual SMTP/Anymail send was NOT invoked (pref off → skipped).
        assert mock_emm.return_value.send.called is False

        # The Notification row WAS created so the user still sees it in-app.
        n = Notification.objects.filter(user=user).first()
        assert n is not None
        assert n.notification_type == 'event_reminder_24h'
        assert n.metadata.get('email_log_id') == log.id

        # EmailLog status reflects the skip.
        log.refresh_from_db()
        assert log.status == EmailLog.Status.SENT
        assert 'skipped' in log.error_message

    @patch('django.core.mail.EmailMultiAlternatives')
    def test_pref_on_sends_email_and_creates_notification(self, mock_emm, db):
        mock_emm.return_value = MagicMock(send=MagicMock(return_value=1))
        from factories import EventFactory, RegistrationFactory, UserFactory

        user = UserFactory(notify_event_reminders=True)
        event = EventFactory(published=True, starts_at=timezone.now() + timedelta(days=1))
        reg = RegistrationFactory(event=event, user=user, email=user.email)
        log = EmailLog.objects.create(
            recipient_email=user.email,
            recipient_name=user.full_name,
            recipient_user=user,
            email_type='event_reminder',
            subject='Reminder',
            event=event,
            registration=reg,
        )

        service = EmailService()
        ok = service.send_log(log, context={'event_title': event.title, 'offset_minutes': 0})

        assert ok is True
        mock_emm.return_value.send.assert_called_once()
        n = Notification.objects.filter(user=user).first()
        assert n is not None
        # offset=0 → starting_soon refinement
        assert n.notification_type == 'event_starting_soon'

    @patch('django.core.mail.EmailMultiAlternatives')
    def test_transactional_send_proceeds_even_when_user_off(self, mock_emm, db):
        mock_emm.return_value = MagicMock(send=MagicMock(return_value=1))
        from factories import EventFactory, RegistrationFactory, UserFactory

        user = UserFactory(notify_event_reminders=False, notify_event_updates=False)
        event = EventFactory(published=True, starts_at=timezone.now() + timedelta(days=1))
        reg = RegistrationFactory(event=event, user=user, email=user.email)
        log = EmailLog.objects.create(
            recipient_email=user.email,
            recipient_name=user.full_name,
            recipient_user=user,
            email_type='registration_confirmation',
            subject='Confirmed',
            event=event,
            registration=reg,
        )

        service = EmailService()
        service.send_log(log, context={'event_title': event.title, 'user_name': user.full_name})

        # Transactional always sends.
        mock_emm.return_value.send.assert_called_once()
