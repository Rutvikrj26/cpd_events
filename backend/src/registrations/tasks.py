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
