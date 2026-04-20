"""
Cloud tasks for integrations.
"""

import logging

from django.utils import timezone

from common.cloud_tasks import task

logger = logging.getLogger(__name__)


@task()
def cleanup_old_logs(email_days: int = 365):
    """
    Clean up old email logs.

    Args:
        email_days: Days to retain email logs (default 365)
    """
    from integrations.models import EmailLog

    email_cutoff = timezone.now() - timezone.timedelta(days=email_days)

    # Delete old email logs
    email_count = EmailLog.objects.filter(
        created_at__lt=email_cutoff, status__in=['sent', 'delivered', 'opened', 'clicked']
    ).delete()[0]

    logger.info("Cleaned up %s email logs", email_count)
    return {'emails': email_count}


@task()
def send_email(email_log_id: int):
    """
    Send a single email from an EmailLog record.

    Args:
        email_log_id: ID of the EmailLog to send
    """
    from integrations.models import EmailLog
    from integrations.services import email_service

    try:
        log = EmailLog.objects.get(id=email_log_id)

        if log.status != EmailLog.Status.PENDING:
            logger.info("Email %s already processed, skipping", email_log_id)
            return False

        # Build context from related objects
        context = {
            'recipient_name': log.recipient_name,
            'recipient_email': log.recipient_email,
        }

        if log.event:
            context['event_title'] = log.event.title
            context['event_date'] = log.event.starts_at.strftime('%B %d, %Y at %I:%M %p')

        if log.registration:
            context['user_name'] = log.registration.full_name

        if log.certificate:
            context['certificate_url'] = log.certificate.verification_url

        # Send via service
        success = email_service._send(
            recipient=log.recipient_email,
            subject=log.subject,
            html_body=email_service._build_simple_html(log.email_type, context),
        )

        if success:
            log.mark_sent()
        else:
            log.mark_failed("Failed to send via backend")

        return success

    except EmailLog.DoesNotExist:
        logger.error("EmailLog %s not found", email_log_id)
        return False
    except Exception as e:
        logger.error("Error sending email %s: %s", email_log_id, e)
        return False


@task()
def retry_failed_emails():
    """
    Retry failed email sends (up to 3 attempts).
    """
    from integrations.models import EmailLog

    # Find failed emails that can be retried
    failed = EmailLog.objects.filter(status=EmailLog.Status.FAILED).order_by('created_at')[:100]

    count = 0
    for log in failed:
        # Reset status and queue for retry
        log.status = EmailLog.Status.PENDING
        log.error_message = ''
        log.save(update_fields=['status', 'error_message', 'updated_at'])
        send_email.delay(log.id)
        count += 1

    logger.info("Queued %s failed emails for retry", count)
    return count


@task()
def send_email_batch(template: str, recipients: list, common_context: dict = None):
    """
    Send batch emails.
    """
    from integrations.services import email_service

    return email_service.send_bulk_emails(template=template, recipients=recipients, common_context=common_context)


@task()
def dispatch_scheduled_emails(limit: int = 500):
    """
    Dispatch ScheduledEmails whose send_at is due. Invoked on a periodic
    schedule (e.g., every minute). Staggering is handled at scheduling time by
    spacing out send_at values across recipients.
    """
    from integrations.models import ScheduledEmail

    now = timezone.now()
    due_qs = ScheduledEmail.objects.filter(status=ScheduledEmail.Status.PENDING, send_at__lte=now).order_by('send_at')[:limit]

    dispatched = 0
    failed = 0
    for scheduled in due_qs:
        try:
            if scheduled.dispatch() is not None:
                dispatched += 1
        except Exception as e:
            logger.error("Failed to dispatch ScheduledEmail %s: %s", scheduled.id, e)
            scheduled.status = ScheduledEmail.Status.FAILED
            scheduled.error_message = str(e)[:500]
            scheduled.save(update_fields=['status', 'error_message', 'updated_at'])
            failed += 1

    logger.info("Dispatched %s scheduled emails (%s failed)", dispatched, failed)
    return {'dispatched': dispatched, 'failed': failed}
