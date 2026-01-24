"""
Signals for the certificates app.

Handles automatic CPD credit awarding when certificates are issued.
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from certificates.models import Certificate

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Certificate)
def award_cpd_credits_on_certificate(sender, instance, created, **kwargs):
    """
    Automatically award CPD credits when a certificate is issued.

    This signal handler:
    1. Checks if certificate is active
    2. Ensures credits haven't been awarded yet for this certificate
    3. Extracts CPD credits from certificate_data
    4. Creates CPDTransaction record
    5. Updates User.total_cpd_credits balance
    """
    # Only process active certificates
    if instance.status != Certificate.Status.ACTIVE:
        return

    # Get the user from either registration or course enrollment
    user = None
    if instance.registration:
        user = instance.registration.user
    elif instance.course_enrollment:
        user = instance.course_enrollment.user

    if not user:
        # Silently fail if user not found (might be deleted or inconsistent state)
        return

    # Extract CPD credits from certificate data
    cpd_credits_val = instance.certificate_data.get("cpd_credits", 0)

    # Convert to Decimal for precision
    try:
        credits = Decimal(str(cpd_credits_val))
    except (TypeError, ValueError, ArithmeticError):
        return

    # Only process if credits > 0
    if credits <= 0:
        return

    # Import here to avoid circular dependency
    from accounts.models import CPDTransaction
    from django.db.models import F

    # Check if a transaction already exists for this certificate to avoid double-awarding
    # This replaces the 'created' check to make the system more robust to multiple saves during issuance
    if CPDTransaction.objects.filter(certificate=instance).exists():
        return

    # Use database transaction to ensure atomicity
    try:
        with transaction.atomic():
            # Refresh user with lock to prevent race conditions on balance update
            from accounts.models import User

            user_obj = User.objects.select_for_update().get(pk=user.pk)

            new_balance = user_obj.total_cpd_credits + credits

            # Create transaction record
            cpd_transaction = CPDTransaction.objects.create(
                user=user_obj,
                certificate=instance,
                transaction_type=CPDTransaction.TransactionType.EARNED,
                credits=credits,
                balance_after=new_balance,
                notes=f"Earned from {instance.context_title}",
                cpd_type=instance.certificate_data.get("cpd_type", ""),
                metadata={
                    "certificate_uuid": str(instance.uuid),
                    "certificate_short_code": instance.short_code,
                    "event_uuid": str(instance.registration.event.uuid) if instance.registration else None,
                    "course_uuid": str(instance.course_enrollment.course.uuid) if instance.course_enrollment else None,
                },
            )

            # Update user's total CPD credits balance
            user_obj.total_cpd_credits = new_balance
            user_obj.save(update_fields=["total_cpd_credits", "updated_at"])

            logger.info(f"Certificate {instance.uuid}: Awarded {credits} CPD credits to {user.email}")

    except Exception as e:
        logger.error(f"Certificate {instance.uuid}: Failed to award CPD credits: {e}")
