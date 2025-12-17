"""
Cloud tasks for certificates.
"""

import contextlib
import logging

from common.cloud_tasks import task

logger = logging.getLogger(__name__)


@task()
def generate_certificate_pdf(certificate_id: int):
    """
    Generate PDF for a certificate.
    """
    from certificates.models import Certificate
    from certificates.services import certificate_service

    try:
        cert = Certificate.objects.get(id=certificate_id)
        pdf_bytes = certificate_service.generate_pdf(cert)
        if pdf_bytes:
            url = certificate_service.upload_pdf(cert, pdf_bytes)
            return url is not None
        return False
    except Certificate.DoesNotExist:
        return False


@task()
def send_certificate_email(certificate_id: int):
    """
    Send certificate email to attendee.
    """
    from certificates.models import Certificate
    from certificates.services import certificate_service

    try:
        cert = Certificate.objects.get(id=certificate_id)
        return certificate_service.send_certificate_email(cert)
    except Certificate.DoesNotExist:
        return False


@task()
def bulk_issue_certificates(event_id: int, issued_by_id: int = None):
    """
    Issue certificates in bulk for an event.
    """
    from accounts.models import User
    from certificates.services import certificate_service
    from events.models import Event

    try:
        event = Event.objects.get(id=event_id)
        issued_by = None
        if issued_by_id:
            with contextlib.suppress(User.DoesNotExist):
                issued_by = User.objects.get(id=issued_by_id)

        result = certificate_service.issue_bulk(event, issued_by=issued_by)
        logger.info(f"Bulk issued certificates for event {event_id}: {result}")
        return result

    except Event.DoesNotExist:
        return {'error': 'Event not found'}


@task()
def issue_certificate_for_registration(registration_id: int, issued_by_id: int = None):
    """
    Issue certificate for a single registration.
    """
    from accounts.models import User
    from certificates.services import certificate_service
    from registrations.models import Registration

    try:
        registration = Registration.objects.get(id=registration_id)
        issued_by = None
        if issued_by_id:
            with contextlib.suppress(User.DoesNotExist):
                issued_by = User.objects.get(id=issued_by_id)

        result = certificate_service.issue_certificate(registration, issued_by=issued_by)

        if result.get('success') and result.get('certificate'):
            # Send email
            send_certificate_email.delay(result['certificate'].id)

        return result.get('success', False)

    except Registration.DoesNotExist:
        return False


@task()
def auto_issue_certificates(event_id: int):
    """
    Automatically issue certificates for all eligible registrations.
    Called after event completion.

    Args:
        event_id: ID of the completed event
    """
    from certificates.services import certificate_service
    from events.models import Event
    from registrations.models import Registration

    try:
        event = Event.objects.get(id=event_id)

        # Event must be completed and have certificates enabled
        if event.status != 'completed':
            logger.warning(f"Event {event_id} is not completed, skipping auto-issue")
            return {'issued': 0, 'skipped': 0}

        if not event.certificate_enabled:
            logger.info(f"Certificates not enabled for event {event_id}")
            return {'issued': 0, 'skipped': 0}

        # Get eligible registrations (attended and meeting attendance threshold)
        registrations = Registration.objects.filter(
            event=event, status='attended', certificate_issued=False, deleted_at__isnull=True
        )

        issued = 0
        skipped = 0

        for reg in registrations:
            # Check attendance eligibility
            if not reg.attendance_eligible:
                skipped += 1
                continue

            try:
                result = certificate_service.issue_certificate(registration=reg, issued_by=event.owner)  # Auto-issued by owner
                if result.get('success'):
                    issued += 1
                    # Queue certificate email
                    if result.get('certificate'):
                        send_certificate_email.delay(result['certificate'].id)
                else:
                    skipped += 1
            except Exception as e:
                logger.error(f"Failed to issue certificate for registration {reg.id}: {e}")
                skipped += 1

        logger.info(f"Auto-issued {issued} certificates for event {event_id} ({skipped} skipped)")
        return {'issued': issued, 'skipped': skipped}

    except Event.DoesNotExist:
        logger.error(f"Event {event_id} not found")
        return {'issued': 0, 'skipped': 0, 'error': 'Event not found'}
