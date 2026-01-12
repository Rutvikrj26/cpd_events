"""
Contacts app serializers (M2, L1).

Field names match actual model fields:
- full_name
- professional_title
- organization_name
- events_invited_count
- events_attended_count
"""

from rest_framework import serializers

from common.serializers import BaseModelSerializer

from .models import Contact, ContactList, Tag

# =============================================================================
# Tag Serializers
# =============================================================================


class TagSerializer(BaseModelSerializer):
    """Tag with contact count and org info."""

    organization_uuid = serializers.UUIDField(source='organization.uuid', read_only=True, allow_null=True)
    is_shared = serializers.BooleanField(read_only=True)

    class Meta:
        model = Tag
        fields = [
            'uuid',
            'name',
            'color',
            'description',
            'contact_count',
            'organization_uuid',
            'is_shared',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['uuid', 'contact_count', 'organization_uuid', 'is_shared', 'created_at', 'updated_at']


class TagCreateSerializer(serializers.ModelSerializer):
    """Create/update a tag."""

    organization_uuid = serializers.UUIDField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = Tag
        fields = ['name', 'color', 'description', 'organization_uuid']

    def validate_organization_uuid(self, value):
        """Validate user has access to the organization."""
        if value:
            from organizations.models import Organization

            user_org_ids = self.context.get('user_org_ids', [])
            try:
                org = Organization.objects.get(uuid=value)
                if org.id not in user_org_ids:
                    raise serializers.ValidationError("You don't have access to this organization.")
                return org
            except Organization.DoesNotExist:
                raise serializers.ValidationError("Organization not found.")
        return None

    def create(self, validated_data):
        org = validated_data.pop('organization_uuid', None)
        if org:
            validated_data['organization'] = org
        return super().create(validated_data)


# =============================================================================
# Contact List Serializers (L1)
# =============================================================================


class ContactListSerializer(BaseModelSerializer):
    """Contact list with summary and org info."""

    organization_uuid = serializers.UUIDField(source='organization.uuid', read_only=True, allow_null=True)
    is_shared = serializers.BooleanField(read_only=True)

    class Meta:
        model = ContactList
        fields = [
            'uuid',
            'name',
            'description',
            'contact_count',
            'organization_uuid',
            'is_shared',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['uuid', 'contact_count', 'organization_uuid', 'is_shared', 'created_at', 'updated_at']


class ContactListDetailSerializer(BaseModelSerializer):
    """Full contact list detail with org info."""

    organization_uuid = serializers.UUIDField(source='organization.uuid', read_only=True, allow_null=True)
    is_shared = serializers.BooleanField(read_only=True)

    class Meta:
        model = ContactList
        fields = [
            'uuid',
            'name',
            'description',
            'contact_count',
            'organization_uuid',
            'is_shared',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['uuid', 'contact_count', 'organization_uuid', 'is_shared', 'created_at', 'updated_at']


class ContactListCreateSerializer(serializers.ModelSerializer):
    """Create/update a contact list."""

    organization_uuid = serializers.UUIDField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = ContactList
        fields = ['name', 'description', 'organization_uuid']

    def validate_organization_uuid(self, value):
        """Validate user has access to the organization."""
        if value:
            from organizations.models import Organization

            user_org_ids = self.context.get('user_org_ids', [])
            try:
                org = Organization.objects.get(uuid=value)
                if org.id not in user_org_ids:
                    raise serializers.ValidationError("You don't have access to this organization.")
                return org
            except Organization.DoesNotExist:
                raise serializers.ValidationError("Organization not found.")
        return None

    def create(self, validated_data):
        org = validated_data.pop('organization_uuid', None)
        if org:
            validated_data['organization'] = org
        return super().create(validated_data)


# =============================================================================
# Contact Serializers (M2)
# =============================================================================


class ContactListMinimalSerializer(serializers.Serializer):
    """Minimal contact list info for embedding."""

    uuid = serializers.UUIDField()
    name = serializers.CharField()


class ContactSerializer(BaseModelSerializer):
    """Full contact serializer with correct field names (M2)."""

    tags = TagSerializer(many=True, read_only=True)
    contact_list = ContactListMinimalSerializer(read_only=True)
    is_linked = serializers.BooleanField(read_only=True)
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = Contact
        fields = [
            'uuid',
            'contact_list',
            'email',
            'full_name',
            'professional_title',
            'organization_name',
            'phone',
            'notes',
            'tags',
            'source',
            # Engagement
            'events_invited_count',
            'events_attended_count',
            'last_invited_at',
            'last_attended_at',
            # Status
            'email_opted_out',
            'email_bounced',
            'is_linked',
            'display_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'uuid',
            'contact_list',
            'events_invited_count',
            'events_attended_count',
            'last_invited_at',
            'last_attended_at',
            'is_linked',
            'display_name',
            'created_at',
            'updated_at',
        ]


class ContactListItemSerializer(BaseModelSerializer):
    """Lightweight contact for list views."""

    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Contact
        fields = [
            'uuid',
            'email',
            'full_name',
            'professional_title',
            'organization_name',
            'events_invited_count',
            'events_attended_count',
            'email_opted_out',
            'email_bounced',
            'tags',
            'created_at',
        ]
        read_only_fields = fields


class ContactCreateSerializer(serializers.ModelSerializer):
    """Create a contact."""

    tag_uuids = serializers.ListField(child=serializers.UUIDField(), required=False, write_only=True)

    class Meta:
        model = Contact
        fields = [
            'email',
            'full_name',
            'professional_title',
            'organization_name',
            'phone',
            'notes',
            'source',
            'tag_uuids',
        ]

    def validate(self, attrs):
        """Validate that email is unique within the contact list."""
        email = attrs.get('email')
        contact_list = self.context.get('contact_list')

        if email and contact_list:
            # Check for duplicate email in same list
            exists = Contact.objects.filter(contact_list=contact_list, email__iexact=email).exists()

            if exists:
                raise serializers.ValidationError({'email': 'A contact with this email already exists in this list.'})

        return attrs

    def create(self, validated_data):
        tag_uuids = validated_data.pop('tag_uuids', [])
        contact = super().create(validated_data)

        if tag_uuids:
            # Allow personal tags OR org-shared tags
            from django.db.models import Q

            user = contact.contact_list.owner

            # Get user's org IDs
            user_org_ids = user.organization_memberships.filter(is_active=True).values_list('organization_id', flat=True)

            tags = Tag.objects.filter(Q(owner=user, organization__isnull=True) | Q(organization_id__in=user_org_ids)).filter(
                uuid__in=tag_uuids
            )

            contact.tags.set(tags)
            contact.contact_list.update_contact_count()

        return contact


class ContactUpdateSerializer(serializers.ModelSerializer):
    """Update a contact."""

    tag_uuids = serializers.ListField(child=serializers.UUIDField(), required=False, write_only=True)

    class Meta:
        model = Contact
        fields = [
            'full_name',
            'professional_title',
            'organization_name',
            'phone',
            'notes',
            'tag_uuids',
            'email_opted_out',
        ]

    def update(self, instance, validated_data):
        tag_uuids = validated_data.pop('tag_uuids', None)
        contact = super().update(instance, validated_data)

        if tag_uuids is not None:
            # Allow personal tags OR org-shared tags
            from django.db.models import Q

            user = contact.contact_list.owner

            user_org_ids = user.organization_memberships.filter(is_active=True).values_list('organization_id', flat=True)

            tags = Tag.objects.filter(Q(owner=user, organization__isnull=True) | Q(organization_id__in=user_org_ids)).filter(
                uuid__in=tag_uuids
            )

            contact.tags.set(tags)

            # Update tag counts for all involved tags
            for tag in tags:
                tag.update_contact_count()

        return contact


class ContactBulkCreateSerializer(serializers.Serializer):
    """Bulk import contacts."""

    contacts = serializers.ListField(child=serializers.DictField(), min_length=1, max_length=1000)
    skip_duplicates = serializers.BooleanField(default=True)

    def validate_contacts(self, value):
        for contact in value:
            if 'email' not in contact:
                raise serializers.ValidationError('Each contact requires an email.')
            if 'full_name' not in contact:
                raise serializers.ValidationError('Each contact requires a full_name.')
        return value
