"""
Organizations app models.

Models:
- Organization: Enterprise entity that owns events, courses, and templates
- OrganizationMembership: Links users to organizations with roles
- OrganizationSubscription: Per-seat billing for organizations
"""

import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from common.config import OrganizationPlanLimits
from common.models import BaseModel, SoftDeleteModel


def generate_invitation_token():
    """Generate a secure invitation token."""
    return secrets.token_urlsafe(32)


class Organization(SoftDeleteModel):
    """
    Enterprise organization that owns events, courses, and templates.

    Organizations provide a home for multiple organizers (team members)
    to collaborate on events and courses. Individual organizers can
    link their accounts to an organization.

    Key Features:
    - Multi-user team management with role-based permissions
    - Branding (logo, colors, website)
    - Per-seat subscription billing
    - Ownership of events, courses, and certificate templates
    """

    # Identity
    name = models.CharField(max_length=255, help_text="Organization display name")
    slug = models.SlugField(
        max_length=100, unique=True, db_index=True, help_text="URL-friendly identifier"
    )
    description = models.TextField(blank=True, max_length=2000, help_text="About this organization")

    # Branding
    logo = models.ImageField(
        upload_to='organizations/logos/', null=True, blank=True, help_text="Organization logo"
    )
    logo_url = models.URLField(blank=True, help_text="External logo URL (if not uploaded)")
    website = models.URLField(blank=True, help_text="Organization website")
    primary_color = models.CharField(
        max_length=7, default='#0066CC', help_text="Primary brand color (hex)"
    )
    secondary_color = models.CharField(
        max_length=7, default='#004499', help_text="Secondary brand color (hex)"
    )

    # Contact
    contact_email = models.EmailField(blank=True, help_text="Public contact email")
    contact_phone = models.CharField(max_length=20, blank=True, help_text="Public contact phone")

    # Status
    is_active = models.BooleanField(default=True, help_text="Whether organization is active")
    is_verified = models.BooleanField(default=False, help_text="Whether organization is verified")

    # Audit
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_organizations',
        help_text="User who created this organization",
    )

    # =========================================
    # Stripe Connect
    # =========================================
    stripe_connect_id = models.CharField(max_length=255, blank=True, null=True, help_text="Stripe Connect Account ID")
    stripe_account_status = models.CharField(max_length=50, default='pending', help_text="Connect account status")
    stripe_charges_enabled = models.BooleanField(default=False, help_text="Whether account can accept payments")

    # Denormalized counts (updated via signals/methods)
    members_count = models.PositiveIntegerField(default=0, help_text="Number of active members")
    events_count = models.PositiveIntegerField(default=0, help_text="Number of events")
    courses_count = models.PositiveIntegerField(default=0, help_text="Number of courses")

    class Meta:
        db_table = 'organizations'
        verbose_name = 'Organization'
        verbose_name_plural = 'Organizations'
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_by']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Auto-generate slug if not provided."""
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure uniqueness
            original_slug = self.slug
            counter = 1
            while Organization.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    @property
    def effective_logo_url(self):
        """Get logo URL, preferring uploaded file over external URL."""
        if self.logo:
            return self.logo.url
        return self.logo_url or ''

    def update_counts(self):
        """Update denormalized counts from related objects."""
        self.members_count = self.memberships.filter(is_active=True).count()
        # Events and courses counts will be updated once those FKs are added
        self.save(update_fields=['members_count', 'events_count', 'courses_count', 'updated_at'])

    def get_owners(self):
        """Get all owners of this organization."""
        return [m.user for m in self.memberships.filter(role='owner', is_active=True)]

    def get_admins(self):
        """Get all admins of this organization."""
        return [m.user for m in self.memberships.filter(role__in=['owner', 'admin'], is_active=True)]


