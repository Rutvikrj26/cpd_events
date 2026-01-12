import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_notification'),
        ('organizations', '0007_add_organization_is_public'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
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
                ('action', models.CharField(db_index=True, max_length=120)),
                ('object_type', models.CharField(blank=True, max_length=120)),
                ('object_uuid', models.CharField(blank=True, max_length=64)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True)),
                (
                    'actor',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='audit_logs',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'organization',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='audit_logs',
                        to='organizations.organization',
                    ),
                ),
            ],
            options={
                'db_table': 'audit_logs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['actor', 'action'], name='audit_logs_actor__0e0c88_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['organization', 'action'], name='audit_logs_organi_5f4f62_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['-created_at'], name='audit_logs_created_d9bb4c_idx'),
        ),
    ]
