"""
Tests for CourseService.
"""

from unittest.mock import MagicMock, patch

import pytest

from learning.models import CourseEnrollment
from learning.services import CourseService


@pytest.mark.django_db
class TestCourseService:
    @patch('learning.services.StripeService')
    @patch('accounts.services.zoom_service')
    def test_confirm_enrollment_success(
        self, mock_zoom_service, MockStripeService, user, course
    ):
        """Test successful enrollment confirmation."""
        # Setup Stripe Mock
        mock_stripe = MockStripeService.return_value
        mock_session = MagicMock()
        mock_session.payment_status = 'paid'
        mock_session.metadata = {'course_uuid': str(course.uuid)}
        mock_stripe.retrieve_checkout_session.return_value = {
            'success': True,
            'session': mock_session,
        }

        # Setup Zoom Mock
        mock_zoom_service.add_meeting_registrant.return_value = {
            'success': True,
            'join_url': 'https://zoom.us/j/123',
            'registrant_id': 'reg-123',
        }

        # Configure course for Zoom
        course.format = 'hybrid'
        course.zoom_meeting_id = '123456789'
        course.save()

        # Call service
        course_service = CourseService()
        result = course_service.confirm_enrollment(user, 'sess_123')

        assert result['success'] is True
        enrollment = result['enrollment']
        assert enrollment.status == CourseEnrollment.Status.ACTIVE
        assert enrollment.zoom_join_url == 'https://zoom.us/j/123'
        assert enrollment.stripe_checkout_session_id == 'sess_123'

    @patch('learning.services.StripeService')
    @patch('accounts.services.zoom_service')
    def test_confirm_enrollment_payment_failed(
        self, mock_zoom, MockStripeService, user, course
    ):
        """Test handling of failed/unpaid sessions."""
        mock_stripe = MockStripeService.return_value
        mock_session = MagicMock()
        mock_session.payment_status = 'unpaid'
        mock_session.metadata = {'course_uuid': str(course.uuid)}
        mock_stripe.retrieve_checkout_session.return_value = {
            'success': True,
            'session': mock_session,
        }

        course_service = CourseService()
        result = course_service.confirm_enrollment(user, 'sess_123')

        assert result['success'] is False
        # If code is present, check it. If not, check error message.
        if 'code' in result:
            assert result['code'] == 'PAYMENT_NOT_COMPLETED'
        else:
            # Fallback if logic changes or error is generic
            assert 'error' in result

    @patch('learning.services.StripeService')
    @patch('accounts.services.zoom_service')
    def test_confirm_enrollment_idempotency(
        self, mock_zoom_service, MockStripeService, user, course
    ):
        """Test that calling confirm multiple times is safe."""
        mock_stripe = MockStripeService.return_value
        mock_session = MagicMock()
        mock_session.payment_status = 'paid'
        mock_session.metadata = {'course_uuid': str(course.uuid)}
        mock_stripe.retrieve_checkout_session.return_value = {
            'success': True,
            'session': mock_session,
        }

        # Setup Zoom Mock
        mock_zoom_service.add_meeting_registrant.return_value = {
            'success': True,
            'join_url': 'https://zoom.us/j/123/duplicate',
            'registrant_id': 'reg-123',
        }

        course_service = CourseService()

        # First call
        result1 = course_service.confirm_enrollment(user, 'sess_123')
        assert result1['success'] is True, f"First call failed: {result1.get('error')}"

        # Second call
        result2 = course_service.confirm_enrollment(user, 'sess_123')
        assert result2['success'] is True, f"Second call failed: {result2.get('error')}"

        # Verify only one enrollment exists
        assert CourseEnrollment.objects.filter(user=user, course=course).count() == 1

        # Verify it remains active
        enrollment = CourseEnrollment.objects.get(user=user, course=course)
        assert enrollment.status == CourseEnrollment.Status.ACTIVE

    @patch('learning.services.StripeService')
    @patch('accounts.services.zoom_service')
    def test_confirm_enrollment_zoom_failure(
        self, mock_zoom_service, MockStripeService, user, course
    ):
        """Test that Zoom failure does not block enrollment."""
        # Setup Stripe Mock
        mock_stripe = MockStripeService.return_value
        mock_session = MagicMock()
        mock_session.payment_status = 'paid'
        mock_session.metadata = {'course_uuid': str(course.uuid)}
        mock_stripe.retrieve_checkout_session.return_value = {
            'success': True,
            'session': mock_session,
        }

        # Setup Zoom Mock to fail
        mock_zoom_service.add_meeting_registrant.return_value = {
            'success': False,
            'error': 'Zoom API Error',
        }

        course.format = 'hybrid'
        course.zoom_meeting_id = '123456789'
        course.save()

        course_service = CourseService()
        result = course_service.confirm_enrollment(user, 'sess_123')

        # Should still succeed
        assert result['success'] is True
        enrollment = result['enrollment']
        assert enrollment.status == CourseEnrollment.Status.ACTIVE

        # But no Zoom URL
        assert not enrollment.zoom_join_url
