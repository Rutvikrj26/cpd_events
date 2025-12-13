# Billing App: Subscriptions & Payments

## Overview

The `billing` app handles:
- Subscription management
- Payment processing (via Stripe)
- Invoice tracking
- Usage-based billing features

---

## Models

### Subscription

User subscription for organizer features.

```python
# billing/models.py

from django.db import models
from django.utils import timezone
from common.models import BaseModel


class Subscription(BaseModel):
    """
    Organizer subscription for premium features.
    
    Integration: Stripe Subscriptions
    
    Lifecycle:
    - User upgrades to organizer → create subscription (trial or paid)
    - Monthly billing cycle
    - Downgrade/cancel → subscription remains until period end
    
    Free Tier (attendee):
    - Register for events
    - Receive certificates
    - View CPD dashboard
    
    Organizer Tier:
    - Create events (limit based on plan)
    - Issue certificates
    - Contact management
    - Zoom integration
    """
    
    class Status(models.TextChoices):
        TRIALING = 'trialing', 'Trialing'
        ACTIVE = 'active', 'Active'
        PAST_DUE = 'past_due', 'Past Due'
        CANCELED = 'canceled', 'Canceled'
        UNPAID = 'unpaid', 'Unpaid'
        INCOMPLETE = 'incomplete', 'Incomplete'
        INCOMPLETE_EXPIRED = 'incomplete_expired', 'Incomplete Expired'
        PAUSED = 'paused', 'Paused'
    
    class Plan(models.TextChoices):
        FREE = 'free', 'Free'
        STARTER = 'starter', 'Starter'
        PROFESSIONAL = 'professional', 'Professional'
        ENTERPRISE = 'enterprise', 'Enterprise'
    
    # Plan limits
    PLAN_LIMITS = {
        'free': {
            'events_per_month': 0,
            'registrations_per_event': 0,
            'certificates_per_month': 0,
            'contact_lists': 0,
            'contacts': 0,
            'templates': 0,
        },
        'starter': {
            'events_per_month': 5,
            'registrations_per_event': 100,
            'certificates_per_month': 500,
            'contact_lists': 5,
            'contacts': 500,
            'templates': 3,
        },
        'professional': {
            'events_per_month': 20,
            'registrations_per_event': 500,
            'certificates_per_month': 5000,
            'contact_lists': 20,
            'contacts': 5000,
            'templates': 10,
        },
        'enterprise': {
            'events_per_month': None,  # Unlimited
            'registrations_per_event': None,
            'certificates_per_month': None,
            'contact_lists': None,
            'contacts': None,
            'templates': None,
        },
    }
    
    # =========================================
    # User Link
    # =========================================
    user = models.OneToOneField(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    
    # =========================================
    # Plan & Status
    # =========================================
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
    
    # =========================================
    # Billing Cycle
    # =========================================
    current_period_start = models.DateTimeField(
        null=True, blank=True,
        help_text="Start of current billing period"
    )
    current_period_end = models.DateTimeField(
        null=True, blank=True,
        help_text="End of current billing period"
    )
    
    # Trial
    trial_start = models.DateTimeField(
        null=True, blank=True
    )
    trial_end = models.DateTimeField(
        null=True, blank=True
    )
    
    # Cancellation
    cancel_at_period_end = models.BooleanField(
        default=False,
        help_text="Cancel at end of current period"
    )
    canceled_at = models.DateTimeField(
        null=True, blank=True
    )
    cancellation_reason = models.TextField(
        blank=True
    )
    
    # =========================================
    # Stripe Integration
    # =========================================
    stripe_customer_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Stripe customer ID"
    )
    stripe_subscription_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Stripe subscription ID"
    )
    stripe_price_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Stripe price ID for current plan"
    )
    
    # =========================================
    # Usage Tracking (current period)
    # =========================================
    events_created_this_period = models.PositiveIntegerField(
        default=0
    )
    certificates_issued_this_period = models.PositiveIntegerField(
        default=0
    )
    
    class Meta:
        db_table = 'subscriptions'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['stripe_customer_id']),
            models.Index(fields=['stripe_subscription_id']),
            models.Index(fields=['current_period_end']),
        ]
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'
    
    def __str__(self):
        return f"{self.user.email} - {self.plan}"
    
    # =========================================
    # Properties
    # =========================================
    @property
    def is_active(self):
        """Check if subscription is active."""
        return self.status in [self.Status.ACTIVE, self.Status.TRIALING]
    
    @property
    def is_trialing(self):
        return self.status == self.Status.TRIALING
    
    @property
    def is_canceled(self):
        return self.status == self.Status.CANCELED
    
    @property
    def trial_days_remaining(self):
        """Days remaining in trial."""
        if not self.is_trialing or not self.trial_end:
            return 0
        delta = self.trial_end - timezone.now()
        return max(0, delta.days)
    
    @property
    def days_until_renewal(self):
        """Days until next billing."""
        if not self.current_period_end:
            return None
        delta = self.current_period_end - timezone.now()
        return max(0, delta.days)
    
    @property
    def limits(self):
        """Get plan limits."""
        return self.PLAN_LIMITS.get(self.plan, self.PLAN_LIMITS['free'])
    
    # =========================================
    # Limit Checking
    # =========================================
    def can_create_event(self):
        """Check if user can create another event."""
        limit = self.limits.get('events_per_month')
        if limit is None:  # Unlimited
            return True
        return self.events_created_this_period < limit
    
    def can_issue_certificate(self):
        """Check if user can issue another certificate."""
        limit = self.limits.get('certificates_per_month')
        if limit is None:
            return True
        return self.certificates_issued_this_period < limit
    
    def can_add_contact_list(self):
        """Check if user can add another contact list."""
        from contacts.models import ContactList
        limit = self.limits.get('contact_lists')
        if limit is None:
            return True
        current = ContactList.objects.filter(owner=self.user).count()
        return current < limit
    
    def can_add_contact(self):
        """Check if user can add another contact."""
        from contacts.models import Contact
        limit = self.limits.get('contacts')
        if limit is None:
            return True
        current = Contact.objects.filter(
            contact_list__owner=self.user
        ).count()
        return current < limit
    
    def can_add_template(self):
        """Check if user can add another template."""
        from certificates.models import CertificateTemplate
        limit = self.limits.get('templates')
        if limit is None:
            return True
        current = CertificateTemplate.objects.filter(
            owner=self.user,
            deleted_at__isnull=True
        ).count()
        return current < limit
    
    def get_event_registration_limit(self):
        """Get max registrations per event."""
        return self.limits.get('registrations_per_event')
    
    # =========================================
    # Usage Tracking
    # =========================================
    def increment_events(self):
        """Increment events created count."""
        from django.db.models import F
        Subscription.objects.filter(pk=self.pk).update(
            events_created_this_period=F('events_created_this_period') + 1
        )
    
    def increment_certificates(self, count=1):
        """Increment certificates issued count."""
        from django.db.models import F
        Subscription.objects.filter(pk=self.pk).update(
            certificates_issued_this_period=F('certificates_issued_this_period') + count
        )
    
    def reset_usage(self):
        """Reset usage counters for new period."""
        self.events_created_this_period = 0
        self.certificates_issued_this_period = 0
        self.save(update_fields=[
            'events_created_this_period',
            'certificates_issued_this_period',
            'updated_at'
        ])
    
    # =========================================
    # Subscription Management
    # =========================================
    def upgrade_plan(self, new_plan):
        """
        Upgrade to a new plan.
        
        Note: Actual Stripe billing change handled by Stripe service.
        This updates local record after webhook confirmation.
        """
        self.plan = new_plan
        self.save(update_fields=['plan', 'updated_at'])
    
    def downgrade_plan(self, new_plan):
        """
        Downgrade to a lower plan (effective at period end).
        """
        # Stripe handles this - just record intent
        self.plan = new_plan
        self.save(update_fields=['plan', 'updated_at'])
    
    def cancel(self, reason='', immediate=False):
        """
        Cancel subscription.
        
        Args:
            reason: Cancellation reason
            immediate: Cancel immediately vs at period end
        """
        if immediate:
            self.status = self.Status.CANCELED
        else:
            self.cancel_at_period_end = True
        
        self.canceled_at = timezone.now()
        self.cancellation_reason = reason
        self.save(update_fields=[
            'status', 'cancel_at_period_end',
            'canceled_at', 'cancellation_reason', 'updated_at'
        ])
    
    def reactivate(self):
        """Reactivate a canceled subscription."""
        if self.cancel_at_period_end:
            self.cancel_at_period_end = False
            self.canceled_at = None
            self.cancellation_reason = ''
            self.save(update_fields=[
                'cancel_at_period_end', 'canceled_at',
                'cancellation_reason', 'updated_at'
            ])
    
    @classmethod
    def create_for_user(cls, user, plan=None):
        """Create subscription for a new user."""
        return cls.objects.create(
            user=user,
            plan=plan or cls.Plan.FREE,
            status=cls.Status.ACTIVE
        )
```

