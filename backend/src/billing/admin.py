"""
Admin configuration for billing app.
"""

from django.contrib import admin

from .models import Invoice, PaymentMethod, Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Admin for Subscription model."""

    list_display = [
        'user',
        'plan',
        'status',
        'current_period_end',
        'events_created_this_period',
        'certificates_issued_this_period',
    ]
    list_filter = ['plan', 'status', 'cancel_at_period_end']
    search_fields = ['user__email', 'stripe_subscription_id', 'stripe_customer_id']
    readonly_fields = ['uuid', 'stripe_subscription_id', 'stripe_customer_id', 'created_at', 'updated_at']

    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('Plan Details', {'fields': ('plan', 'status')}),
        ('Stripe Integration', {'fields': ('stripe_subscription_id', 'stripe_customer_id'), 'classes': ('collapse',)}),
        ('Billing Period', {'fields': ('current_period_start', 'current_period_end', 'trial_ends_at')}),
        ('Cancellation', {'fields': ('cancel_at_period_end', 'canceled_at', 'cancellation_reason'), 'classes': ('collapse',)}),
        ('Usage', {'fields': ('events_created_this_period', 'certificates_issued_this_period')}),
        ('Metadata', {'fields': ('uuid', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """Admin for Invoice model."""

    list_display = ['stripe_invoice_id', 'user', 'amount_display', 'status', 'paid_at']
    list_filter = ['status', 'currency']
    search_fields = ['user__email', 'stripe_invoice_id']
    readonly_fields = ['uuid', 'stripe_invoice_id', 'amount_display', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'

    def amount_display(self, obj):
        return obj.amount_display

    amount_display.short_description = 'Amount'


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    """Admin for PaymentMethod model."""

    list_display = ['user', 'card_brand', 'card_last4', 'is_default', 'is_expired']
    list_filter = ['card_brand', 'is_default']
    search_fields = ['user__email', 'stripe_payment_method_id']
    readonly_fields = ['uuid', 'stripe_payment_method_id', 'is_expired', 'created_at', 'updated_at']

    def is_expired(self, obj):
        return obj.is_expired

    is_expired.boolean = True
    is_expired.short_description = 'Expired'
