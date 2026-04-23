"""Daily Stripe drift check.

Usage::

    python manage.py reconcile_stripe [--hours 26]

Compares Stripe's view of PaymentIntents / Subscriptions / Refunds / Disputes
/ Checkout Sessions against local state. Logs drift; attempts safe
auto-repair for missed webhook fulfilment.
"""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from billing.reconciliation import reconcile


class Command(BaseCommand):
    help = "Reconcile Stripe state with local DB over the last N hours."

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours",
            type=int,
            default=26,
            help="Lookback window in hours (default 26 for daily run with overlap).",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Emit findings as JSON (for scripted consumption).",
        )

    def handle(self, *args, **options):
        result = reconcile(hours=options["hours"])
        if options["json"]:
            self.stdout.write(json.dumps(result, default=str, indent=2))
            return

        summary = result["summary"]
        self.stdout.write(self.style.SUCCESS(
            f"Reconciled since {summary['since']} — {summary['total']} drift finding(s)."
        ))
        for kind, count in summary["by_kind"].items():
            self.stdout.write(f"  {kind}: {count}")
        for f in result["findings"]:
            self.stdout.write(
                f"  • {f['entity']:<18} {f['stripe_id']:<40} {f['kind']}  {f['detail']}"
            )
