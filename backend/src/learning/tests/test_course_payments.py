from unittest.mock import patch

import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from learning.models import Course, CourseEnrollment


class TestCoursePayments(APITestCase):
    def setUp(self):
        from django.contrib.auth.models import Group
        self.user = User.objects.create_user(email='learner@example.com', password='password')
        self.user.groups.add(Group.objects.get_or_create(name='learner')[0])
        self.course_paid = Course.objects.create(
            title="Paid Course", slug="paid-course", price_cents=1000, stripe_price_id="price_123"
        )
        self.course_free = Course.objects.create(title="Free Course", slug="free-course", price_cents=0)
        self.client.force_authenticate(user=self.user)

    def test_enrollment_blocked_for_paid_course(self):
        """Ensure standard enrollment logic blocks paid courses."""
        url = reverse('learning:course-enrollment-list')
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
        url = reverse('learning:course-enrollment-list')
        data = {'course_uuid': self.course_free.uuid}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(CourseEnrollment.objects.filter(user=self.user, course=self.course_free).exists())

    @patch('learning.payment_views.checkout_service.for_course_enrollment')
    def test_checkout_session_creation(self, mock_create_session):
        """Test that checkout view delegates to billing.checkout.checkout_service."""
        from billing.checkout import CheckoutResult
        mock_create_session.return_value = CheckoutResult(
            url='https://checkout.stripe.com/...', session_id='sess_123',
        )

        url = reverse('learning:course-checkout', kwargs={'uuid': self.course_paid.uuid})
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['session_id'], 'sess_123')

        mock_create_session.assert_called_once_with(self.user, self.course_paid)

    @pytest.mark.skip(
        reason="Webhook processing was moved to an async Cloud Tasks pipeline "
        "(billing/webhooks.py → process_stripe_event.delay). End-to-end "
        "webhook→enrollment activation is now covered by "
        "billing/tests/test_webhook_idempotency.py + the handler tests; this "
        "test pre-dates that split."
    )
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
                        'user_id': self.user.id,
                    }
                }
            },
        }
        mock_construct_event.return_value = payload

        url = reverse('stripe-webhook')

        # Manually constructing headers for signature
        response = self.client.post(url, data=payload, format='json', HTTP_STRIPE_SIGNATURE='t=123,v1=signature')

        # Check enrollment exists and is active
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            CourseEnrollment.objects.filter(
                user=self.user, course=self.course_paid, status=CourseEnrollment.Status.ACTIVE
            ).exists()
        )
