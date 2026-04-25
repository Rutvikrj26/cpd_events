"""Internal cron tick endpoint.

Single endpoint that fans out to every periodic Cloud Task. Cloud Scheduler
hits this on a fixed cadence (every minute in prod). For local development,
operators can curl it with the shared secret.

Auth model:
- Production:  ``Authorization: Bearer <CRON_SHARED_SECRET>`` header. The
  Cloud Scheduler job is configured with the same secret via Terraform.
  This is intentionally simple — upgrading to OIDC verification is tracked
  as a follow-up; the value of OIDC over a strong secret here is small
  given the endpoint just dispatches already-idempotent tasks.
- DEBUG/dev:   if ``CRON_SHARED_SECRET`` is unset, requests from localhost
  are allowed unauthenticated to keep local iteration cheap.
"""

import logging

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


def _is_authorized(request) -> bool:
    secret = getattr(settings, 'CRON_SHARED_SECRET', '') or ''
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if secret:
        expected = f"Bearer {secret}"
        return auth == expected
    # No secret configured — only permit local (dev) traffic.
    if not getattr(settings, 'DEBUG', False):
        return False
    remote = request.META.get('REMOTE_ADDR', '')
    return remote in ('127.0.0.1', '::1', 'localhost')


class CronTickView(APIView):
    """Fan-out to every periodic task. Idempotent under repeat invocation."""

    # Disable DRF authentication so our Bearer-secret check isn't intercepted
    # by JWT auth (which would 401 on a non-JWT bearer value).
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request):
        if not _is_authorized(request):
            return Response({'detail': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        # Lazy imports so settings are loaded and to keep the endpoint small.
        from events.tasks import auto_complete_events, send_event_reminders
        from integrations.tasks import dispatch_scheduled_emails, retry_failed_emails

        results = {}
        for name, task in (
            ('dispatch_scheduled_emails', dispatch_scheduled_emails),
            ('send_event_reminders', send_event_reminders),
            ('auto_complete_events', auto_complete_events),
            ('retry_failed_emails', retry_failed_emails),
        ):
            try:
                task.delay()
                results[name] = 'queued'
            except Exception as e:
                logger.exception("Cron tick: failed to queue %s", name)
                results[name] = f'error: {e}'
        return Response({'status': 'ok', 'tasks': results})
