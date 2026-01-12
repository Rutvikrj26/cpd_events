from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0007_subscription_usage_reset_and_disputes'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='billing_interval',
            field=models.CharField(choices=[('month', 'Monthly'), ('year', 'Annual')], default='month', max_length=10),
        ),
        migrations.AddField(
            model_name='subscription',
            name='pending_plan',
            field=models.CharField(
                blank=True,
                choices=[
                    ('attendee', 'Attendee'),
                    ('organizer', 'Organizer'),
                    ('lms', 'LMS'),
                    ('organization', 'Organization'),
                ],
                help_text='Scheduled plan change at period end, if any',
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='subscription',
            name='pending_billing_interval',
            field=models.CharField(
                blank=True,
                choices=[('month', 'Monthly'), ('year', 'Annual')],
                help_text='Scheduled billing interval change at period end, if any',
                max_length=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='subscription',
            name='pending_change_at',
            field=models.DateTimeField(blank=True, help_text='When a pending plan change should take effect', null=True),
        ),
    ]
