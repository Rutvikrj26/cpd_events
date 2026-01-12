from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0005_update_course_ownership'),
        ('organizations', '0005_add_course_manager_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='organizationmembership',
            name='assigned_course',
            field=models.ForeignKey(
                blank=True,
                help_text='Course the instructor is assigned to (instructors can only access their assigned course)',
                null=True,
                on_delete=models.SET_NULL,
                related_name='assigned_instructors',
                to='learning.course',
            ),
        ),
    ]
