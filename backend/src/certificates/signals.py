"""
Signals for the certificates app.

Handles automatic CPD credit awarding when certificates are issued.
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from certificates.models import Certificate

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Certificate)
def award_cpd_credits_on_certificate(sender, instance, created, **kwargs):
    """
    Automatically award CPD credits when a certificate is created.

    This signal handler:
    1. Checks if certificate is newly created and active
    2. Extracts CPD credits from certificate_data
    3. Creates CPDTransaction record
    4. Updates User.total_cpd_credits balance
    5. Logs all actions for audit trail

    Args:
        sender: Certificate model class
        instance: Certificate instance that was saved
        created: True if this is a new certificate
        **kwargs: Additional signal arguments
    """
    # Only process new certificates with active status
    if not created or instance.status != Certificate.Status.ACTIVE:
        return

    # Get the user from either registration or course enrollment
    user = None
    if instance.registration:
        user = instance.registration.user
    elif instance.course_enrollment:
        user = instance.course_enrollment.user

    if not user:
        logger.warning(f"Certificate {instance.uuid}: No user found, skipping CPD award")
        return

    # Extract CPD credits from certificate data
    cpd_credits = instance.certificate_data.get("cpd_credits", 0)

    # Convert to Decimal for precision
    try:
        credits = Decimal(str(cpd_credits))
    except (TypeError, ValueError, ArithmeticError) as e:
        logger.error(f"Certificate {instance.uuid}: Invalid CPD credit value '{cpd_credits}': {e}")
        return

    # Only process if credits > 0
    if credits <= 0:
        logger.info(f"Certificate {instance.uuid}: No CPD credits to award (credits={credits})")
        return

    # Import here to avoid circular dependency
    from accounts.models import CPDTransaction

    # Use database transaction to ensure atomicity
    try:
        with transaction.atomic():
            # Calculate new balance
            new_balance = user.total_cpd_credits + credits

            # Create transaction record
            cpd_transaction = CPDTransaction.objects.create(
                user=user,
                certificate=instance,
                transaction_type=CPDTransaction.TransactionType.EARNED,
                credits=credits,
                balance_after=new_balance,
                notes=f"Earned from certificate {instance.short_code}",
                cpd_type=instance.certificate_data.get("cpd_type", ""),
                metadata={
                    "certificate_uuid": str(instance.uuid),
                    "certificate_short_code": instance.short_code,
                    "event_uuid": str(instance.registration.event.uuid) if instance.registration else None,
                    "course_uuid": str(instance.course_enrollment.course.uuid) if instance.course_enrollment else None,
                },
            )

            # Update user's total CPD credits
            user.total_cpd_credits = new_balance
            user.save(update_fields=["total_cpd_credits", "updated_at"])

            logger.info(
                f"Certificate {instance.uuid}: Awarded {credits} CPD credits to {user.email}. "
                f"New balance: {new_balance}. Transaction: {cpd_transaction.uuid}"
            )

    except Exception as e:
        logger.error(f"Certificate {instance.uuid}: Failed to award CPD credits to {user.email}: {e}", exc_info=True)
        # Don't re-raise - certificate issuance should succeed even if CPD award fails
        # The transaction will be rolled back but certificate remains saved
