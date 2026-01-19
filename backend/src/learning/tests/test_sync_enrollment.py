
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework import status

from learning.models import Course, CourseEnrollment


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()

@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(email='test@example.com', password='password', full_name='Test User')

@pytest.fixture
def course(db, user):
    return Course.objects.create(
        title="Test Course",
        price_cents=1000,
        status=Course.Status.PUBLISHED,
        owner=user
    )

@pytest.mark.django_db
class TestSyncEnrollment:

    def test_confirm_enrollment_success(self, api_client, user, course):
        api_client.force_authenticate(user=user)
        url = reverse('learning:course-enrollment-confirm-checkout')

        session_id = 'cs_test_123'

        # Mock Stripe Service
        with patch('learning.services.StripeService') as MockStripeService:
            # Setup mock
            mock_service_instance = MockStripeService.return_value
            mock_session = MagicMock()
            mock_session.payment_status = 'paid'
            mock_session.metadata = {'course_uuid': str(course.uuid)}

            mock_service_instance.retrieve_checkout_session.return_value = {
                'success': True,
                'session': mock_session
            }

            # Make request
            response = api_client.post(url, {'session_id': session_id})

            # Verify response
            assert response.status_code == status.HTTP_200_OK
            assert response.data['status'] == 'active'

            # Verify DB
            enrollment = CourseEnrollment.objects.get(user=user, course=course)
            assert enrollment.status == CourseEnrollment.Status.ACTIVE
            assert enrollment.stripe_checkout_session_id == session_id

    def test_confirm_enrollment_idempotency(self, api_client, user, course):
        """Verify calling twice doesn't error or duplicate."""
        api_client.force_authenticate(user=user)
        url = reverse('learning:course-enrollment-confirm-checkout')
        session_id = 'cs_test_123'

        # Pre-create enrollment
        CourseEnrollment.objects.create(
            user=user,
            course=course,
            status=CourseEnrollment.Status.ACTIVE,
            stripe_checkout_session_id=session_id
        )

        with patch('learning.services.StripeService') as MockStripeService:
            mock_service_instance = MockStripeService.return_value
            mock_session = MagicMock()
            mock_session.payment_status = 'paid'
            mock_session.metadata = {'course_uuid': str(course.uuid)}

            mock_service_instance.retrieve_checkout_session.return_value = {
                'success': True,
                'session': mock_session
            }

            response = api_client.post(url, {'session_id': session_id})
            assert response.status_code == status.HTTP_200_OK
            assert CourseEnrollment.objects.filter(user=user, course=course).count() == 1

    def test_confirm_enrollment_with_zoom(self, api_client, user, course):
        """Verify synchronous Zoom registration."""
        api_client.force_authenticate(user=user)
        url = reverse('learning:course-enrollment-confirm-checkout')

        # Setup hybrid course with Zoom
        course.format = Course.CourseFormat.HYBRID
        course.zoom_meeting_id = '123456789'
        course.save()

        session_id = 'cs_test_zoom'

        # Mock Stripe
        with patch('learning.services.StripeService') as MockStripeService:
            mock_stripe_instance = MockStripeService.return_value
            mock_session = MagicMock()
            mock_session.payment_status = 'paid'
            mock_session.metadata = {'course_uuid': str(course.uuid)}
            mock_stripe_instance.retrieve_checkout_session.return_value = {
                'success': True,
                'session': mock_session
            }

            # Mock Zoom Service
            with patch('accounts.services.zoom_service.add_meeting_registrant') as mock_zoom_register:
                mock_zoom_register.return_value = {
                    'success': True,
                    'join_url': 'https://zoom.us/j/unique_link',
                    'registrant_id': 'reg_123'
                }

                response = api_client.post(url, {'session_id': session_id})

                assert response.status_code == status.HTTP_200_OK

                # Check DB
                enrollment = CourseEnrollment.objects.get(user=user, course=course)
                assert enrollment.zoom_join_url == 'https://zoom.us/j/unique_link'
                assert enrollment.zoom_registrant_id == 'reg_123'

                # Verify Zoom called
                mock_zoom_register.assert_called_once()
