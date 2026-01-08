import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from integrations.services import EmailService
from integrations.models import EmailLog

@pytest.mark.django_db
class TestEmailService:
    @patch('django.core.mail.send_mail')
    def test_send_email_success(self, mock_send_mail):
        """Test successful email sending."""
        service = EmailService()
        recipient = 'test@example.com'
        template = 'registration_confirmation'
        context = {'user_name': 'Test User', 'event_title': 'Test Event'}
        
        # Success case
        success = service.send_email(template, recipient, context)
        
        assert success is True
        mock_send_mail.assert_called_once()
        
        # Verify EmailLog created with correct status
        log = EmailLog.objects.last()
        assert log.recipient_email == recipient
        assert log.email_type == template
        assert log.status == 'sent'
        assert log.sent_at is not None

    @patch('django.core.mail.send_mail')
    def test_send_email_failure(self, mock_send_mail):
        """Test partial failure (backend raises exception)."""
        mock_send_mail.side_effect = Exception("SMTP Error")
        
        service = EmailService()
        recipient = 'test@example.com'
        template = 'registration_confirmation'
        # Fix: Provide required context for subject formatting
        context = {'user_name': 'Test User', 'event_title': 'Test Event'}
        
        with patch('integrations.services.logger') as mock_logger:
             success = service.send_email(template, recipient, context)
        
        assert success is False
        
        # Verify EmailLog created with failed status
        log = EmailLog.objects.last()
        assert log is not None
        assert log.recipient_email == recipient
        assert log.status == 'failed'
        assert log.sent_at is None

    @patch('django.core.mail.send_mail')
    def test_simple_html_fallback(self, mock_send_mail):
        """Test fallback to simple HTML if template missing."""
        service = EmailService()
        recipient = 'test@example.com'
        template = 'non_existent_template'
        context = {'special_key': 'special_value'}
        
        success = service.send_email(template, recipient, context)
        
        assert success is True
        args, kwargs = mock_send_mail.call_args
        html_message = kwargs.get('html_message')
        assert 'special_key: special_value' in html_message
