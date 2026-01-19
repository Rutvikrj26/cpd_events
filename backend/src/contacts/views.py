"""
Contacts app views and viewsets.
"""

from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.permissions import CanCreateEvents
from common.utils import error_response
from common.viewsets import BaseModelViewSet

from . import serializers
from .models import Contact, ContactList, Tag

# =============================================================================
# Filters
# =============================================================================


class ContactFilter(filters.FilterSet):
    """Filter contacts."""

    email = filters.CharFilter(lookup_expr="icontains")
    full_name = filters.CharFilter(lookup_expr="icontains")
    organization = filters.CharFilter(field_name="organization_name", lookup_expr="icontains")
    tag = filters.UUIDFilter(field_name="tags__uuid")
    opted_out = filters.BooleanFilter(field_name="email_opted_out")
    bounced = filters.BooleanFilter(field_name="email_bounced")

    class Meta:
        model = Contact
        fields = ["email", "full_name", "organization", "tag", "opted_out", "bounced"]


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

    Returns tags owned by the user.
    """

    permission_classes = [IsAuthenticated, CanCreateEvents]

    def get_queryset(self):
        """Return tags owned by current user."""
        return Tag.objects.filter(owner=self.request.user)

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return serializers.TagCreateSerializer
        return serializers.TagSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @swagger_auto_schema(
        operation_summary="Merge tags",
        operation_description="Merge this tag into another tag. Contacts will be re-tagged.",
        responses={200: serializers.TagSerializer, 400: '{"error": {}}'},
    )
    @action(detail=True, methods=["post"])
    def merge(self, request, uuid=None):
        """Merge this tag into another."""
        tag = self.get_object()
        target_uuid = request.data.get("target_uuid")

        if not target_uuid:
            return error_response("target_uuid required.", code="MISSING_TARGET")

        try:
            target = self.get_queryset().get(uuid=target_uuid)
        except Tag.DoesNotExist:
            return error_response("Target tag not found.", code="NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND)

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

    Returns personal lists owned by the user.
    """

    permission_classes = [IsAuthenticated, CanCreateEvents]

    def get_queryset(self):
        """Return lists owned by current user."""
        return ContactList.objects.filter(owner=self.request.user)

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return serializers.ContactListCreateSerializer
        if self.action == "retrieve":
            return serializers.ContactListDetailSerializer
        return serializers.ContactListSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @swagger_auto_schema(
        operation_summary="Duplicate list",
        operation_description="Create a copy of this contact list with all contacts.",
        responses={201: serializers.ContactListDetailSerializer},
    )
    @action(detail=True, methods=["post"])
    def duplicate(self, request, uuid=None):
        """Duplicate this contact list."""
        contact_list = self.get_object()
        new_name = request.data.get("name")

        new_list = contact_list.duplicate(new_name)
        return Response(serializers.ContactListDetailSerializer(new_list).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Merge lists",
        operation_description="Merge this contact list into another list.",
        responses={200: serializers.ContactListDetailSerializer, 400: '{"error": {}}'},
    )
    @action(detail=True, methods=["post"])
    def merge(self, request, uuid=None):
        """Merge this list into another."""
        contact_list = self.get_object()
        target_uuid = request.data.get("target_uuid")

        if not target_uuid:
            return error_response("target_uuid required.", code="MISSING_TARGET")

        try:
            target = self.get_queryset().get(uuid=target_uuid)
        except ContactList.DoesNotExist:
            return error_response("Target list not found.", code="NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND)

        contact_list.merge_into(target)
        return Response(serializers.ContactListDetailSerializer(target).data)

    @swagger_auto_schema(
        operation_summary="Export contacts as CSV",
        operation_description="Download all contacts in this list as a CSV file.",
        responses={200: "text/csv"},
    )
    @action(detail=True, methods=["get"])
    def export(self, request, uuid=None):
        """Export contacts in this list as CSV."""
        import csv

        from django.http import HttpResponse

        contact_list = self.get_object()
        contacts = contact_list.contacts.all().prefetch_related("tags")

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{contact_list.name}_contacts.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "Email",
                "Full Name",
                "Professional Title",
                "Organization",
                "Phone",
                "Notes",
                "Tags",
                "Source",
                "Events Invited",
                "Events Attended",
                "Status",
            ]
        )

        for contact in contacts:
            status_str = "Bounced" if contact.email_bounced else ("Opted Out" if contact.email_opted_out else "Active")
            tags_str = ", ".join(tag.name for tag in contact.tags.all())

            writer.writerow(
                [
                    contact.email,
                    contact.full_name,
                    contact.professional_title or "",
                    contact.organization_name or "",
                    contact.phone or "",
                    contact.notes or "",
                    tags_str,
                    contact.source or "",
                    contact.events_invited_count,
                    contact.events_attended_count,
                    status_str,
                ]
            )

        return response


