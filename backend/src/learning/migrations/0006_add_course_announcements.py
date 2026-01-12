import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0005_update_course_ownership'),
    ]

    operations = [
        migrations.CreateModel(
            name='CourseAnnouncement',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
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
                ('title', models.CharField(max_length=255)),
                ('body', models.TextField()),
                ('is_published', models.BooleanField(default=True)),
                (
                    'course',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name='announcements', to='learning.course'
                    ),
                ),
                (
                    'created_by',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='course_announcements',
                        to='accounts.user',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Course Announcement',
                'verbose_name_plural': 'Course Announcements',
                'db_table': 'course_announcements',
                'ordering': ['-created_at'],
            },
        ),
    ]
