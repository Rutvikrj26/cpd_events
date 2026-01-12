import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_add_course_manager_account_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='When this record was created')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='When this record was last modified')),
                (
                    'uuid',
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        unique=True,
                        help_text='Public identifier for external use',
                    ),
                ),
                (
                    'notification_type',
                    models.CharField(
                        choices=[
                            ('org_invite', 'Organization Invitation'),
                            ('payment_failed', 'Payment Failed'),
                            ('refund_processed', 'Refund Processed'),
                            ('trial_ending', 'Trial Ending'),
                            ('payment_method_expired', 'Payment Method Expired'),
                            ('system', 'System'),
                        ],
                        db_index=True,
                        default='system',
                        max_length=50,
                    ),
                ),
                ('title', models.CharField(max_length=255)),
                ('message', models.TextField(blank=True)),
                ('action_url', models.CharField(blank=True, max_length=500)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('read_at', models.DateTimeField(blank=True, null=True)),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
            options={
                'db_table': 'notifications',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['user', 'notification_type'], name='notifications_user_n_1d3c7d_idx'),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['user', 'read_at'], name='notifications_user_r_0f6b4a_idx'),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['-created_at'], name='notifications_created_1b2e7f_idx'),
        ),
    ]
