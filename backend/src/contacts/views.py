"""
Contacts app views and viewsets.
"""

from django_filters import rest_framework as filters
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from common.permissions import IsOrganizer
from common.viewsets import BaseModelViewSet
from common.utils import error_response

from . import serializers
from .models import Contact, ContactList, Tag

# =============================================================================
# Filters
# =============================================================================


class ContactFilter(filters.FilterSet):
    """Filter contacts."""

    email = filters.CharFilter(lookup_expr='icontains')
    full_name = filters.CharFilter(lookup_expr='icontains')
    organization = filters.CharFilter(field_name='organization_name', lookup_expr='icontains')
    tag = filters.UUIDFilter(field_name='tags__uuid')
    opted_out = filters.BooleanFilter(field_name='email_opted_out')
    bounced = filters.BooleanFilter(field_name='email_bounced')

    class Meta:
        model = Contact
        fields = ['email', 'full_name', 'organization', 'tag', 'opted_out', 'bounced']


# =============================================================================
# Tag ViewSet
# =============================================================================


class TagViewSet(BaseModelViewSet):
    """
    Manage tags.

    GET /api/v1/tags/
    POST /api/v1/tags/
    GET /api/v1/tags/{uuid}/
    PATCH /api/v1/tags/{uuid}/
    DELETE /api/v1/tags/{uuid}/
    """

    permission_classes = [IsAuthenticated, IsOrganizer]

    def get_queryset(self):
        return Tag.objects.filter(owner=self.request.user)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return serializers.TagCreateSerializer
        return serializers.TagSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @swagger_auto_schema(
        operation_summary="Merge tags",
        operation_description="Merge this tag into another tag. Contacts will be re-tagged.",
        responses={200: serializers.TagSerializer, 400: '{"error": {}}'},
    )
    @action(detail=True, methods=['post'])
    def merge(self, request, uuid=None):
        """Merge this tag into another."""
        tag = self.get_object()
        target_uuid = request.data.get('target_uuid')

        if not target_uuid:
            return error_response('target_uuid required.', code='MISSING_TARGET')

        try:
            target = Tag.objects.get(uuid=target_uuid, owner=request.user)
        except Tag.DoesNotExist:
            return error_response('Target tag not found.', code='NOT_FOUND', status_code=status.HTTP_404_NOT_FOUND)

        tag.merge_into(target)
        return Response(serializers.TagSerializer(target).data)


# =============================================================================
# Contact List ViewSet
# =============================================================================


class ContactListViewSet(BaseModelViewSet):
    """
    Manage contact lists.

    GET /api/v1/contact-lists/
    POST /api/v1/contact-lists/
    GET /api/v1/contact-lists/{uuid}/
    PATCH /api/v1/contact-lists/{uuid}/
    DELETE /api/v1/contact-lists/{uuid}/
    """

    permission_classes = [IsAuthenticated, IsOrganizer]

    def get_queryset(self):
        return ContactList.objects.filter(owner=self.request.user)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return serializers.ContactListCreateSerializer
        if self.action == 'retrieve':
            return serializers.ContactListDetailSerializer
        return serializers.ContactListSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @swagger_auto_schema(
        operation_summary="Set default list",
        operation_description="Set this contact list as the default.",
        responses={200: serializers.ContactListDetailSerializer},
    )
    @action(detail=True, methods=['post'], url_path='set-default')
    def set_default(self, request, uuid=None):
        """Set as default contact list."""
        contact_list = self.get_object()
        contact_list.set_as_default()
        return Response(serializers.ContactListDetailSerializer(contact_list).data)

    @swagger_auto_schema(
        operation_summary="Duplicate list",
        operation_description="Create a copy of this contact list with all contacts.",
        responses={201: serializers.ContactListDetailSerializer},
    )
    @action(detail=True, methods=['post'])
    def duplicate(self, request, uuid=None):
        """Duplicate this contact list."""
        contact_list = self.get_object()
        new_name = request.data.get('name')

        new_list = contact_list.duplicate(new_name)
        return Response(serializers.ContactListDetailSerializer(new_list).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Merge lists",
        operation_description="Merge this contact list into another list.",
        responses={200: serializers.ContactListDetailSerializer, 400: '{"error": {}}'},
    )
    @action(detail=True, methods=['post'])
    def merge(self, request, uuid=None):
        """Merge this list into another."""
        contact_list = self.get_object()
        target_uuid = request.data.get('target_uuid')

        if not target_uuid:
            return error_response('target_uuid required.', code='MISSING_TARGET')

        try:
            target = ContactList.objects.get(uuid=target_uuid, owner=request.user)
        except ContactList.DoesNotExist:
            return error_response('Target list not found.', code='NOT_FOUND', status_code=status.HTTP_404_NOT_FOUND)

        contact_list.merge_into(target)
        return Response(serializers.ContactListDetailSerializer(target).data)


