"""
Celery tasks for certificates.
"""

from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task
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


@shared_task
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


@shared_task
def bulk_issue_certificates(event_id: int, issued_by_id: int = None):
    """
    Issue certificates in bulk for an event.
    """
    from events.models import Event
    from accounts.models import User
    from certificates.services import certificate_service
    
    try:
        event = Event.objects.get(id=event_id)
        issued_by = None
        if issued_by_id:
            try:
                issued_by = User.objects.get(id=issued_by_id)
            except User.DoesNotExist:
                pass
        
        result = certificate_service.issue_bulk(event, issued_by=issued_by)
        logger.info(f"Bulk issued certificates for event {event_id}: {result}")
        return result
        
    except Event.DoesNotExist:
        return {'error': 'Event not found'}


@shared_task
def issue_certificate_for_registration(registration_id: int, issued_by_id: int = None):
    """
    Issue certificate for a single registration.
    """
    from registrations.models import Registration
    from accounts.models import User
    from certificates.services import certificate_service
    
    try:
        registration = Registration.objects.get(id=registration_id)
        issued_by = None
        if issued_by_id:
            try:
                issued_by = User.objects.get(id=issued_by_id)
            except User.DoesNotExist:
                pass
        
        result = certificate_service.issue_certificate(registration, issued_by=issued_by)
        
        if result.get('success') and result.get('certificate'):
            # Send email
            send_certificate_email.delay(result['certificate'].id)
        
        return result.get('success', False)
        
    except Registration.DoesNotExist:
        return False