class OrganizationMembership(BaseModel):
    """
    Links users to organizations with role-based permissions.

    Roles (in order of permission level):
    - owner: Full control, billing, can delete org
    - admin: Manage members, events, courses, templates
    - manager: Create/edit events & courses
    - member: View only, complete assigned tasks

    Individual organizers can be "linked" to an organization while
    maintaining their individual accounts. The membership tracks this link.
    """

    class Role(models.TextChoices):
        OWNER = 'owner', 'Owner'
        ADMIN = 'admin', 'Admin'
        MANAGER = 'manager', 'Manager'
        MEMBER = 'member', 'Member'

    # Relationships
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='memberships'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organization_memberships'
    )

    # Role
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.MEMBER, help_text="Role within organization"
    )
    title = models.CharField(
        max_length=100, blank=True, help_text="Job title in organization (e.g., Training Manager)"
    )

    # Status
    is_active = models.BooleanField(default=True, help_text="Whether membership is active")

    # Invitation tracking
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_org_invites',
    )
    invited_at = models.DateTimeField(null=True, blank=True, help_text="When invitation was sent")
    accepted_at = models.DateTimeField(null=True, blank=True, help_text="When invitation was accepted")
    invitation_token = models.CharField(
        max_length=64, blank=True, db_index=True, help_text="Token for accepting invitation"
    )
    invitation_email = models.EmailField(
        blank=True, help_text="Email address invitation was sent to"
    )

    # Linking metadata - tracks if this user was linked from individual organizer
    linked_from_individual = models.BooleanField(
        default=False, help_text="Whether user was linked from individual organizer account"
    )
    linked_at = models.DateTimeField(
        null=True, blank=True, help_text="When user's data was linked to organization"
    )

    class Meta:
        db_table = 'organization_memberships'
        verbose_name = 'Organization Membership'
        verbose_name_plural = 'Organization Memberships'
        unique_together = ['organization', 'user']
        indexes = [
            models.Index(fields=['organization', 'role']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['invitation_token']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.organization.name} ({self.role})"

    @property
    def is_organizer_role(self):
        """Check if role has organizer-level permissions (counts toward billing)."""
        return self.role in [self.Role.OWNER, self.Role.ADMIN, self.Role.MANAGER]

    @property
    def is_pending(self):
        """Check if invitation is pending (not yet accepted)."""
        return self.invitation_token and not self.accepted_at

    def generate_invitation_token(self):
        """Generate a new invitation token."""
        self.invitation_token = generate_invitation_token()
        self.invited_at = timezone.now()
        self.save(update_fields=['invitation_token', 'invited_at', 'updated_at'])
        return self.invitation_token

    def accept_invitation(self):
        """Accept the invitation and activate membership."""
        if self.invitation_token:
            self.accepted_at = timezone.now()
            self.invitation_token = ''
            self.is_active = True
            self.save(update_fields=['accepted_at', 'invitation_token', 'is_active', 'updated_at'])

    def deactivate(self):
        """Deactivate this membership."""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])

    def reactivate(self):
        """Reactivate this membership."""
        self.is_active = True
        self.save(update_fields=['is_active', 'updated_at'])


