"""
Common base viewsets for the API.
"""

from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response


class UUIDLookupMixin:
    """Use UUID for object lookups instead of PK."""
    lookup_field = 'uuid'
    lookup_url_kwarg = 'uuid'


class SoftDeleteMixin:
    """Handle soft-delete in viewsets."""
    
    def get_queryset(self):
        """Override to exclude deleted items."""
        qs = super().get_queryset()
        if hasattr(qs.model, 'deleted_at'):
            qs = qs.filter(deleted_at__isnull=True)
        return qs
    
    def perform_destroy(self, instance):
        """Soft delete instead of hard delete."""
        instance.soft_delete()


class BaseModelViewSet(UUIDLookupMixin, viewsets.ModelViewSet):
    """Base viewset with UUID lookups and standard CRUD."""
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class SoftDeleteModelViewSet(SoftDeleteMixin, BaseModelViewSet):
    """Base viewset for soft-delete models."""
    
    @action(detail=True, methods=['post'])
    def restore(self, request, uuid=None):
        """Restore a soft-deleted object."""
        instance = self.get_queryset().model.all_objects.get(uuid=uuid)
        instance.restore()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class ReadOnlyModelViewSet(UUIDLookupMixin, viewsets.ReadOnlyModelViewSet):
    """Base viewset for read-only resources."""
    pass


class CreateListRetrieveViewSet(
    UUIDLookupMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    """ViewSet for create, list, retrieve (no update/delete)."""
    pass
