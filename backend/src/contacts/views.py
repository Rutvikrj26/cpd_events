"""
Contacts app views and viewsets.
"""

from django.db.models import Count, Q
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.permissions import IsOrganizerOrAdmin
from common.rbac import roles
from common.utils import error_response
from common.viewsets import BaseModelViewSet

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


@roles('organizer', 'admin', route_name='tags')
class TagViewSet(BaseModelViewSet):
    """
    Manage tags.

    GET /api/v1/tags/
    POST /api/v1/tags/
    GET /api/v1/tags/{uuid}/
    PATCH /api/v1/tags/{uuid}/
    DELETE /api/v1/tags/{uuid}/
    """

    permission_classes = [IsAuthenticated, IsOrganizerOrAdmin]

    def get_queryset(self):
        if self.request.user.groups.filter(name="admin").exists():
            return Tag.objects.all()
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
            target = self.get_queryset().get(uuid=target_uuid)
        except Tag.DoesNotExist:
            return error_response('Target tag not found.', code='NOT_FOUND', status_code=status.HTTP_404_NOT_FOUND)

        tag.merge_into(target)
        return Response(serializers.TagSerializer(target).data)


# =============================================================================
# Contact List ViewSet
# =============================================================================


@roles('organizer', 'admin', route_name='contact_lists')
class ContactListViewSet(BaseModelViewSet):
    """
    Manage contact lists.

    GET /api/v1/contact-lists/
    POST /api/v1/contact-lists/
    GET /api/v1/contact-lists/{uuid}/
    PATCH /api/v1/contact-lists/{uuid}/
    DELETE /api/v1/contact-lists/{uuid}/
    """

    permission_classes = [IsAuthenticated, IsOrganizerOrAdmin]

    def get_queryset(self):
        if self.request.user.groups.filter(name="admin").exists():
            return ContactList.objects.all()
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
            target = self.get_queryset().get(uuid=target_uuid)
        except ContactList.DoesNotExist:
            return error_response('Target list not found.', code='NOT_FOUND', status_code=status.HTTP_404_NOT_FOUND)

        contact_list.merge_into(target)
        return Response(serializers.ContactListDetailSerializer(target).data)

    @swagger_auto_schema(
        operation_summary="Export contacts as CSV",
        operation_description="Download all contacts in this list as a CSV file.",
        responses={200: 'text/csv'},
    )
    @action(detail=True, methods=['get'])
    def export(self, request, uuid=None):
        """Export contacts in this list as CSV."""
        import csv

        from django.http import HttpResponse

        contact_list = self.get_object()
        contacts = contact_list.contacts.all().prefetch_related('tags')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{contact_list.name}_contacts.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                'Email',
                'Full Name',
                'Professional Title',
                'Organization',
                'Phone',
                'Notes',
                'Tags',
                'Source',
                'Events Invited',
                'Events Attended',
                'Status',
            ]
        )

        for contact in contacts:
            status_str = 'Bounced' if contact.email_bounced else ('Opted Out' if contact.email_opted_out else 'Active')
            tags_str = ', '.join(tag.name for tag in contact.tags.all())

            writer.writerow(
                [
                    contact.email,
                    contact.full_name,
                    contact.professional_title or '',
                    contact.organization_name or '',
                    contact.phone or '',
                    contact.notes or '',
                    tags_str,
                    contact.source or '',
                    contact.events_invited_count,
                    contact.events_attended_count,
                    status_str,
                ]
            )

        return response


# =============================================================================
# Contact ViewSet (simplified - auto-resolves user's list)
# =============================================================================


