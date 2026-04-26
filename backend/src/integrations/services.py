"""
Integration services for email and external providers.
"""

import logging
from typing import Any

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


# =============================================================================
# Notification preference gating
# =============================================================================
#
# Maps a template_key (or EmailLog.email_type) to the User boolean field that
# gates whether the email is delivered. ``None`` means the email is always
# transactional and ignores prefs (registration confirmations, password
# resets, payment receipts, etc.).
EMAIL_PREF_MAP: dict[str, str | None] = {
    # Transactional — always send
    "registration_confirmation": None,
    "registration_confirm": None,
    "password_reset": None,
    "email_verification": None,
    "verification": None,
    "payment_failed": None,
    "refund_processed": None,
    "payment_method_expired": None,
    "invitation": None,
    "organization_invitation": None,
    # Pref-gated
    "event_reminder": "notify_event_reminders",
    "event_cancelled": "notify_event_updates",
    "event_update": "notify_event_updates",
    "waitlist_promotion": "notify_event_updates",
    "certificate_issued": "notify_certificate_issued",
    "certificate": "notify_certificate_issued",
    "badge_issued": "notify_badges",
    "recording_available": "notify_recordings",
    "course_enrolled": "notify_course_progress",
    "enrollment_confirmation": "notify_course_progress",
    "module_released": "notify_course_progress",
    "course_completed": "notify_course_progress",
    "discussion_reply": "notify_event_updates",  # share existing toggle
    "discussion_mention": "notify_event_updates",
}


def user_allows_email(user, template_key: str) -> bool:
    """Whether this user wants to receive emails of this template type.

    Anonymous (no User) recipients always receive — they can't manage prefs
    and reminders go to the email they registered with. Transactional types
    always go through. For unknown templates we default to allow.
    """
    pref_field = EMAIL_PREF_MAP.get(template_key)
    if pref_field is None:
        return True
    if user is None:
        return True
    return bool(getattr(user, pref_field, True))


# Map email template_key → in-app Notification.Type. Templates not in the map
# are not mirrored into the user's inbox (e.g., password reset, payment receipts).
#
# NOTE: Course-flow templates (course_enrolled, module_released, course_completed)
# are deliberately NOT auto-mirrored here — the learning tasks own that path
# explicitly because they need to set richer metadata (course_uuid, module_id,
# enrollment_id) that EmailLog has no FKs to provide.
TEMPLATE_NOTIFICATION_TYPE: dict[str, str] = {
    "event_reminder": "event_reminder_24h",  # default reminder type; offset_minutes refines it
    "event_cancelled": "event_cancelled",
    "event_update": "event_rescheduled",
    "waitlist_promotion": "waitlist_promoted",
    "certificate_issued": "certificate_issued",
    "certificate": "certificate_issued",
    "badge_issued": "badge_issued",
    "recording_available": "recording_available",
}


def create_notification_for_log(log, context: dict[str, Any]) -> None:
    """Mirror an outbound email as an in-app Notification for the recipient
    User (when there is one). Idempotent per (user, type, log.id) — repeat
    invocations don't create duplicates.
    """
    if not log.recipient_user_id:
        return
    template = log.email_type
    notif_type = TEMPLATE_NOTIFICATION_TYPE.get(template)
    if notif_type is None:
        return

    # Refine event_reminder by offset_minutes when present.
    if template == "event_reminder":
        offset = context.get("offset_minutes", None)
        if offset is not None and int(offset) <= 60:
            notif_type = "event_starting_soon"

    from accounts.models import Notification

    title = log.subject or context.get("event_title") or template.replace('_', ' ').title()
    message = ''
    if context.get("event_title") and template not in ("certificate_issued", "badge_issued"):
        message = f"{context.get('event_title')} — {context.get('event_date', '')}".strip(' —')

    action_url = context.get("join_url") or context.get("certificate_url") or context.get("verification_url") or ''

    metadata = {
        "email_log_id": log.id,
        "template_key": template,
    }
    if log.event_id:
        metadata["event_uuid"] = str(log.event.uuid)
    if log.registration_id:
        metadata["registration_uuid"] = str(log.registration.uuid)

    # ScheduledEmail.dispatch() is itself idempotent (no-op when status != PENDING),
    # so this path runs at most once per EmailLog. We don't add a separate check.
    Notification.objects.create(
        user_id=log.recipient_user_id,
        notification_type=notif_type,
        title=title,
        message=message,
        action_url=action_url,
        metadata=metadata,
    )


