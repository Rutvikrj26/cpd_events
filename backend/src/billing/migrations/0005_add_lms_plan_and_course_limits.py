from django.db import migrations, models


def migrate_professional_to_organizer(apps, schema_editor):
    Subscription = apps.get_model('billing', 'Subscription')
    StripeProduct = apps.get_model('billing', 'StripeProduct')
    Subscription.objects.filter(plan='professional').update(plan='organizer')
    StripeProduct.objects.filter(plan='professional').update(plan='organizer')


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0004_stripeproduct_included_seats_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='courses_created_this_period',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='stripeproduct',
            name='courses_per_month',
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                help_text='Max courses per month (null = unlimited)',
            ),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='plan',
            field=models.CharField(
                choices=[
                    ('attendee', 'Attendee'),
                    ('organizer', 'Organizer'),
                    ('lms', 'LMS'),
                    ('organization', 'Organization'),
                ],
                default='attendee',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='stripeproduct',
            name='plan',
            field=models.CharField(
                choices=[
                    ('attendee', 'Attendee'),
                    ('organizer', 'Organizer'),
                    ('lms', 'LMS'),
                    ('organization', 'Organization'),
                ],
                help_text='Which subscription plan this product represents',
                max_length=50,
                unique=True,
            ),
        ),
        migrations.RunPython(migrate_professional_to_organizer, migrations.RunPython.noop),
    ]