---

### PaymentMethod

Stored payment methods for billing.

```python
class PaymentMethod(BaseModel):
    """
    Stored payment method for a user.
    
    Integration: Stripe Payment Methods
    """
    
    class Type(models.TextChoices):
        CARD = 'card', 'Credit/Debit Card'
        BANK_ACCOUNT = 'bank_account', 'Bank Account'
    
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='payment_methods'
    )
    
    # Type and provider
    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.CARD
    )
    
    # Stripe
    stripe_payment_method_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True
    )
    
    # Card details (from Stripe, for display only)
    card_brand = models.CharField(
        max_length=20,
        blank=True,
        help_text="Card brand (visa, mastercard, etc.)"
    )
    card_last4 = models.CharField(
        max_length=4,
        blank=True,
        help_text="Last 4 digits"
    )
    card_exp_month = models.PositiveSmallIntegerField(
        null=True, blank=True
    )
    card_exp_year = models.PositiveSmallIntegerField(
        null=True, blank=True
    )
    
    # Status
    is_default = models.BooleanField(
        default=False
    )
    is_valid = models.BooleanField(
        default=True,
        help_text="False if card expired or declined"
    )
    
    class Meta:
        db_table = 'payment_methods'
        ordering = ['-is_default', '-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['stripe_payment_method_id']),
        ]
        verbose_name = 'Payment Method'
        verbose_name_plural = 'Payment Methods'
    
    def __str__(self):
        if self.type == self.Type.CARD:
            return f"{self.card_brand.title()} •••• {self.card_last4}"
        return f"Payment Method {self.id}"
    
    @property
    def display_name(self):
        """Human-readable name."""
        if self.type == self.Type.CARD:
            return f"{self.card_brand.title()} ending in {self.card_last4}"
        return "Bank Account"
    
    @property
    def is_expired(self):
        """Check if card is expired."""
        if self.type != self.Type.CARD:
            return False
        if not self.card_exp_year or not self.card_exp_month:
            return False
        
        now = timezone.now()
        return (
            self.card_exp_year < now.year or
            (self.card_exp_year == now.year and self.card_exp_month < now.month)
        )
    
    def set_as_default(self):
        """Set this as the default payment method."""
        PaymentMethod.objects.filter(
            user=self.user,
            is_default=True
        ).exclude(pk=self.pk).update(is_default=False)
        
        self.is_default = True
        self.save(update_fields=['is_default', 'updated_at'])
```

