"""
Migration to add 'admin' to AccountType choices and upgrade existing org admins.
"""

from django.db import migrations, models
from django.utils import timezone


def upgrade_existing_org_admins(apps, schema_editor):
    """
    Upgrade all existing org admins to account_type='admin'.

    This finds users who are currently active organization admins and upgrades
    their account_type to 'admin', allowing them to create both events and courses.
    """
    User = apps.get_model("accounts", "User")
    OrganizationMembership = apps.get_model("organizations", "OrganizationMembership")

    # Find all users who are active org admins
    admin_user_ids = (
        OrganizationMembership.objects.filter(
            role="admin",
            is_active=True,
        )
        .values_list("user_id", flat=True)
        .distinct()
    )

    # Upgrade them to admin account type
    updated = User.objects.filter(id__in=admin_user_ids).update(
        account_type="admin",
        updated_at=timezone.now(),
    )

    if updated > 0:
        print(f"Upgraded {updated} existing org admins to account_type='admin'")


def reverse_upgrade(apps, schema_editor):
    """
    Downgrade admin account types back to organizer.

    This is the reverse operation - not perfect since we don't know what
    they were before, but organizer is a reasonable fallback.
    """
    User = apps.get_model("accounts", "User")

    # Downgrade all admins to organizer (safe fallback)
    User.objects.filter(account_type="admin").update(
        account_type="organizer",
        updated_at=timezone.now(),
    )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_initial"),
        ("organizations", "0001_initial"),  # Need this for OrganizationMembership
    ]

    operations = [
        # First, alter the field to add the new choice
        migrations.AlterField(
            model_name="user",
            name="account_type",
            field=models.CharField(
                choices=[
                    ("attendee", "Attendee"),
                    ("organizer", "Organizer"),
                    ("course_manager", "Course Manager"),
                    ("admin", "Admin"),
                ],
                db_index=True,
                default="attendee",
                help_text="Account type determines available features",
                max_length=20,
            ),
        ),
        # Then, run the data migration to upgrade existing org admins
        migrations.RunPython(upgrade_existing_org_admins, reverse_upgrade),
    ]
