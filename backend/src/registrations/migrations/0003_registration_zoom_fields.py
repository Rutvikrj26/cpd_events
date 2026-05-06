"""Add Zoom registrant fields to Registration.

Both nullable / blank so legacy rows under the LiveKit provider remain
valid without backfill. Populated by the registration confirmation task
when the event's video provider is Zoom (see registrations/tasks.py).
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0002_registration_comped_by_registration_was_comped'),
    ]

    operations = [
        migrations.AddField(
            model_name='registration',
            name='zoom_registrant_id',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='Zoom registrant_id (returned by POST /meetings/{id}/registrants). Used to match webhook participant events back to this registration.',
                max_length=64,
            ),
        ),
        migrations.AddField(
            model_name='registration',
            name='zoom_registrant_join_url',
            field=models.URLField(
                blank=True,
                help_text='Personalized Zoom join URL with `tk=` token; not echoed in our emails (Zoom emails it directly).',
                max_length=1000,
            ),
        ),
    ]