---

### Invoice

Record of billing invoices.

```python
class Invoice(BaseModel):
    """
    Invoice record for billing.
    
    Integration: Stripe Invoices
    
    Created from Stripe webhooks when invoices are generated.
    """
    
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        OPEN = 'open', 'Open'
        PAID = 'paid', 'Paid'
        VOID = 'void', 'Void'
        UNCOLLECTIBLE = 'uncollectible', 'Uncollectible'
    
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='invoices'
    )
    
    # Stripe
    stripe_invoice_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True
    )
    stripe_hosted_invoice_url = models.URLField(
        blank=True,
        help_text="URL to hosted invoice page"
    )
    stripe_pdf_url = models.URLField(
        blank=True,
        help_text="URL to invoice PDF"
    )
    
    # Invoice details
    invoice_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Invoice number for display"
    )
    description = models.CharField(
        max_length=500,
        blank=True
    )
    
    # Amounts (in cents)
    amount_due = models.PositiveIntegerField(
        default=0,
        help_text="Amount due in cents"
    )
    amount_paid = models.PositiveIntegerField(
        default=0,
        help_text="Amount paid in cents"
    )
    amount_remaining = models.PositiveIntegerField(
        default=0,
        help_text="Remaining amount in cents"
    )
    currency = models.CharField(
        max_length=3,
        default='usd'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    
    # Dates
    period_start = models.DateTimeField(
        null=True, blank=True,
        help_text="Billing period start"
    )
    period_end = models.DateTimeField(
        null=True, blank=True,
        help_text="Billing period end"
    )
    due_date = models.DateTimeField(
        null=True, blank=True
    )
    paid_at = models.DateTimeField(
        null=True, blank=True
    )
    
    # Line items (denormalized for display)
    line_items = models.JSONField(
        default=list,
        help_text="Invoice line items"
    )
    """
    Schema:
    [
        {
            "description": "Professional Plan (Jan 2025)",
            "quantity": 1,
            "amount": 4900,
            "currency": "usd"
        },
        ...
    ]
    """
    
    class Meta:
        db_table = 'invoices'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['stripe_invoice_id']),
            models.Index(fields=['status']),
        ]
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'
    
    def __str__(self):
        return f"Invoice {self.invoice_number or self.id} - {self.user.email}"
    
    @property
    def amount_due_display(self):
        """Format amount for display."""
        return f"${self.amount_due / 100:.2f}"
    
    @property
    def is_paid(self):
        return self.status == self.Status.PAID
    
    def mark_paid(self):
        """Mark invoice as paid."""
        self.status = self.Status.PAID
        self.paid_at = timezone.now()
        self.amount_remaining = 0
        self.save(update_fields=[
            'status', 'paid_at', 'amount_remaining', 'updated_at'
        ])
```