class OrganizationSubscription(BaseModel):
    """
    Billing subscription for an organization with per-seat pricing.

    Billing Model:
    - Free tier: 1 organizer seat, limited features
    - Team: 3 included seats, $15/additional seat
    - Business: 10 included seats, $12/additional seat
    - Enterprise: Custom seats and pricing

    Only organizer roles (owner, admin, manager) count toward billable seats.
    Member role is free and unlimited.
    """

    class Plan(models.TextChoices):
        FREE = 'free', 'Free'
        TEAM = 'team', 'Team'
        BUSINESS = 'business', 'Business'
        ENTERPRISE = 'enterprise', 'Enterprise'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        TRIALING = 'trialing', 'Trialing'
        PAST_DUE = 'past_due', 'Past Due'
        CANCELED = 'canceled', 'Canceled'
        UNPAID = 'unpaid', 'Unpaid'

    # Relationship
    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name='subscription'
    )

    # Plan
    plan = models.CharField(max_length=20, choices=Plan.choices, default=Plan.FREE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    # Seat management
    included_seats = models.PositiveIntegerField(default=1, help_text="Seats included in base plan")
    additional_seats = models.PositiveIntegerField(default=0, help_text="Extra seats purchased")
    seat_price_cents = models.PositiveIntegerField(
        default=0, help_text="Price per additional seat in cents"
    )

    # Usage (computed from memberships)
    active_organizer_seats = models.PositiveIntegerField(
        default=1, help_text="Current organizer seats in use"
    )

    # Stripe integration
    stripe_subscription_id = models.CharField(
        max_length=255, blank=True, null=True, unique=True, db_index=True
    )
    stripe_customer_id = models.CharField(max_length=255, blank=True, db_index=True)

    # Billing period
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)

    # Trial
    trial_ends_at = models.DateTimeField(null=True, blank=True)

    # Cancellation
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)

    # Usage tracking
    events_created_this_period = models.PositiveIntegerField(default=0)
    courses_created_this_period = models.PositiveIntegerField(default=0)

    # Plan configuration (imported from common.config.billing)
    PLAN_CONFIG = {
        Plan.FREE: OrganizationPlanLimits.FREE,
        Plan.TEAM: OrganizationPlanLimits.TEAM,
        Plan.BUSINESS: OrganizationPlanLimits.BUSINESS,
        Plan.ENTERPRISE: OrganizationPlanLimits.ENTERPRISE,
    }

    class Meta:
        db_table = 'organization_subscriptions'
        verbose_name = 'Organization Subscription'
        verbose_name_plural = 'Organization Subscriptions'
        indexes = [
            models.Index(fields=['plan']),
            models.Index(fields=['status']),
            models.Index(fields=['current_period_end']),
        ]

    def __str__(self):
        return f"{self.organization.name} - {self.plan} ({self.status})"

    @property
    def config(self):
        """Get configuration for current plan."""
        return self.PLAN_CONFIG.get(self.plan, self.PLAN_CONFIG[self.Plan.FREE])

    @property
    def total_seats(self):
        """Total available organizer seats."""
        return self.included_seats + self.additional_seats

    @property
    def available_seats(self):
        """Remaining organizer seats."""
        return max(0, self.total_seats - self.active_organizer_seats)

    @property
    def is_active(self):
        """Check if subscription allows usage."""
        return self.status in [self.Status.ACTIVE, self.Status.TRIALING]

    def can_add_organizer(self):
        """Check if organization can add another organizer seat."""
        return self.available_seats > 0

    def update_seat_usage(self):
        """Update active organizer seat count from memberships."""
        organizer_roles = [
            OrganizationMembership.Role.OWNER,
            OrganizationMembership.Role.ADMIN,
            OrganizationMembership.Role.MANAGER,
        ]
        self.active_organizer_seats = self.organization.memberships.filter(
            role__in=organizer_roles, is_active=True
        ).count()
        self.save(update_fields=['active_organizer_seats', 'updated_at'])

    def check_event_limit(self):
        """Check if organization can create more events this period."""
        limit = self.config['events_per_month']
        if limit is None:
            return True
        return self.events_created_this_period < limit

    def check_course_limit(self):
        """Check if organization can create more courses this period."""
        limit = self.config['courses_per_month']
        if limit is None:
            return True
        return self.courses_created_this_period < limit

    def increment_events(self, count=1):
        """Increment event counter."""
        self.events_created_this_period += count
        self.save(update_fields=['events_created_this_period', 'updated_at'])

    def increment_courses(self, count=1):
        """Increment course counter."""
        self.courses_created_this_period += count
        self.save(update_fields=['courses_created_this_period', 'updated_at'])

    def reset_usage(self):
        """Reset usage counters for new period."""
        self.events_created_this_period = 0
        self.courses_created_this_period = 0
        self.save(update_fields=['events_created_this_period', 'courses_created_this_period', 'updated_at'])

    @classmethod
    def create_for_organization(cls, organization, plan=None):
        """Create a new subscription for an organization."""
        if plan is None:
            plan = cls.Plan.FREE

        config = cls.PLAN_CONFIG.get(plan, cls.PLAN_CONFIG[cls.Plan.FREE])

        subscription, created = cls.objects.get_or_create(
            organization=organization,
            defaults={
                'plan': plan,
                'status': cls.Status.ACTIVE,
                'included_seats': config['included_seats'],
                'seat_price_cents': config['seat_price_cents'],
                'current_period_start': timezone.now(),
            },
        )
        return subscription
