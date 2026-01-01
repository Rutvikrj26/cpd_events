# Generated migration for new pricing tiers

from django.db import migrations


def migrate_legacy_plans_forward(apps, schema_editor):
    """
    Migrate existing subscriptions from legacy plans to new tiers.

    Mapping:
    - 'organizer' → 'professional' (same limits, new name)
    - 'organization' → keep as is (used by organizations, not individual subscriptions)
    """
    Subscription = apps.get_model('billing', 'Subscription')

    # Migrate 'organizer' to 'professional'
    updated_count = Subscription.objects.filter(plan='organizer').update(plan='professional')

    print(f"Migrated {updated_count} subscriptions from 'organizer' to 'professional'")


def migrate_legacy_plans_backward(apps, schema_editor):
    """Reverse migration - convert new plans back to legacy."""
    Subscription = apps.get_model('billing', 'Subscription')

    # Revert 'professional' back to 'organizer'
    Subscription.objects.filter(plan='professional').update(plan='organizer')

    # Revert new plan types to appropriate legacy equivalents
    Subscription.objects.filter(plan='starter').update(plan='organizer')
    Subscription.objects.filter(plan='premium').update(plan='organizer')


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0002_update_plan_choices'),
    ]

    operations = [
        migrations.RunPython(migrate_legacy_plans_forward, migrate_legacy_plans_backward),
    ]
