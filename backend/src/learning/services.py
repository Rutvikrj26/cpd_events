"""
Services for the learning app.
"""

import logging
from typing import Any

from django.db import transaction, OperationalError
from django.shortcuts import get_object_or_404
from django.utils import timezone
import stripe

from billing.services import StripeService
from .models import Course, CourseEnrollment

logger = logging.getLogger(__name__)


class CourseService:
    """Service for managing course operations."""
    
    def __init__(self):
        self.stripe_service = StripeService()

    def confirm_enrollment(self, user, session_id: str) -> dict[str, Any]:
        """
        Confirm a course enrollment from a Stripe checkout session.
        
        Args:
            user: The user checking out
            session_id: The Stripe Checkout Session ID
            
        Returns:
            dict with success/error and enrollment data
        """
        # 1. Verify session with Stripe
        session_result = self.stripe_service.retrieve_checkout_session(session_id)
        if not session_result.get('success'):
            return {'success': False, 'error': session_result.get('error')}
        
        session = session_result['session']
        
        # Verify payment status
        if session.payment_status != 'paid':
             return {'success': False, 'error': 'Payment not completed', 'code': 'PAYMENT_NOT_COMPLETED'}
             
        # Extract course ID from metadata
        course_uuid = session.metadata.get('course_uuid')
        if not course_uuid:
            return {'success': False, 'error': 'No course ID in session metadata'}

        try:
            course = Course.objects.get(uuid=course_uuid)
        except Course.DoesNotExist:
             return {'success': False, 'error': 'Course not found'}

        # 2. Create/Activate Enrollment (with retry for locking)
        import time
        from accounts.services import zoom_service
        
        max_retries = 3
        enrollment = None
        
        for attempt in range(max_retries):
            try:
                with transaction.atomic():
                    # Create or update enrollment
                    enrollment, created = CourseEnrollment.objects.get_or_create(
                        course=course,
                        user=user,
                        defaults={
                            'status': CourseEnrollment.Status.ACTIVE,
                            'enrolled_at': timezone.now(),
                            'access_type': CourseEnrollment.AccessType.LIFETIME, 
                            'stripe_checkout_session_id': session_id,
                        }
                    )
                    
                    # If it existed but was inactive/pending payment, activate it
                    if not created and enrollment.status != CourseEnrollment.Status.ACTIVE:
                        enrollment.status = CourseEnrollment.Status.ACTIVE
                        if not enrollment.enrolled_at:
                            enrollment.enrolled_at = timezone.now()
                        enrollment.stripe_checkout_session_id = session_id
                        enrollment.save(update_fields=['status', 'enrolled_at', 'stripe_checkout_session_id', 'updated_at'])
                
                # Success - break loop
                break
                
            except OperationalError as e:
                # Retry on SQLite database locked error
                if 'locked' in str(e).lower() and attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                logger.error(f"Database locked confirming course enrollment: {e}")
                return {'success': False, 'error': 'System busy, please try again'}
                
            except Exception as e:
                logger.error(f"Failed to confirm course enrollment: {e}")
                return {'success': False, 'error': str(e)}
        else:
            # Loop finished without breaking = failed all retries
            return {'success': False, 'error': 'Failed to confirm enrollment after retries'}

        # 3. Synchronous Zoom Registration (if hybrid)
        if enrollment and course.format == 'hybrid' and course.zoom_meeting_id:
            try:
                # Split full name
                full_name = getattr(user, 'full_name', '').strip()
                if ' ' in full_name:
                    first_name, last_name = full_name.rsplit(' ', 1)
                else:
                    first_name = full_name
                    last_name = '.' # Zoom requires last name
                
                zoom_result = zoom_service.add_meeting_registrant(
                    event=course, 
                    email=user.email,
                    first_name=first_name,
                    last_name=last_name
                )
                
                if zoom_result['success']:
                    enrollment.zoom_join_url = zoom_result['join_url']
                    enrollment.zoom_registrant_id = zoom_result['registrant_id']
                    enrollment.save(update_fields=['zoom_join_url', 'zoom_registrant_id', 'updated_at'])
                else:
                    logger.warning(f"Failed to register user {user.email} for Zoom meeting {course.zoom_meeting_id}: {zoom_result.get('error')}")
                    
            except Exception as e:
                 logger.error(f"Error during Zoom registration: {e}")
                 # We don't fail the enrollment, just log
        
        return {'success': True, 'enrollment': enrollment}
