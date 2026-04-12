"""
Certificates app views and viewsets.
"""

import logging

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from django.http import HttpResponse
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

from common.pagination import SmallPagination
from common.permissions import IsContentCreator, IsEducatorOrAdmin
from common.rbac import roles
from common.utils import error_response
from common.viewsets import ReadOnlyModelViewSet, SoftDeleteModelViewSet

from . import serializers
from .models import Certificate, CertificateTemplate

INSTITUTION_CONTENT_GROUPS = ('educator', 'course_manager', 'admin')


def _get_writable_event(event_uuid, user):
    """
    Fetch an active event that `user` is allowed to manage certificates for.

    Institutional single-tenant model: staff, or any user in the educator /
    course_manager / admin groups, can manage certificates for any active
    event. Regular users may only manage events they own.

    Returns the Event or None.
    """
    from events.models import Event

    qs = Event.objects.filter(uuid=event_uuid, deleted_at__isnull=True)
    if user.groups.filter(name__in=INSTITUTION_CONTENT_GROUPS).exists():
        return qs.first()
    return qs.filter(owner=user).first()


def _get_writable_course(course_uuid, user):
    """Course equivalent of _get_writable_event."""
    from learning.models import Course

    qs = Course.objects.filter(uuid=course_uuid, deleted_at__isnull=True)
    if user.groups.filter(name__in=INSTITUTION_CONTENT_GROUPS).exists():
        return qs.first()
    return qs.filter(owner=user).first()


# =============================================================================
# Certificate Template ViewSet
# =============================================================================


