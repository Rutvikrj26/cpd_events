"""
Billing models for subscription management.

Models:
- Subscription: User subscription to a plan
- Invoice: Billing history records
- PaymentMethod: Stored payment methods
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator

from common.models import BaseModel


class Subscription(BaseModel):
    """
    User subscription to a plan.
    
    Tracks subscription status, billing cycles, and usage limits.
    """
    
    class Plan(models.TextChoices):
        FREE = 'free', 'Free'
        STARTER = 'starter', 'Starter'
        PROFESSIONAL = 'professional', 'Professional'
        ENTERPRISE = 'enterprise', 'Enterprise'
    
    class Status(models.TextChoices):
        TRIALING = 'trialing', 'Trialing'
        ACTIVE = 'active', 'Active'
        PAST_DUE = 'past_due', 'Past Due'
        CANCELED = 'canceled', 'Canceled'
        UNPAID = 'unpaid', 'Unpaid'
        INCOMPLETE = 'incomplete', 'Incomplete'
        PAUSED = 'paused', 'Paused'
    
    # Relationships
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    
    # Plan details
    plan = models.CharField(
        max_length=20,
        choices=Plan.choices,
        default=Plan.FREE
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    
    # Stripe integration
    stripe_subscription_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        unique=True,
        db_index=True
    )
    stripe_customer_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True
    )
    
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
    certificates_issued_this_period = models.PositiveIntegerField(default=0)
    
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
    
    # Plan limits configuration
    PLAN_LIMITS = {
        Plan.FREE: {
            'events_per_month': 2,
            'certificates_per_month': 100,
            'max_attendees_per_event': 50,
        },
        Plan.STARTER: {
            'events_per_month': 10,
            'certificates_per_month': 500,
            'max_attendees_per_event': 200,
        },
        Plan.PROFESSIONAL: {
            'events_per_month': 50,
            'certificates_per_month': 5000,
            'max_attendees_per_event': 1000,
        },
        Plan.ENTERPRISE: {
            'events_per_month': None,  # Unlimited
            'certificates_per_month': None,  # Unlimited
            'max_attendees_per_event': None,  # Unlimited
        },
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
        """Get limits for current plan."""
        return self.PLAN_LIMITS.get(self.plan, self.PLAN_LIMITS[self.Plan.FREE])
    
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
    
    def increment_events(self, count=1):
        """Increment event counter."""
        self.events_created_this_period += count
        self.save(update_fields=['events_created_this_period', 'updated_at'])
    
    def increment_certificates(self, count=1):
        """Increment certificate counter."""
        self.certificates_issued_this_period += count
        self.save(update_fields=['certificates_issued_this_period', 'updated_at'])
    
    def reset_usage(self):
        """Reset usage counters for new period."""
        self.events_created_this_period = 0
        self.certificates_issued_this_period = 0
        self.save(update_fields=[
            'events_created_this_period',
            'certificates_issued_this_period',
            'updated_at'
        ])
    
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
            plan = cls.Plan.FREE
        
        subscription, created = cls.objects.get_or_create(
            user=user,
            defaults={
                'plan': plan,
                'status': cls.Status.ACTIVE,
                'current_period_start': timezone.now(),
            }
        )
        return subscription


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
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices'
    )
    
    # Stripe data
    stripe_invoice_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True
    )
    
    # Amount
    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default='usd')
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    
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
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_methods'
    )
    
    # Stripe data
    stripe_payment_method_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True
    )
    
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
        return (self.card_exp_year < now.year or 
                (self.card_exp_year == now.year and self.card_exp_month < now.month))
    
    def set_as_default(self):
        """Set this payment method as default."""
        # Remove default from other methods
        PaymentMethod.objects.filter(
            user=self.user,
            is_default=True
        ).exclude(id=self.id).update(is_default=False)
        
        self.is_default = True
        self.save(update_fields=['is_default', 'updated_at'])
