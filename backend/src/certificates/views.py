"""
Certificates app views and viewsets.
"""

from django.db.models import Q
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from common.pagination import SmallPagination
from common.permissions import IsOrganizer
from common.utils import error_response
from common.viewsets import ReadOnlyModelViewSet, SoftDeleteModelViewSet

from . import serializers
from .models import Certificate, CertificateTemplate

# =============================================================================
# Certificate Template ViewSet
# =============================================================================


class CertificateTemplateViewSet(SoftDeleteModelViewSet):
    """
    Manage certificate templates.

    GET /api/v1/certificate-templates/
    POST /api/v1/certificate-templates/
    GET /api/v1/certificate-templates/{uuid}/
    PATCH /api/v1/certificate-templates/{uuid}/
    DELETE /api/v1/certificate-templates/{uuid}/
    """

    permission_classes = [IsAuthenticated, IsOrganizer]

    def get_queryset(self):
        return CertificateTemplate.objects.filter(owner=self.request.user, deleted_at__isnull=True)

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


# =============================================================================
# Event Certificates ViewSet
# =============================================================================


class EventCertificateFilter(filters.FilterSet):
    """Filter certificates."""

    status = filters.ChoiceFilter(choices=Certificate.Status.choices)

    class Meta:
        model = Certificate
        fields = ['status']


class EventCertificateViewSet(viewsets.ModelViewSet):
    """
    Manage certificates for an event.

    Nested under events: /api/v1/events/{event_uuid}/certificates/
    """

    permission_classes = [IsAuthenticated, IsOrganizer]
    pagination_class = SmallPagination  # M5: Nested resource pagination
    filterset_class = EventCertificateFilter
    ordering = ['-created_at']

    def get_queryset(self):
        event_uuid = self.kwargs.get('event_uuid')
        return Certificate.objects.filter(
            event__uuid=event_uuid, event__owner=self.request.user, deleted_at__isnull=True
        ).select_related('registration', 'event', 'template')

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

        from events.models import Event
        from registrations.models import Registration

        try:
            event = Event.objects.get(uuid=event_uuid, owner=request.user)
        except Event.DoesNotExist:
            return error_response('Event not found.', code='NOT_FOUND', status_code=status.HTTP_404_NOT_FOUND)

        if not event.certificates_enabled:
            return error_response('Certificates not enabled for this event.', code='NOT_ENABLED')

        issued = []
        skipped = []

        if serializer.validated_data.get('issue_all_eligible'):
            # Issue to all eligible registrations
            registrations = (
                Registration.objects.filter(event=event, status='confirmed', deleted_at__isnull=True)
                .filter(Q(attendance_eligible=True) | Q(attendance_override=True))
                .exclude(certificate_issued=True)
            )
        elif serializer.validated_data.get('registration_uuids'):
            registrations = Registration.objects.filter(
                event=event, uuid__in=serializer.validated_data['registration_uuids'], deleted_at__isnull=True
            )
        else:
            registrations = []

        for reg in registrations:
            # Check eligibility
            if not reg.can_receive_certificate:
                skipped.append(str(reg.uuid))
                continue

            # Check if already issued
            if reg.certificate_issued:
                skipped.append(str(reg.uuid))
                continue

            # Create certificate
            cert = Certificate.objects.create(
                event=event,
                registration=reg,
                template=event.certificate_template,
                status='issued',
                issued_at=timezone.now(),
                certificate_data={
                    'recipient_name': reg.full_name,
                    'event_title': event.title,
                    'event_date': event.starts_at.strftime('%B %d, %Y') if event.starts_at else '',
                    'cpd_credits': str(event.cpd_credits) if event.cpd_credits else '',
                    'cpd_type': event.cpd_type_display,
                    'organizer_name': event.owner.display_name,
                },
            )

            # Mark registration
            reg.certificate_issued = True
            reg.certificate_issued_at = timezone.now()
            reg.save(update_fields=['certificate_issued', 'certificate_issued_at', 'updated_at'])

            issued.append(str(cert.uuid))

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

        certificate.revoke(reason=serializer.validated_data['reason'], revoked_by=request.user)

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
                'issued': qs.filter(status='issued').count(),
                'pending': qs.filter(status='pending').count(),
                'revoked': qs.filter(status='revoked').count(),
            }
        )


# =============================================================================
# Public Verification
# =============================================================================


class CertificateVerificationView(generics.RetrieveAPIView):
    """
    GET /api/v1/public/certificates/verify/{code}/

    Public certificate verification.
    """

    serializer_class = serializers.PublicCertificateVerificationSerializer
    permission_classes = [AllowAny]
    lookup_field = 'short_code'
    lookup_url_kwarg = 'code'

    def get_queryset(self):
        return Certificate.objects.filter(deleted_at__isnull=True).select_related('event', 'event__owner', 'registration')

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        # Track view
        instance.view_count = (instance.view_count or 0) + 1
        instance.last_viewed_at = timezone.now()
        instance.save(update_fields=['view_count', 'last_viewed_at'])

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


# =============================================================================
# Attendee Certificates
# =============================================================================


class MyCertificateViewSet(ReadOnlyModelViewSet):
    """
    Current user's certificates.

    GET /api/v1/users/me/certificates/
    GET /api/v1/users/me/certificates/{uuid}/
    """

    serializer_class = serializers.MyCertificateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Certificate.objects.filter(registration__user=self.request.user, deleted_at__isnull=True).select_related(
            'event', 'registration'
        )

    @swagger_auto_schema(
        operation_summary="Download certificate",
        operation_description="Get a signed download URL for the certificate PDF.",
        responses={200: '{"download_url": "..."}', 400: '{"error": {}}'},
    )
    @action(detail=True, methods=['post'])
    def download(self, request, uuid=None):
        """Track and return download URL."""
        certificate = self.get_object()

        if certificate.status != 'issued':
            return error_response('Certificate not available.', code='NOT_AVAILABLE')

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
