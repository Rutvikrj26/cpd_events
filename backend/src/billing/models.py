"""
Billing models for institutional deployment.

The institution configures how learners pay for content:
- FREE: All content is free
- PER_ITEM: Pay per course/event
- SUBSCRIPTION: Monthly/annual plans for access
- HYBRID: Some free, some paid

Models:
- InstitutionBillingConfig: Single-row config for billing mode
- InstitutionPlan: Subscription plans the institution offers learners
- Subscription: Learner subscription to an InstitutionPlan
- Invoice: Payment history
- PaymentMethod: Stored payment methods
- RefundRecord: Refund tracking
- CoursePurchase: Individual course/event purchases (per-item mode)
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from common.fields import EncryptedTextField
from common.models import BaseModel


# =============================================================================
# Institution Billing Configuration
# =============================================================================


class InstitutionBillingConfig(BaseModel):
    """
    Single-row configuration for how this institution charges learners.

    Only one row should exist. Use get_config() classmethod.
    """

    class PricingModel(models.TextChoices):
        FREE = "free", "Free Access"
        PER_ITEM = "per_item", "Per Course/Event"
        SUBSCRIPTION = "subscription", "Subscription"
        HYBRID = "hybrid", "Hybrid"

    pricing_model = models.CharField(
        max_length=20,
        choices=PricingModel.choices,
        default=PricingModel.FREE,
        help_text="How learners pay for content",
    )

    # Stripe configuration (institution's own Stripe account)
    stripe_secret_key = EncryptedTextField(blank=True, help_text="Institution's Stripe secret key")
    stripe_publishable_key = models.CharField(max_length=255, blank=True, help_text="Institution's Stripe publishable key")
    stripe_webhook_secret = EncryptedTextField(blank=True, help_text="Stripe webhook signing secret")

    # Defaults
    default_currency = models.CharField(max_length=3, default="CAD", help_text="Default currency for pricing")
    tax_enabled = models.BooleanField(default=False, help_text="Enable Stripe Tax")
    tax_id = models.CharField(max_length=50, blank=True, help_text="Institution's tax ID (GST/HST)")

    class Meta:
        db_table = "institution_billing_config"
        verbose_name = "Institution Billing Configuration"
        verbose_name_plural = "Institution Billing Configuration"
        permissions = [
            ("can_configure_billing", "Can configure institutional billing"),
        ]

    def __str__(self):
        return f"Billing Config: {self.get_pricing_model_display()}"

    @property
    def is_stripe_configured(self):
        return bool(self.stripe_secret_key and self.stripe_publishable_key)

    @property
    def is_free(self):
        return self.pricing_model == self.PricingModel.FREE

    @classmethod
    def get_config(cls):
        """Get or create the singleton billing config."""
        config, _ = cls.objects.get_or_create(pk=1, defaults={"pricing_model": cls.PricingModel.FREE})
        return config


# =============================================================================
# Institution Plans (for subscription pricing model)
# =============================================================================


class InstitutionPlan(BaseModel):
    """
    Subscription plans the institution offers to learners.

    Examples: "Basic" ($29/mo, 5 courses), "Premium" ($99/mo, all courses), "All Access" ($199/yr)
    """

    class BillingInterval(models.TextChoices):
        MONTH = "month", "Monthly"
        YEAR = "year", "Annual"

    name = models.CharField(max_length=100, help_text='Plan name (e.g., "Basic", "Premium")')
    description = models.TextField(blank=True, help_text="Plan description shown to learners")
    price_cents = models.PositiveIntegerField(default=0, help_text="Price in cents (e.g., 2900 = $29.00)")
    billing_interval = models.CharField(
        max_length=10,
        choices=BillingInterval.choices,
        default=BillingInterval.MONTH,
    )

    # Stripe
    stripe_price_id = models.CharField(max_length=255, blank=True, help_text="Stripe Price ID")
    stripe_product_id = models.CharField(max_length=255, blank=True, help_text="Stripe Product ID")

    # Access control
    includes_all_courses = models.BooleanField(default=False, help_text="Grants access to all courses")
    included_courses = models.ManyToManyField("learning.Course", blank=True, help_text="Specific courses included in plan")
    includes_all_events = models.BooleanField(default=False, help_text="Grants access to all paid events")
    max_enrollments = models.PositiveIntegerField(null=True, blank=True, help_text="Max active enrollments (null = unlimited)")

    # Display
    is_active = models.BooleanField(default=True, help_text="Whether plan is available for purchase")
    is_featured = models.BooleanField(default=False, help_text="Highlight this plan in the UI")
    sort_order = models.IntegerField(default=0, help_text="Display order")
    features_list = models.JSONField(default=list, blank=True, help_text='List of feature strings for display (e.g., ["5 courses", "Certificate included"])')

    class Meta:
        db_table = "institution_plans"
        ordering = ["sort_order", "price_cents"]
        verbose_name = "Institution Plan"
        verbose_name_plural = "Institution Plans"

    def __str__(self):
        return f"{self.name} (${self.price_cents / 100:.2f}/{self.billing_interval})"

    @property
    def price_display(self):
        return f"${self.price_cents / 100:.2f}"

    def grants_access_to_course(self, course):
        """Check if this plan grants access to a specific course."""
        if self.includes_all_courses:
            return True
        return self.included_courses.filter(pk=course.pk).exists()


# =============================================================================
# Learner Subscription
# =============================================================================


class Subscription(BaseModel):
    """
    Learner's subscription to an InstitutionPlan.

    Created when a learner subscribes to a plan via Stripe checkout.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past Due"
        CANCELED = "canceled", "Canceled"
        UNPAID = "unpaid", "Unpaid"
        INCOMPLETE = "incomplete", "Incomplete"
        PAUSED = "paused", "Paused"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscription")
    institution_plan = models.ForeignKey(InstitutionPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name="subscriptions")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    # Stripe
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True, unique=True, db_index=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)

    # Billing period
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)

    # Cancellation
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "subscriptions"
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["current_period_end"]),
        ]

    def __str__(self):
        plan_name = self.institution_plan.name if self.institution_plan else "None"
        return f"{self.user.email} - {plan_name} ({self.status})"

    @property
    def is_active(self):
        return self.status in [self.Status.ACTIVE]

    @property
    def plan_name(self):
        return self.institution_plan.name if self.institution_plan else None

    def grants_access_to_course(self, course):
        """Check if this subscription grants access to a course."""
        if not self.is_active or not self.institution_plan:
            return False
        return self.institution_plan.grants_access_to_course(course)

    def cancel(self, immediate=False):
        if immediate:
            self.status = self.Status.CANCELED
        else:
            self.cancel_at_period_end = True
        self.canceled_at = timezone.now()
        self.save()


