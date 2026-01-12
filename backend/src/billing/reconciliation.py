"""
Stripe reconciliation helpers.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from django.utils import timezone

from billing.services import stripe_service
from registrations.models import Registration


def reconcile_payment_intents(days: int = 30, limit: int = 200) -> dict:
    since = timezone.now() - timedelta(days=days)

    db_regs = Registration.objects.filter(
        payment_intent_id__isnull=False,
        payment_intent_id__gt='',
        created_at__gte=since,
        deleted_at__isnull=True,
    ).select_related('event')

    db_by_intent = {r.payment_intent_id: r for r in db_regs}

    stripe_result = stripe_service.list_payment_intents(created_gte=since, limit=limit)
    if not stripe_result.get('success'):
        return {
            'success': False,
            'error': stripe_result.get('error', 'Stripe not configured'),
        }

    stripe_intents = stripe_result.get('payment_intents', [])
    stripe_ids = {intent.id for intent in stripe_intents}

    missing_in_db = []
    for intent in stripe_intents:
        if intent.id in db_by_intent:
            continue
        missing_in_db.append(
            {
                'stripe_payment_intent_id': intent.id,
                'amount_cents': getattr(intent, 'amount', 0),
                'currency': getattr(intent, 'currency', 'usd'),
                'status': getattr(intent, 'status', ''),
                'created_at': datetime.fromtimestamp(
                    getattr(intent, 'created', 0),
                    tz=UTC,
                ).isoformat(),
            }
        )

    missing_in_stripe = []
    for intent_id, registration in db_by_intent.items():
        if intent_id in stripe_ids:
            continue
        missing_in_stripe.append(
            {
                'registration_uuid': str(registration.uuid),
                'payment_intent_id': intent_id,
                'event_title': registration.event.title if registration.event else '',
                'amount_cents': int((registration.total_amount or 0) * 100),
                'created_at': registration.created_at.isoformat(),
            }
        )

    return {
        'success': True,
        'summary': {
            'stripe_intents': len(stripe_intents),
            'db_registrations': len(db_by_intent),
            'missing_in_db': len(missing_in_db),
            'missing_in_stripe': len(missing_in_stripe),
            'since': since.isoformat(),
        },
        'missing_in_db': missing_in_db,
        'missing_in_stripe': missing_in_stripe,
    }
