"""Stripe webhook endpoint.

Verify signature → persist ``StripeEvent`` (unique key dedupes replays) →
enqueue the async worker → return 200. All business logic lives in
``billing.handlers``; the worker in ``billing.tasks.process_stripe_event``
re-fetches the canonical event and dispatches to the matching handler.
"""

from __future__ import annotations

import logging

from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from billing.client import get_stripe, webhook_secret

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(View):
    """POST /api/v1/webhooks/stripe/"""

    def post(self, request):
        secret = webhook_secret()
        if not secret:
            logger.error("stripe.webhook.secret_missing")
            return HttpResponse(status=500)

        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
        if not sig_header:
            logger.warning("stripe.webhook.signature_missing")
            return HttpResponse(status=400)

        payload = request.body  # raw bytes — signature HMACs this, not JSON
        stripe = get_stripe()
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, secret)
        except ValueError:
            logger.warning("stripe.webhook.payload_invalid")
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError:
            logger.warning("stripe.webhook.signature_invalid")
            return HttpResponse(status=400)

        self._persist_and_enqueue(event)
        return HttpResponse(status=200)

    def _persist_and_enqueue(self, event) -> None:
        from billing.models import StripeEvent
        from billing.tasks import process_stripe_event

        from billing import metrics

        metrics.inc("stripe.webhook.received")
        metrics.inc(f"stripe.webhook.received.{event.type}")

        try:
            # Savepoint so a duplicate insert doesn't poison any outer
            # transaction (matters in tests; harmless in prod).
            with transaction.atomic():
                StripeEvent.objects.create(
                    event_id=event.id,
                    event_type=event.type,
                    payload=event.to_dict_recursive() if hasattr(event, "to_dict_recursive") else event.to_dict(),
                )
        except IntegrityError:
            metrics.inc("stripe.webhook.deduped")
            logger.info(
                "stripe.webhook.deduped",
                extra={"stripe_event_id": event.id, "stripe_event_type": event.type},
            )
            return
        logger.info(
            "stripe.webhook.received",
            extra={"stripe_event_id": event.id, "stripe_event_type": event.type},
        )
        try:
            process_stripe_event.delay(event.id)
        except Exception as exc:
            # If enqueue fails we still 200'd (event is safely persisted); the
            # reconciliation cron will pick up stragglers. Log loud so we notice.
            logger.error(
                "stripe.webhook.enqueue_failed",
                extra={"stripe_event_id": event.id, "error": str(exc)},
            )