# =============================================================================
# Course/Event Purchase (per-item mode)
# =============================================================================


class CoursePurchase(BaseModel):
    """
    Individual course or event purchase (for per-item pricing model).
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        REFUNDED = "refunded", "Refunded"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="purchases")
    course = models.ForeignKey("learning.Course", on_delete=models.SET_NULL, null=True, blank=True, related_name="purchases")
    event = models.ForeignKey("events.Event", on_delete=models.SET_NULL, null=True, blank=True, related_name="purchases")

    # Payment
    amount_cents = models.PositiveIntegerField(help_text="Amount paid in cents")
    currency = models.CharField(max_length=3, default="CAD")
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, db_index=True)
    stripe_checkout_session_id = models.CharField(max_length=255, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    class Meta:
        db_table = "course_purchases"
        ordering = ["-created_at"]
        verbose_name = "Course Purchase"
        verbose_name_plural = "Course Purchases"

    def __str__(self):
        item = self.course or self.event
        return f"{self.user.email} purchased {item}"

    @property
    def is_completed(self):
        return self.status == self.Status.COMPLETED

    def has_access(self):
        """Check if this purchase grants access."""
        return self.status == self.Status.COMPLETED


# =============================================================================
# Invoice (payment history)
# =============================================================================


class Invoice(BaseModel):
    """Invoice record from Stripe."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open"
        PAID = "paid", "Paid"
        VOID = "void", "Void"
        UNCOLLECTIBLE = "uncollectible", "Uncollectible"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="invoices")
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices")

    stripe_invoice_id = models.CharField(max_length=255, unique=True, db_index=True)
    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="cad")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    invoice_pdf_url = models.URLField(max_length=500, blank=True)
    hosted_invoice_url = models.URLField(max_length=500, blank=True)

    period_start = models.DateTimeField(null=True, blank=True)
    period_end = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "invoices"
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invoice {self.stripe_invoice_id} - {self.amount_display}"

    @property
    def amount_display(self):
        return f"${self.amount_cents / 100:.2f} {self.currency.upper()}"

    @property
    def is_paid(self):
        return self.status == self.Status.PAID