@roles('educator', 'course_manager', 'admin', route_name='certificate_templates')
class CertificateTemplateViewSet(SoftDeleteModelViewSet):
    """
    Manage certificate templates.

    GET /api/v1/certificate-templates/
    POST /api/v1/certificate-templates/
    GET /api/v1/certificate-templates/{uuid}/
    PATCH /api/v1/certificate-templates/{uuid}/
    DELETE /api/v1/certificate-templates/{uuid}/
    """

    permission_classes = [IsAuthenticated, IsContentCreator]
    lookup_field = 'uuid'

    def get_queryset(self):
        qs = CertificateTemplate.objects.filter(deleted_at__isnull=True, is_active=True)
        if not self.request.user.groups.filter(name="admin").exists():
            qs = qs.filter(owner=self.request.user)
        return qs.select_related('owner')

    def get_serializer_class(self):
        if self.action == 'create':
            return serializers.CertificateTemplateCreateSerializer
        if self.action in ['update', 'partial_update']:
            return serializers.CertificateTemplateUpdateSerializer
        if self.action == 'list':
            return serializers.CertificateTemplateListSerializer
        return serializers.CertificateTemplateDetailSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Duplicate template",
        operation_description="Create an independent copy of this template.",
        responses={201: serializers.CertificateTemplateDetailSerializer},
    )
    @action(detail=True, methods=['post'], url_path='duplicate')
    def duplicate(self, request, uuid=None):
        """Duplicate this template."""
        template = self.get_object()
        new_name = request.data.get('name') if isinstance(request.data, dict) else None
        new_template = template.duplicate(new_name=new_name)
        return Response(
            serializers.CertificateTemplateDetailSerializer(new_template).data,
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary="Set default template",
        operation_description="Set this template as the default for new events.",
        responses={200: serializers.CertificateTemplateDetailSerializer},
    )
    @action(detail=True, methods=['post'], url_path='set-default')
    def set_default(self, request, uuid=None):
        """Set as default template."""
        template = self.get_object()
        template.set_as_default()
        return Response(serializers.CertificateTemplateDetailSerializer(template).data)

    @swagger_auto_schema(
        operation_summary="List available templates",
        operation_description="Get all templates available to the user.",
        responses={200: serializers.CertificateTemplateListSerializer(many=True)},
    )
    @action(detail=False, methods=['get'], url_path='available')
    def available_templates(self, request):
        """
        Get every template the current user is allowed to pick from.

        In institutional single-tenant mode this matches the main list: all
        active non-deleted templates for staff / educators / course_managers /
        admins, and owned-only templates for anyone else.
        """
        templates = self.get_queryset()
        serializer = serializers.CertificateTemplateListSerializer(templates, many=True)
        return Response({'own_count': templates.count(), 'templates': serializer.data})

    @swagger_auto_schema(
        operation_summary="Upload template PDF",
        operation_description="Upload a PDF file to use as the certificate background.",
    )
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser])
    def upload(self, request, uuid=None):
        """Upload PDF template file."""
        template = self.get_object()

        file = request.FILES.get('file')
        if not file:
            return error_response('No file provided.', code='MISSING_FILE', status_code=status.HTTP_400_BAD_REQUEST)

        # Validate file type
        if not file.name.lower().endswith('.pdf'):
            return error_response(
                'Only PDF files are allowed.', code='INVALID_FILE_TYPE', status_code=status.HTTP_400_BAD_REQUEST
            )

        # Validate file size (max 10MB)
        if file.size > 10 * 1024 * 1024:
            return error_response(
                'File too large. Maximum size is 10MB.', code='FILE_TOO_LARGE', status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            from common.storage import gcs_storage

            # Read file content
            content = file.read()

            # Generate path
            path = f"certificate-templates/{template.uuid}/{file.name}"

            # Upload to storage
            file_url = gcs_storage.upload(
                content=content,
                path=path,
                content_type='application/pdf',
                public=False,
            )

            if not file_url:
                return error_response(
                    'Failed to upload file.', code='UPLOAD_FAILED', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Update template
            template.file_url = file_url
            template.file_type = 'pdf'
            template.file_size_bytes = file.size
            template.save(update_fields=['file_url', 'file_type', 'file_size_bytes', 'updated_at'])

            return Response(
                {
                    'file_url': file_url,
                    'file_size': file.size,
                    'message': 'Template uploaded successfully.',
                }
            )

        except Exception as e:
            logger.error(f"Template upload failed: {e}")
            return error_response('Upload failed.', code='UPLOAD_FAILED', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_summary="Preview certificate",
        operation_description="Generate a preview of the certificate with sample data.",
    )
    @action(detail=True, methods=['post'])
    def preview(self, request, uuid=None):
        """Generate preview with sample data."""
        template = self.get_object()

        # Get field positions from request or use template's saved positions
        field_positions = request.data.get('field_positions', template.field_positions)

        # Sample data for preview - keys must match Certificate.build_certificate_data()
        sample_data = {
            'attendee_name': 'John Doe',
            'event_title': 'Sample Event Title',
            'event_date': '2025-12-20',
            'cpd_credits': '2.0',
            'organizer_name': 'Sample Organizer',
            'issued_date': '2025-12-22',
            'cpd_type': 'CME',
            'attendee_email': 'john.doe@example.com',
            'attendee_title': 'Dr.',
            'attendee_organization': 'Sample Hospital',
        }

        try:
            from .services import certificate_service

            # Generate preview PDF
            preview_bytes = certificate_service.generate_template_preview(template, field_positions, sample_data)

            if not preview_bytes:
                return error_response(
                    'Failed to generate preview.', code='PREVIEW_FAILED', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Upload preview (temporary)
            import uuid as uuid_lib

            from common.storage import gcs_storage

            preview_path = f"certificate-templates/{template.uuid}/preview-{uuid_lib.uuid4().hex[:8]}.pdf"
            preview_url = gcs_storage.upload(
                content=preview_bytes,
                path=preview_path,
                content_type='application/pdf',
                public=True,  # Preview can be public
            )

            return Response(
                {
                    'preview_url': preview_url,
                    'field_positions': field_positions,
                }
            )

        except Exception as e:
            logger.error(f"Preview generation failed: {e}")
            return error_response('Preview failed.', code='PREVIEW_FAILED', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================================
# Organization-wide Certificate Listing
# =============================================================================


@roles('educator', 'course_manager', 'admin', route_name='organization_certificates')
class OrganizationCertificateListView(generics.ListAPIView):
    """
    List every certificate that belongs to an event or course the current
    user is allowed to manage.

    GET /api/v1/certificates/organization/
    Supports ?search= (recipient name, short code), ?event=<uuid>, ?course=<uuid>,
    ?status=active|revoked.
    """

    serializer_class = serializers.CertificateListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = SmallPagination

    def get_queryset(self):
        user = self.request.user
        qs = Certificate.objects.filter(deleted_at__isnull=True).select_related(
            'registration', 'registration__event', 'course_enrollment', 'course_enrollment__course', 'template'
        )
        if not (
            user.groups.filter(name__in=INSTITUTION_CONTENT_GROUPS).exists()
        ):
            qs = qs.filter(
                Q(registration__event__owner=user) | Q(course_enrollment__course__owner=user)
            )

        params = self.request.query_params
        if event_uuid := params.get('event'):
            qs = qs.filter(registration__event__uuid=event_uuid)
        if course_uuid := params.get('course'):
            qs = qs.filter(course_enrollment__course__uuid=course_uuid)
        if status_filter := params.get('status'):
            qs = qs.filter(status=status_filter)
        if search := params.get('search'):
            qs = qs.filter(
                Q(registration__full_name__icontains=search)
                | Q(registration__email__icontains=search)
                | Q(course_enrollment__user__full_name__icontains=search)
                | Q(course_enrollment__user__email__icontains=search)
                | Q(short_code__icontains=search)
            )
        return qs.order_by('-created_at')


# =============================================================================
# Top-level Certificate Issue Endpoint
# =============================================================================


@roles('educator', 'course_manager', 'admin', route_name='certificate_issue')
class CertificateIssueView(generics.GenericAPIView):
    """
    POST /api/v1/certificates/issue/

    Unified issuance endpoint that accepts either registration_uuids or
    course_enrollment_uuids and dispatches through the certificate service.
    """

    serializer_class = serializers.CertificateIssueSerializer
    permission_classes = [IsAuthenticated, IsEducatorOrAdmin]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        force = data.get('force', False)

        from registrations.models import Registration
        from learning.models import CourseEnrollment
        from .services import certificate_service

        targets = []
        if data.get('registration_uuids'):
            regs = Registration.objects.filter(
                uuid__in=data['registration_uuids'], deleted_at__isnull=True
            ).select_related('event')
            for reg in regs:
                event = _get_writable_event(reg.event.uuid, request.user)
                if event is None:
                    targets.append(('skip', reg.uuid, 'NOT_AUTHORIZED', None))
                else:
                    targets.append(('registration', reg.uuid, None, reg))
        if data.get('course_enrollment_uuids'):
            enrollments = CourseEnrollment.objects.filter(
                uuid__in=data['course_enrollment_uuids'], deleted_at__isnull=True
            ).select_related('course')
            for enrollment in enrollments:
                course = _get_writable_course(enrollment.course.uuid, request.user)
                if course is None:
                    targets.append(('skip', enrollment.uuid, 'NOT_AUTHORIZED', None))
                else:
                    targets.append(('course_enrollment', enrollment.uuid, None, enrollment))

        issued = []
        skipped = []
        for kind, uuid_value, reason, obj in targets:
            if kind == 'skip':
                skipped.append({'uuid': str(uuid_value), 'reason': reason})
                continue

            if kind == 'registration':
                if not obj.can_receive_certificate:
                    skipped.append({'uuid': str(uuid_value), 'reason': 'NOT_ELIGIBLE'})
                    continue
                if obj.certificate_issued and not force:
                    skipped.append({'uuid': str(uuid_value), 'reason': 'ALREADY_ISSUED'})
                    continue
                result = certificate_service.issue_certificate(
                    registration=obj, issued_by=request.user, force=force
                )
            else:  # course_enrollment
                if obj.certificate_issued and not force:
                    skipped.append({'uuid': str(uuid_value), 'reason': 'ALREADY_ISSUED'})
                    continue
                result = certificate_service.issue_certificate(
                    course_enrollment=obj, issued_by=request.user, force=force
                )

            if result['success']:
                issued.append(str(result['certificate'].uuid))
            else:
                skipped.append(
                    {
                        'uuid': str(uuid_value),
                        'reason': result.get('code', 'ISSUE_FAILED'),
                        'detail': result.get('error'),
                    }
                )

        return Response(
            {
                'issued_count': len(issued),
                'skipped_count': len(skipped),
                'issued': issued,
                'skipped': skipped,
            }
        )


# =============================================================================
# Top-level Certificate Revoke Endpoint
# =============================================================================


@roles('educator', 'course_manager', 'admin', route_name='certificate_revoke')
class CertificateRevokeView(APIView):
    """
    POST /api/v1/certificates/<uuid>/revoke/

    Revokes a certificate the current user is allowed to manage.
    Body: { "reason": "..." }
    """

    permission_classes = [IsAuthenticated, IsEducatorOrAdmin]

    def post(self, request, uuid):
        try:
            certificate = Certificate.objects.select_related(
                'registration__event', 'course_enrollment__course'
            ).get(uuid=uuid, deleted_at__isnull=True)
        except Certificate.DoesNotExist:
            return error_response(
                'Certificate not found.',
                code='NOT_FOUND',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # Authorization: the user must be able to manage the underlying event/course.
        authorized = False
        if certificate.event is not None:
            authorized = _get_writable_event(certificate.event.uuid, request.user) is not None
        elif certificate.course is not None:
            authorized = _get_writable_course(certificate.course.uuid, request.user) is not None

        if not authorized:
            return error_response(
                'Not authorized to revoke this certificate.',
                code='FORBIDDEN',
                status_code=status.HTTP_403_FORBIDDEN,
            )

        serializer = serializers.CertificateRevokeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if certificate.status == 'revoked':
            return error_response('Certificate already revoked.', code='ALREADY_REVOKED')

        certificate.revoke(request.user, reason=serializer.validated_data['reason'])
        return Response(serializers.CertificateDetailSerializer(certificate).data)


# =============================================================================
# Event Certificates ViewSet
# =============================================================================


class EventCertificateFilter(filters.FilterSet):
    """Filter certificates."""

    status = filters.ChoiceFilter(choices=Certificate.Status.choices)

    class Meta:
        model = Certificate
        fields = ['status']


@roles('educator', 'admin', route_name='event_certificates')
class EventCertificateViewSet(viewsets.ModelViewSet):
    """
    Manage certificates for an event.

    Nested under events: /api/v1/events/{event_uuid}/certificates/
    """

    permission_classes = [IsAuthenticated, IsEducatorOrAdmin]
    pagination_class = SmallPagination  # M5: Nested resource pagination
    filterset_class = EventCertificateFilter
    ordering = ['-created_at']
    lookup_field = 'uuid'

    def get_queryset(self):
        event_uuid = self.kwargs.get('event_uuid')
        event = _get_writable_event(event_uuid, self.request.user)
        if event is None:
            return Certificate.objects.none()
        return Certificate.objects.filter(
            registration__event=event, deleted_at__isnull=True
        ).select_related('registration', 'registration__event', 'template')

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.CertificateListSerializer
        return serializers.CertificateDetailSerializer

    @swagger_auto_schema(
        operation_summary="Issue certificates",
        operation_description="Issue certificates to one or more registrations.",
        request_body=serializers.CertificateIssueSerializer,
    )
    @action(detail=False, methods=['post'])
    def issue(self, request, event_uuid=None):
        """Issue certificates to registrations."""
        serializer = serializers.CertificateIssueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from registrations.models import Registration

        event = _get_writable_event(event_uuid, request.user)
        if event is None:
            return error_response('Event not found.', code='NOT_FOUND', status_code=status.HTTP_404_NOT_FOUND)

        if not event.certificates_enabled:
            return error_response('Certificates not enabled for this event.', code='NOT_ENABLED')

        force = serializer.validated_data.get('force', False)
        issued = []
        skipped = []

        if serializer.validated_data.get('issue_all_eligible'):
            registrations = Registration.objects.filter(
                event=event, status='confirmed', deleted_at__isnull=True
            ).filter(Q(attendance_eligible=True) | Q(attendance_override=True))
            if not force:
                registrations = registrations.exclude(certificate_issued=True)
        elif serializer.validated_data.get('registration_uuids'):
            registrations = Registration.objects.filter(
                event=event,
                uuid__in=serializer.validated_data['registration_uuids'],
                deleted_at__isnull=True,
            )
        else:
            registrations = Registration.objects.none()

        from .services import certificate_service

        for reg in registrations:
            if not reg.can_receive_certificate:
                skipped.append({'uuid': str(reg.uuid), 'reason': 'NOT_ELIGIBLE'})
                continue

            if reg.certificate_issued and not force:
                skipped.append({'uuid': str(reg.uuid), 'reason': 'ALREADY_ISSUED'})
                continue

            result = certificate_service.issue_certificate(
                registration=reg, issued_by=request.user, force=force
            )

            if result['success']:
                issued.append(str(result['certificate'].uuid))
            else:
                skipped.append(
                    {
                        'uuid': str(reg.uuid),
                        'reason': result.get('code', 'ISSUE_FAILED'),
                        'detail': result.get('error'),
                    }
                )
                logger.warning(
                    "Failed to issue certificate for registration %s: %s",
                    reg.uuid,
                    result.get('error'),
                )

        return Response(
            {
                'issued_count': len(issued),
                'skipped_count': len(skipped),
                'issued': issued,
                'skipped': skipped,
            }
        )

    @swagger_auto_schema(
        operation_summary="Revoke certificate",
        operation_description="Revoke a previously issued certificate.",
        request_body=serializers.CertificateRevokeSerializer,
        responses={200: serializers.CertificateDetailSerializer, 400: '{"error": {"code": "ALREADY_REVOKED"}}'},
    )
    @action(detail=True, methods=['post'])
    def revoke(self, request, event_uuid=None, uuid=None):
        """Revoke a certificate."""
        certificate = self.get_object()
        serializer = serializers.CertificateRevokeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if certificate.status == 'revoked':
            return error_response('Certificate already revoked.', code='ALREADY_REVOKED')

        certificate.revoke(request.user, reason=serializer.validated_data['reason'])

        return Response(serializers.CertificateDetailSerializer(certificate).data)

    @swagger_auto_schema(
        operation_summary="Certificate summary",
        operation_description="Get aggregate statistics for event certificates.",
    )
    @action(detail=False, methods=['get'])
    def summary(self, request, event_uuid=None):
        """Get certificate summary for event."""
        qs = self.get_queryset()

        return Response(
            {
                'total': qs.count(),
                'issued': qs.filter(status='active').count(),
                'pending': qs.filter(status='pending').count(),
                'revoked': qs.filter(status='revoked').count(),
            }
        )


# =============================================================================
# Public Verification
# =============================================================================


@roles('public', route_name='certificate_verification')
class CertificateVerificationView(generics.RetrieveAPIView):
    """
    GET /api/v1/public/certificates/verify/{code}/

    Public certificate verification.
    Supports both short_code (8 chars) and full verification_code lookup.
    """

    serializer_class = serializers.PublicCertificateVerificationSerializer
    permission_classes = [AllowAny]
    lookup_field = 'short_code'
    lookup_url_kwarg = 'code'

    def get_queryset(self):
        return Certificate.objects.filter(deleted_at__isnull=True).select_related(
            'registration', 'registration__event', 'registration__event__owner'
        )

    def get_object(self):
        """Override to support both short_code and verification_code lookup."""
        code = self.kwargs.get('code')
        queryset = self.get_queryset()

        # Try short_code first (8 characters, alphanumeric)
        if len(code) <= 10:
            try:
                obj = queryset.get(short_code__iexact=code)
                self.check_object_permissions(self.request, obj)
                return obj
            except Certificate.DoesNotExist:
                pass

        # Try full verification_code (longer, URL-safe string)
        try:
            obj = queryset.get(verification_code=code)
            self.check_object_permissions(self.request, obj)
            return obj
        except Certificate.DoesNotExist:
            pass

        # If neither works, raise 404
        from rest_framework.exceptions import NotFound

        raise NotFound('Certificate not found with the provided code.')

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        owner_user = None
        if instance.registration is not None:
            owner_user = instance.registration.user
        elif instance.course_enrollment is not None:
            owner_user = instance.course_enrollment.user

        is_owner = request.user.is_authenticated and owner_user == request.user

        event = instance.event
        if is_owner and event is not None and event.require_feedback_for_certificate:
            from feedback.models import EventFeedback

            feedback_exists = EventFeedback.objects.filter(
                event=event, registration=instance.registration
            ).exists()

            if not feedback_exists:
                return error_response(
                    'Please submit feedback for this event before accessing your certificate.',
                    code='FEEDBACK_REQUIRED',
                    status_code=status.HTTP_403_FORBIDDEN,
                )

        instance.view_count = (instance.view_count or 0) + 1
        update_fields = ['view_count']
        if not instance.first_viewed_at:
            instance.first_viewed_at = timezone.now()
            update_fields.append('first_viewed_at')
        instance.save(update_fields=update_fields)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class CertificateQrCodeView(APIView):
    """
    GET /api/v1/public/certificates/verify/<code>/qr.svg

    Streams a cacheable SVG QR code whose payload is the public verification
    URL for a given short or verification code. No data is leaked — the QR
    encodes only the verify-page URL.
    """

    permission_classes = [AllowAny]

    def get(self, request, code):
        import io

        import qrcode
        import qrcode.image.svg
        from django.conf import settings

        site_url = getattr(settings, 'SITE_URL', request.build_absolute_uri('/'))
        target = f"{site_url.rstrip('/')}/verify/{code}"

        factory = qrcode.image.svg.SvgImage
        img = qrcode.make(target, image_factory=factory, box_size=10, border=2)
        buffer = io.BytesIO()
        img.save(buffer)
        response = HttpResponse(buffer.getvalue(), content_type='image/svg+xml')
        response['Cache-Control'] = 'public, max-age=3600'
        return response


# =============================================================================
# Attendee Certificates
# =============================================================================


@roles('learner', 'educator', 'admin', route_name='my_certificates')
class MyCertificateViewSet(ReadOnlyModelViewSet):
    """
    Current user's certificates.

    GET /api/v1/users/me/certificates/
    GET /api/v1/users/me/certificates/{uuid}/
    """

    serializer_class = serializers.MyCertificateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Include certificates from both event registrations and course enrollments
        return Certificate.objects.filter(
            Q(registration__user=self.request.user) | Q(course_enrollment__user=self.request.user), deleted_at__isnull=True
        ).select_related('registration__event', 'registration', 'course_enrollment__course', 'course_enrollment')

    @swagger_auto_schema(
        operation_summary="Download certificate",
        operation_description="Get a signed download URL for the certificate PDF.",
        responses={200: '{"download_url": "..."}', 400: '{"error": {}}', 403: '{"error": {"code": "FEEDBACK_REQUIRED"}}'},
    )
    @action(detail=True, methods=['post'])
    def download(self, request, uuid=None):
        """Track and return download URL."""
        certificate = self.get_object()

        if certificate.status != 'active':
            return error_response('Certificate not available.', code='NOT_AVAILABLE')

        # Feedback gate only applies to event certificates.
        event = certificate.event
        if event is not None and event.require_feedback_for_certificate:
            from feedback.models import EventFeedback

            feedback_exists = EventFeedback.objects.filter(
                event=event, registration=certificate.registration
            ).exists()

            if not feedback_exists:
                return error_response(
                    'Please submit feedback for this event before downloading your certificate.',
                    code='FEEDBACK_REQUIRED',
                    status_code=status.HTTP_403_FORBIDDEN,
                )

        # Track download
        certificate.download_count = (certificate.download_count or 0) + 1
        certificate.save(update_fields=['download_count'])

        # M7: Generate signed URL
        from .services import certificate_service

        return Response(
            {
                'download_url': certificate_service.get_pdf_url(certificate, expiration_minutes=60),
            }
        )
