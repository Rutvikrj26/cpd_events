from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0006_add_stripe_transfer_id'),
        ('registrations', '0006_alter_registration_total_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='registration',
            name='stripe_tax_transaction_id',
            field=models.CharField(
                blank=True,
                help_text='Stripe Tax Transaction ID created from the tax calculation',
                max_length=255,
            ),
        ),
    ]
