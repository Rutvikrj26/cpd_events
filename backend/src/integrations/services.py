"""
Integration services for email and external providers.
"""

import logging
from typing import Any

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


class EmailService:
    """
    Service for sending emails.

    Supports multiple backends and template rendering.
    """

    # Email template mapping
    TEMPLATES = {
        "registration_confirmation": "emails/registration_confirmation.html",
        "event_reminder": "emails/event_reminder.html",
        "certificate_issued": "emails/certificate_issued.html",
        "badge_issued": "emails/badge_issued.html",
        "event_cancelled": "emails/event_cancelled.html",
        "password_reset": "emails/password_reset.html",
        "email_verification": "emails/email_verification.html",
        "invitation": "emails/invitation.html",
        "organization_invitation": "emails/organization_invitation.html",
        "payment_failed": "emails/payment_failed.html",
        "waitlist_promotion": "emails/waitlist_promotion.html",
        "refund_processed": "emails/refund_processed.html",
        "payment_method_expired": "emails/payment_method_expired.html",
        "trial_ending": "emails/trial_ending.html",
    }

    # Subject lines
    SUBJECTS = {
        "registration_confirmation": "Registration Confirmed: {event_title}",
        "event_reminder": "Reminder: {event_title} starts soon",
        "certificate_issued": "Your Certificate: {event_title}",
        "badge_issued": "You earned a badge: {badge_name}",
        "event_cancelled": "Event Cancelled: {event_title}",
        "password_reset": "Password Reset Request",
        "email_verification": "Verify Your Email",
        "invitation": "You're invited: {event_title}",
        "organization_invitation": "You're invited to join {organization_name}",
        "payment_failed": "Payment Failed: Invoice #{invoice_number}",
        "waitlist_promotion": "Spot Available: {event_title}",
        "refund_processed": "Refund Processed: {event_title}",
        "payment_method_expired": "Payment Method Expired",
        "trial_ending": "Your Trial Is Ending Soon",
    }

    def send_email(self, template: str, recipient: str, context: dict[str, Any], subject: str | None = None) -> bool:
        """
        Send a templated email.

        Args:
            template: Template name
            recipient: Recipient email
            context: Template context
            subject: Optional custom subject

        Returns:
            True if successful
        """
        from integrations.models import EmailLog

        try:
            # Render subject
            if subject is None:
                subject_template = self.SUBJECTS.get(template, "Notification")
                subject = subject_template.format(**context)

            # Render body
            template_path = self.TEMPLATES.get(template)
            if template_path:
                try:
                    html_body = render_to_string(template_path, context)
                except Exception:
                    html_body = self._build_simple_html(template, context)
            else:
                html_body = self._build_simple_html(template, context)

            # Send via configured backend
            success = self._send(recipient, subject, html_body)

            # Log email
            EmailLog.objects.create(
                recipient_email=recipient,
                email_type=template,
                subject=subject,
                status="sent" if success else "failed",
                sent_at=timezone.now() if success else None,
            )

            return success

        except Exception as e:
            logger.error("Email send failed: %s", e)
            return False

    def send_bulk_emails(
        self, template: str, recipients: list[dict[str, Any]], common_context: dict | None = None
    ) -> dict[str, Any]:
        """
        Send emails to multiple recipients.

        Args:
            template: Template name
            recipients: List of {email, context} dicts
            common_context: Context shared by all emails

        Returns:
            Dict with success/failure counts
        """
        results = {"total": len(recipients), "sent": 0, "failed": 0}

        for recipient in recipients:
            email = recipient.get("email")
            ctx = {**(common_context or {}), **(recipient.get("context", {}))}

            if self.send_email(template, email, ctx):
                results["sent"] += 1
            else:
                results["failed"] += 1

        return results

    def _send(self, recipient: str, subject: str, html_body: str) -> bool:
        """Send email using Django's email backend."""
        try:
            from django.core.mail import send_mail

            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com")

            send_mail(
                subject=subject,
                message="",  # Plain text fallback
                from_email=from_email,
                recipient_list=[recipient],
                html_message=html_body,
                fail_silently=False,
            )

            return True

        except Exception as e:
            logger.error("Email send via backend failed: %s", e)
            return False

    def _build_simple_html(self, template: str, context: dict) -> str:
        """Build simple HTML email when template not found."""
        lines = [
            f"<p>Hello {context.get('user_name', 'there')},</p>",
        ]

        if template == "certificate_issued":
            lines.append(f"<p>Your certificate for <strong>{context.get('event_title', 'the event')}</strong> is ready.</p>")
            if context.get("certificate_url"):
                lines.append(f"<p><a href='{context['certificate_url']}'>Download Certificate</a></p>")

        elif template == "badge_issued":
            lines.append(
                f"<p>Congratulations! You have earned the <strong>{context.get('badge_name', 'Badge')}</strong> for <strong>{context.get('event_title', 'the event')}</strong>.</p>"
            )
            if context.get("badge_url"):
                lines.append(f"<p><img src='{context['badge_url']}' alt='Badge' width='200' /></p>")
                lines.append(f"<p><a href='{context.get('verification_url', '#')}'>View & Verify Badge</a></p>")

        elif template == "registration_confirmation":
            lines.append(f"<p>You are registered for <strong>{context.get('event_title', 'the event')}</strong>.</p>")

        elif template == "event_reminder":
            lines.append(f"<p><strong>{context.get('event_title', 'Your event')}</strong> starts soon.</p>")

        elif template == "organization_invitation":
            lines.append(
                f"<p>{context.get('inviter_name', 'Someone')} has invited you to join <strong>{context.get('organization_name', 'their organization')}</strong> as a <strong>{context.get('role', 'member')}</strong>.</p>"
            )
            if context.get("invitation_url"):
                lines.append(
                    f"<p><a href='{context['invitation_url']}' style='background-color: #0066cc; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;'>Accept Invitation</a></p>"
                )
            lines.append("<p>This invitation will expire in 7 days.</p>")

        else:
            for key, value in context.items():
                if isinstance(value, str) and key not in ["user_name"]:
                    lines.append(f"<p>{key}: {value}</p>")

        lines.append("<p>Best regards,<br>The Team</p>")

        return "\n".join(lines)


# Singleton instance
email_service = EmailService()
