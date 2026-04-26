import logging

from django.db import models as django_models
from django.shortcuts import get_object_or_404
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.rbac import roles
from events.models import Event

from .models import EventFeedback, FeedbackField
from .serializers import (
    EventFeedbackSerializer,
    FeedbackFieldCreateSerializer,
    FeedbackFieldSerializer,
)

logger = logging.getLogger(__name__)


def _event_access_q(user, prefix: str = ''):
    """Q filter for events accessible by `user` (admin sees all)."""
    if user.groups.filter(name='admin').exists():
        return django_models.Q()
    owner_key = f'{prefix}owner'
    return django_models.Q(**{owner_key: user})


@roles('learner', 'organizer', 'admin', route_name='event_feedback')
class EventFeedbackViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing event feedback.

    - Attendees can create feedback for events they attended.
    - Organizers can view feedback for their events.
    """

    queryset = EventFeedback.objects.all()
    serializer_class = EventFeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'

    def get_queryset(self):
        user = self.request.user
        if user.groups.filter(name="admin").exists():
            queryset = EventFeedback.objects.all()
        else:
            queryset = EventFeedback.objects.filter(
                django_models.Q(event__owner=user)
                | django_models.Q(registration__user=user)
                | django_models.Q(registration__user__isnull=True, registration__email__iexact=user.email)
            ).distinct()

        queryset = queryset.select_related('event', 'session', 'registration').prefetch_related(
            'field_responses__field'
        )

        event_uuid = self.request.query_params.get('event')
        if event_uuid:
            queryset = queryset.filter(event__uuid=event_uuid)

        registration_uuid = self.request.query_params.get('registration')
        if registration_uuid:
            queryset = queryset.filter(registration__uuid=registration_uuid)

        session_uuid = self.request.query_params.get('session')
        if session_uuid:
            queryset = queryset.filter(session__uuid=session_uuid)

        return queryset

    def perform_create(self, serializer):
        registration = serializer.validated_data.get('registration')
        user = self.request.user

        is_owner = registration.user == user or (
            registration.user is None and registration.email.lower() == user.email.lower()
        )
        if not is_owner:
            raise permissions.PermissionDenied(
                "You can only submit feedback for your own registration."
            )

        feedback = serializer.save()
        self._auto_issue_certificate_after_feedback(registration, feedback)

    def _auto_issue_certificate_after_feedback(self, registration, feedback):
        from django.utils import timezone

        try:
            event = registration.event

            if registration.certificate_issued:
                return
            if registration.status != 'attended':
                return
            if not event.certificate_template:
                return

            event_end = event.end_datetime or event.start_datetime
            if event_end and event_end > timezone.now():
                return

            should_auto_issue = getattr(event, 'require_feedback_for_certificate', False) or getattr(
                event, 'auto_issue_certificates', True
            )
            if not should_auto_issue:
                return

            from certificates.services import certificate_service

            result = certificate_service.issue_certificate(
                registration=registration,
                template=event.certificate_template,
                issued_by=event.owner,
            )

            if result.get('success'):
                logger.info(f"Auto-issued certificate for registration {registration.uuid} after feedback")
                certificate = result.get('certificate')
                if certificate and not result.get('already_issued'):
                    certificate_service.send_certificate_email(certificate)
            else:
                logger.warning(f"Failed to auto-issue certificate: {result.get('error')}")

        except Exception as e:
            logger.error(f"Auto-certificate issuance failed: {e}")


@roles('organizer', 'admin', route_name='event_feedback_fields')
class EventFeedbackFieldViewSet(viewsets.ModelViewSet):
    """
    CRUD for an event's feedback form schema.

    Nested under events: /api/v1/events/{event_uuid}/feedback-fields/
    """

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'

    def get_queryset(self):
        event_uuid = self.kwargs.get('event_uuid')
        return FeedbackField.objects.filter(event__uuid=event_uuid).filter(
            _event_access_q(self.request.user, prefix='event__')
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return FeedbackFieldCreateSerializer
        return FeedbackFieldSerializer

    def perform_create(self, serializer):
        event_uuid = self.kwargs.get('event_uuid')
        event = get_object_or_404(
            Event.objects.filter(_event_access_q(self.request.user)),
            uuid=event_uuid,
        )
        max_order = self.get_queryset().order_by('-order').values_list('order', flat=True).first() or 0
        serializer.save(event=event, order=max_order + 1)

    @action(detail=False, methods=['post'])
    def reorder(self, request, event_uuid=None):
        field_order = request.data.get('order', [])
        for order, field_uuid in enumerate(field_order):
            self.get_queryset().filter(uuid=field_uuid).update(order=order)
        return Response({'message': 'Fields reordered.'})
