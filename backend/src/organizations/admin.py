"""
Django admin configuration for Organizations app.
"""

import logging

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import path
from django.utils import timezone
from django.utils.text import slugify

from .models import Organization, OrganizationMembership, OrganizationSubscription

logger = logging.getLogger(__name__)
User = get_user_model()


class ProvisionOrganizationForm(forms.Form):
    """Form for provisioning an organization with admin user."""

    organization_name = forms.CharField(
        max_length=200,
        label="Organization Name",
        help_text="Public name of the organization",
    )
    admin_email = forms.EmailField(
        label="Admin Email",
        help_text="Email address for the organization admin. Must not already exist.",
    )
    admin_name = forms.CharField(
        max_length=200,
        label="Admin Full Name",
    )

    def clean_admin_email(self):
        """Validate admin email is unique."""
        email = self.cleaned_data['admin_email'].lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean_organization_name(self):
        """Validate organization name generates unique slug."""
        name = self.cleaned_data['organization_name'].strip()
        slug = slugify(name)
        if not slug:
            raise forms.ValidationError("Organization name must contain valid characters.")
        if Organization.objects.filter(slug=slug).exists():
            raise forms.ValidationError(
                f"An organization with this name (slug: {slug}) already exists."
            )
        return name




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

    def get_urls(self):
        """Add custom provision URL."""
        urls = super().get_urls()
        custom_urls = [
            path(
                'provision/',
                self.admin_site.admin_view(self.provision_organization_view),
                name='organizations_organization_provision',
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        """Add provision button to changelist."""
        extra_context = extra_context or {}
        extra_context['show_provision_button'] = True
        return super().changelist_view(request, extra_context=extra_context)

    def provision_organization_view(self, request):
        """
        Custom admin view to provision an organization with admin user.

        Creates:
        - User account (organizer, unverified)
        - Organization
        - OrganizationMembership (admin role)
        - OrganizationSubscription (auto via signal)
        - Sends verification email
        """
        if request.method == 'POST':
            form = ProvisionOrganizationForm(request.POST)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        # 1. Create user with random password
                        email = form.cleaned_data['admin_email']
                        name = form.cleaned_data['admin_name']
                        org_name = form.cleaned_data['organization_name']

                        user = User.objects.create_user(
                            email=email,
                            password=User.objects.make_random_password(20),
                            full_name=name,
                            account_type='organizer',
                            email_verified=False,
                        )

                        # 2. Create organization
                        org = Organization.objects.create(
                            name=org_name,
                            slug=slugify(org_name),
                            created_by=user,
                            onboarding_completed=False,
                        )
                        # Signal auto-creates OrganizationSubscription

                        # 3. Create admin membership
                        OrganizationMembership.objects.create(
                            organization=org,
                            user=user,
                            role='admin',
                            is_active=True,
                            accepted_at=timezone.now(),
                        )

                        # 4. Generate verification token
                        verification_token = user.generate_email_verification_token()

                        # 5. Generate password reset token
                        password_token = user.generate_password_reset_token()

                        # 6. Send combined email
                        setup_url = (
                            f"{settings.FRONTEND_URL}/auth/verify-email"
                            f"?token={verification_token}"
                            f"&password_token={password_token}"
                        )

                        # Log URL for debugging
                        logger.info(f"Provisioned org '{org.name}' for {email}")
                        logger.info(f"Setup URL: {setup_url}")

                        send_mail(
                            subject=f"Welcome to {org.name} on Accredit",
                            message=(
                                f"Hi {name},\n\n"
                                f"Your organization '{org.name}' has been created on Accredit.\n\n"
                                f"Please click the following link to verify your email and set your password:\n"
                                f"{setup_url}\n\n"
                                f"This link will expire in 24 hours.\n\n"
                                f"Best regards,\nThe Accredit Team"
                            ),
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[email],
                            fail_silently=False,
                        )

                    messages.success(
                        request,
                        f"Organization '{org.name}' provisioned successfully. "
                        f"Verification email sent to {email}."
                    )
                    return redirect('admin:organizations_organization_changelist')

                except Exception as e:
                    logger.exception(f"Failed to provision organization: {e}")
                    messages.error(request, f"Failed to provision organization: {e}")
        else:
            form = ProvisionOrganizationForm()

        context = {
            **self.admin_site.each_context(request),
            'form': form,
            'title': 'Provision New Organization',
            'opts': self.model._meta,
        }
        return render(request, 'admin/organizations/provision_form.html', context)


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
