"""Ensure every `is_staff=True` user is also a member of the `admin` group.

Phase 3 of the user-management rework migrates application authorization off
of `is_staff` onto the `admin` Django group. This migration is idempotent and
non-destructive — it does NOT flip `is_staff=False`. Django's own `/admin/`
site still uses `is_staff` for its own gating; we only care that any user who
historically had admin power via `is_staff` now also has it via the group, so
the application-layer sweep away from `is_staff` doesn't silently lock them
out.
"""

from django.db import migrations


def forwards(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Group = apps.get_model("auth", "Group")

    admin_group, _ = Group.objects.get_or_create(name="admin")

    staff_users = User.objects.filter(is_staff=True)
    for user in staff_users:
        if not user.groups.filter(pk=admin_group.pk).exists():
            user.groups.add(admin_group)


def backwards(apps, schema_editor):
    # Non-destructive forward migration; nothing to undo.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_userrolechange"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
