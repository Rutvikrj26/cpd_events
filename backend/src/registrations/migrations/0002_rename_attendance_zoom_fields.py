# Rename AttendanceRecord zoom_* fields to provider-agnostic names.
# Uses RenameField (not drop+add) so existing attendance rows are preserved.

import common.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0001_initial'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='attendancerecord',
            name='attendance__zoom_us_dcc972_idx',
        ),
        migrations.RemoveIndex(
            model_name='attendancerecord',
            name='attendance__zoom_pa_47f605_idx',
        ),
        migrations.RenameField(
            model_name='attendancerecord',
            old_name='zoom_participant_id',
            new_name='participant_id',
        ),
        migrations.RenameField(
            model_name='attendancerecord',
            old_name='zoom_user_id',
            new_name='external_user_id',
        ),
        migrations.RenameField(
            model_name='attendancerecord',
            old_name='zoom_user_email',
            new_name='participant_email',
        ),
        migrations.RenameField(
            model_name='attendancerecord',
            old_name='zoom_user_name',
            new_name='participant_name',
        ),
        migrations.AlterField(
            model_name='attendancerecord',
            name='participant_id',
            field=models.CharField(
                blank=True,
                help_text='Provider participant ID (unique per meeting session)',
                max_length=100,
            ),
        ),
        migrations.AlterField(
            model_name='attendancerecord',
            name='external_user_id',
            field=models.CharField(
                blank=True,
                help_text='External user id (for registered provider users)',
                max_length=100,
            ),
        ),
        migrations.AlterField(
            model_name='attendancerecord',
            name='participant_email',
            field=common.fields.LowercaseEmailField(
                blank=True,
                db_index=True,
                help_text='Email from the video provider (for matching)',
                max_length=254,
            ),
        ),
        migrations.AlterField(
            model_name='attendancerecord',
            name='participant_name',
            field=models.CharField(
                blank=True,
                help_text='Display name in the meeting',
                max_length=255,
            ),
        ),
        migrations.AddIndex(
            model_name='attendancerecord',
            index=models.Index(fields=['participant_email'], name='attendance__partici_51bcb4_idx'),
        ),
        migrations.AddIndex(
            model_name='attendancerecord',
            index=models.Index(fields=['participant_id'], name='attendance__partici_33bfe3_idx'),
        ),
    ]
