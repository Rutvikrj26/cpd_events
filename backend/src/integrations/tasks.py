"""
Cloud tasks for integrations.
"""

import logging

from django.utils import timezone

from common.cloud_tasks import task

logger = logging.getLogger(__name__)


@task()
def process_zoom_webhook(log_id: int):
    """
    Process a Zoom webhook log entry.
    """
    from integrations.models import ZoomWebhookLog
    from integrations.services import webhook_processor

    try:
        log = ZoomWebhookLog.objects.get(id=log_id)
        log.processing_started_at = timezone.now()
        log.save(update_fields=['processing_started_at', 'updated_at'])

        success = webhook_processor.process_zoom_webhook(log)

        log.processed_at = timezone.now()
        log.processing_successful = success
        log.save(update_fields=['processed_at', 'processing_successful', 'updated_at'])

        return success

    except ZoomWebhookLog.DoesNotExist:
        return False


@task()
def cleanup_old_logs(webhook_days: int = 90, email_days: int = 365):
    """
    Clean up old webhook and email logs.

    Args:
        webhook_days: Days to retain webhook logs (default 90)
        email_days: Days to retain email logs (default 365)
    """
    from integrations.models import EmailLog, ZoomWebhookLog

    webhook_cutoff = timezone.now() - timezone.timedelta(days=webhook_days)
    email_cutoff = timezone.now() - timezone.timedelta(days=email_days)

    # Delete old webhook logs
    webhook_count = ZoomWebhookLog.objects.filter(created_at__lt=webhook_cutoff, processing_status='completed').delete()[0]

    # Delete old email logs
    email_count = EmailLog.objects.filter(
        created_at__lt=email_cutoff, status__in=['sent', 'delivered', 'opened', 'clicked']
    ).delete()[0]

    logger.info(f"Cleaned up {webhook_count} webhook logs and {email_count} email logs")
    return {'webhooks': webhook_count, 'emails': email_count}


@task()
def retry_failed_webhooks():
    """
    Retry failed webhook processing.
    """
    from integrations.models import ZoomWebhookLog

    # Get failed webhooks that haven't been retried too many times
    failed = ZoomWebhookLog.objects.filter(
        processing_status=ZoomWebhookLog.ProcessingStatus.FAILED, processing_attempts__lt=3
    ).order_by('created_at')[:100]

    count = 0
    for log in failed:
        process_zoom_webhook.delay(log.id)
        count += 1

    logger.info(f"Queued {count} failed webhooks for retry")
    return count


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
            logger.info(f"Email {email_log_id} already processed, skipping")
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
        logger.error(f"EmailLog {email_log_id} not found")
        return False
    except Exception as e:
        logger.error(f"Error sending email {email_log_id}: {e}")
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

    logger.info(f"Queued {count} failed emails for retry")
    return count


@task()
def send_email_batch(template: str, recipients: list, common_context: dict = None):
    """
    Send batch emails.
    """
    from integrations.services import email_service

    return email_service.send_bulk_emails(template=template, recipients=recipients, common_context=common_context)


@task()
def sync_zoom_recordings(event_id: int):
    """
    Sync Zoom recordings for an event.
    """
    import requests

    from accounts.services import zoom_service
    from events.models import Event
    from integrations.models import ZoomRecording

    try:
        event = Event.objects.get(id=event_id)

        if not event.zoom_meeting_id:
            return False

        # Get access token
        from accounts.models import ZoomConnection

        try:
            connection = ZoomConnection.objects.get(user=event.owner, is_active=True)
            access_token = zoom_service.get_access_token(connection)
        except ZoomConnection.DoesNotExist:
            return False

        if not access_token:
            return False

        # Fetch recordings from Zoom
        response = requests.get(
            f"https://api.zoom.us/v2/meetings/{event.zoom_meeting_id}/recordings",
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=30,
        )

        if response.status_code != 200:
            return False

        data = response.json()

        # Create recording records
        for rec_file in data.get('recording_files', []):
            ZoomRecording.objects.update_or_create(
                event=event,
                recording_id=rec_file.get('id', ''),
                defaults={
                    'zoom_meeting_id': event.zoom_meeting_id,
                    'topic': data.get('topic', ''),
                    'recording_type': rec_file.get('recording_type', ''),
                    'file_type': rec_file.get('file_type', ''),
                    'file_size': rec_file.get('file_size', 0),
                    'download_url': rec_file.get('download_url', ''),
                    'play_url': rec_file.get('play_url', ''),
                    'status': rec_file.get('status', ''),
                },
            )

        return True

    except Event.DoesNotExist:
        return False
