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
        COURSE_SESSION_REMINDER = 'course_session_reminder', 'Course Session Reminder'
        COURSE_SESSION_UPDATE = 'course_session_update', 'Course Session Update'

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


class ScheduledEmail(BaseModel):
    """
    Queued email intent. A periodic task dispatches due rows by creating an
    EmailLog + enqueueing send. Used for reminders, speaker follow-ups, and any
    future-dated send. Stagger large batches by spacing send_at values.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        DISPATCHED = 'dispatched', 'Dispatched'
        CANCELLED = 'cancelled', 'Cancelled'
        FAILED = 'failed', 'Failed'

    recipient_email = models.EmailField(db_index=True)
    recipient_name = models.CharField(max_length=255, blank=True)
    recipient_user = models.ForeignKey(
        'accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='scheduled_emails'
    )

    template_key = models.CharField(max_length=50, db_index=True)
    subject = models.CharField(max_length=255)
    context = models.JSONField(default=dict, blank=True)

    event = models.ForeignKey(
        'events.Event', null=True, blank=True, on_delete=models.CASCADE, related_name='scheduled_emails'
    )
    registration = models.ForeignKey(
        'registrations.Registration', null=True, blank=True, on_delete=models.CASCADE, related_name='scheduled_emails'
    )

    send_at = models.DateTimeField(db_index=True)
    batch_key = models.CharField(max_length=64, blank=True, db_index=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    email_log = models.ForeignKey(
        'integrations.EmailLog', null=True, blank=True, on_delete=models.SET_NULL, related_name='scheduled_sources'
    )
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = 'scheduled_emails'
        ordering = ['send_at']
        indexes = [
            models.Index(fields=['status', 'send_at']),
            models.Index(fields=['batch_key']),
        ]

    def __str__(self):
        return f"{self.template_key} → {self.recipient_email} @ {self.send_at.isoformat()}"

    def dispatch(self):
        """Create an EmailLog and enqueue send. Idempotent per ScheduledEmail."""
        from integrations.tasks import send_email

        if self.status != self.Status.PENDING:
            return None

        email_type = self.template_key
        valid_types = {choice[0] for choice in EmailLog.EmailType.choices}
        if email_type not in valid_types:
            email_type = EmailLog.EmailType.EVENT_UPDATE

        log = EmailLog.objects.create(
            recipient_email=self.recipient_email,
            recipient_name=self.recipient_name,
            recipient_user=self.recipient_user,
            email_type=email_type,
            subject=self.subject,
            event=self.event,
            registration=self.registration,
        )
        self.email_log = log
        self.status = self.Status.DISPATCHED
        self.dispatched_at = timezone.now()
        self.save(update_fields=['email_log', 'status', 'dispatched_at', 'updated_at'])
        send_email.delay(log.id)
        return log

    def cancel(self, reason=''):
        if self.status == self.Status.PENDING:
            self.status = self.Status.CANCELLED
            if reason:
                self.error_message = reason
            self.save(update_fields=['status', 'error_message', 'updated_at'])
