"""Billing models for course-based institutional deployment.

Learners pay per course/event; there is no subscription tier. Stripe
Checkout drives every purchase and its webhook writes the local rows.

Models:
- StripeEvent: idempotency + async dispatch record for incoming webhooks
- CoursePurchase: individual course/event purchase
- PaymentMethod: stored payment methods (kept for future "use saved card")
- RefundRecord: refund tracking
- Dispute: Stripe chargeback/dispute record
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from common.models import BaseModel


# =============================================================================
# Stripe Event (idempotency + async dispatch record)
# =============================================================================


class StripeEvent(models.Model):
    """One row per webhook delivery, keyed on the Stripe event id.

    The webhook endpoint inserts on receipt (unique constraint dedupes
    replays); a cloud task picks up unprocessed rows, re-fetches the canonical
    event from Stripe, and runs the matching handler inside a transaction
    that also flips ``processed_at``. ``error`` captures the last handler
    failure so retries can be investigated in admin.
    """

    event_id = models.CharField(max_length=80, primary_key=True, help_text="Stripe event id (evt_...)")
    event_type = models.CharField(max_length=120, db_index=True)
    payload = models.JSONField(default=dict, help_text="Snapshot of event body as received from Stripe")
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    error = models.TextField(blank=True)

    class Meta:
        db_table = "stripe_events"
        ordering = ["-received_at"]
        indexes = [
            models.Index(fields=["event_type", "-received_at"]),
            models.Index(fields=["processed_at"]),
        ]
        verbose_name = "Stripe Event"
        verbose_name_plural = "Stripe Events"

    def __str__(self):
        return f"{self.event_type} ({self.event_id})"

    @property
    def is_processed(self):
        return self.processed_at is not None


# =============================================================================
# Course/Event Purchase
# =============================================================================


class CoursePurchase(BaseModel):
    """One row per Stripe-Checkout-backed purchase of a course, event, or program.

    Exactly one of ``course``, ``event``, ``program`` is non-null per row.
    The model name is a legacy holdover from the courses-only iteration; it
    is now the shared receipt surface for every non-subscription purchase.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        REFUNDED = "refunded", "Refunded"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="purchases")
    course = models.ForeignKey("learning.Course", on_delete=models.SET_NULL, null=True, blank=True, related_name="purchases")
    event = models.ForeignKey("events.Event", on_delete=models.SET_NULL, null=True, blank=True, related_name="purchases")
    program = models.ForeignKey(
        "learning.Program", on_delete=models.SET_NULL, null=True, blank=True, related_name="purchases"
    )

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
        item = self.course or self.event or self.program
        return f"{self.user.email} purchased {item}"

    @property
    def is_completed(self):
        return self.status == self.Status.COMPLETED

    def has_access(self):
        """Check if this purchase grants access."""
        return self.status == self.Status.COMPLETED


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


# =============================================================================
# Disputes (chargebacks)
# =============================================================================


class Dispute(BaseModel):
    """Stripe dispute / chargeback record.

    Written by ``charge.dispute.*`` webhook handlers. Kept as its own entity
    (not fused with RefundRecord) because disputes have their own lifecycle —
    evidence due dates, outcomes, and reason taxonomy distinct from refunds.
    """

    class Status(models.TextChoices):
        WARNING_NEEDS_RESPONSE = "warning_needs_response", "Warning — Needs Response"
        WARNING_UNDER_REVIEW = "warning_under_review", "Warning — Under Review"
        WARNING_CLOSED = "warning_closed", "Warning — Closed"
        NEEDS_RESPONSE = "needs_response", "Needs Response"
        UNDER_REVIEW = "under_review", "Under Review"
        WON = "won", "Won"
        LOST = "lost", "Lost"

    class Reason(models.TextChoices):
        CREDIT_NOT_PROCESSED = "credit_not_processed", "Credit not processed"
        DUPLICATE = "duplicate", "Duplicate"
        FRAUDULENT = "fraudulent", "Fraudulent"
        GENERAL = "general", "General"
        INCORRECT_AMOUNT = "incorrect_account_details", "Incorrect account details"
        INSUFFICIENT_FUNDS = "insufficient_funds", "Insufficient funds"
        PRODUCT_NOT_RECEIVED = "product_not_received", "Product not received"
        PRODUCT_UNACCEPTABLE = "product_unacceptable", "Product unacceptable"
        SUBSCRIPTION_CANCELED = "subscription_canceled", "Subscription canceled"
        UNRECOGNIZED = "unrecognized", "Unrecognized"
        OTHER = "other", "Other"

    stripe_dispute_id = models.CharField(max_length=255, unique=True, db_index=True)
    stripe_charge_id = models.CharField(max_length=255, blank=True, db_index=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, db_index=True)

    registration = models.ForeignKey(
        "registrations.Registration",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="disputes",
    )
    course_purchase = models.ForeignKey(
        CoursePurchase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="disputes",
    )

    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="cad")
    reason = models.CharField(max_length=64, choices=Reason.choices, default=Reason.GENERAL)
    status = models.CharField(max_length=64, choices=Status.choices, default=Status.NEEDS_RESPONSE, db_index=True)

    evidence_due_by = models.DateTimeField(null=True, blank=True, db_index=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    outcome = models.CharField(max_length=64, blank=True)

    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "disputes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["evidence_due_by"]),
        ]

    def __str__(self):
        return f"Dispute {self.stripe_dispute_id} ({self.status})"

    @property
    def is_open(self) -> bool:
        return self.status in {
            self.Status.NEEDS_RESPONSE,
            self.Status.UNDER_REVIEW,
            self.Status.WARNING_NEEDS_RESPONSE,
            self.Status.WARNING_UNDER_REVIEW,
        }

    @property
    def is_lost(self) -> bool:
        return self.status == self.Status.LOST
