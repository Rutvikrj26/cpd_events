from common.cloud_tasks import task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from django.utils.html import strip_tags

import logging

logger = logging.getLogger(__name__)
User = get_user_model()

@task()
def send_email_verification(user_id, verification_url):
    """Send email verification link."""
    try:
        user = User.objects.get(pk=user_id)
        subject = "Verify your email address - CPD Events"
        html_message = render_to_string('emails/verification.html', {
            'user': user,
            'verification_url': verification_url
        })
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
        logger.error(f"User {user_id} not found for verification email")
    except Exception as e:
        logger.error(f"Failed to send verify email to user {user_id}: {e}")

@task()
def send_password_reset(user_id, reset_url):
    """Send password reset link."""
    try:
        user = User.objects.get(pk=user_id)
        subject = "Reset your password - CPD Events"
        html_message = render_to_string('emails/password_reset.html', {
            'user': user,
            'reset_url': reset_url
        })
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
        logger.error(f"User {user_id} not found for password reset email")
    except Exception as e:
        logger.error(f"Failed to send password reset email to user {user_id}: {e}")
