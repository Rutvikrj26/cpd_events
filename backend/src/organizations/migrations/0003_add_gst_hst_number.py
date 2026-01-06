from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0002_alter_organizationmembership_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='organization',
            name='gst_hst_number',
            field=models.CharField(blank=True, help_text='GST/HST registration number for tax handling', max_length=50),
        ),
    ]
