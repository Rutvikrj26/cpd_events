from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0005_add_fee_and_tax_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='registration',
            name='stripe_transfer_id',
            field=models.CharField(blank=True, help_text='Stripe Transfer ID created for organizer payout', max_length=255),
        ),
    ]
