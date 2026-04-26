"""
Replace EventFeedback's hardcoded rating/comment columns with admin-configurable
FeedbackField + FeedbackFieldResponse rows.

Steps:
  1. Create FeedbackField + FeedbackFieldResponse models.
  2. Add nullable session FK + session-aware unique constraint on EventFeedback.
  3. Data migrate existing feedback rows into the new schema:
     - For every event with feedback, seed 4 default fields
       (Overall rating, Content quality, Speaker rating, Comments).
     - For every EventFeedback row, create 4 FeedbackFieldResponse rows
       from the old columns.
  4. Drop the old hardcoded columns.
"""

import uuid

import django.db.models.deletion
from django.db import migrations, models


DEFAULT_FIELDS = [
    ('Overall rating', 'rating', True, 0),
    ('Content quality', 'rating', True, 1),
    ('Speaker rating', 'rating', True, 2),
    ('Comments', 'textarea', False, 3),
]


def forwards(apps, schema_editor):
    Event = apps.get_model('events', 'Event')
    EventFeedback = apps.get_model('feedback', 'EventFeedback')
    FeedbackField = apps.get_model('feedback', 'FeedbackField')
    FeedbackFieldResponse = apps.get_model('feedback', 'FeedbackFieldResponse')

    # Seed default fields on every event that has feedback.
    events_with_feedback = Event.objects.filter(
        id__in=EventFeedback.objects.values_list('event_id', flat=True).distinct()
    )

    for event in events_with_feedback:
        field_lookup = {}
        for label, ftype, required, order in DEFAULT_FIELDS:
            field, _ = FeedbackField.objects.get_or_create(
                event=event,
                label=label,
                defaults={
                    'field_type': ftype,
                    'required': required,
                    'order': order,
                    'min_value': 1 if ftype == 'rating' else None,
                    'max_value': 5 if ftype == 'rating' else None,
                    'options': [],
                },
            )
            field_lookup[label] = field

        column_map = {
            'Overall rating': 'rating',
            'Content quality': 'content_quality_rating',
            'Speaker rating': 'speaker_rating',
            'Comments': 'comments',
        }

        for fb in EventFeedback.objects.filter(event=event):
            for label, column in column_map.items():
                raw_value = getattr(fb, column, None)
                if raw_value in (None, ''):
                    continue
                FeedbackFieldResponse.objects.get_or_create(
                    feedback=fb,
                    field=field_lookup[label],
                    defaults={'value': raw_value},
                )


def backwards(apps, schema_editor):
    # Data migration is one-way — existing rows are flattened into
    # FeedbackFieldResponse rows, and we won't reconstruct the old columns.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('feedback', '0001_initial'),
        ('events', '0002_initial'),
        ('registrations', '0001_initial'),
    ]

    operations = [
        # --- Create new models -------------------------------------------------
        migrations.CreateModel(
            name='FeedbackField',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='When this record was created')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='When this record was last modified')),
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, help_text='Public identifier for external use', unique=True)),
                ('label', models.CharField(help_text='Question label', max_length=200)),
                ('field_type', models.CharField(choices=[('rating', 'Rating (1-5)'), ('text', 'Single Line Text'), ('textarea', 'Multi-line Text'), ('select', 'Dropdown'), ('multiselect', 'Multi-select'), ('checkbox', 'Yes/No Checkbox'), ('radio', 'Radio Buttons'), ('date', 'Date'), ('number', 'Number')], max_length=20)),
                ('required', models.BooleanField(default=False)),
                ('placeholder', models.CharField(blank=True, max_length=200)),
                ('help_text', models.CharField(blank=True, max_length=500)),
                ('options', models.JSONField(blank=True, default=list, help_text='Choice list for select / multiselect / radio fields')),
                ('min_value', models.IntegerField(blank=True, null=True)),
                ('max_value', models.IntegerField(blank=True, null=True)),
                ('order', models.PositiveIntegerField(default=0, help_text='Display order (0 = first)')),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='feedback_fields', to='events.event')),
            ],
            options={
                'verbose_name': 'Feedback Field',
                'verbose_name_plural': 'Feedback Fields',
                'db_table': 'feedback_fields',
                'ordering': ['order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='FeedbackFieldResponse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='When this record was created')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='When this record was last modified')),
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, help_text='Public identifier for external use', unique=True)),
                ('value', models.JSONField(blank=True, help_text='Answer (type depends on field.field_type)', null=True)),
                ('feedback', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='field_responses', to='feedback.eventfeedback')),
                ('field', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='responses', to='feedback.feedbackfield')),
            ],
            options={
                'verbose_name': 'Feedback Field Response',
                'verbose_name_plural': 'Feedback Field Responses',
                'db_table': 'feedback_field_responses',
                'ordering': ['field__order', 'id'],
            },
        ),
        # --- Add session FK + swap unique_together ----------------------------
        migrations.AlterUniqueTogether(
            name='eventfeedback',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='eventfeedback',
            name='session',
            field=models.ForeignKey(
                blank=True,
                help_text='Session being evaluated; null for event-level feedback',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='feedback',
                to='events.eventsession',
            ),
        ),
        migrations.AddConstraint(
            model_name='eventfeedback',
            constraint=models.UniqueConstraint(
                fields=('event', 'session', 'registration'),
                name='unique_feedback_per_session_registration',
            ),
        ),
        migrations.AddConstraint(
            model_name='feedbackfieldresponse',
            constraint=models.UniqueConstraint(
                fields=('feedback', 'field'),
                name='unique_response_per_field',
            ),
        ),
        # --- Data migration: seed defaults + port old rows --------------------
        migrations.RunPython(forwards, backwards),
        # --- Drop hardcoded columns -------------------------------------------
        migrations.RemoveField(model_name='eventfeedback', name='rating'),
        migrations.RemoveField(model_name='eventfeedback', name='content_quality_rating'),
        migrations.RemoveField(model_name='eventfeedback', name='speaker_rating'),
        migrations.RemoveField(model_name='eventfeedback', name='comments'),
    ]
