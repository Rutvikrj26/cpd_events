"""
Common base serializers for the API.
"""

from rest_framework import serializers


class UUIDLookupMixin:
    """Mixin to use UUID for lookups instead of PK."""

    def get_fields(self):
        fields = super().get_fields()
        # Remove 'id' field if present
        fields.pop('id', None)
        return fields


class TimestampMixin(serializers.Serializer):
    """Standard timestamp fields."""

    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class BaseModelSerializer(UUIDLookupMixin, serializers.ModelSerializer):
    """
    Base serializer for all models.

    Provides:
    - UUID as primary identifier
    - Timestamps (read-only)
    - Excludes internal 'id' field
    """

    uuid = serializers.UUIDField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class SoftDeleteModelSerializer(BaseModelSerializer):
    """Base serializer for soft-delete models."""

    is_deleted = serializers.SerializerMethodField()

    def get_is_deleted(self, obj):
        return obj.deleted_at is not None


# Minimal serializers for embedding in responses
class MinimalUserSerializer(serializers.Serializer):
    """Minimal user representation for embedding."""

    uuid = serializers.UUIDField()
    full_name = serializers.CharField()
    email = serializers.EmailField()


class MinimalEventSerializer(serializers.Serializer):
    """Minimal event representation for embedding."""

    uuid = serializers.UUIDField()
    title = serializers.CharField()
    slug = serializers.SlugField()
    starts_at = serializers.DateTimeField()
    status = serializers.CharField()
    cpd_credit_value = serializers.DecimalField(max_digits=5, decimal_places=2)
    cpd_credit_type = serializers.CharField()
