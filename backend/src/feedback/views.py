from django.db import models as django_models
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import EventFeedback
from .serializers import EventFeedbackSerializer
from common.permissions import IsOrganizerOrReadOnly, IsOwnerOrReadOnly
from common.rbac import roles


@roles('attendee', 'organizer', 'admin', route_name='event_feedback')
class EventFeedbackViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing event feedback.
    
    - Attendees can create feedback for events they attended.
    - Organizers can view feedback for their events.
    """
    queryset = EventFeedback.objects.all()
    serializer_class = EventFeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return EventFeedback.objects.all()

        # Combined query:
        # Feedback for events owned by user OR feedback created by user (via registration)
        # Handle null registration.user for guest registrations by matching email
        return EventFeedback.objects.filter(
            django_models.Q(event__owner=user) |
            django_models.Q(registration__user=user) |
            django_models.Q(registration__user__isnull=True, registration__email__iexact=user.email)
        ).distinct()

    def perform_create(self, serializer):
        # Ensure the user owns the registration they are submitting for
        # This is a critical security check to prevent submitting for others
        registration = serializer.validated_data.get('registration')
        user = self.request.user

        # Check ownership: either user is linked OR emails match (for guest registrations)
        is_owner = (
            registration.user == user or
            (registration.user is None and registration.email.lower() == user.email.lower())
        )

        if not is_owner:
            raise permissions.PermissionDenied("You can only submit feedback for your own registration.")

        serializer.save()
