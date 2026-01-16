"""
Admin configuration for billing app.
"""

from django.contrib import admin, messages

from .models import DisputeRecord, Invoice, PaymentMethod, StripePrice, StripeProduct, Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Admin for Subscription model."""

    list_display = [
        'user',
        'plan',
        'status',
        'billing_interval',
        'current_period_end',
        'events_created_this_period',
        'certificates_issued_this_period',
        'last_usage_reset_at',
    ]
    list_filter = ['plan', 'status', 'cancel_at_period_end']
    search_fields = ['user__email', 'stripe_subscription_id', 'stripe_customer_id']
    readonly_fields = ['uuid', 'stripe_subscription_id', 'stripe_customer_id', 'created_at', 'updated_at']

    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('Plan Details', {'fields': ('plan', 'status', 'billing_interval')}),
        (
            'Pending Change',
            {'fields': ('pending_plan', 'pending_billing_interval', 'pending_change_at'), 'classes': ('collapse',)},
        ),
        ('Stripe Integration', {'fields': ('stripe_subscription_id', 'stripe_customer_id'), 'classes': ('collapse',)}),
        ('Billing Period', {'fields': ('current_period_start', 'current_period_end', 'trial_ends_at')}),
        ('Cancellation', {'fields': ('cancel_at_period_end', 'canceled_at', 'cancellation_reason'), 'classes': ('collapse',)}),
        ('Usage', {'fields': ('events_created_this_period', 'certificates_issued_this_period', 'last_usage_reset_at')}),
        ('Metadata', {'fields': ('uuid', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def save_model(self, request, obj, form, change):
        """Override save to sync trial changes to Stripe."""
        super().save_model(request, obj, form, change)

        # Check if trial_ends_at changed
        if 'trial_ends_at' in form.changed_data:
            if obj.stripe_subscription_id and obj.trial_ends_at:
                from .services import StripeService

                service = StripeService()
                result = service.update_subscription_trial(obj.stripe_subscription_id, obj.trial_ends_at)

                if result['success']:
                    messages.success(request, f"✓ Trial end updated in Stripe for {obj.user.email}")
                else:
                    messages.error(request, f"✗ Failed to sync trial end to Stripe: {result['error']}")
            elif 'trial_ends_at' in form.changed_data and not obj.trial_ends_at:
                # Handle trial removal if needed, or just log
                pass


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


@admin.register(StripeProduct)
class StripeProductAdmin(admin.ModelAdmin):
    """Admin for Stripe Products with auto-sync to Stripe."""

    list_display = [
        'name',
        'plan',
        'trial_period_days',
        'show_contact_sales',
        'is_active',
        'stripe_product_id',
        'created_at',
    ]
    list_filter = ['is_active', 'plan', 'show_contact_sales']
    search_fields = ['name', 'stripe_product_id', 'description']
    readonly_fields = ['uuid', 'stripe_product_id', 'created_at', 'updated_at']

    fieldsets = (
        ('Product Details', {'fields': ('name', 'description', 'plan', 'is_active')}),
        (
            'Pricing Display',
            {
                'fields': ('show_contact_sales',),
                'description': 'Check this to hide pricing and show "Contact Sales" button instead (for custom/enterprise plans)',
            },
        ),
        ('Trial Configuration', {'fields': ('trial_period_days',), 'description': 'Set trial period in days for this plan.'}),
        (
            'Feature Limits',
            {
                'fields': ('events_per_month', 'courses_per_month', 'certificates_per_month', 'max_attendees_per_event'),
                'description': 'Set feature limits for this plan (leave blank for unlimited). These limits affect both subscription enforcement and pricing page features display.',
            },
        ),
        (
            'Seat Configuration',
            {
                'fields': ('included_seats', 'seat_price_cents'),
                'description': 'Seat limits and pricing for organization plans.',
            },
        ),
        (
            'Stripe Integration',
            {
                'fields': ('stripe_product_id',),
                'classes': ('collapse',),
                'description': 'Stripe product ID is auto-populated when you save. Click "Sync to Stripe" to push updates.',
            },
        ),
        ('Metadata', {'fields': ('uuid', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    actions = ['sync_to_stripe_action']

    def save_model(self, request, obj, form, change):
        """Auto-sync to Stripe on save."""
        super().save_model(request, obj, form, change)

        result = obj.sync_to_stripe()
        if result['success']:
            if obj.stripe_product_id:
                messages.success(request, f"✓ Product synced to Stripe: {obj.stripe_product_id}")
            else:
                messages.success(request, "✓ Product created in Stripe")
        else:
            messages.error(request, f"✗ Failed to sync to Stripe: {result['error']}")

    @admin.action(description='Sync selected products to Stripe')
    def sync_to_stripe_action(self, request, queryset):
        """Bulk sync products to Stripe."""
        success_count = 0
        error_count = 0

        for product in queryset:
            result = product.sync_to_stripe()
            if result['success']:
                success_count += 1
            else:
                error_count += 1
                messages.error(request, f"{product.name}: {result['error']}")

        if success_count:
            messages.success(request, f"✓ Successfully synced {success_count} product(s)")
        if error_count:
            messages.warning(request, f"✗ Failed to sync {error_count} product(s)")


@admin.register(StripePrice)
class StripePriceAdmin(admin.ModelAdmin):
    """Admin for Stripe Prices with auto-sync to Stripe."""

    list_display = [
        'product',
        'amount_display_formatted',
        'billing_interval',
        'is_active',
        'stripe_price_id',
        'created_at',
    ]
    list_filter = ['is_active', 'billing_interval', 'product__plan']
    search_fields = ['product__name', 'stripe_price_id']
    readonly_fields = ['uuid', 'stripe_price_id', 'amount_display', 'created_at', 'updated_at']
    raw_id_fields = ['product']

    fieldsets = (
        (
            'Price Details',
            {
                'fields': ('product', 'amount_cents', 'currency', 'billing_interval', 'is_active'),
                'description': 'Amount in cents (e.g., 9900 = $99.00)',
            },
        ),
        ('Preview', {'fields': ('amount_display',), 'description': 'Read-only preview of the price'}),
        (
            'Stripe Integration',
            {
                'fields': ('stripe_price_id',),
                'classes': ('collapse',),
                'description': 'Stripe price ID is auto-populated when you save. Click "Sync to Stripe" to push updates.',
            },
        ),
        ('Metadata', {'fields': ('uuid', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    actions = ['sync_to_stripe_action']

    def amount_display_formatted(self, obj):
        """Display formatted price in list view."""
        return f"${obj.amount_display}"

    amount_display_formatted.short_description = 'Amount'

    def save_model(self, request, obj, form, change):
        """Auto-sync to Stripe on save."""
        super().save_model(request, obj, form, change)

        result = obj.sync_to_stripe()
        if result['success']:
            if obj.stripe_price_id:
                messages.success(request, f"✓ Price synced to Stripe: {obj.stripe_price_id}")
            else:
                messages.success(request, "✓ Price created in Stripe")
        else:
            messages.error(request, f"✗ Failed to sync to Stripe: {result['error']}")


@admin.register(DisputeRecord)
class DisputeRecordAdmin(admin.ModelAdmin):
    """Admin for DisputeRecord model."""

    list_display = ['stripe_dispute_id', 'status', 'amount_cents', 'currency', 'created_at']
    list_filter = ['status', 'currency']
    search_fields = ['stripe_dispute_id', 'stripe_charge_id', 'stripe_payment_intent_id']
    readonly_fields = ['uuid', 'stripe_dispute_id', 'created_at', 'updated_at']

    @admin.action(description='Sync selected prices to Stripe')
    def sync_to_stripe_action(self, request, queryset):
        """Bulk sync prices to Stripe."""
        success_count = 0
        error_count = 0

        for price in queryset:
            result = price.sync_to_stripe()
            if result['success']:
                success_count += 1
            else:
                error_count += 1
                messages.error(request, f"{price}: {result['error']}")

        if success_count:
            messages.success(request, f"✓ Successfully synced {success_count} price(s)")
        if error_count:
            messages.warning(request, f"✗ Failed to sync {error_count} price(s)")