# =============================================================================
# Payment Method
# =============================================================================


class PaymentMethod(BaseModel):
    """Stored payment method for a user."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payment_methods")
    stripe_payment_method_id = models.CharField(max_length=255, unique=True, db_index=True)

    card_brand = models.CharField(max_length=50, blank=True)
    card_last4 = models.CharField(max_length=4, blank=True)
    card_exp_month = models.PositiveSmallIntegerField(null=True, blank=True)
    card_exp_year = models.PositiveSmallIntegerField(null=True, blank=True)

    is_default = models.BooleanField(default=False)
    billing_name = models.CharField(max_length=255, blank=True)
    billing_email = models.EmailField(blank=True)

    class Meta:
        db_table = "payment_methods"
        verbose_name = "Payment Method"
        verbose_name_plural = "Payment Methods"
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.card_brand} ****{self.card_last4}"

    @property
    def is_expired(self):
        if not self.card_exp_month or not self.card_exp_year:
            return False
        now = timezone.now()
        return self.card_exp_year < now.year or (self.card_exp_year == now.year and self.card_exp_month < now.month)

    def set_as_default(self):
        PaymentMethod.objects.filter(user=self.user, is_default=True).exclude(id=self.id).update(is_default=False)
        self.is_default = True
        self.save(update_fields=["is_default", "updated_at"])


# =============================================================================
# Refund Record
# =============================================================================


class RefundRecord(BaseModel):
    """Record of a processed refund."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELED = "canceled", "Canceled"

    class Reason(models.TextChoices):
        DUPLICATE = "duplicate", "Duplicate"
        FRAUDULENT = "fraudulent", "Fraudulent"
        REQUESTED_BY_CUSTOMER = "requested_by_customer", "Requested by Customer"
        OTHER = "other", "Other"

    registration = models.ForeignKey(
        "registrations.Registration", on_delete=models.SET_NULL, null=True, blank=True, related_name="refunds"
    )
    purchase = models.ForeignKey(
        CoursePurchase, on_delete=models.SET_NULL, null=True, blank=True, related_name="refunds"
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="processed_refunds"
    )

    stripe_refund_id = models.CharField(max_length=255, unique=True, db_index=True)
    stripe_payment_intent_id = models.CharField(max_length=255, db_index=True)

    amount_cents = models.PositiveIntegerField(help_text="Amount refunded in cents")
    currency = models.CharField(max_length=3, default="cad")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reason = models.CharField(max_length=50, choices=Reason.choices, default=Reason.REQUESTED_BY_CUSTOMER)
    description = models.TextField(blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "refund_records"
        verbose_name = "Refund Record"
        verbose_name_plural = "Refund Records"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Refund {self.stripe_refund_id} - {self.amount_display}"

    @property
    def amount_display(self):
        return f"${self.amount_cents / 100:.2f} {self.currency.upper()}"
