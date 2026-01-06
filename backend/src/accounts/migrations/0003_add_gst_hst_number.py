from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_alter_cpdrequirement_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='gst_hst_number',
            field=models.CharField(blank=True, help_text='GST/HST registration number for tax handling', max_length=50),
        ),
    ]
