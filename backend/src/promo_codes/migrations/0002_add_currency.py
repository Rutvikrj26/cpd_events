from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('promo_codes', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='promocode',
            name='currency',
            field=models.CharField(default='USD', help_text='Currency code for fixed-amount discounts', max_length=3),
        ),
    ]
