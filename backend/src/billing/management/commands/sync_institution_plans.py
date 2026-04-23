"""Create Stripe Product + Price for every active InstitutionPlan.

Run once (or whenever new plans are added) before subscription checkout can
work. Idempotent — skips plans that already have ``stripe_price_id`` unless
``--force`` is passed.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from billing.client import get_stripe
from billing.models import InstitutionPlan


class Command(BaseCommand):
    help = "Sync InstitutionPlan rows to Stripe Products + Prices."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-create Product + Price even when stripe_price_id is already set.",
        )

    def handle(self, *args, **options):
        stripe = get_stripe()
        force = options["force"]
        synced = 0

        for plan in InstitutionPlan.objects.filter(is_active=True):
            if plan.stripe_price_id and not force:
                self.stdout.write(f"skip: {plan.name} (already has stripe_price_id)")
                continue

            product_id = plan.stripe_product_id
            if not product_id or force:
                product = stripe.Product.create(
                    name=plan.name,
                    description=(plan.description or plan.name)[:500],
                    metadata={"plan_uuid": str(plan.uuid)},
                    idempotency_key=f"plan-product:{plan.uuid}:v1",
                )
                product_id = product.id
                plan.stripe_product_id = product_id

            interval = "month" if plan.billing_interval == InstitutionPlan.BillingInterval.MONTH else "year"
            price = stripe.Price.create(
                product=product_id,
                unit_amount=plan.price_cents,
                currency="cad",
                recurring={"interval": interval},
                metadata={"plan_uuid": str(plan.uuid)},
                idempotency_key=f"plan-price:{plan.uuid}:{interval}:{plan.price_cents}:v1",
            )
            plan.stripe_price_id = price.id
            plan.save(update_fields=["stripe_product_id", "stripe_price_id", "updated_at"])
            synced += 1
            self.stdout.write(self.style.SUCCESS(f"synced: {plan.name} → {price.id}"))

        self.stdout.write(self.style.SUCCESS(f"Done. {synced} plan(s) synced."))
