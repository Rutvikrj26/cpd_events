"""
Admin configuration for billing app.
"""

from django.contrib import admin

from .models import (
    CoursePurchase,
    Dispute,
    PaymentMethod,
    RefundRecord,
    StripeEvent,
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


@admin.register(CoursePurchase)
class CoursePurchaseAdmin(admin.ModelAdmin):
    list_display = ["user", "course", "event", "amount_cents", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["user__email"]
    raw_id_fields = ["user", "course", "event"]


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
