from django.db import models as django_models
from rest_framework import permissions, viewsets

from .models import EventFeedback
from .serializers import EventFeedbackSerializer


class EventFeedbackViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing event feedback.

    - Attendees can create feedback for events they attended.
    - Organizers can view feedback for their events.
    """

    queryset = EventFeedback.objects.all()
    serializer_class = EventFeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "uuid"

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            queryset = EventFeedback.objects.all()
        else:
            # Combined query:
            # Feedback for events owned by user OR feedback created by user (via registration)
            # Handle null registration.user for guest registrations by matching email
            queryset = EventFeedback.objects.filter(
                django_models.Q(event__owner=user)
                | django_models.Q(registration__user=user)
                | django_models.Q(registration__user__isnull=True, registration__email__iexact=user.email)
            ).distinct()

        event_uuid = self.request.query_params.get("event")
        if event_uuid:
            queryset = queryset.filter(event__uuid=event_uuid)

        registration_uuid = self.request.query_params.get("registration")
        if registration_uuid:
            queryset = queryset.filter(registration__uuid=registration_uuid)

        return queryset

    def perform_create(self, serializer):
        # Ensure the user owns the registration they are submitting for
        # This is a critical security check to prevent submitting for others
        registration = serializer.validated_data.get("registration")
        user = self.request.user

        # Check ownership: either user is linked OR emails match (for guest registrations)
        is_owner = registration.user == user or (registration.user is None and registration.email.lower() == user.email.lower())

        if not is_owner:
            raise permissions.PermissionDenied("You can only submit feedback for your own registration.")

        feedback = serializer.save()

        # Auto-issue certificate after feedback if conditions are met
        self._auto_issue_certificate_after_feedback(registration, feedback)

    def _auto_issue_certificate_after_feedback(self, registration, feedback):
        """
        Auto-issue certificate after feedback submission if conditions are met.

        Business Rule: Certificate is issued after:
        - Event is completed (end time has passed)
        - Attendee has attended (status = 'attended')
        - Certificate hasn't already been issued
        - Event has a certificate template configured
        - Event has auto_issue_certificates enabled (or require_feedback_for_certificate)
        """
        import logging

        from django.utils import timezone

        logger = logging.getLogger(__name__)

        try:
            event = registration.event

            # Check conditions
            if registration.certificate_issued:
                logger.debug(f"Certificate already issued for registration {registration.uuid}")
                return

            if registration.status != "attended":
                logger.debug(f"Registration {registration.uuid} not marked as attended")
                return

            if not event.certificate_template:
                logger.debug(f"No certificate template for event {event.uuid}")
                return

            # Check if event has ended
            event_end = event.end_datetime or event.start_datetime
            if event_end and event_end > timezone.now():
                logger.debug(f"Event {event.uuid} has not ended yet")
                return

            # Auto-issue if require_feedback_for_certificate OR auto_issue_certificates is enabled
            should_auto_issue = getattr(event, "require_feedback_for_certificate", False) or getattr(
                event, "auto_issue_certificates", True
            )

            if not should_auto_issue:
                logger.debug(f"Auto-issue not enabled for event {event.uuid}")
                return

            # Issue certificate
            from certificates.services import certificate_service

            result = certificate_service.issue_certificate(
                registration=registration,
                template=event.certificate_template,
                issued_by=event.owner,
            )

            if result.get("success"):
                logger.info(f"Auto-issued certificate for registration {registration.uuid} after feedback")

                # Send certificate email
                certificate = result.get("certificate")
                if certificate and not result.get("already_issued"):
                    certificate_service.send_certificate_email(certificate)
            else:
                logger.warning(f"Failed to auto-issue certificate: {result.get('error')}")

        except Exception as e:
            logger.error(f"Auto-certificate issuance failed: {e}")
