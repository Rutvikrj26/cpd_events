"""P5 — course flow email lifecycle (enrollment / module-released / completed)."""

from unittest.mock import MagicMock, patch

import pytest

from accounts.models import Notification
from integrations.models import EmailLog
from learning.tasks import (
    send_course_completed,
    send_enrollment_confirmation,
    send_module_released,
)


@pytest.mark.django_db
class TestSendEnrollmentConfirmation:
    @patch('django.core.mail.EmailMultiAlternatives')
    def test_creates_log_and_notification(self, mock_emm):
        mock_emm.return_value = MagicMock(send=MagicMock(return_value=1))
        from factories import CourseEnrollmentFactory

        enrollment = CourseEnrollmentFactory()

        ok = send_enrollment_confirmation(enrollment.id)
        assert ok is True
        log = EmailLog.objects.filter(recipient_user=enrollment.user, email_type='course_enrolled').first()
        assert log is not None
        assert log.status == 'sent'
        n = Notification.objects.filter(user=enrollment.user, notification_type='course_enrolled').first()
        assert n is not None
        assert n.metadata.get('course_uuid') == str(enrollment.course.uuid)

    @patch('django.core.mail.EmailMultiAlternatives')
    def test_idempotent_under_repeat_call(self, mock_emm):
        mock_emm.return_value = MagicMock(send=MagicMock(return_value=1))
        from factories import CourseEnrollmentFactory

        enrollment = CourseEnrollmentFactory()
        send_enrollment_confirmation(enrollment.id)
        send_enrollment_confirmation(enrollment.id)
        # Only ONE EmailLog row total — idempotency check on second call.
        assert EmailLog.objects.filter(
            recipient_user=enrollment.user,
            email_type='course_enrolled',
        ).count() == 1

    @patch('django.core.mail.EmailMultiAlternatives')
    def test_pref_off_skips_send_but_creates_notification(self, mock_emm):
        mock_emm.return_value = MagicMock(send=MagicMock(return_value=1))
        from factories import CourseEnrollmentFactory, UserFactory

        user = UserFactory(notify_course_progress=False)
        enrollment = CourseEnrollmentFactory(user=user)
        send_enrollment_confirmation(enrollment.id)

        assert mock_emm.return_value.send.called is False
        # Notification still created.
        assert Notification.objects.filter(user=user, notification_type='course_enrolled').exists()


@pytest.mark.django_db
class TestSendCourseCompleted:
    @patch('django.core.mail.EmailMultiAlternatives')
    def test_only_fires_when_status_completed(self, mock_emm):
        mock_emm.return_value = MagicMock(send=MagicMock(return_value=1))
        from factories import CourseEnrollmentFactory

        enrollment = CourseEnrollmentFactory()  # status=active (signal fires enrollment email)
        # Reset call tracking — we only care about the explicit send_course_completed call below.
        mock_emm.return_value.send.reset_mock()

        ok = send_course_completed(enrollment.id)
        assert ok is False  # active, not completed → no-op
        assert mock_emm.return_value.send.called is False

    @patch('django.core.mail.EmailMultiAlternatives')
    def test_fires_when_completed(self, mock_emm):
        mock_emm.return_value = MagicMock(send=MagicMock(return_value=1))
        from factories import CourseEnrollmentFactory

        enrollment = CourseEnrollmentFactory(status='completed')
        ok = send_course_completed(enrollment.id)
        assert ok is True
        assert EmailLog.objects.filter(
            recipient_user=enrollment.user,
            email_type='course_completed',
        ).exists()
        assert Notification.objects.filter(
            user=enrollment.user,
            notification_type='course_completed',
        ).exists()


@pytest.mark.django_db
class TestSendModuleReleased:
    @patch('django.core.mail.EmailMultiAlternatives')
    def test_creates_log_and_notification(self, mock_emm):
        mock_emm.return_value = MagicMock(send=MagicMock(return_value=1))
        from learning.models import EventModule
        from factories import CourseEnrollmentFactory

        enrollment = CourseEnrollmentFactory()
        module = EventModule.objects.create(title='Module 1', is_published=True)
        send_module_released(enrollment.id, module.id)

        log = EmailLog.objects.filter(
            recipient_user=enrollment.user, email_type='module_released'
        ).first()
        assert log is not None
        n = Notification.objects.filter(
            user=enrollment.user, notification_type='module_released'
        ).first()
        assert n is not None
        assert n.metadata.get('module_id') == module.id


@pytest.mark.django_db
class TestEnrollmentSignalTriggers:
    @patch('learning.tasks.send_enrollment_confirmation.delay')
    def test_active_create_fires_enrollment_email(self, mock_delay):
        from factories import CourseEnrollmentFactory

        enrollment = CourseEnrollmentFactory()
        mock_delay.assert_called_once_with(enrollment.id)

    @patch('learning.tasks.send_course_completed.delay')
    def test_status_to_completed_fires_completion_email(self, mock_delay):
        from factories import CourseEnrollmentFactory

        enrollment = CourseEnrollmentFactory()
        mock_delay.assert_not_called()

        enrollment.status = 'completed'
        enrollment.save()
        mock_delay.assert_called_once_with(enrollment.id)

    @patch('learning.tasks.send_course_completed.delay')
    def test_no_double_fire_on_resave_when_already_completed(self, mock_delay):
        from factories import CourseEnrollmentFactory

        enrollment = CourseEnrollmentFactory(status='completed')
        # First save was create — no completion email (signal only fires on
        # transition, not on initial create with status=completed).
        # A second save should also not re-fire.
        enrollment.progress_percent = 100
        enrollment.save()
        mock_delay.assert_not_called()