class EmailService:
    """
    Service for sending emails.

    Supports multiple backends and template rendering.
    """

    # Email template mapping
    TEMPLATES = {
        "registration_confirm": "emails/registration_confirmation.html",
        "registration_confirmation": "emails/registration_confirmation.html",
        "event_reminder": "emails/event_reminder.html",
        "certificate_issued": "emails/certificate_issued.html",
        "certificate": "emails/certificate_issued.html",
        "badge_issued": "emails/badge_issued.html",
        "event_cancelled": "emails/event_cancelled.html",
        "event_update": "emails/event_cancelled.html",
        "password_reset": "emails/password_reset.html",
        "email_verification": "emails/email_verification.html",
        "verification": "emails/email_verification.html",
        "invitation": "emails/invitation.html",
        "organization_invitation": "emails/organization_invitation.html",
        "payment_failed": "emails/payment_failed.html",
        "waitlist_promotion": "emails/waitlist_promotion.html",
        "refund_processed": "emails/refund_processed.html",
        "payment_method_expired": "emails/payment_method_expired.html",
        "trial_ending": "emails/trial_ending.html",
        "discussion_reply": "emails/discussion_reply.html",
        "discussion_mention": "emails/discussion_mention.html",
        # P5 — course flow
        "course_enrolled": "emails/enrollment_confirmation.html",
        "enrollment_confirmation": "emails/enrollment_confirmation.html",
        "module_released": "emails/module_released.html",
        "course_completed": "emails/course_completed.html",
        "session_cancelled": "emails/session_cancelled.html",
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
        "discussion_reply": "New reply in {thread_title}",
        "discussion_mention": "You were mentioned in {thread_title}",
        # P5 — course flow
        "course_enrolled": "You're enrolled in {course_title}",
        "enrollment_confirmation": "You're enrolled in {course_title}",
        "module_released": "New module unlocked: {module_title}",
        "course_completed": "Course complete: {course_title}",
    }

    def send_email(
        self,
        template: str,
        recipient: str,
        context: dict[str, Any],
        subject: str | None = None,
        attachments: list[tuple[str, str | bytes, str]] | None = None,
        locale: str = 'en',
    ) -> bool:
        """
        Send a templated email.

        Args:
            template: Template name
            recipient: Recipient email
            context: Template context
            subject: Optional custom subject
            attachments: Optional list of ``(filename, content, mimetype)``
                tuples — e.g. ``[('event.ics', ics_str, 'text/calendar; method=PUBLISH')]``.
            locale: Reserved for future i18n; currently a no-op.

        Returns:
            True if successful
        """
        from integrations.models import EmailLog

        try:
            # Render subject
            if subject is None:
                subject_template = self.SUBJECTS.get(template, "Notification")
                try:
                    subject = subject_template.format(**context)
                except (KeyError, IndexError):
                    subject = subject_template

            # Render body
            template_path = self.TEMPLATES.get(template)
            if template_path:
                try:
                    html_body = render_to_string(template_path, context)
                except Exception:
                    logger.warning("Template %s render failed; using fallback HTML", template_path, exc_info=True)
                    html_body = self._build_simple_html(template, context)
            else:
                html_body = self._build_simple_html(template, context)

            # Send via configured backend
            success = self._send(recipient, subject, html_body, attachments=attachments)

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

    def _send(
        self,
        recipient: str,
        subject: str,
        html_body: str,
        attachments: list[tuple[str, str | bytes, str]] | None = None,
    ) -> bool:
        """Send email via Django/Anymail. Uses EmailMultiAlternatives so we
        can attach files (e.g., ``.ics`` calendar invites)."""
        try:
            from django.core.mail import EmailMultiAlternatives

            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com")

            msg = EmailMultiAlternatives(
                subject=subject,
                body="",  # plaintext fallback (HTML below)
                from_email=from_email,
                to=[recipient],
            )
            msg.attach_alternative(html_body, "text/html")

            for filename, content, mimetype in attachments or []:
                msg.attach(filename, content, mimetype)

            msg.send(fail_silently=False)
            return True

        except Exception as e:
            logger.error("Email send via backend failed: %s", e)
            return False

    def send_log(
        self,
        log,
        context: dict[str, Any] | None = None,
        attachments: list[tuple[str, str | bytes, str]] | None = None,
    ) -> bool:
        """Render and send an email backed by an existing ``EmailLog`` row.

        This is the canonical path for ``ScheduledEmail.dispatch()`` and any
        caller that pre-creates an ``EmailLog`` to track delivery state. The
        log row is updated in place rather than a duplicate row being created.

        For learner-facing email types we always create an in-app
        ``Notification`` row (so the user sees it in their inbox), but only
        actually send the email when the user's preferences allow.
        """
        ctx = dict(context or {})
        # Auto-fill common context from related objects if missing.
        if log.event and 'event_title' not in ctx:
            ctx['event_title'] = log.event.title
            ctx['event_date'] = log.event.starts_at.strftime('%B %d, %Y at %I:%M %p')
        if log.registration and 'user_name' not in ctx:
            ctx['user_name'] = log.registration.full_name
        if log.certificate and 'certificate_url' not in ctx:
            ctx['certificate_url'] = getattr(log.certificate, 'verification_url', '') or ''

        # Mirror the email as an in-app Notification when the recipient is a
        # known User and the template maps to a learner-facing notification.
        try:
            create_notification_for_log(log, ctx)
        except Exception:
            logger.exception("Failed to create Notification for EmailLog %s", log.id)

        # Honor user notification preferences for non-transactional templates.
        if not user_allows_email(log.recipient_user, log.email_type):
            log.status = log.Status.SENT  # treat as fulfilled — Notification covers it
            log.sent_at = timezone.now()
            log.error_message = 'skipped: user disabled this email category'
            log.save(update_fields=['status', 'sent_at', 'error_message', 'updated_at'])
            return True

        template = log.email_type
        template_path = self.TEMPLATES.get(template)
        if template_path:
            try:
                html_body = render_to_string(template_path, ctx)
            except Exception:
                logger.warning("Template %s render failed; using fallback HTML", template_path, exc_info=True)
                html_body = self._build_simple_html(template, ctx)
        else:
            html_body = self._build_simple_html(template, ctx)

        success = self._send(log.recipient_email, log.subject, html_body, attachments=attachments)
        if success:
            log.mark_sent()
        else:
            log.mark_failed("Email backend send failed")
        return success

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


