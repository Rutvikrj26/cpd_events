import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0006_payoutrequest_refundrecord_transferrecord'),
        ('registrations', '0007_add_stripe_tax_transaction_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='last_usage_reset_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='DisputeRecord',
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
                        help_text='Public identifier for external use',
                        unique=True,
                    ),
                ),
                ('stripe_dispute_id', models.CharField(db_index=True, max_length=255, unique=True)),
                ('stripe_charge_id', models.CharField(blank=True, db_index=True, max_length=255)),
                ('stripe_payment_intent_id', models.CharField(blank=True, db_index=True, max_length=255)),
                ('amount_cents', models.PositiveIntegerField(default=0)),
                ('currency', models.CharField(default='usd', max_length=3)),
                ('reason', models.CharField(blank=True, max_length=100)),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('needs_response', 'Needs Response'),
                            ('warning_needs_response', 'Warning Needs Response'),
                            ('under_review', 'Under Review'),
                            ('won', 'Won'),
                            ('lost', 'Lost'),
                        ],
                        default='needs_response',
                        max_length=50,
                    ),
                ),
                ('evidence_due_by', models.DateTimeField(blank=True, null=True)),
                ('closed_at', models.DateTimeField(blank=True, null=True)),
                (
                    'registration',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='disputes',
                        to='registrations.registration',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Dispute Record',
                'verbose_name_plural': 'Dispute Records',
                'db_table': 'dispute_records',
                'ordering': ['-created_at'],
            },
        ),
    ]
