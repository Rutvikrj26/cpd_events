"""
Admin configuration for billing app.
"""

from django.contrib import admin

from .models import (
    CoursePurchase,
    Dispute,
    InstitutionBillingConfig,
    InstitutionPlan,
    Invoice,
    PaymentMethod,
    RefundRecord,
    StripeEvent,
    Subscription,
)


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = [
        "stripe_dispute_id", "status", "reason", "amount_cents",
        "evidence_due_by", "registration", "created_at",
    ]
    list_filter = ["status", "reason"]
    search_fields = [
        "stripe_dispute_id", "stripe_charge_id", "stripe_payment_intent_id",
    ]
    readonly_fields = [
        "stripe_dispute_id", "stripe_charge_id", "stripe_payment_intent_id",
        "registration", "course_purchase", "raw_payload", "created_at", "updated_at",
    ]
    ordering = ["-created_at", "evidence_due_by"]

    def has_add_permission(self, request):
        return False


@admin.register(StripeEvent)
class StripeEventAdmin(admin.ModelAdmin):
    list_display = ["event_id", "event_type", "received_at", "processed_at", "error_short"]
    list_filter = ["event_type", "processed_at"]
    search_fields = ["event_id", "event_type"]
    readonly_fields = ["event_id", "event_type", "payload", "received_at", "processed_at", "error"]
    ordering = ["-received_at"]

    def error_short(self, obj):
        return (obj.error or "")[:60]
    error_short.short_description = "Error"

    def has_add_permission(self, request):
        return False


@admin.register(InstitutionBillingConfig)
class InstitutionBillingConfigAdmin(admin.ModelAdmin):
    list_display = ["pricing_model", "default_currency", "tax_enabled", "is_stripe_configured"]
    readonly_fields = ["uuid", "created_at", "updated_at"]

    def is_stripe_configured(self, obj):
        return obj.is_stripe_configured
    is_stripe_configured.boolean = True

    def has_add_permission(self, request):
        # Only one config row allowed
        return not InstitutionBillingConfig.objects.exists()


@admin.register(InstitutionPlan)
class InstitutionPlanAdmin(admin.ModelAdmin):
    list_display = ["name", "price_display", "billing_interval", "is_active", "is_featured", "includes_all_courses"]
    list_filter = ["is_active", "billing_interval", "includes_all_courses"]
    search_fields = ["name"]
    readonly_fields = ["uuid", "created_at", "updated_at"]
    filter_horizontal = ["included_courses"]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "plan_name", "status", "current_period_end"]
    list_filter = ["status"]
    search_fields = ["user__email", "stripe_subscription_id"]
    readonly_fields = ["uuid", "stripe_subscription_id", "stripe_customer_id", "created_at", "updated_at"]
    raw_id_fields = ["user", "institution_plan"]

    def plan_name(self, obj):
        return obj.plan_name or "—"
    plan_name.short_description = "Plan"


@admin.register(CoursePurchase)
class CoursePurchaseAdmin(admin.ModelAdmin):
    list_display = ["user", "course", "event", "amount_cents", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["user__email"]
    raw_id_fields = ["user", "course", "event"]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["stripe_invoice_id", "user", "amount_display", "status", "paid_at"]
    list_filter = ["status", "currency"]
    search_fields = ["user__email", "stripe_invoice_id"]
    readonly_fields = ["uuid", "stripe_invoice_id", "created_at", "updated_at"]


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ["user", "card_brand", "card_last4", "is_default"]
    list_filter = ["card_brand", "is_default"]
    search_fields = ["user__email"]
    readonly_fields = ["uuid", "stripe_payment_method_id", "created_at", "updated_at"]


@admin.register(RefundRecord)
class RefundRecordAdmin(admin.ModelAdmin):
    list_display = ["stripe_refund_id", "amount_display", "status", "reason", "created_at"]
    list_filter = ["status", "reason"]
    search_fields = ["stripe_refund_id", "stripe_payment_intent_id"]
    readonly_fields = ["uuid", "created_at", "updated_at"]