---

## Stripe Service

```python
# billing/services.py

import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """Service for Stripe API interactions."""
    
    PLAN_PRICE_MAP = {
        'starter': settings.STRIPE_STARTER_PRICE_ID,
        'professional': settings.STRIPE_PROFESSIONAL_PRICE_ID,
        'enterprise': settings.STRIPE_ENTERPRISE_PRICE_ID,
    }
    
    @classmethod
    def create_customer(cls, user):
        """Create Stripe customer for user."""
        customer = stripe.Customer.create(
            email=user.email,
            name=user.full_name,
            metadata={'user_id': str(user.id)}
        )
        
        # Update subscription with customer ID
        subscription = user.subscription
        subscription.stripe_customer_id = customer.id
        subscription.save(update_fields=['stripe_customer_id', 'updated_at'])
        
        return customer
    
    @classmethod
    def create_subscription(cls, user, plan, payment_method_id=None, trial_days=14):
        """
        Create Stripe subscription for user.
        
        Args:
            user: User to subscribe
            plan: Plan name (starter, professional, enterprise)
            payment_method_id: Stripe payment method ID
            trial_days: Number of trial days
        
        Returns:
            Stripe Subscription object
        """
        subscription = user.subscription
        
        # Create customer if needed
        if not subscription.stripe_customer_id:
            customer = cls.create_customer(user)
            customer_id = customer.id
        else:
            customer_id = subscription.stripe_customer_id
        
        # Attach payment method if provided
        if payment_method_id:
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id
            )
            stripe.Customer.modify(
                customer_id,
                invoice_settings={'default_payment_method': payment_method_id}
            )
        
        # Create subscription
        stripe_sub = stripe.Subscription.create(
            customer=customer_id,
            items=[{'price': cls.PLAN_PRICE_MAP[plan]}],
            trial_period_days=trial_days if trial_days else None,
            metadata={'user_id': str(user.id)},
            expand=['latest_invoice.payment_intent']
        )
        
        # Update local subscription
        subscription.stripe_subscription_id = stripe_sub.id
        subscription.stripe_price_id = cls.PLAN_PRICE_MAP[plan]
        subscription.plan = plan
        subscription.status = stripe_sub.status
        
        if stripe_sub.trial_end:
            subscription.trial_end = timezone.fromtimestamp(stripe_sub.trial_end)
            subscription.status = Subscription.Status.TRIALING
        
        subscription.current_period_start = timezone.fromtimestamp(
            stripe_sub.current_period_start
        )
        subscription.current_period_end = timezone.fromtimestamp(
            stripe_sub.current_period_end
        )
        
        subscription.save()
        
        return stripe_sub
    
    @classmethod
    def cancel_subscription(cls, user, immediate=False):
        """Cancel user's subscription."""
        subscription = user.subscription
        
        if not subscription.stripe_subscription_id:
            raise ValueError("No Stripe subscription found")
        
        if immediate:
            stripe.Subscription.delete(subscription.stripe_subscription_id)
        else:
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )
    
    @classmethod
    def change_plan(cls, user, new_plan):
        """Change subscription plan."""
        subscription = user.subscription
        
        if not subscription.stripe_subscription_id:
            raise ValueError("No Stripe subscription found")
        
        stripe_sub = stripe.Subscription.retrieve(
            subscription.stripe_subscription_id
        )
        
        stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            items=[{
                'id': stripe_sub['items']['data'][0].id,
                'price': cls.PLAN_PRICE_MAP[new_plan]
            }],
            proration_behavior='create_prorations'
        )
    
    @classmethod
    def create_checkout_session(cls, user, plan, success_url, cancel_url):
        """
        Create Stripe Checkout session for new subscription.
        
        Returns:
            Checkout Session with URL to redirect user
        """
        subscription = user.subscription
        
        # Create customer if needed
        if not subscription.stripe_customer_id:
            customer = cls.create_customer(user)
            customer_id = customer.id
        else:
            customer_id = subscription.stripe_customer_id
        
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode='subscription',
            line_items=[{
                'price': cls.PLAN_PRICE_MAP[plan],
                'quantity': 1
            }],
            success_url=success_url,
            cancel_url=cancel_url,
            subscription_data={
                'trial_period_days': 14,
                'metadata': {'user_id': str(user.id)}
            }
        )
        
        return session
    
    @classmethod
    def create_billing_portal_session(cls, user, return_url):
        """
        Create Stripe Billing Portal session.
        
        Returns:
            Portal Session with URL for user to manage billing
        """
        subscription = user.subscription
        
        if not subscription.stripe_customer_id:
            raise ValueError("No Stripe customer found")
        
        session = stripe.billing_portal.Session.create(
            customer=subscription.stripe_customer_id,
            return_url=return_url
        )
        
        return session
```