# =============================================================================
# Contact ViewSet (nested under lists)
# =============================================================================


class ListContactViewSet(BaseModelViewSet):
    """
    Manage contacts in a list.

    GET /api/v1/contact-lists/{list_uuid}/contacts/
    POST /api/v1/contact-lists/{list_uuid}/contacts/
    GET /api/v1/contact-lists/{list_uuid}/contacts/{uuid}/
    PATCH /api/v1/contact-lists/{list_uuid}/contacts/{uuid}/
    DELETE /api/v1/contact-lists/{list_uuid}/contacts/{uuid}/
    """

    permission_classes = [IsAuthenticated, IsOrganizer]
    filterset_class = ContactFilter
    search_fields = ['email', 'full_name', 'organization_name']
    ordering_fields = ['full_name', 'email', 'created_at', 'events_attended_count']
    ordering = ['full_name']

    def get_queryset(self):
        list_uuid = self.kwargs.get('list_uuid')
        return Contact.objects.filter(contact_list__uuid=list_uuid, contact_list__owner=self.request.user).prefetch_related(
            'tags'
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return serializers.ContactCreateSerializer
        if self.action in ['update', 'partial_update']:
            return serializers.ContactUpdateSerializer
        if self.action == 'list':
            return serializers.ContactListItemSerializer
        return serializers.ContactSerializer

    def perform_create(self, serializer):
        list_uuid = self.kwargs.get('list_uuid')
        contact_list = ContactList.objects.get(uuid=list_uuid, owner=self.request.user)
        serializer.save(contact_list=contact_list)

    @swagger_auto_schema(
        operation_summary="Bulk create contacts",
        operation_description="Import multiple contacts into this list.",
        request_body=serializers.ContactBulkCreateSerializer,
    )
    @action(detail=False, methods=['post'])
    def bulk_create(self, request, list_uuid=None):
        """Bulk import contacts."""
        serializer = serializers.ContactBulkCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        contact_list = ContactList.objects.get(uuid=list_uuid, owner=request.user)

        created = []
        skipped = []

        for contact_data in serializer.validated_data['contacts']:
            email = contact_data['email'].lower()

            # Check for duplicate
            if Contact.objects.filter(contact_list=contact_list, email__iexact=email).exists():
                if serializer.validated_data['skip_duplicates']:
                    skipped.append(email)
                    continue

            contact = Contact.objects.create(
                contact_list=contact_list,
                email=email,
                full_name=contact_data['full_name'],
                professional_title=contact_data.get('professional_title', ''),
                organization_name=contact_data.get('organization_name', ''),
                phone=contact_data.get('phone', ''),
                notes=contact_data.get('notes', ''),
                source='import',
            )
            created.append(str(contact.uuid))

        contact_list.update_contact_count()

        return Response(
            {
                'created': len(created),
                'skipped': len(skipped),
                'skipped_emails': skipped,
            },
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary="Move contact",
        operation_description="Move a contact to a different list.",
        request_body=serializers.ContactMoveSerializer,
        responses={200: serializers.ContactSerializer, 400: '{"error": {}}'},
    )
    @action(detail=True, methods=['post'])
    def move(self, request, list_uuid=None, uuid=None):
        """Move contact to another list."""
        contact = self.get_object()
        serializer = serializers.ContactMoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            target_list = ContactList.objects.get(uuid=serializer.validated_data['target_list_uuid'], owner=request.user)
        except ContactList.DoesNotExist:
            return error_response('Target list not found.', code='NOT_FOUND', status_code=status.HTTP_404_NOT_FOUND)

        try:
            contact.move_to_list(target_list)
        except ValueError as e:
            return error_response(str(e), code='MOVE_FAILED')

        return Response(serializers.ContactSerializer(contact).data)
