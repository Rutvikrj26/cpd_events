# Migration to simplify pricing from 5 tiers to 2 tiers

from django.db import migrations


def consolidate_plans_forward(apps, schema_editor):
    """
    Consolidate plans to 2 tiers:
    - Professional: $49/mo (was Starter/Organizer)
    - Organization: $199/mo (was Premium)

    Migration strategy:
    - starter → professional
    - premium → organization
    - organizer → professional (already mapped)
    """
    Subscription = apps.get_model('billing', 'Subscription')

    # Migrate starter to professional
    starter_count = Subscription.objects.filter(plan='starter').update(plan='professional')
    print(f"Migrated {starter_count} starter subscriptions to professional")

    # Migrate premium to organization
    premium_count = Subscription.objects.filter(plan='premium').update(plan='organization')
    print(f"Migrated {premium_count} premium subscriptions to organization")

    # organizer already maps to professional, no change needed


def consolidate_plans_reverse(apps, schema_editor):
    """
    Reverse migration - can't fully restore original plans.
    Map professional → starter, organization → premium as best guess.
    """
    Subscription = apps.get_model('billing', 'Subscription')

    # This is a lossy reversal - we don't know which professional was originally starter
    # Best effort: keep as is since legacy values still exist
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0004_stripe_product_models'),
    ]

    operations = [
        migrations.RunPython(consolidate_plans_forward, consolidate_plans_reverse),
    ]
