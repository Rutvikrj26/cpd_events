from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0004_add_zoom_fields_to_course'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='organization',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.CASCADE,
                related_name='courses',
                to='organizations.organization',
                help_text='Organization that owns this course (null for personal LMS plans)',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='course',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='course',
            constraint=models.UniqueConstraint(
                condition=models.Q(organization__isnull=False),
                fields=('organization', 'slug'),
                name='unique_course_slug_per_organization',
            ),
        ),
        migrations.AddConstraint(
            model_name='course',
            constraint=models.UniqueConstraint(
                condition=models.Q(organization__isnull=True),
                fields=('created_by', 'slug'),
                name='unique_course_slug_per_owner',
            ),
        ),
    ]
