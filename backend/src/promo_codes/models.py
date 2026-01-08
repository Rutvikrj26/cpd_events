"""
Promo Codes app models - PromoCode, PromoCodeUsage.
"""

from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone

from common.models import BaseModel


class PromoCode(BaseModel):
    """
    A promo/discount code for events.

    Supports:
    - Percentage discounts (10% off)
    - Fixed amount discounts ($5 off)
    - Usage limits (max 100 uses)
    - Per-user limits (1 use per person)
    - Date-based validity
    - Event-specific or global codes
    """

    class DiscountType(models.TextChoices):
        PERCENTAGE = 'percentage', 'Percentage'
        FIXED_AMOUNT = 'fixed_amount', 'Fixed Amount'

    # =========================================
    # Ownership
    # =========================================
    owner = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='promo_codes',
        help_text="Organizer who created this code"
    )
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='promo_codes',
        help_text="Organization that owns this code"
    )

    # =========================================
    # Code Details
    # =========================================
    code = models.CharField(
        max_length=50,
        db_index=True,
        help_text="The promo code string (case-insensitive)"
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Internal description/notes"
    )

    # =========================================
    # Discount Configuration
    # =========================================
    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.PERCENTAGE
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Discount amount (percentage 0-100 or fixed amount in currency)"
    )

    # For percentage discounts, optionally cap the discount
    max_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Max discount amount for percentage codes (e.g., '20% off up to $50')"
    )

    # =========================================
    # Validity
    # =========================================
    is_active = models.BooleanField(default=True, help_text="Whether code can be used")
    valid_from = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When code becomes valid (null = immediately)"
    )
    valid_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When code expires (null = never)"
    )

    # =========================================
    # Usage Limits
    # =========================================
    max_uses = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum total uses (null = unlimited)"
    )
    max_uses_per_user = models.PositiveIntegerField(
        default=1,
        help_text="Max uses per user/email"
    )
    current_uses = models.PositiveIntegerField(
        default=0,
        help_text="Current usage count (denormalized)"
    )

    # =========================================
    # Applicability
    # =========================================
    # If events is empty, code applies to ALL events by this organizer
    events = models.ManyToManyField(
        'events.Event',
        blank=True,
        related_name='promo_codes',
        help_text="Specific events this code applies to (empty = all organizer events)"
    )

    # Minimum order value
    minimum_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Minimum ticket price to use this code"
    )

    # =========================================
    # First-time buyer only
    # =========================================
    first_time_only = models.BooleanField(
        default=False,
        help_text="Only for users who haven't registered for any event before"
    )

    class Meta:
        db_table = 'promo_codes'
        ordering = ['-created_at']
        # Code must be unique per owner (organizer can't have duplicate codes)
        unique_together = [['owner', 'code']]
        indexes = [
            models.Index(fields=['owner', 'is_active']),
            models.Index(fields=['code']),
        ]
        verbose_name = 'Promo Code'
        verbose_name_plural = 'Promo Codes'

    def __str__(self):
        return f"{self.code} ({self.get_discount_display()})"

    # =========================================
    # Properties
    # =========================================
    @property
    def is_valid(self):
        """Check if code is currently valid (not expired, active, has uses)."""
        if not self.is_active:
            return False

        now = timezone.now()

        if self.valid_from and now < self.valid_from:
            return False

        if self.valid_until and now > self.valid_until:
            return False

        if self.max_uses and self.current_uses >= self.max_uses:
            return False

        return True

    @property
    def is_expired(self):
        """Check if code has expired."""
        if self.valid_until and timezone.now() > self.valid_until:
            return True
        return False

    @property
    def uses_remaining(self):
        """Number of uses remaining."""
        if self.max_uses is None:
            return None
        return max(0, self.max_uses - self.current_uses)

    def get_discount_display(self):
        """Human-readable discount display."""
        if self.discount_type == self.DiscountType.PERCENTAGE:
            s = f"{self.discount_value}% off"
            if self.max_discount_amount:
                s += f" (max ${self.max_discount_amount})"
            return s
        else:
            return f"${self.discount_value} off"

    # =========================================
    # Methods
    # =========================================
    def calculate_discount(self, original_price: Decimal) -> Decimal:
        """
        Calculate the discount amount for a given price.

        Args:
            original_price: The original ticket price

        Returns:
            The discount amount (not the final price)
        """
        if self.discount_type == self.DiscountType.PERCENTAGE:
            discount = (original_price * self.discount_value) / Decimal('100')
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
        else:
            discount = min(self.discount_value, original_price)

        return discount.quantize(Decimal('0.01'))

    def increment_usage(self):
        """Increment usage count."""
        from django.db.models import F
        self.current_uses = F('current_uses') + 1
        self.save(update_fields=['current_uses', 'updated_at'])


class PromoCodeUsage(BaseModel):
    """
    Record of promo code usage.

    Tracks which registration used which code for audit and limit enforcement.
    """

    promo_code = models.ForeignKey(
        PromoCode,
        on_delete=models.CASCADE,
        related_name='usages'
    )
    registration = models.ForeignKey(
        'registrations.Registration',
        on_delete=models.CASCADE,
        related_name='promo_code_usages'
    )

    # Denormalized for easy querying
    user_email = models.EmailField(
        db_index=True,
        help_text="Email used for registration"
    )
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='promo_code_usages',
        help_text="User account if registered"
    )

    # Record the discount applied
    original_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    final_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'promo_code_usages'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['promo_code', 'user_email']),
            models.Index(fields=['registration']),
        ]
        verbose_name = 'Promo Code Usage'
        verbose_name_plural = 'Promo Code Usages'

    def __str__(self):
        return f"{self.promo_code.code} used by {self.user_email}"