def schedule_email(
    *,
    recipient_email: str,
    template_key: str,
    send_at,
    subject: str | None = None,
    context: dict | None = None,
    recipient_name: str = '',
    recipient_user=None,
    event=None,
    registration=None,
    batch_key: str = '',
):
    """Create a ScheduledEmail. Subject is rendered from EmailService.SUBJECTS if not passed."""
    from integrations.models import ScheduledEmail

    ctx = context or {}
    if subject is None:
        subject_template = email_service.SUBJECTS.get(template_key, 'Notification')
        try:
            subject = subject_template.format(**ctx)
        except (KeyError, IndexError):
            subject = subject_template

    return ScheduledEmail.objects.create(
        recipient_email=recipient_email,
        recipient_name=recipient_name,
        recipient_user=recipient_user,
        template_key=template_key,
        subject=subject,
        context=ctx,
        event=event,
        registration=registration,
        send_at=send_at,
        batch_key=batch_key,
    )


def schedule_bulk_emails(
    *,
    recipients: list[dict],
    template_key: str,
    send_at,
    stagger_seconds: int = 0,
    common_context: dict | None = None,
    event=None,
    batch_key: str = '',
):
    """
    Schedule emails for many recipients. Space them out by `stagger_seconds`
    starting at `send_at` to avoid rate-limit spikes and to look more human.

    recipients: list of dicts with keys: email, name (opt), user (opt),
                registration (opt), context (opt).
    """
    from integrations.models import ScheduledEmail

    ctx_base = common_context or {}
    rows = []
    for idx, r in enumerate(recipients):
        if not r.get('email'):
            continue
        ctx = {**ctx_base, **(r.get('context') or {})}
        subject_template = email_service.SUBJECTS.get(template_key, 'Notification')
        try:
            subject = subject_template.format(**ctx)
        except (KeyError, IndexError):
            subject = subject_template
        rows.append(
            ScheduledEmail(
                recipient_email=r['email'],
                recipient_name=r.get('name', ''),
                recipient_user=r.get('user'),
                template_key=template_key,
                subject=subject,
                context=ctx,
                event=event,
                registration=r.get('registration'),
                send_at=send_at + timezone.timedelta(seconds=idx * stagger_seconds),
                batch_key=batch_key,
            )
        )
    if rows:
        ScheduledEmail.objects.bulk_create(rows)
    return len(rows)
