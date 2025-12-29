"""
Promo Code validation and application service.
"""

from decimal import Decimal
from typing import Optional

from django.db.models import Q
from django.utils import timezone

from .models import PromoCode, PromoCodeUsage


class PromoCodeError(Exception):
    """Base exception for promo code errors."""
    pass


class PromoCodeNotFoundError(PromoCodeError):
    """Code doesn't exist."""
    pass


class PromoCodeInactiveError(PromoCodeError):
    """Code is not active."""
    pass


class PromoCodeExpiredError(PromoCodeError):
    """Code has expired."""
    pass


class PromoCodeNotYetValidError(PromoCodeError):
    """Code is not yet valid."""
    pass


class PromoCodeExhaustedError(PromoCodeError):
    """Code has reached max uses."""
    pass


class PromoCodeUserLimitError(PromoCodeError):
    """User has reached their limit for this code."""
    pass


class PromoCodeNotApplicableError(PromoCodeError):
    """Code doesn't apply to this event."""
    pass


class PromoCodeMinimumNotMetError(PromoCodeError):
    """Order doesn't meet minimum amount."""
    pass


class PromoCodeFirstTimeOnlyError(PromoCodeError):
    """Code is for first-time buyers only."""
    pass


class PromoCodeService:
    """
    Service for validating and applying promo codes.
    """

    @staticmethod
    def find_code(code: str, event) -> Optional[PromoCode]:
        """
        Find a promo code that applies to the given event.

        Args:
            code: The promo code string
            event: The Event instance

        Returns:
            PromoCode instance or None
        """
        code_upper = code.upper().strip()

        # Find codes owned by the event owner or organization
        owner_filter = Q(owner=event.owner)
        if event.organization:
            owner_filter |= Q(organization=event.organization)

        promo = PromoCode.objects.filter(
            owner_filter,
            code__iexact=code_upper
        ).first()

        return promo

    @staticmethod
    def validate_code(
        promo_code: PromoCode,
        event,
        email: str,
        user=None
    ) -> None:
        """
        Validate a promo code for use.

        Args:
            promo_code: The PromoCode instance
            event: The Event instance
            email: Email of the registrant
            user: User instance (if logged in)

        Raises:
            PromoCodeError subclass on validation failure
        """
        now = timezone.now()

        # Check if active
        if not promo_code.is_active:
            raise PromoCodeInactiveError("This promo code is no longer active.")

        # Check date validity
        if promo_code.valid_from and now < promo_code.valid_from:
            raise PromoCodeNotYetValidError(
                f"This code is not valid until {promo_code.valid_from.strftime('%B %d, %Y')}."
            )

        if promo_code.valid_until and now > promo_code.valid_until:
            raise PromoCodeExpiredError("This promo code has expired.")

        # Check max uses
        if promo_code.max_uses and promo_code.current_uses >= promo_code.max_uses:
            raise PromoCodeExhaustedError("This promo code has reached its usage limit.")

        # Check per-user limit
        email_lower = email.lower()
        user_usage_count = PromoCodeUsage.objects.filter(
            promo_code=promo_code,
            user_email__iexact=email_lower
        ).count()

        if user_usage_count >= promo_code.max_uses_per_user:
            raise PromoCodeUserLimitError(
                f"You have already used this code {user_usage_count} time(s)."
            )

        # Check event applicability
        if promo_code.events.exists():
            if not promo_code.events.filter(pk=event.pk).exists():
                raise PromoCodeNotApplicableError(
                    "This promo code cannot be used for this event."
                )

        # Check minimum order amount
        if event.price < promo_code.minimum_order_amount:
            raise PromoCodeMinimumNotMetError(
                f"This code requires a minimum order of ${promo_code.minimum_order_amount}."
            )

        # Check first-time only
        if promo_code.first_time_only:
            from registrations.models import Registration

            # Check if user has any past registrations
            past_registrations = Registration.objects.filter(
                email__iexact=email_lower,
                status=Registration.Status.CONFIRMED,
                deleted_at__isnull=True
            ).exclude(event=event).exists()

            if past_registrations:
                raise PromoCodeFirstTimeOnlyError(
                    "This code is only valid for first-time attendees."
                )

    @staticmethod
    def apply_code(
        promo_code: PromoCode,
        registration,
        original_price: Decimal
    ) -> PromoCodeUsage:
        """
        Apply a promo code to a registration.

        Args:
            promo_code: Validated PromoCode instance
            registration: Registration instance
            original_price: Original ticket price

        Returns:
            PromoCodeUsage instance
        """
        discount_amount = promo_code.calculate_discount(original_price)
        final_price = max(Decimal('0.00'), original_price - discount_amount)

        # Create usage record
        usage = PromoCodeUsage.objects.create(
            promo_code=promo_code,
            registration=registration,
            user_email=registration.email,
            user=registration.user,
            original_price=original_price,
            discount_amount=discount_amount,
            final_price=final_price
        )

        # Increment usage count
        promo_code.increment_usage()

        # Update registration's amount
        registration.amount_paid = final_price
        registration.save(update_fields=['amount_paid', 'updated_at'])

        return usage

    @classmethod
    def validate_and_preview(
        cls,
        code: str,
        event,
        email: str,
        user=None
    ) -> dict:
        """
        Validate a code and return discount preview.

        Args:
            code: The promo code string
            event: The Event instance
            email: Email of the registrant
            user: User instance (if logged in)

        Returns:
            Dict with discount details

        Raises:
            PromoCodeError subclass on validation failure
        """
        promo_code = cls.find_code(code, event)

        if not promo_code:
            raise PromoCodeNotFoundError("Invalid promo code.")

        # Validate
        cls.validate_code(promo_code, event, email, user)

        # Calculate discount
        original_price = event.price
        discount_amount = promo_code.calculate_discount(original_price)
        final_price = max(Decimal('0.00'), original_price - discount_amount)

        return {
            'valid': True,
            'code': promo_code.code,
            'discount_type': promo_code.discount_type,
            'discount_value': str(promo_code.discount_value),
            'discount_display': promo_code.get_discount_display(),
            'original_price': str(original_price),
            'discount_amount': str(discount_amount),
            'final_price': str(final_price),
            'promo_code_uuid': str(promo_code.uuid),
        }


# Singleton instance
promo_code_service = PromoCodeService()