# =============================================================================
# Contact ViewSet (simplified - auto-resolves user's list)
# =============================================================================


class ContactViewSet(BaseModelViewSet):
    """
    Manage contacts.

    GET /api/v1/contacts/
    POST /api/v1/contacts/
    GET /api/v1/contacts/{uuid}/
    PATCH /api/v1/contacts/{uuid}/
    DELETE /api/v1/contacts/{uuid}/

    Automatically uses the user's personal contact list.
    Tags are used for segmentation instead of multiple lists.
    """

    permission_classes = [IsAuthenticated, CanCreateEvents]
    filterset_class = ContactFilter
    search_fields = ["email", "full_name", "organization_name"]
    ordering_fields = ["full_name", "email", "created_at", "events_attended_count"]
    ordering = ["full_name"]

    def _get_user_list(self):
        """Get or create the user's personal contact list."""
        return ContactList.get_or_create_for_user(self.request.user)

    def get_queryset(self):
        contact_list = self._get_user_list()
        return Contact.objects.filter(contact_list=contact_list).prefetch_related("tags")

    def get_serializer_class(self):
        if self.action == "create":
            return serializers.ContactCreateSerializer
        if self.action in ["update", "partial_update"]:
            return serializers.ContactUpdateSerializer
        if self.action == "list":
            return serializers.ContactListItemSerializer
        return serializers.ContactSerializer

    def get_serializer_context(self):
        """Add contact_list to serializer context."""
        context = super().get_serializer_context()
        context["contact_list"] = self._get_user_list()
        return context

    def perform_create(self, serializer):
        contact_list = self._get_user_list()
        serializer.save(contact_list=contact_list)

    @swagger_auto_schema(
        operation_summary="Bulk create contacts",
        operation_description="Import multiple contacts.",
        request_body=serializers.ContactBulkCreateSerializer,
    )
    @action(detail=False, methods=["post"])
    def bulk_create(self, request):
        """Bulk import contacts."""
        serializer = serializers.ContactBulkCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        contact_list = self._get_user_list()

        created = []
        skipped = []

        for contact_data in serializer.validated_data["contacts"]:
            email = contact_data["email"].lower()

            # Check for duplicate
            if Contact.objects.filter(contact_list=contact_list, email__iexact=email).exists():
                if serializer.validated_data["skip_duplicates"]:
                    skipped.append(email)
                    continue

            contact = Contact.objects.create(
                contact_list=contact_list,
                email=email,
                full_name=contact_data["full_name"],
                professional_title=contact_data.get("professional_title", ""),
                organization_name=contact_data.get("organization_name", ""),
                phone=contact_data.get("phone", ""),
                notes=contact_data.get("notes", ""),
                source="import",
            )
            created.append(str(contact.uuid))

        contact_list.update_contact_count()

        return Response(
            {
                "created": len(created),
                "skipped": len(skipped),
                "skipped_emails": skipped,
            },
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary="Export contacts",
        operation_description="Export contacts as CSV.",
    )
    @action(detail=False, methods=["get"])
    def export(self, request):
        """Export contacts as CSV."""
        import csv

        from django.http import HttpResponse

        contact_list = self._get_user_list()
        contacts = contact_list.contacts.all().prefetch_related("tags")

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="contacts.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "Email",
                "Full Name",
                "Professional Title",
                "Organization",
                "Phone",
                "Notes",
                "Tags",
                "Source",
                "Events Invited",
                "Events Attended",
                "Status",
            ]
        )

        for contact in contacts:
            status_str = "Bounced" if contact.email_bounced else ("Opted Out" if contact.email_opted_out else "Active")
            tags_str = ", ".join(tag.name for tag in contact.tags.all())

            writer.writerow(
                [
                    contact.email,
                    contact.full_name,
                    contact.professional_title or "",
                    contact.organization_name or "",
                    contact.phone or "",
                    contact.notes or "",
                    tags_str,
                    contact.source or "",
                    contact.events_invited_count,
                    contact.events_attended_count,
                    status_str,
                ]
            )

        return response
