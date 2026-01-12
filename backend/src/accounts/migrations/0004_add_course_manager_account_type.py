from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_add_gst_hst_number'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='account_type',
            field=models.CharField(
                choices=[
                    ('attendee', 'Attendee'),
                    ('organizer', 'Organizer'),
                    ('course_manager', 'Course Manager'),
                ],
                db_index=True,
                default='attendee',
                help_text='Account type determines available features',
                max_length=20,
            ),
        ),
    ]
