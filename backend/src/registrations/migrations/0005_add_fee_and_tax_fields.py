from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0004_add_payment_fee_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='registration',
            name='service_fee_amount',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Service fee charged to attendee', max_digits=10),
        ),
        migrations.AddField(
            model_name='registration',
            name='processing_fee_amount',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Payment processing fee charged to attendee', max_digits=10),
        ),
        migrations.AddField(
            model_name='registration',
            name='tax_amount',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Tax amount charged on ticket and service fee', max_digits=10),
        ),
        migrations.AddField(
            model_name='registration',
            name='stripe_tax_calculation_id',
            field=models.CharField(blank=True, help_text='Stripe Tax Calculation ID used for this charge', max_length=255),
        ),
        migrations.AddField(
            model_name='registration',
            name='billing_country',
            field=models.CharField(blank=True, help_text='Billing country code', max_length=2),
        ),
        migrations.AddField(
            model_name='registration',
            name='billing_state',
            field=models.CharField(blank=True, help_text='Billing state/province', max_length=100),
        ),
        migrations.AddField(
            model_name='registration',
            name='billing_postal_code',
            field=models.CharField(blank=True, help_text='Billing postal/ZIP code', max_length=20),
        ),
        migrations.AddField(
            model_name='registration',
            name='billing_city',
            field=models.CharField(blank=True, help_text='Billing city', max_length=100),
        ),
    ]