@roles('organizer', 'admin', route_name='contacts')
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

    permission_classes = [IsAuthenticated, IsOrganizerOrAdmin]
    filterset_class = ContactFilter
    search_fields = ['email', 'full_name', 'organization_name']
    ordering_fields = ['full_name', 'email', 'created_at', 'events_attended_count']
    ordering = ['full_name']

    def _get_user_list(self):
        """Get or create the user's personal contact list."""
        return ContactList.get_or_create_for_user(self.request.user)

    def get_queryset(self):
        if self.request.user.groups.filter(name="admin").exists():
            qs = Contact.objects.all()
        else:
            contact_list = self._get_user_list()
            qs = Contact.objects.filter(contact_list=contact_list)
        # Annotate course enrollment counts via the optional User link.
        # distinct=True prevents double-counting through the tags prefetch join path.
        return qs.prefetch_related('tags').annotate(
            courses_enrolled_count=Count('user__course_enrollments', distinct=True),
            courses_completed_count=Count(
                'user__course_enrollments',
                filter=Q(user__course_enrollments__status='completed'),
                distinct=True,
            ),
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return serializers.ContactCreateSerializer
        if self.action in ['update', 'partial_update']:
            return serializers.ContactUpdateSerializer
        if self.action == 'list':
            return serializers.ContactListItemSerializer
        return serializers.ContactSerializer

    def get_serializer_context(self):
        """Add contact_list to serializer context."""
        context = super().get_serializer_context()
        context['contact_list'] = self._get_user_list()
        return context

    def perform_create(self, serializer):
        contact_list = self._get_user_list()
        serializer.save(contact_list=contact_list)

    @swagger_auto_schema(
        operation_summary="Bulk create contacts",
        operation_description="Import multiple contacts.",
        request_body=serializers.ContactBulkCreateSerializer,
    )
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Bulk import contacts."""
        serializer = serializers.ContactBulkCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        contact_list = self._get_user_list()

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
        operation_summary="Export contacts",
        operation_description="Export contacts as CSV.",
    )
    @action(detail=False, methods=['get'])
    def export(self, request):
        """Export contacts as CSV."""
        import csv

        from django.http import HttpResponse

        contact_list = self._get_user_list()
        contacts = contact_list.contacts.all().prefetch_related('tags')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="contacts.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                'Email',
                'Full Name',
                'Professional Title',
                'Organization',
                'Phone',
                'Notes',
                'Tags',
                'Source',
                'Events Invited',
                'Events Attended',
                'Status',
            ]
        )

        for contact in contacts:
            status_str = 'Bounced' if contact.email_bounced else ('Opted Out' if contact.email_opted_out else 'Active')
            tags_str = ', '.join(tag.name for tag in contact.tags.all())

            writer.writerow(
                [
                    contact.email,
                    contact.full_name,
                    contact.professional_title or '',
                    contact.organization_name or '',
                    contact.phone or '',
                    contact.notes or '',
                    tags_str,
                    contact.source or '',
                    contact.events_invited_count,
                    contact.events_attended_count,
                    status_str,
                ]
            )

        return response

    IMPORT_COLUMNS = [
        'email',
        'full_name',
        'professional_title',
        'organization_name',
        'phone',
        'notes',
    ]

    @swagger_auto_schema(
        operation_summary="Download import template",
        operation_description="Download a CSV template with the expected columns for /import-csv/.",
    )
    @action(detail=False, methods=['get'], url_path='import-template')
    def import_template(self, request):
        """Empty CSV template for the CSV import flow."""
        import csv

        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="contacts_import_template.csv"'
        writer = csv.writer(response)
        writer.writerow(self.IMPORT_COLUMNS)
        writer.writerow([
            'attendee@example.com',
            'Jane Doe',
            'MD',
            'Example Clinic',
            '+1 555 0123',
            'Met at conference',
        ])
        return response

    @swagger_auto_schema(
        operation_summary="Import contacts from CSV",
        operation_description="Upload a CSV file (multipart/form-data, field name 'file') with columns from /import-template/.",
    )
    @action(detail=False, methods=['post'], url_path='import-csv')
    def import_csv(self, request):
        """Parse an uploaded CSV into contacts with row-level error reporting."""
        import csv
        import io

        upload = request.FILES.get('file')
        if not upload:
            return Response({'error': 'No file uploaded under the "file" field.'}, status=status.HTTP_400_BAD_REQUEST)

        skip_duplicates = request.data.get('skip_duplicates', 'true')
        skip_duplicates = str(skip_duplicates).lower() not in ('false', '0', 'no')

        try:
            decoded = upload.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            return Response({'error': 'File must be UTF-8 encoded.'}, status=status.HTTP_400_BAD_REQUEST)

        reader = csv.DictReader(io.StringIO(decoded))
        if not reader.fieldnames:
            return Response({'error': 'CSV is empty.'}, status=status.HTTP_400_BAD_REQUEST)

        normalized = [(name or '').strip().lower() for name in reader.fieldnames]
        missing = [col for col in ('email', 'full_name') if col not in normalized]
        if missing:
            return Response(
                {'error': f'Missing required column(s): {", ".join(missing)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        contact_list = self._get_user_list()
        created: list[str] = []
        skipped: list[dict] = []
        errors: list[dict] = []

        for index, raw_row in enumerate(reader, start=2):  # row 1 = header
            row = {(k or '').strip().lower(): (v or '').strip() for k, v in raw_row.items()}
            email = row.get('email', '').lower()
            full_name = row.get('full_name', '')

            if not email or '@' not in email:
                errors.append({'row': index, 'email': email, 'error': 'Invalid email'})
                continue
            if not full_name:
                errors.append({'row': index, 'email': email, 'error': 'full_name is required'})
                continue

            if Contact.objects.filter(contact_list=contact_list, email__iexact=email).exists():
                if skip_duplicates:
                    skipped.append({'row': index, 'email': email})
                    continue
                errors.append({'row': index, 'email': email, 'error': 'Duplicate email'})
                continue

            try:
                contact = Contact.objects.create(
                    contact_list=contact_list,
                    email=email,
                    full_name=full_name,
                    professional_title=row.get('professional_title', ''),
                    organization_name=row.get('organization_name', ''),
                    phone=row.get('phone', ''),
                    notes=row.get('notes', ''),
                    source='import',
                )
                created.append(str(contact.uuid))
            except Exception as e:
                errors.append({'row': index, 'email': email, 'error': str(e)[:200]})

        contact_list.update_contact_count()

        return Response(
            {
                'created': len(created),
                'skipped': len(skipped),
                'errors': errors,
                'skipped_rows': skipped,
            },
            status=status.HTTP_200_OK if errors else status.HTTP_201_CREATED,
        )
