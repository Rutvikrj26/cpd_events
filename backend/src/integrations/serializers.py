"""
Integrations app serializers.
"""

from rest_framework import serializers

from common.serializers import BaseModelSerializer

from .models import EmailLog


# =============================================================================
# Email Log Serializers
# =============================================================================


class EmailLogSerializer(BaseModelSerializer):
    """Email log entry."""

    class Meta:
        model = EmailLog
        fields = [
            'uuid',
            'recipient_email',
            'email_type',
            'subject',
            'status',
            'sent_at',
            'delivered_at',
            'opened_at',
            'clicked_at',
            'error_message',
            'created_at',
        ]
        read_only_fields = fields
