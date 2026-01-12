"""
Promo Codes admin configuration.
"""

from django.contrib import admin

from .models import PromoCode, PromoCodeUsage


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = [
        'code',
        'owner',
        'discount_display',
        'is_active',
        'current_uses',
        'max_uses',
        'valid_until',
        'created_at',
    ]
    list_filter = ['is_active', 'discount_type', 'first_time_only']
    search_fields = ['code', 'description', 'owner__email']
    readonly_fields = ['uuid', 'current_uses', 'created_at', 'updated_at']
    raw_id_fields = ['owner', 'organization']
    filter_horizontal = ['events']

    def discount_display(self, obj):
        return obj.get_discount_display()

    discount_display.short_description = 'Discount'


@admin.register(PromoCodeUsage)
class PromoCodeUsageAdmin(admin.ModelAdmin):
    list_display = [
        'promo_code',
        'user_email',
        'original_price',
        'discount_amount',
        'final_price',
        'created_at',
    ]
    list_filter = ['promo_code__code']
    search_fields = ['user_email', 'promo_code__code']
    readonly_fields = ['uuid', 'created_at', 'updated_at']
    raw_id_fields = ['promo_code', 'registration', 'user']
