"""
Integrations app models - EmailLog.
"""

from django.db import models
from django.utils import timezone

from common.models import BaseModel


class EmailLog(BaseModel):
    """
    Log of emails sent through the platform.
    """

    class EmailType(models.TextChoices):
        VERIFICATION = 'verification', 'Email Verification'
        PASSWORD_RESET = 'password_reset', 'Password Reset'
        EVENT_REMINDER = 'event_reminder', 'Event Reminder'
        REGISTRATION_CONFIRM = 'registration_confirm', 'Registration Confirmation'
        CERTIFICATE = 'certificate', 'Certificate Delivery'
        INVITATION = 'invitation', 'Event Invitation'
        EVENT_UPDATE = 'event_update', 'Event Update'
        WAITLIST_PROMOTION = 'waitlist_promotion', 'Waitlist Promotion'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        DELIVERED = 'delivered', 'Delivered'
        OPENED = 'opened', 'Opened'
        CLICKED = 'clicked', 'Clicked'
        BOUNCED = 'bounced', 'Bounced'
        FAILED = 'failed', 'Failed'

    # Recipient
    recipient_email = models.EmailField(db_index=True)
    recipient_name = models.CharField(max_length=255, blank=True)
    recipient_user = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='emails_received'
    )

    # Email Details
    email_type = models.CharField(max_length=30, choices=EmailType.choices, db_index=True)
    subject = models.CharField(max_length=255)

    # Related Objects
    event = models.ForeignKey('events.Event', on_delete=models.SET_NULL, null=True, blank=True, related_name='emails')
    registration = models.ForeignKey(
        'registrations.Registration', on_delete=models.SET_NULL, null=True, blank=True, related_name='emails'
    )
    certificate = models.ForeignKey(
        'certificates.Certificate', on_delete=models.SET_NULL, null=True, blank=True, related_name='emails'
    )

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)

    # Timestamps
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)

    # Error
    error_message = models.TextField(blank=True)

    # Provider
    provider_message_id = models.CharField(max_length=100, blank=True, help_text="Message ID from email provider")

    class Meta:
        db_table = 'email_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient_email']),
            models.Index(fields=['email_type', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['event']),
        ]
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'

    def __str__(self):
        return f"{self.email_type} to {self.recipient_email}"

    def mark_sent(self, message_id=''):
        """Mark email as sent."""
        self.status = self.Status.SENT
        self.sent_at = timezone.now()
        self.provider_message_id = message_id
        self.save(update_fields=['status', 'sent_at', 'provider_message_id', 'updated_at'])

    def mark_delivered(self):
        """Mark email as delivered."""
        self.status = self.Status.DELIVERED
        self.delivered_at = timezone.now()
        self.save(update_fields=['status', 'delivered_at', 'updated_at'])

    def mark_opened(self):
        """Mark email as opened."""
        if self.status not in [self.Status.OPENED, self.Status.CLICKED]:
            self.status = self.Status.OPENED
            self.opened_at = timezone.now()
            self.save(update_fields=['status', 'opened_at', 'updated_at'])

    def mark_clicked(self):
        """Mark email as clicked."""
        self.status = self.Status.CLICKED
        self.clicked_at = timezone.now()
        if not self.opened_at:
            self.opened_at = timezone.now()
        self.save(update_fields=['status', 'clicked_at', 'opened_at', 'updated_at'])

    def mark_bounced(self, error=''):
        """Mark email as bounced."""
        self.status = self.Status.BOUNCED
        self.error_message = error
        self.save(update_fields=['status', 'error_message', 'updated_at'])

    def mark_failed(self, error):
        """Mark email as failed."""
        self.status = self.Status.FAILED
        self.error_message = error
        self.save(update_fields=['status', 'error_message', 'updated_at'])
