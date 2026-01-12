"""
Django admin configuration for Organizations app.
"""

from django.contrib import admin

from .models import Organization, OrganizationMembership, OrganizationSubscription


class OrganizationMembershipInline(admin.TabularInline):
    """Inline admin for organization memberships."""

    model = OrganizationMembership
    extra = 0
    fields = ['user', 'role', 'title', 'is_active', 'accepted_at', 'linked_from_individual']
    readonly_fields = ['accepted_at']
    raw_id_fields = ['user']


class OrganizationSubscriptionInline(admin.StackedInline):
    """Inline admin for organization subscription."""

    model = OrganizationSubscription
    extra = 0
    fields = [
        'plan',
        'status',
        ('included_seats', 'additional_seats', 'active_organizer_seats'),
        ('current_period_start', 'current_period_end', 'trial_ends_at'),
        'stripe_subscription_id',
        'stripe_customer_id',
    ]
    readonly_fields = ['active_organizer_seats']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """Admin for Organization model."""

    list_display = ['name', 'slug', 'is_active', 'is_verified', 'members_count', 'events_count', 'created_at']
    list_filter = ['is_active', 'is_verified', 'created_at']
    search_fields = ['name', 'slug', 'description']
    readonly_fields = ['uuid', 'created_at', 'updated_at', 'members_count', 'events_count', 'courses_count']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [OrganizationMembershipInline, OrganizationSubscriptionInline]

    fieldsets = [
        (
            'Identity',
            {
                'fields': ['name', 'slug', 'description', 'uuid'],
            },
        ),
        (
            'Branding',
            {
                'fields': ['logo', 'logo_url', 'website', 'primary_color', 'secondary_color'],
            },
        ),
        (
            'Contact',
            {
                'fields': ['contact_email', 'contact_phone'],
            },
        ),
        (
            'Status',
            {
                'fields': ['is_active', 'is_verified', 'created_by'],
            },
        ),
        (
            'Stats',
            {
                'fields': ['members_count', 'events_count', 'courses_count'],
                'classes': ['collapse'],
            },
        ),
        (
            'Timestamps',
            {
                'fields': ['created_at', 'updated_at'],
                'classes': ['collapse'],
            },
        ),
    ]


@admin.register(OrganizationMembership)
class OrganizationMembershipAdmin(admin.ModelAdmin):
    """Admin for OrganizationMembership model."""

    list_display = ['user', 'organization', 'role', 'is_active', 'is_pending', 'linked_from_individual', 'created_at']
    list_filter = ['role', 'is_active', 'linked_from_individual', 'created_at']
    search_fields = ['user__email', 'user__full_name', 'organization__name']
    readonly_fields = ['uuid', 'created_at', 'updated_at', 'is_pending']
    raw_id_fields = ['user', 'organization', 'invited_by']

    fieldsets = [
        (
            'Membership',
            {
                'fields': ['organization', 'user', 'role', 'title', 'is_active'],
            },
        ),
        (
            'Invitation',
            {
                'fields': ['invited_by', 'invited_at', 'accepted_at', 'invitation_token', 'invitation_email', 'is_pending'],
                'classes': ['collapse'],
            },
        ),
        (
            'Linking',
            {
                'fields': ['linked_from_individual', 'linked_at'],
                'classes': ['collapse'],
            },
        ),
        (
            'Metadata',
            {
                'fields': ['uuid', 'created_at', 'updated_at'],
                'classes': ['collapse'],
            },
        ),
    ]

    @admin.display(boolean=True, description='Pending')
    def is_pending(self, obj):
        """Display pending status."""
        return obj.is_pending


@admin.register(OrganizationSubscription)
class OrganizationSubscriptionAdmin(admin.ModelAdmin):
    """Admin for OrganizationSubscription model."""

    list_display = [
        'organization',
        'plan',
        'status',
        'is_trialing',
        'active_organizer_seats',
        'total_seats',
        'current_period_end',
    ]
    list_filter = ['plan', 'status', 'created_at']
    search_fields = ['organization__name', 'stripe_subscription_id', 'stripe_customer_id']
    readonly_fields = ['uuid', 'created_at', 'updated_at', 'active_organizer_seats', 'total_seats', 'available_seats']
    raw_id_fields = ['organization']

    fieldsets = [
        (
            'Organization',
            {
                'fields': ['organization'],
            },
        ),
        (
            'Plan',
            {
                'fields': ['plan', 'status'],
            },
        ),
        (
            'Seats',
            {
                'fields': [
                    'included_seats',
                    'additional_seats',
                    'seat_price_cents',
                    'active_organizer_seats',
                    'total_seats',
                    'available_seats',
                ],
            },
        ),
        (
            'Billing Period',
            {
                'fields': ['current_period_start', 'current_period_end', 'trial_ends_at'],
            },
        ),
        (
            'Stripe',
            {
                'fields': ['stripe_subscription_id', 'stripe_customer_id'],
                'classes': ['collapse'],
            },
        ),
        (
            'Cancellation',
            {
                'fields': ['cancel_at_period_end', 'canceled_at', 'cancellation_reason'],
                'classes': ['collapse'],
            },
        ),
        (
            'Usage',
            {
                'fields': ['events_created_this_period', 'courses_created_this_period'],
                'classes': ['collapse'],
            },
        ),
        (
            'Metadata',
            {
                'fields': ['uuid', 'created_at', 'updated_at'],
                'classes': ['collapse'],
            },
        ),
    ]

    @admin.display(description='Total Seats')
    def total_seats(self, obj):
        """Display total seats."""
        return obj.total_seats

    @admin.display(description='Available')
    def available_seats(self, obj):
        """Display available seats."""
        return obj.available_seats

    @admin.display(boolean=True, description='Trialing')
    def is_trialing(self, obj):
        return obj.is_trialing
