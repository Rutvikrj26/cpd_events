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
    gst_hst_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="GST/HST registration number for tax handling",
    )

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

    Roles:
    - admin: The organization plan subscriber (1 per org). Can create/manage courses AND events.
    - instructor: Course instructor (free, unlimited). Can manage course sessions.
    - organizer: Event organizer (requires organizer subscription). Can create/manage events.

    Organizer billing:
    - When adding an organizer, billing can be paid by organization OR organizer
    - If org pays: Creates organizer subscription as line item on org's Stripe subscription
    - If organizer pays: Links their existing organizer subscription to the organization
    """

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        INSTRUCTOR = 'instructor', 'Course Instructor'
        ORGANIZER = 'organizer', 'Organizer'

    # Relationships
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='memberships'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='organization_memberships',
        null=True,
        blank=True,
    )

    # Role
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.ORGANIZER, help_text="Role within organization"
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

    # Organizer billing (only for organizer role)
    organizer_billing_payer = models.CharField(
        max_length=20,
        choices=[
            ('organization', 'Organization Pays'),
            ('organizer', 'Organizer Pays'),
        ],
        null=True,
        blank=True,
        help_text="Who pays for organizer subscription (only for organizer role)",
    )
    linked_subscription = models.ForeignKey(
        'billing.Subscription',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='organization_memberships',
        help_text="Link to organizer's individual subscription if organizer pays",
    )
    stripe_subscription_item_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Stripe subscription item ID if org pays for organizer",
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
        """
        Check if role requires organizer subscription billing.

        Note: Admin is included in the $199 base plan, so doesn't count here.
        Only additional organizers require organizer subscription billing.
        """
        return self.role == self.Role.ORGANIZER

    @property
    def is_admin(self):
        """Check if this is the admin role (subscriber)."""
        return self.role == self.Role.ADMIN

    @property
    def can_create_courses(self):
        """Check if role can create courses."""
        return self.role == self.Role.ADMIN

    @property
    def can_manage_course_sessions(self):
        """Check if role can manage course sessions."""
        return self.role in [self.Role.ADMIN, self.Role.INSTRUCTOR]

    @property
    def can_create_events(self):
        """Check if role can create events."""
        return self.role in [self.Role.ADMIN, self.Role.ORGANIZER]

    @property
    def is_pending(self):
        """Check if invitation is pending (not yet accepted)."""
        return bool(self.invitation_token) and not self.accepted_at

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
    Billing subscription for an organization.

    Billing Model:
    - FREE: $0/month - Trial tier (2 events/mo, 1 course/mo, limited attendees)
    - ORGANIZATION: $199/month base - Full course platform + admin has organizer capabilities
      - 1 Admin included (can create courses AND events)
      - Unlimited Course Instructors (free)
      - Can add Organizers (requires separate organizer subscription - org-paid or self-paid)

    Note: Organizers added to the organization require their own organizer subscription ($99-$199/mo).
    The org can choose to pay for these subscriptions (added as line items) or the organizer pays themselves.
    """

    class Plan(models.TextChoices):
        FREE = 'free', 'Free'
        ORGANIZATION = 'organization', 'Organization'

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
        Plan.ORGANIZATION: OrganizationPlanLimits.ORGANIZATION,
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
        """
        Get configuration for current plan.
        Prioritizes database-driven configuration (StripeProduct) over hardcoded defaults.
        """
        # Try to get from StripeProduct (database source of truth)
        try:
            from billing.models import StripeProduct
            product = StripeProduct.objects.get(plan=self.plan, is_active=True)
            
            # Start with fallback limit structure
            config = self.PLAN_CONFIG.get(self.plan, self.PLAN_CONFIG[self.Plan.FREE]).copy()
            
            # Update with DB values if present
            feature_limits = product.get_feature_limits()
            for key, value in feature_limits.items():
                if value is not None: # Only override if value is set
                    config[key] = value
            
            # Update seat configuration
            if product.included_seats is not None:
                config['included_seats'] = product.included_seats
            
            if product.seat_price_cents is not None:
                config['seat_price_cents'] = product.seat_price_cents
                
            return config
            
        except (ImportError, Exception):
            # Fallback to hardcoded config
            return self.PLAN_CONFIG.get(self.plan, self.PLAN_CONFIG[self.Plan.FREE])

    @property
    def total_seats(self):
        """
        Total available organizer seats (legacy property).

        Note: In new model, this represents org-paid organizer slots, not total team size.
        Admin is included in base $199 plan. Course instructors are unlimited/free.
        """
        return self.included_seats + self.additional_seats

    @property
    def available_seats(self):
        """
        Remaining org-paid organizer slots (legacy property).

        Note: In new model, organizers can always be added (either org-paid or self-paid).
        This tracks only org-paid slots if any are configured.
        """
        return max(0, self.total_seats - self.active_organizer_seats)

    @property
    def is_active(self):
        """Check if subscription allows usage."""
        return self.status in [self.Status.ACTIVE, self.Status.TRIALING]

    @property
    def org_paid_organizers_count(self):
        """Count of organizers paid by the organization."""
        return self.organization.memberships.filter(
            role=OrganizationMembership.Role.ORGANIZER,
            organizer_billing_payer='organization',
            is_active=True
        ).count()

    def can_add_instructor(self):
        """Check if organization can add course instructor (always true, instructors are free)."""
        return True

    def can_add_organizer(self):
        """
        Check if organization can add another organizer.

        Always true - organizers can be added either as:
        - Org-paid (requires org to pay for organizer subscription)
        - Self-paid (organizer pays their own subscription)
        """
        return True

    def update_seat_usage(self):
        """
        Update active organizer seat count (for backward compatibility).

        In new model, tracks org-paid organizers only.
        """
        self.active_organizer_seats = self.org_paid_organizers_count
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
                'included_seats': config.get('included_seats', 1),  # Legacy field
                'seat_price_cents': config.get('seat_price_cents', 0),  # Legacy field
                'current_period_start': timezone.now(),
            },
        )
        return subscription
