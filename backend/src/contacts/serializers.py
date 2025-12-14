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
from .models import ContactList, Contact, Tag


# =============================================================================
# Tag Serializers
# =============================================================================

class TagSerializer(BaseModelSerializer):
    """Tag with contact count."""
    
    class Meta:
        model = Tag
        fields = [
            'uuid', 'name', 'color', 'description', 'contact_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['uuid', 'contact_count', 'created_at', 'updated_at']


class TagCreateSerializer(serializers.ModelSerializer):
    """Create/update a tag."""
    
    class Meta:
        model = Tag
        fields = ['name', 'color', 'description']


# =============================================================================
# Contact List Serializers (L1)
# =============================================================================

class ContactListSerializer(BaseModelSerializer):
    """Contact list with summary."""
    
    class Meta:
        model = ContactList
        fields = [
            'uuid', 'name', 'description', 'is_default', 'contact_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['uuid', 'contact_count', 'created_at', 'updated_at']


class ContactListDetailSerializer(BaseModelSerializer):
    """Full contact list detail."""
    
    class Meta:
        model = ContactList
        fields = [
            'uuid', 'name', 'description', 'is_default', 'contact_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['uuid', 'contact_count', 'created_at', 'updated_at']


class ContactListCreateSerializer(serializers.ModelSerializer):
    """Create/update a contact list."""
    
    class Meta:
        model = ContactList
        fields = ['name', 'description', 'is_default']


# =============================================================================
# Contact Serializers (M2)
# =============================================================================

class ContactListSerializer_Minimal(serializers.Serializer):
    """Minimal contact list info for embedding."""
    uuid = serializers.UUIDField()
    name = serializers.CharField()


class ContactSerializer(BaseModelSerializer):
    """Full contact serializer with correct field names (M2)."""
    tags = TagSerializer(many=True, read_only=True)
    contact_list = ContactListSerializer_Minimal(read_only=True)
    is_linked = serializers.BooleanField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = Contact
        fields = [
            'uuid', 'contact_list', 'email', 'full_name',
            'professional_title', 'organization_name', 'phone',
            'notes', 'tags', 'source',
            # Engagement
            'events_invited_count', 'events_attended_count',
            'last_invited_at', 'last_attended_at',
            # Status
            'email_opted_out', 'email_bounced', 'is_linked',
            'display_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'uuid', 'contact_list', 'events_invited_count', 'events_attended_count',
            'last_invited_at', 'last_attended_at', 'is_linked', 'display_name',
            'created_at', 'updated_at',
        ]


class ContactListItemSerializer(BaseModelSerializer):
    """Lightweight contact for list views."""
    tag_names = serializers.SerializerMethodField()
    
    class Meta:
        model = Contact
        fields = [
            'uuid', 'email', 'full_name', 'professional_title', 'organization_name',
            'events_invited_count', 'events_attended_count',
            'email_opted_out', 'email_bounced', 'tag_names',
            'created_at',
        ]
        read_only_fields = fields
    
    def get_tag_names(self, obj):
        return [tag.name for tag in obj.tags.all()]


class ContactCreateSerializer(serializers.ModelSerializer):
    """Create a contact."""
    tag_uuids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True
    )
    
    class Meta:
        model = Contact
        fields = [
            'email', 'full_name', 'professional_title', 'organization_name',
            'phone', 'notes', 'source', 'tag_uuids',
        ]
    
    def create(self, validated_data):
        tag_uuids = validated_data.pop('tag_uuids', [])
        contact = super().create(validated_data)
        
        if tag_uuids:
            tags = Tag.objects.filter(
                uuid__in=tag_uuids,
                owner=contact.contact_list.owner
            )
            contact.tags.set(tags)
        
        # Update list count
        contact.contact_list.update_contact_count()
        
        return contact


class ContactUpdateSerializer(serializers.ModelSerializer):
    """Update a contact."""
    tag_uuids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        write_only=True
    )
    
    class Meta:
        model = Contact
        fields = [
            'full_name', 'professional_title', 'organization_name',
            'phone', 'notes', 'tag_uuids',
            'email_opted_out',
        ]
    
    def update(self, instance, validated_data):
        tag_uuids = validated_data.pop('tag_uuids', None)
        contact = super().update(instance, validated_data)
        
        if tag_uuids is not None:
            tags = Tag.objects.filter(
                uuid__in=tag_uuids,
                owner=contact.contact_list.owner
            )
            contact.tags.set(tags)
            
            # Update tag counts
            for tag in Tag.objects.filter(owner=contact.contact_list.owner):
                tag.update_contact_count()
        
        return contact


class ContactBulkCreateSerializer(serializers.Serializer):
    """Bulk import contacts."""
    contacts = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        max_length=1000
    )
    skip_duplicates = serializers.BooleanField(default=True)
    
    def validate_contacts(self, value):
        for contact in value:
            if 'email' not in contact:
                raise serializers.ValidationError('Each contact requires an email.')
            if 'full_name' not in contact:
                raise serializers.ValidationError('Each contact requires a full_name.')
        return value


class ContactMoveSerializer(serializers.Serializer):
    """Move contact to another list."""
    target_list_uuid = serializers.UUIDField()
