"""
Billing models for subscription management.

Models:
- Subscription: User subscription to a plan
- Invoice: Billing history records
- PaymentMethod: Stored payment methods
"""

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from common.config import IndividualPlanLimits
from common.models import BaseModel


class Subscription(BaseModel):
    """
    User subscription to a plan.

    Tracks subscription status, billing cycles, and usage limits.
    """

    class Plan(models.TextChoices):
        ATTENDEE = 'attendee', 'Attendee'
        ORGANIZER = 'organizer', 'Organizer'
        LMS = 'lms', 'LMS'
        ORGANIZATION = 'organization', 'Organization'

    class Status(models.TextChoices):
        TRIALING = 'trialing', 'Trialing'
        ACTIVE = 'active', 'Active'
        PAST_DUE = 'past_due', 'Past Due'
        CANCELED = 'canceled', 'Canceled'
        UNPAID = 'unpaid', 'Unpaid'
        INCOMPLETE = 'incomplete', 'Incomplete'
        PAUSED = 'paused', 'Paused'

    class BillingInterval(models.TextChoices):
        MONTH = 'month', 'Monthly'
        YEAR = 'year', 'Annual'

    # Relationships
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscription')

    # Plan details
    plan = models.CharField(max_length=20, choices=Plan.choices, default=Plan.ATTENDEE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    billing_interval = models.CharField(
        max_length=10,
        choices=BillingInterval.choices,
        default=BillingInterval.MONTH,
    )

    pending_plan = models.CharField(
        max_length=20,
        choices=Plan.choices,
        blank=True,
        null=True,
        help_text="Scheduled plan change at period end, if any",
    )
    pending_billing_interval = models.CharField(
        max_length=10,
        choices=BillingInterval.choices,
        blank=True,
        null=True,
        help_text="Scheduled billing interval change at period end, if any",
    )
    pending_change_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When a pending plan change should take effect",
    )

    # Stripe integration
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True, unique=True, db_index=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)

    # Billing period
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)

    # Trial
    trial_ends_at = models.DateTimeField(null=True, blank=True)

    # Cancellation
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)

    # Usage tracking for current period
    events_created_this_period = models.PositiveIntegerField(default=0)
    courses_created_this_period = models.PositiveIntegerField(default=0)
    certificates_issued_this_period = models.PositiveIntegerField(default=0)
    last_usage_reset_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'subscriptions'
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'
        indexes = [
            models.Index(fields=['plan']),
            models.Index(fields=['status']),
            models.Index(fields=['current_period_end']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.plan} ({self.status})"

    # Plan limits configuration (imported from common.config.billing)
    PLAN_LIMITS = {
        Plan.ATTENDEE: IndividualPlanLimits.ATTENDEE,
        Plan.ORGANIZER: IndividualPlanLimits.ORGANIZER,
        Plan.LMS: IndividualPlanLimits.LMS,
        Plan.ORGANIZATION: IndividualPlanLimits.ORGANIZATION,
    }

    @property
    def is_active(self):
        """Check if subscription is in active status."""
        return self.status in [self.Status.ACTIVE, self.Status.TRIALING]

    @property
    def is_trialing(self):
        """Check if currently in trial period."""
        if self.status != self.Status.TRIALING:
            return False
        if not self.trial_ends_at:
            return False
        return timezone.now() < self.trial_ends_at

    @property
    def limits(self):
        """
        Get limits for current plan.
        Reads from StripeProduct if available (database-driven),
        otherwise falls back to PLAN_LIMITS (code fallback).
        """
        # Try to get limits from StripeProduct (database - source of truth)
        try:
            product = StripeProduct.objects.get(plan=self.plan, is_active=True)
            return {
                'events_per_month': product.events_per_month,
                'courses_per_month': getattr(product, 'courses_per_month', None),
                'certificates_per_month': product.certificates_per_month,
                'max_attendees_per_event': product.max_attendees_per_event,
            }
        except StripeProduct.DoesNotExist:
            # Fallback to hardcoded limits (backward compatibility)
            return self.PLAN_LIMITS.get(self.plan, self.PLAN_LIMITS[self.Plan.ATTENDEE])

    def check_event_limit(self):
        """Check if user can create more events this period."""
        limit = self.limits['events_per_month']
        if limit is None:
            return True
        return self.events_created_this_period < limit

    def check_certificate_limit(self, count=1):
        """Check if user can issue more certificates this period."""
        limit = self.limits['certificates_per_month']
        if limit is None:
            return True
        return (self.certificates_issued_this_period + count) <= limit

    def check_course_limit(self):
        """Check if user can create more courses this period."""
        limit = self.limits.get('courses_per_month')
        if limit is None:
            return True
        return self.courses_created_this_period < limit

    def increment_events(self, count=1):
        """Increment event counter."""
        self.events_created_this_period += count
        self.save(update_fields=['events_created_this_period', 'updated_at'])

    def increment_certificates(self, count=1):
        """Increment certificate counter."""
        self.certificates_issued_this_period += count
        self.save(update_fields=['certificates_issued_this_period', 'updated_at'])

    def increment_courses(self, count=1):
        """Increment course counter."""
        self.courses_created_this_period += count
        self.save(update_fields=['courses_created_this_period', 'updated_at'])

    def reset_usage(self):
        """Reset usage counters for new period."""
        self.events_created_this_period = 0
        self.courses_created_this_period = 0
        self.certificates_issued_this_period = 0
        self.last_usage_reset_at = timezone.now()
        self.save(
            update_fields=[
                'events_created_this_period',
                'courses_created_this_period',
                'certificates_issued_this_period',
                'last_usage_reset_at',
                'updated_at',
            ]
        )

    def upgrade_plan(self, new_plan):
        """Upgrade to a higher plan."""
        self.plan = new_plan
        self.save(update_fields=['plan', 'updated_at'])

    def downgrade_plan(self, new_plan):
        """Downgrade to a lower plan (at period end)."""
        self.plan = new_plan
        self.save(update_fields=['plan', 'updated_at'])

    def cancel(self, reason='', immediate=False):
        """Cancel subscription."""
        self.cancellation_reason = reason
        self.canceled_at = timezone.now()

        if immediate:
            self.status = self.Status.CANCELED
        else:
            self.cancel_at_period_end = True

        self.save()

    def reactivate(self):
        """Reactivate a canceled subscription."""
        self.cancel_at_period_end = False
        self.canceled_at = None
        self.cancellation_reason = ''
        self.status = self.Status.ACTIVE
        self.save()

    @classmethod
    def create_for_user(cls, user, plan=None):
        """Create a new subscription for a user."""
        if plan is None:
            plan = cls.Plan.ATTENDEE

        subscription, created = cls.objects.get_or_create(
            user=user,
            defaults={
                'plan': plan,
                'status': cls.Status.ACTIVE,
                'billing_interval': cls.BillingInterval.MONTH,
                'current_period_start': timezone.now(),
            },
        )
        return subscription

    @property
    def is_trial_expired(self):
        """Check if trial period has expired."""
        if self.status != self.Status.TRIALING:
            return False
        if not self.trial_ends_at:
            return False
        return timezone.now() >= self.trial_ends_at

    @property
    def days_until_trial_ends(self):
        """Get days remaining in trial. Returns None if not trialing."""
        if not self.is_trialing:
            return None
        if not self.trial_ends_at:
            return None
        delta = self.trial_ends_at - timezone.now()
        return max(0, delta.days)

    def get_grace_period_days(self):
        """Get grace period days for this subscription's plan."""
        try:
            product = StripeProduct.objects.filter(plan=self.plan, is_active=True).first()
            return product.grace_period_days if product else 14
        except Exception:
            return 14  # Safe fallback

    @property
    def is_in_grace_period(self):
        """
        Check if subscription is in grace period after trial.
        Grace period = trial_ends_at + grace_period_days
        During grace period: can't create events, but can still access dashboard
        After grace period: complete access block
        """
        if self.status not in [self.Status.TRIALING, self.Status.PAST_DUE]:
            return False
        if not self.trial_ends_at:
            return False

        grace_end = self.trial_ends_at + timedelta(days=self.get_grace_period_days())
        now = timezone.now()

        return self.trial_ends_at <= now < grace_end

    @property
    def is_access_blocked(self):
        """
        Check if access should be completely blocked.
        This happens after trial + grace period with no payment.
        """
        # Active/paid subscriptions are never blocked
        if self.status == self.Status.ACTIVE and not self.is_trial_expired:
            return False
        if self.stripe_subscription_id:
            # Has a Stripe subscription - let Stripe status determine access
            return self.status in [self.Status.CANCELED, self.Status.UNPAID]

        # For trials without payment
        if not self.trial_ends_at:
            return False

        grace_end = self.trial_ends_at + timedelta(days=self.get_grace_period_days())

        return timezone.now() >= grace_end

    @property
    def can_create_events(self):
        """
        Check if user can create new events.
        Returns False if:
        - Trial expired (even during grace period)
        - Access blocked
        - Event limit reached (for free plans)
        """
        # Access completely blocked
        if self.is_access_blocked:
            return False

        # Trial expired - block event creation but allow dashboard access
        if self.is_trial_expired:
            return False

        # Check event limits for active subscriptions
        if not self.check_event_limit():
            return False

        return True

    @property
    def can_create_courses(self):
        """
        Check if user can create new courses.
        Returns False if:
        - Trial expired (even during grace period)
        - Access blocked
        - Course limit reached (for free plans)
        """
        # Access completely blocked
        if self.is_access_blocked:
            return False

        # Trial expired - block course creation but allow dashboard access
        if self.is_trial_expired:
            return False

        if not self.check_course_limit():
            return False

        return True

    @property
    def subscription_status_display(self):
        """Get user-friendly status for frontend display."""
        if self.is_access_blocked:
            return 'blocked'
        if self.is_in_grace_period:
            return 'grace_period'
        if self.is_trial_expired:
            return 'trial_expired'
        if self.is_trialing:
            return 'trialing'
        return self.status


class Invoice(BaseModel):
    """
    Invoice record from Stripe.

    Tracks billing history and payment status.
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        OPEN = 'open', 'Open'
        PAID = 'paid', 'Paid'
        VOID = 'void', 'Void'
        UNCOLLECTIBLE = 'uncollectible', 'Uncollectible'

    # Relationships
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='invoices')
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')

    # Stripe data
    stripe_invoice_id = models.CharField(max_length=255, unique=True, db_index=True)

    # Amount
    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default='usd')

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    # URLs
    invoice_pdf_url = models.URLField(max_length=500, blank=True)
    hosted_invoice_url = models.URLField(max_length=500, blank=True)

    # Dates
    period_start = models.DateTimeField(null=True, blank=True)
    period_end = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'invoices'
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"Invoice {self.stripe_invoice_id} - {self.amount_display}"

    @property
    def amount_display(self):
        """Format amount for display."""
        if self.amount_cents is None:
            return f"$0.00 {self.currency.upper()}"
        return f"${self.amount_cents / 100:.2f} {self.currency.upper()}"

    @property
    def is_paid(self):
        """Check if invoice is paid."""
        return self.status == self.Status.PAID


class PaymentMethod(BaseModel):
    """
    Stored payment method for a user.

    Tracks card details and default status.
    """

    # Relationships
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payment_methods')

    # Stripe data
    stripe_payment_method_id = models.CharField(max_length=255, unique=True, db_index=True)

    # Card details (stored from Stripe, not raw card data)
    card_brand = models.CharField(max_length=50, blank=True)
    card_last4 = models.CharField(max_length=4, blank=True)
    card_exp_month = models.PositiveSmallIntegerField(null=True, blank=True)
    card_exp_year = models.PositiveSmallIntegerField(null=True, blank=True)

    # Default flag
    is_default = models.BooleanField(default=False)

    # Billing details
    billing_name = models.CharField(max_length=255, blank=True)
    billing_email = models.EmailField(blank=True)

    class Meta:
        db_table = 'payment_methods'
        verbose_name = 'Payment Method'
        verbose_name_plural = 'Payment Methods'
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f"{self.card_brand} ****{self.card_last4}"

    @property
    def is_expired(self):
        """Check if card is expired."""
        if not self.card_exp_month or not self.card_exp_year:
            return False
        now = timezone.now()
        # Card expires at end of month
        return self.card_exp_year < now.year or (self.card_exp_year == now.year and self.card_exp_month < now.month)

    def set_as_default(self):
        """Set this payment method as default."""
        # Remove default from other methods
        PaymentMethod.objects.filter(user=self.user, is_default=True).exclude(id=self.id).update(is_default=False)

        self.is_default = True
        self.save(update_fields=['is_default', 'updated_at'])


class StripeProduct(BaseModel):
    """
    Represents a Stripe Product (e.g., "CPD Events - Organizer").

    Manages pricing products with auto-sync to Stripe.
    This allows managing all pricing from Django Admin instead of manually in Stripe Dashboard.
    """

    name = models.CharField(max_length=255, help_text="Product name (shown to customers)")
    description = models.TextField(blank=True, help_text="Product description")
    stripe_product_id = models.CharField(
        max_length=255, unique=True, blank=True, null=True, help_text="Stripe product ID (prod_...)"
    )
    is_active = models.BooleanField(default=True, help_text="Whether product is active")

    # Plan association
    plan = models.CharField(
        max_length=50,
        choices=Subscription.Plan.choices,
        unique=True,
        help_text="Which subscription plan this product represents",
    )

    # Tax Codes (Hardcoded per plan)
    PLAN_TAX_CODES = {
        'organizer': 'txcd_10103000',  # SaaS/Digital Service
        'lms': 'txcd_10103000',  # SaaS/Digital Service
        'organization': 'txcd_10103001',  # SaaS/Digital Service (Organization)
    }

    # Trial period configuration
    trial_period_days = models.PositiveIntegerField(default=30, help_text="Trial period in days")

    grace_period_days = models.PositiveIntegerField(
        default=14, help_text="Grace period in days (after trial/subscription ends)"
    )

    # Contact Sales flag - hides pricing and shows "Contact Sales" button
    show_contact_sales = models.BooleanField(
        default=False, help_text="If true, hides pricing and shows 'Contact Sales' button instead"
    )

    # Feature limits (null = unlimited, syncs with PLAN_LIMITS)
    events_per_month = models.PositiveIntegerField(null=True, blank=True, help_text="Max events per month (null = unlimited)")
    certificates_per_month = models.PositiveIntegerField(
        null=True, blank=True, help_text="Max certificates per month (null = unlimited)"
    )
    courses_per_month = models.PositiveIntegerField(null=True, blank=True, help_text="Max courses per month (null = unlimited)")
    max_attendees_per_event = models.PositiveIntegerField(
        null=True, blank=True, help_text="Max attendees per event (null = unlimited)"
    )

    # Seat configuration (for Organization plans)
    included_seats = models.PositiveIntegerField(default=0, help_text="Number of included seats (for organization plans)")
    seat_price_cents = models.PositiveIntegerField(default=0, help_text="Price per additional seat in cents")

    class Meta:
        db_table = 'stripe_products'
        ordering = ['plan']
        verbose_name = 'Stripe Product'
        verbose_name_plural = 'Stripe Products'

    def save(self, *args, **kwargs):
        previous_trial_days = None
        if self.pk:
            previous_trial_days = StripeProduct.objects.filter(pk=self.pk).values_list('trial_period_days', flat=True).first()

        super().save(*args, **kwargs)

        if previous_trial_days is not None and self.trial_period_days != previous_trial_days:
            try:
                from .services import stripe_service

                stripe_service.sync_trial_period_days(
                    self.plan,
                    self.trial_period_days,
                    previous_trial_days,
                )
            except Exception as exc:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Failed to sync trial days for plan {self.plan}: {exc}")

    def __str__(self):
        return f"{self.name} ({self.get_plan_display()})"

    def sync_to_stripe(self):
        """Create or update product in Stripe."""
        from .services import stripe_service

        if not stripe_service.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        try:
            params = {
                'name': self.name,
                'description': self.description,
                'active': self.is_active,
            }

            # Add tax code from constants
            tax_code = self.PLAN_TAX_CODES.get(self.plan)
            if tax_code:
                params['tax_code'] = tax_code

            if self.stripe_product_id:
                # Update existing product
                product = stripe_service.stripe.Product.modify(self.stripe_product_id, **params)
            else:
                # Create new product
                product = stripe_service.stripe.Product.create(**params)
                self.stripe_product_id = product.id
                self.save(update_fields=['stripe_product_id', 'updated_at'])

            return {'success': True, 'product': product}

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to sync product to Stripe: {e}")
            return {'success': False, 'error': str(e)}

    def get_trial_days(self):
        """Get trial period days for this product."""
        return self.trial_period_days

    def get_feature_limits(self):
        """Get feature limits for this product."""
        return {
            'events_per_month': self.events_per_month,
            'certificates_per_month': self.certificates_per_month,
            'courses_per_month': self.courses_per_month,
            'max_attendees_per_event': self.max_attendees_per_event,
        }

    def get_features_list(self):
        """
        Generate a human-readable features list for this product.
        Returns a list of strings describing the features.
        """
        features = []

        # Events per month
        if self.events_per_month is None:
            features.append("Unlimited events")
        elif self.events_per_month > 0:
            features.append(f"{self.events_per_month} events per month")

        # Courses per month
        if self.courses_per_month is None:
            features.append("Unlimited courses")
        elif self.courses_per_month > 0:
            features.append(f"{self.courses_per_month} courses per month")

        # Certificates per month
        if self.certificates_per_month is None:
            features.append("Unlimited certificates")
        elif self.certificates_per_month > 0:
            features.append(f"{self.certificates_per_month:,} certificates/month")

        # Max attendees per event
        if self.max_attendees_per_event is None:
            features.append("Unlimited attendees per event")
        elif self.max_attendees_per_event > 0:
            features.append(f"{self.max_attendees_per_event:,} attendees per event")

        # Add plan-specific features
        if self.plan == 'organizer':
            features.extend(
                [
                    "Zoom integration",
                    "Custom certificate templates",
                    "Priority email support",
                ]
            )
        elif self.plan == 'lms':
            features.extend(
                [
                    "Self-paced course builder",
                    "Course certificates",
                    "Learner progress tracking",
                ]
            )
        elif self.plan == 'organization':
            features.extend(
                [
                    "Multi-user team access",
                    "White-label options",
                    "API access",
                    "Priority support",
                    "Team collaboration",
                    "Shared templates",
                    "Dedicated account manager",
                ]
            )

        return features


class StripePrice(BaseModel):
    """
    Represents a Stripe Price (e.g., "$99/month" for Organizer plan).

    Each product can have multiple prices (monthly, annual).
    Manages pricing with auto-sync to Stripe.
    """

    class BillingInterval(models.TextChoices):
        MONTH = 'month', 'Monthly'
        YEAR = 'year', 'Annual'

    product = models.ForeignKey(StripeProduct, on_delete=models.CASCADE, related_name='prices')

    # Pricing details
    amount_cents = models.PositiveIntegerField(help_text="Price in cents (e.g., 9900 = $99.00)")
    currency = models.CharField(max_length=3, default='usd')
    billing_interval = models.CharField(max_length=10, choices=BillingInterval.choices, default=BillingInterval.MONTH)

    # Stripe sync
    stripe_price_id = models.CharField(
        max_length=255, unique=True, blank=True, null=True, help_text="Stripe price ID (price_...)"
    )
    is_active = models.BooleanField(default=True, help_text="Whether price is available for new subscriptions")

    class Meta:
        db_table = 'stripe_prices'
        ordering = ['product', 'billing_interval']
        unique_together = [['product', 'billing_interval']]
        verbose_name = 'Stripe Price'
        verbose_name_plural = 'Stripe Prices'

    def __str__(self):
        return f"${self.amount_display}/{self.billing_interval} - {self.product.name}"

    @property
    def amount_display(self):
        """Format amount as dollars."""
        if self.amount_cents is None:
            return "0.00"
        return f"{self.amount_cents / 100:.2f}"

    def save(self, *args, **kwargs):
        if self.pk:
            previous = (
                StripePrice.objects.filter(pk=self.pk)
                .values(
                    'amount_cents',
                    'currency',
                    'billing_interval',
                )
                .first()
            )
            if previous:
                self._previous_amount_cents = previous['amount_cents']
                self._previous_currency = previous['currency']
                self._previous_billing_interval = previous['billing_interval']
        super().save(*args, **kwargs)

    def sync_to_stripe(self):
        """Create or update price in Stripe."""
        from django.utils import timezone

        from .services import stripe_service

        if not stripe_service.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        if not self.product.stripe_product_id:
            # Product must exist in Stripe first
            result = self.product.sync_to_stripe()
            if not result['success']:
                return result

        try:
            previous_amount = getattr(self, '_previous_amount_cents', None)
            previous_currency = getattr(self, '_previous_currency', None)
            previous_interval = getattr(self, '_previous_billing_interval', None)
            price_changed = any(
                prev is not None and prev != current
                for prev, current in [
                    (previous_amount, self.amount_cents),
                    (previous_currency, self.currency),
                    (previous_interval, self.billing_interval),
                ]
            )

            if self.stripe_price_id and price_changed:
                # Stripe doesn't allow changing price amounts; create a new price and deactivate the old one.
                try:
                    stripe_service.stripe.Price.modify(self.stripe_price_id, active=False)
                except Exception:
                    pass

                price = stripe_service.stripe.Price.create(
                    product=self.product.stripe_product_id,
                    unit_amount=self.amount_cents,
                    currency=self.currency,
                    recurring={'interval': self.billing_interval},
                    tax_behavior='exclusive',
                    active=self.is_active,
                )
                StripePrice.objects.filter(pk=self.pk).update(
                    stripe_price_id=price.id,
                    updated_at=timezone.now(),
                )
                self.stripe_price_id = price.id
            elif self.stripe_price_id:
                # Update existing price (Stripe only allows updating 'active' status)
                price = stripe_service.stripe.Price.modify(
                    self.stripe_price_id,
                    active=self.is_active,
                )
            else:
                # Create new price
                price = stripe_service.stripe.Price.create(
                    product=self.product.stripe_product_id,
                    unit_amount=self.amount_cents,
                    currency=self.currency,
                    recurring={'interval': self.billing_interval},
                    tax_behavior='exclusive',
                    active=self.is_active,
                )
                self.stripe_price_id = price.id
                self.save(update_fields=['stripe_price_id', 'updated_at'])

            return {'success': True, 'price': price}

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to sync price to Stripe: {e}")
            return {'success': False, 'error': str(e)}


# =============================================================================
# Financial Models (Refunds, Payouts, Transfers)
# =============================================================================


class RefundRecord(BaseModel):
    """
    Record of a processed refund.

    Tracks refunds for registrations or other payments.
    Ensures fees are tracked and transfers are reversed where possible.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCEEDED = 'succeeded', 'Succeeded'
        FAILED = 'failed', 'Failed'
        CANCELED = 'canceled', 'Canceled'

    class Reason(models.TextChoices):
        DUPLICATE = 'duplicate', 'Duplicate'
        FRAUDULENT = 'fraudulent', 'Fraudulent'
        REQUESTED_BY_CUSTOMER = 'requested_by_customer', 'Requested by Customer'
        EXPIRED_UNCAPTURED = 'expired_uncaptured', 'Expired Uncaptured Charge'
        OTHER = 'other', 'Other'

    # Relationships
    registration = models.ForeignKey(
        'registrations.Registration', on_delete=models.SET_NULL, null=True, blank=True, related_name='refunds'
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_refunds'
    )

    # Stripe Reference
    stripe_refund_id = models.CharField(max_length=255, unique=True, db_index=True)
    stripe_payment_intent_id = models.CharField(max_length=255, db_index=True)

    # Financials
    amount_cents = models.PositiveIntegerField(help_text="Amount refunded in cents")
    currency = models.CharField(max_length=3, default='usd')

    # Platform Tracking
    platform_fee_reversed_cents = models.IntegerField(default=0, help_text="Amount of platform fee returned (if any)")

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reason = models.CharField(max_length=50, choices=Reason.choices, default=Reason.REQUESTED_BY_CUSTOMER)
    description = models.TextField(blank=True, help_text="Internal notes or description")

    # Error tracking
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = 'refund_records'
        verbose_name = 'Refund Record'
        verbose_name_plural = 'Refund Records'
        ordering = ['-created_at']

    def __str__(self):
        return f"Refund {self.stripe_refund_id} - {self.amount_display}"

    @property
    def amount_display(self):
        return f"{self.amount_cents / 100:.2f} {self.currency.upper()}"


class PayoutRequest(BaseModel):
    """
    Organizer payout request.

    Used when organizers want to withdraw funds from their Stripe Connect account
    to their external bank account manually (if not on automatic schedule).
    Also tracks automatic payouts synced from Stripe.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        IN_TRANSIT = 'in_transit', 'In Transit'
        PAID = 'paid', 'Paid'
        FAILED = 'failed', 'Failed'
        CANCELED = 'canceled', 'Canceled'

    # The organizer requesting the payout
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payouts')

    # Stripe Connect
    stripe_connect_account_id = models.CharField(max_length=255, db_index=True)
    stripe_payout_id = models.CharField(max_length=255, unique=True, blank=True, null=True, db_index=True)

    # Financials
    amount_cents = models.PositiveIntegerField(help_text="Amount in cents")
    currency = models.CharField(max_length=3, default='usd')

    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    arrival_date = models.DateField(null=True, blank=True, help_text="Expected arrival date")

    # Methods
    destination_bank_last4 = models.CharField(max_length=4, blank=True)

    # Error tracking
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = 'payout_requests'
        verbose_name = 'Payout Request'
        verbose_name_plural = 'Payout Requests'
        ordering = ['-created_at']

    def __str__(self):
        return f"Payout {self.amount_display} to {self.user.email}"

    @property
    def amount_display(self):
        return f"{self.amount_cents / 100:.2f} {self.currency.upper()}"


class TransferRecord(BaseModel):
    """
    Log of funds transferred from Platform to Organizer (Connect Account).

    Usually occurs automatically during payment intent processing (destination charge),
    but good to track explicitly for reconciliation.
    """

    event = models.ForeignKey('events.Event', on_delete=models.SET_NULL, null=True, blank=True, related_name='transfers')
    registration = models.ForeignKey(
        'registrations.Registration', on_delete=models.SET_NULL, null=True, blank=True, related_name='transfers'
    )
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_transfers')

    stripe_transfer_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)

    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default='usd')

    description = models.CharField(max_length=255, blank=True)
    reversed = models.BooleanField(default=False, help_text="If transfer was reversed (e.g. refund)")
    reversed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'transfer_records'
        verbose_name = 'Transfer Record'
        verbose_name_plural = 'Transfer Records'
        ordering = ['-created_at']

    def __str__(self):
        return f"Transfer {self.amount_cents/100:.2f} to {self.recipient.email}"


class DisputeRecord(BaseModel):
    """
    Stripe charge dispute record.
    """

    class Status(models.TextChoices):
        NEEDS_RESPONSE = 'needs_response', 'Needs Response'
        WARNING_NEEDS_RESPONSE = 'warning_needs_response', 'Warning Needs Response'
        UNDER_REVIEW = 'under_review', 'Under Review'
        WON = 'won', 'Won'
        LOST = 'lost', 'Lost'

    registration = models.ForeignKey(
        'registrations.Registration',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='disputes',
    )

    stripe_dispute_id = models.CharField(max_length=255, unique=True, db_index=True)
    stripe_charge_id = models.CharField(max_length=255, blank=True, db_index=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, db_index=True)

    amount_cents = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=3, default='usd')
    reason = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.NEEDS_RESPONSE)
    evidence_due_by = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'dispute_records'
        ordering = ['-created_at']
        verbose_name = 'Dispute Record'
        verbose_name_plural = 'Dispute Records'

    def __str__(self):
        return f"Dispute {self.stripe_dispute_id} ({self.status})"
