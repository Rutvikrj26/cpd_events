"""Account email helpers."""

import logging

from django.conf import settings
from django.core.mail import send_mail

from common.config.deployment import INSTITUTION_NAME

logger = logging.getLogger(__name__)


def send_invitation_email(invitation, fail_silently: bool = False) -> bool:
    """Send the invitation email for a UserInvitation.

    Returns True if the underlying send_mail call succeeded, False otherwise.
    When fail_silently is True, exceptions are swallowed and logged.
    """
    invite_url = f"{settings.FRONTEND_URL}/auth/accept-invitation?token={invitation.token}"

    expires_days = max(1, (invitation.expires_at - invitation.created_at).days)

    body_lines = [
        f"Hello {invitation.full_name},",
        "",
        f"You've been invited to join {INSTITUTION_NAME}.",
        "",
        "Click the following link to set up your account:",
        invite_url,
        "",
        f"This invitation expires in {expires_days} days.",
    ]
    if invitation.message:
        body_lines.extend(["", invitation.message])

    print("\n" + "=" * 80)
    print("📧 INVITATION LINK (copy this, NOT the email body below):")
    print(f"   {invite_url}")
    print("=" * 80 + "\n")

    try:
        send_mail(
            subject=f"You've been invited to {INSTITUTION_NAME}",
            message="\n".join(body_lines),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[invitation.email],
            fail_silently=False,
        )
        return True
    except Exception as exc:
        logger.error("Failed to send invitation email to %s: %s", invitation.email, exc)
        if not fail_silently:
            raise
        return False
