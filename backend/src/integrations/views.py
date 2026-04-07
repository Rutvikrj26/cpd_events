"""
Integrations app views - Email logs API.
"""

from rest_framework.permissions import IsAuthenticated

from common.permissions import IsContentCreator
from common.rbac import roles
from common.viewsets import ReadOnlyModelViewSet

from . import serializers
from .models import EmailLog


# =============================================================================
# Email Logs (for debugging)
# =============================================================================


@roles('educator', 'course_manager', 'admin', route_name='email_logs')
class EmailLogViewSet(ReadOnlyModelViewSet):
    """
    View email logs for an event.

    GET /api/v1/events/{event_uuid}/emails/
    """

    serializer_class = serializers.EmailLogSerializer
    permission_classes = [IsAuthenticated, IsContentCreator]

    def get_queryset(self):
        event_uuid = self.kwargs.get('event_uuid')
        qs_filter = {'event__uuid': event_uuid}
        if not self.request.user.is_staff:
            qs_filter['event__owner'] = self.request.user
        return EmailLog.objects.filter(**qs_filter).order_by('-created_at')
