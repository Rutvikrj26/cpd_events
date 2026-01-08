"""
DRF Serializers for Organizations app.
"""

from rest_framework import serializers

from .models import Organization, OrganizationMembership, OrganizationSubscription


class OrganizationListSerializer(serializers.ModelSerializer):
    """Serializer for listing organizations (minimal data)."""

    user_role = serializers.SerializerMethodField()
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            'uuid',
            'name',
            'slug',
            'logo_url',
            'is_active',
            'is_verified',
            'members_count',
            'events_count',
            'user_role',
        ]
        read_only_fields = fields

    def get_user_role(self, obj):
        """Get the current user's role in this organization."""
        user = self.context.get('request')
        if not user:
            return None
        user = user.user
        try:
            membership = obj.memberships.get(user=user, is_active=True)
            return membership.role
        except OrganizationMembership.DoesNotExist:
            return None

    def get_logo_url(self, obj):
        """Get effective logo URL."""
        return obj.effective_logo_url


class OrganizationDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed organization view."""

    logo_url = serializers.SerializerMethodField()
    user_role = serializers.SerializerMethodField()
    subscription = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = Organization
        fields = [
            'uuid',
            'name',
            'slug',
            'description',
            'logo_url',
            'website',
            'primary_color',
            'secondary_color',
            'contact_email',
            'contact_phone',
            'gst_hst_number',
            'is_active',
            'is_verified',
            'members_count',
            'events_count',
            'courses_count',
            'user_role',
            'subscription',
            'created_by_name',
            'created_at',
            'updated_at',
            'stripe_connect_id',
            'stripe_account_status',
            'stripe_charges_enabled',
        ]
        read_only_fields = [
            'uuid',
            'slug',
            'is_verified',
            'members_count',
            'events_count',
            'courses_count',
            'user_role',
            'subscription',
            'created_by_name',
            'created_at',
            'updated_at',
            'stripe_connect_id',
            'stripe_account_status',
            'stripe_charges_enabled',
        ]

    def get_logo_url(self, obj):
        return obj.effective_logo_url

    def get_user_role(self, obj):
        user = self.context.get('request')
        if not user:
            return None
        user = user.user
        try:
            membership = obj.memberships.get(user=user, is_active=True)
            return membership.role
        except OrganizationMembership.DoesNotExist:
            return None

    def get_subscription(self, obj):
        if hasattr(obj, 'subscription'):
            return OrganizationSubscriptionSerializer(obj.subscription).data
        return None


class OrganizationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new organization."""

    class Meta:
        model = Organization
        fields = [
            'name',
            'description',
            'logo_url',
            'website',
            'primary_color',
            'contact_email',
            'gst_hst_number',
        ]

    def create(self, validated_data):
        """Create organization with current user as admin (subscriber)."""
        user = self.context['request'].user

        # Create organization
        organization = Organization.objects.create(
            created_by=user,
            **validated_data,
        )

        # Create admin membership (the organization plan subscriber)
        # Admin has full capabilities: can create courses AND events
        OrganizationMembership.objects.create(
            organization=organization,
            user=user,
            role=OrganizationMembership.Role.ADMIN,
            accepted_at=__import__('django.utils.timezone', fromlist=['now']).now(),
        )

        # Create FREE subscription (by default)
        OrganizationSubscription.create_for_organization(organization)

        # Update counts
        organization.update_counts()

        return organization


class OrganizationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating an organization."""

    class Meta:
        model = Organization
        fields = [
            'name',
            'description',
            'logo_url',
            'website',
            'primary_color',
            'secondary_color',
            'contact_email',
            'contact_phone',
            'gst_hst_number',
        ]


# =============================================================================
# Membership Serializers
# =============================================================================

class OrganizationMembershipListSerializer(serializers.ModelSerializer):
    """Serializer for listing organization members."""

    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_uuid = serializers.UUIDField(source='user.uuid', read_only=True)
    invited_by_name = serializers.CharField(source='invited_by.full_name', read_only=True)
    linked_subscription_uuid = serializers.UUIDField(source='linked_subscription.uuid', read_only=True)

    class Meta:
        model = OrganizationMembership
        fields = [
            'uuid',
            'user_uuid',
            'user_email',
            'user_name',
            'role',
            'title',
            'is_active',
            'accepted_at',
            'linked_from_individual',
            'invited_by_name',
            'created_at',
            # Organizer billing fields
            'organizer_billing_payer',
            'linked_subscription_uuid',
        ]
        read_only_fields = fields


class OrganizationMembershipInviteSerializer(serializers.Serializer):
    """Serializer for inviting a new member."""

    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=OrganizationMembership.Role.choices,
        default=OrganizationMembership.Role.INSTRUCTOR,
    )
    title = serializers.CharField(max_length=100, required=False, allow_blank=True)
    billing_payer = serializers.ChoiceField(
        choices=['organization', 'organizer'],
        required=False,
        help_text="Who pays for organizer subscription (only for organizer role)",
    )

    def validate(self, attrs):
        """Validate that billing_payer is only provided for organizer role."""
        role = attrs.get('role')
        billing_payer = attrs.get('billing_payer')

        if role == OrganizationMembership.Role.ORGANIZER and not billing_payer:
            raise serializers.ValidationError({
                'billing_payer': 'billing_payer is required for organizer role'
            })

        if role != OrganizationMembership.Role.ORGANIZER and billing_payer:
            raise serializers.ValidationError({
                'billing_payer': 'billing_payer can only be set for organizer role'
            })

        return attrs


class OrganizationMembershipUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a membership (role, title)."""

    class Meta:
        model = OrganizationMembership
        fields = ['role', 'title']


class LinkOrganizerSerializer(serializers.Serializer):
    """Serializer for linking an individual organizer to an organization."""

    organizer_email = serializers.EmailField(
        required=False,
        help_text="Email of organizer to link (optional, for inviting)",
    )
    role = serializers.ChoiceField(
        choices=OrganizationMembership.Role.choices,
        default=OrganizationMembership.Role.ORGANIZER,
    )
    transfer_data = serializers.BooleanField(
        default=True,
        help_text="Whether to transfer the organizer's events and templates",
    )


class CreateOrgFromAccountSerializer(serializers.Serializer):
    """Serializer for creating an organization from current organizer account."""

    name = serializers.CharField(max_length=255, required=False)
    slug = serializers.SlugField(max_length=100, required=False)
    transfer_data = serializers.BooleanField(
        default=True,
        help_text="Whether to transfer existing events and templates to the new organization",
    )


# =============================================================================
# Subscription Serializers
# =============================================================================

class OrganizationSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for organization subscription details."""

    total_seats = serializers.IntegerField(read_only=True)
    available_seats = serializers.IntegerField(read_only=True)
    org_paid_organizers_count = serializers.IntegerField(read_only=True)
    plan_display = serializers.CharField(source='get_plan_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = OrganizationSubscription
        fields = [
            'plan',
            'plan_display',
            'status',
            'status_display',
            'included_seats',
            'additional_seats',
            'total_seats',
            'active_organizer_seats',
            'available_seats',
            'seat_price_cents',
            'org_paid_organizers_count',
            'events_created_this_period',
            'courses_created_this_period',
            'current_period_start',
            'current_period_end',
            'trial_ends_at',
        ]
        read_only_fields = fields
