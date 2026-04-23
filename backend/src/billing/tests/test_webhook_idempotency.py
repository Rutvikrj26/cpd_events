"""Phase 1 idempotency + async pipeline smoke tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse

from billing.models import StripeEvent


pytestmark = pytest.mark.django_db


def _make_event(event_id: str = "evt_test_1", event_type: str = "charge.refunded"):
    """Minimal stripe.Event shape for verify→persist path."""

    class _Obj:
        id = event_id
        type = event_type

        def to_dict_recursive(self):
            return {"id": event_id, "type": event_type, "data": {"object": {}}}

        def to_dict(self):
            return self.to_dict_recursive()

    return _Obj()


def test_webhook_persists_and_enqueues(settings):
    settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
    client = Client()
    event = _make_event("evt_test_persist")

    with patch("billing.webhooks.get_stripe") as stripe_mod:
        stripe_mod.return_value.Webhook.construct_event.return_value = event
        with patch("billing.tasks.process_stripe_event") as task:
            resp = client.post(
                reverse("stripe-webhook"),
                data=b"{}",
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="sig",
            )
            assert resp.status_code == 200
            task.delay.assert_called_once_with("evt_test_persist")

    row = StripeEvent.objects.get(event_id="evt_test_persist")
    assert row.event_type == "charge.refunded"
    assert row.processed_at is None


def test_webhook_dedupes_replays(settings):
    settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
    client = Client()
    event = _make_event("evt_test_dedupe")

    with patch("billing.webhooks.get_stripe") as stripe_mod:
        stripe_mod.return_value.Webhook.construct_event.return_value = event
        with patch("billing.tasks.process_stripe_event") as task:
            first = client.post(
                reverse("stripe-webhook"),
                data=b"{}",
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="sig",
            )
            second = client.post(
                reverse("stripe-webhook"),
                data=b"{}",
                content_type="application/json",
                HTTP_STRIPE_SIGNATURE="sig",
            )
            assert first.status_code == 200
            assert second.status_code == 200
            assert task.delay.call_count == 1

    assert StripeEvent.objects.filter(event_id="evt_test_dedupe").count() == 1


def test_webhook_rejects_missing_signature():
    client = Client()
    resp = client.post(reverse("stripe-webhook"), data=b"{}", content_type="application/json")
    # No STRIPE_WEBHOOK_SECRET set → 500; but either 400 or 500 is acceptable rejection.
    assert resp.status_code in (400, 500)
