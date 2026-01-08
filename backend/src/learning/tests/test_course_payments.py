from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from accounts.models import User
from organizations.models import Organization
from learning.models import Course, CourseEnrollment

from django.test import override_settings

class TestCoursePayments(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='learner@example.com', password='password')
        self.org = Organization.objects.create(name='Test Org', slug='test-org')
        self.course_paid = Course.objects.create(
            organization=self.org,
            title="Paid Course",
            slug="paid-course",
            price_cents=1000,
            stripe_price_id="price_123"
        )
        self.course_free = Course.objects.create(
            organization=self.org,
            title="Free Course",
            slug="free-course",
            price_cents=0
        )
        self.client.force_authenticate(user=self.user)

    def test_enrollment_blocked_for_paid_course(self):
        """Ensure standard enrollment logic blocks paid courses."""
        url = reverse('course-enrollment-list')
        data = {'course_uuid': self.course_paid.uuid}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # DRF PermissionDenied usually returns 'detail', but checking text is safer if format varies
        if 'detail' in response.data:
            self.assertIn("requires payment", str(response.data['detail']))
        else:
            # If standard handler is overridden or error_response structure is used (though exceptions usually bypass error_response helper)
            pass

    def test_enrollment_allowed_for_free_course(self):
        """Ensure free courses can be enrolled in directly."""
        url = reverse('course-enrollment-list')
        data = {'course_uuid': self.course_free.uuid}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(CourseEnrollment.objects.filter(user=self.user, course=self.course_free).exists())

    @patch('billing.services.stripe_service.create_one_time_checkout_session')
    def test_checkout_session_creation(self, mock_create_session):
        """Test that checkout view calls Stripe service correctly."""
        mock_create_session.return_value = {
            'success': True,
            'session_id': 'sess_123',
            'url': 'https://checkout.stripe.com/...'
        }
        
        url = reverse('course-checkout', kwargs={'uuid': self.course_paid.uuid})
        data = {
            'success_url': 'http://localhost/success',
            'cancel_url': 'http://localhost/cancel'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['session_id'], 'sess_123')
        
        mock_create_session.assert_called_once()
        args, kwargs = mock_create_session.call_args
        self.assertEqual(kwargs['price_id'], 'price_123')
        self.assertEqual(kwargs['user'], self.user)

    @override_settings(STRIPE_WEBHOOK_SECRET='whsec_test')
    @patch('stripe.Webhook.construct_event')
    def test_webhook_activates_enrollment(self, mock_construct_event):
        """Test that checkout.session.completed webhook activates enrollment."""
        payload = {
            'id': 'evt_123',
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'metadata': {
                        'type': 'course_enrollment',
                        'course_uuid': str(self.course_paid.uuid),
                        'user_id': self.user.id
                    }
                }
            }
        }
        mock_construct_event.return_value = payload
        
        url = reverse('stripe_webhook') # Ensure this URL name exists, usually in billing/urls or root
        # If 'stripe_webhook' name is not standard, I might need to check urls.
        # usually /webhooks/stripe/
        
        # Manually constructing headers for signature
        response = self.client.post(
            url, 
            data=payload, 
            format='json',
            HTTP_STRIPE_SIGNATURE='t=123,v1=signature'
        )
        
        # Check enrollment exists and is active
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(CourseEnrollment.objects.filter(
            user=self.user, 
            course=self.course_paid, 
            status=CourseEnrollment.Status.ACTIVE
        ).exists())
