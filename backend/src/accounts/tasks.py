import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from common.cloud_tasks import task

logger = logging.getLogger(__name__)
User = get_user_model()


@task()
def send_email_verification(user_uuid, verification_url):
    """Send email verification link."""
    try:
        user = User.objects.get(uuid=user_uuid)
        subject = "Verify your email address - CPD Events"
        html_message = render_to_string('emails/verification.html', {'user': user, 'verification_url': verification_url})
        plain_message = strip_tags(html_message)

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
        )
        logger.info(f"Verification email sent to {user.email}")
    except User.DoesNotExist:
        logger.error(f"User {user_uuid} not found for verification email")
    except Exception as e:
        logger.error(f"Failed to send verify email to user {user_uuid}: {e}")


@task()
def send_password_reset(user_uuid, reset_url):
    """Send password reset link."""
    try:
        user = User.objects.get(uuid=user_uuid)
        subject = "Reset your password - CPD Events"
        html_message = render_to_string('emails/password_reset.html', {'user': user, 'reset_url': reset_url})
        plain_message = strip_tags(html_message)

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
        )
        logger.info(f"Password reset email sent to {user.email}")
    except User.DoesNotExist:
        logger.error(f"User {user_uuid} not found for password reset email")
    except Exception as e:
        logger.error(f"Failed to send password reset email to user {user_uuid}: {e}")


@task()
def cleanup_expired_tokens():
    """Remove expired email verification and password reset tokens."""
    now = timezone.now()
    expired_verifications = User.objects.filter(
        email_verification_sent_at__isnull=False,
        email_verification_sent_at__lt=now - timezone.timedelta(hours=24),
    ).exclude(email_verification_token='')

    expired_password_resets = User.objects.filter(
        password_reset_sent_at__isnull=False,
        password_reset_sent_at__lt=now - timezone.timedelta(hours=24),
    ).exclude(password_reset_token='')

    cleared = 0
    cleared += expired_verifications.update(email_verification_token='', updated_at=now)
    cleared += expired_password_resets.update(password_reset_token='', updated_at=now)

    logger.info("Cleared %s expired tokens", cleared)
    return cleared