---

## Stripe Webhook Handler

```python
# billing/webhooks.py

import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Handle Stripe webhook events."""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)
    
    # Handle event types
    handlers = {
        'customer.subscription.created': handle_subscription_created,
        'customer.subscription.updated': handle_subscription_updated,
        'customer.subscription.deleted': handle_subscription_deleted,
        'invoice.paid': handle_invoice_paid,
        'invoice.payment_failed': handle_invoice_payment_failed,
        'payment_method.attached': handle_payment_method_attached,
        'payment_method.detached': handle_payment_method_detached,
    }
    
    handler = handlers.get(event['type'])
    if handler:
        handler(event['data']['object'])
    
    return HttpResponse(status=200)


def handle_subscription_updated(stripe_sub):
    """Update local subscription from Stripe."""
    from billing.models import Subscription
    
    try:
        subscription = Subscription.objects.get(
            stripe_subscription_id=stripe_sub.id
        )
    except Subscription.DoesNotExist:
        return
    
    # Map Stripe status to our status
    status_map = {
        'trialing': Subscription.Status.TRIALING,
        'active': Subscription.Status.ACTIVE,
        'past_due': Subscription.Status.PAST_DUE,
        'canceled': Subscription.Status.CANCELED,
        'unpaid': Subscription.Status.UNPAID,
        'incomplete': Subscription.Status.INCOMPLETE,
        'incomplete_expired': Subscription.Status.INCOMPLETE_EXPIRED,
        'paused': Subscription.Status.PAUSED,
    }
    
    subscription.status = status_map.get(
        stripe_sub.status, 
        Subscription.Status.ACTIVE
    )
    subscription.current_period_start = timezone.fromtimestamp(
        stripe_sub.current_period_start
    )
    subscription.current_period_end = timezone.fromtimestamp(
        stripe_sub.current_period_end
    )
    subscription.cancel_at_period_end = stripe_sub.cancel_at_period_end
    
    if stripe_sub.trial_end:
        subscription.trial_end = timezone.fromtimestamp(stripe_sub.trial_end)
    
    subscription.save()
    
    # Reset usage on new period
    if subscription.current_period_start == timezone.fromtimestamp(
        stripe_sub.current_period_start
    ):
        subscription.reset_usage()


def handle_invoice_paid(stripe_invoice):
    """Record paid invoice."""
    from billing.models import Invoice, Subscription
    from accounts.models import User
    
    # Find user
    try:
        subscription = Subscription.objects.get(
            stripe_customer_id=stripe_invoice.customer
        )
        user = subscription.user
    except Subscription.DoesNotExist:
        return
    
    # Create or update invoice
    Invoice.objects.update_or_create(
        stripe_invoice_id=stripe_invoice.id,
        defaults={
            'user': user,
            'subscription': subscription,
            'invoice_number': stripe_invoice.number,
            'amount_due': stripe_invoice.amount_due,
            'amount_paid': stripe_invoice.amount_paid,
            'amount_remaining': stripe_invoice.amount_remaining,
            'currency': stripe_invoice.currency,
            'status': Invoice.Status.PAID,
            'period_start': timezone.fromtimestamp(stripe_invoice.period_start) if stripe_invoice.period_start else None,
            'period_end': timezone.fromtimestamp(stripe_invoice.period_end) if stripe_invoice.period_end else None,
            'paid_at': timezone.now(),
            'stripe_hosted_invoice_url': stripe_invoice.hosted_invoice_url or '',
            'stripe_pdf_url': stripe_invoice.invoice_pdf or '',
            'line_items': [
                {
                    'description': line.description,
                    'quantity': line.quantity,
                    'amount': line.amount,
                    'currency': line.currency
                }
                for line in stripe_invoice.lines.data
            ]
        }
    )
```

---

## Relationships

```
Subscription
├── User (1:1, CASCADE)
└── Invoice (1:N, SET_NULL)

PaymentMethod
└── User (N:1, CASCADE)

Invoice
├── User (N:1, CASCADE)
└── Subscription (N:1, SET_NULL)
```

---

## Indexes

| Table | Index | Purpose |
|-------|-------|---------|
| subscriptions | user_id (unique) | One per user |
| subscriptions | status | Filter by status |
| subscriptions | stripe_customer_id | Webhook matching |
| subscriptions | stripe_subscription_id | Webhook matching |
| subscriptions | current_period_end | Renewal queries |
| payment_methods | user_id | User's methods |
| payment_methods | stripe_payment_method_id | Stripe matching |
| invoices | user_id, -created_at | User's invoices |
| invoices | stripe_invoice_id | Webhook matching |

---

## Business Rules

1. **One subscription per user**: Even free users have a subscription record
2. **Plan limits**: Enforced via `can_*` methods before actions
3. **Usage reset**: Counters reset on new billing period
4. **Cancellation**: Takes effect at period end by default
5. **Trial**: 14 days default, no payment method required
6. **Upgrade/downgrade**: Prorated via Stripe
7. **Payment failure**: Subscription marked past_due, user notified
