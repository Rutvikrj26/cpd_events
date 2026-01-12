from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('organizations', '0006_add_assigned_course_to_membership'),
    ]

    operations = [
        migrations.AddField(
            model_name='organization',
            name='is_public',
            field=models.BooleanField(default=True, help_text='Whether organization is visible publicly'),
        ),
    ]
