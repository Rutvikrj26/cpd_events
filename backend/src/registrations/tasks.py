"""
Cloud tasks for registrations.
"""

import logging

from django.utils import timezone

from common.cloud_tasks import task

logger = logging.getLogger(__name__)


@task()
def send_registration_confirmation(registration_id: int):
    """
    Send registration confirmation email.

    Args:
        registration_id: ID of the registration to confirm
    """
    from integrations.models import EmailLog
    from integrations.tasks import send_email
    from registrations.models import Registration

    try:
        registration = Registration.objects.select_related('event', 'user').get(id=registration_id)

        if registration.status != 'confirmed':
            logger.warning(f"Registration {registration_id} is not confirmed, skipping")
            return False

        # Create email log
        email_log = EmailLog.objects.create(
            recipient_email=registration.email,
            recipient_name=registration.full_name,
            recipient_user=registration.user,
            email_type=EmailLog.EmailType.REGISTRATION_CONFIRM,
            subject=f"Registration Confirmed: {registration.event.title}",
            event=registration.event,
            registration=registration,
        )

        # Queue for sending
        send_email.delay(email_log.id)

        # Update registration
        registration.confirmation_sent = True
        registration.confirmation_sent_at = timezone.now()
        registration.save(update_fields=['confirmation_sent', 'confirmation_sent_at', 'updated_at'])

        logger.info(f"Queued confirmation email for registration {registration_id}")
        return True

    except Registration.DoesNotExist:
        logger.error(f"Registration {registration_id} not found")
        return False


@task()
def send_registration_confirmations(registration_ids: list):
    """
    Send registration confirmation emails in batch.

    Args:
        registration_ids: List of registration IDs
    """
    count = 0
    for reg_id in registration_ids:
        send_registration_confirmation.delay(reg_id)
        count += 1

    logger.info(f"Queued {count} registration confirmations")
    return count


@task()
def add_zoom_registrant(registration_id: int, retry_count: int = 0):
    """
    Add registration to Zoom meeting as registrant.

    Background task that adds a confirmed registration to the Zoom meeting
    as a registrant, giving them a unique join URL.

    Args:
        registration_id: Registration ID to add to Zoom
        retry_count: Current retry attempt (for app-level retry logic)

    Returns:
        bool: True if successful, False otherwise
    """
    from accounts.services import zoom_service
    from registrations.models import Registration

    # Retry configuration
    MAX_RETRIES = 5
    BACKOFF_BASE_SECONDS = 60  # 1 minute base, doubles each retry

    try:
        registration = Registration.objects.select_related('event').get(id=registration_id)

        # Skip if no Zoom meeting
        if not registration.event.zoom_meeting_id:
            logger.info(f"Skipping Zoom for {registration.uuid}: No meeting")
            return False

        # Idempotency: Skip if already registered
        if registration.zoom_registrant_id:
            logger.info(f"Already registered to Zoom: {registration.uuid}")
            return True

        # Only add confirmed registrations
        if registration.status != Registration.Status.CONFIRMED:
            logger.info(f"Skipping non-confirmed registration: {registration.uuid}")
            return False

        # Parse name
        name_parts = registration.full_name.split(' ', 1)
        first_name = name_parts[0] if name_parts else 'Guest'
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        # Call Zoom API
        result = zoom_service.add_meeting_registrant(
            event=registration.event,
            email=registration.email,
            first_name=first_name,
            last_name=last_name,
        )

        if result['success']:
            # Update registration
            registration.zoom_registrant_join_url = result['join_url']
            registration.zoom_registrant_id = result['registrant_id']
            registration.zoom_add_attempt_count = retry_count + 1
            registration.save(update_fields=[
                'zoom_registrant_join_url',
                'zoom_registrant_id',
                'zoom_add_attempt_count',
                'updated_at'
            ])

            logger.info(f"Added {registration.uuid} to Zoom: {result['registrant_id']}")
            return True
        else:
            error_msg = result.get('error', 'Unknown error')
            logger.error(f"Zoom registration failed for {registration.uuid}: {error_msg}")

            # App-level retry with exponential backoff
            if retry_count < MAX_RETRIES:
                next_retry = retry_count + 1
                backoff_seconds = BACKOFF_BASE_SECONDS * (2 ** retry_count)  # 60, 120, 240, 480, 960
                logger.info(
                    f"Scheduling retry {next_retry}/{MAX_RETRIES} for {registration.uuid} "
                    f"in {backoff_seconds}s"
                )
                # Update attempt count
                registration.zoom_add_attempt_count = next_retry
                registration.zoom_add_error = error_msg
                registration.save(update_fields=['zoom_add_attempt_count', 'zoom_add_error', 'updated_at'])

                # Schedule retry (uses Cloud Tasks scheduling if available)
                add_zoom_registrant.delay(registration_id, retry_count=next_retry)
                return False
            else:
                # Max retries exceeded - log and give up
                logger.error(
                    f"Max retries ({MAX_RETRIES}) exceeded for {registration.uuid}. "
                    f"Final error: {error_msg}"
                )
                registration.zoom_add_attempt_count = retry_count + 1
                registration.zoom_add_error = f"Max retries exceeded: {error_msg}"
                registration.save(update_fields=['zoom_add_attempt_count', 'zoom_add_error', 'updated_at'])
                return False

    except Registration.DoesNotExist:
        logger.error(f"Registration {registration_id} not found")
        return False
    except Exception as e:
        logger.error(f"Error adding to Zoom: {e}")
        # For unexpected exceptions, still use app-level retry
        if retry_count < MAX_RETRIES:
            logger.info(f"Scheduling retry after exception for registration {registration_id}")
            add_zoom_registrant.delay(registration_id, retry_count=retry_count + 1)
            return False
        raise  # Only raise after max retries to avoid Cloud Tasks retry loop

