"""
Celery tasks for integrations.
"""

from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task
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


@shared_task
def cleanup_old_logs(days_old: int = 30):
    """
    Clean up old webhook logs.
    """
    from integrations.models import ZoomWebhookLog, EmailLog
    
    cutoff = timezone.now() - timezone.timedelta(days=days_old)
    
    # Delete old webhook logs
    webhook_count = ZoomWebhookLog.objects.filter(
        created_at__lt=cutoff,
        processing_successful=True
    ).delete()[0]
    
    # Delete old email logs
    email_count = EmailLog.objects.filter(
        created_at__lt=cutoff,
        delivery_status='sent'
    ).delete()[0]
    
    logger.info(f"Cleaned up {webhook_count} webhook logs and {email_count} email logs")
    return {'webhooks': webhook_count, 'emails': email_count}


@shared_task
def retry_failed_webhooks():
    """
    Retry failed webhook processing.
    """
    from integrations.models import ZoomWebhookLog
    
    # Get failed webhooks that haven't been retried too many times
    failed = ZoomWebhookLog.objects.filter(
        processing_successful=False,
        retry_count__lt=3
    ).order_by('created_at')[:10]
    
    count = 0
    for log in failed:
        log.retry_count += 1
        log.save(update_fields=['retry_count', 'updated_at'])
        process_zoom_webhook.delay(log.id)
        count += 1
    
    return count


@shared_task
def send_email_batch(template: str, recipients: list, common_context: dict = None):
    """
    Send batch emails.
    """
    from integrations.services import email_service
    
    return email_service.send_bulk_emails(
        template=template,
        recipients=recipients,
        common_context=common_context
    )


@shared_task
def sync_zoom_recordings(event_id: int):
    """
    Sync Zoom recordings for an event.
    """
    from events.models import Event
    from accounts.services import zoom_service
    from integrations.models import ZoomRecording
    import requests
    
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
            timeout=30
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
                }
            )
        
        return True
        
    except Event.DoesNotExist:
        return False
