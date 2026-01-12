from django.core.management.base import BaseCommand

from billing.reconciliation import reconcile_payment_intents


class Command(BaseCommand):
    help = "Reconcile recent Stripe payment intents with local registrations"

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to look back',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=200,
            help='Maximum number of Stripe intents to fetch',
        )

    def handle(self, *args, **options):
        days = options['days']
        limit = options['limit']

        result = reconcile_payment_intents(days=days, limit=limit)
        if not result.get('success'):
            self.stdout.write(self.style.ERROR(result.get('error', 'Reconciliation failed')))
            return

        summary = result['summary']
        self.stdout.write(self.style.MIGRATE_HEADING('Reconciliation Summary'))
        self.stdout.write(f"Stripe intents: {summary['stripe_intents']}")
        self.stdout.write(f"DB registrations: {summary['db_registrations']}")
        self.stdout.write(f"Missing in DB: {summary['missing_in_db']}")
        self.stdout.write(f"Missing in Stripe: {summary['missing_in_stripe']}")

        if result['missing_in_db']:
            self.stdout.write(self.style.WARNING("\nStripe intents missing in DB:"))
            for item in result['missing_in_db'][:20]:
                self.stdout.write(f"- {item['stripe_payment_intent_id']} {item['amount_cents']} {item['currency']}")

        if result['missing_in_stripe']:
            self.stdout.write(self.style.WARNING("\nDB registrations missing in Stripe:"))
            for item in result['missing_in_stripe'][:20]:
                self.stdout.write(f"- {item['payment_intent_id']} ({item['registration_uuid']})")
