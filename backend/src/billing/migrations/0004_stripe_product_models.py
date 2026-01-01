# Generated migration for Stripe Product and Price models

from django.db import migrations, models
import django.db.models.deletion
import uuid


def seed_initial_products(apps, schema_editor):
    """
    Create initial Stripe products and prices from current pricing structure.

    This seeds the database with the current pricing so we can manage it via Django Admin.
    Note: stripe_product_id and stripe_price_id will be null initially.
    They will be populated when you sync to Stripe via Django Admin.
    """
    StripeProduct = apps.get_model('billing', 'StripeProduct')
    StripePrice = apps.get_model('billing', 'StripePrice')

    # Define simplified pricing structure (2 tiers only)
    # Strategy: Undercut market with simple, aggressive pricing
    products_data = [
        {
            'name': 'CPD Events - Professional',
            'description': 'Everything you need to run professional CPD events - 30 events/mo, 500 certificates, up to 500 attendees',
            'plan': 'professional',
            'trial_period_days': 90,  # 3 months trial - aggressive market entry
            'prices': [
                {'amount_cents': 4900, 'interval': 'month'},   # $49/mo - AGGRESSIVE PRICING
                {'amount_cents': 41 * 100, 'interval': 'year'},  # $41/mo annual (billed $492/year)
            ]
        },
        {
            'name': 'CPD Events - Organization',
            'description': 'For teams and organizations - unlimited events & certificates, up to 2000 attendees per event',
            'plan': 'organization',
            'trial_period_days': 90,  # 3 months trial
            'prices': [
                {'amount_cents': 19900, 'interval': 'month'},  # $199/mo - undercuts competition
                {'amount_cents': 166 * 100, 'interval': 'year'},  # $166/mo annual (billed $1,992/year)
            ]
        },
    ]

    for product_data in products_data:
        # Create product
        product = StripeProduct.objects.create(
            uuid=uuid.uuid4(),
            name=product_data['name'],
            description=product_data['description'],
            plan=product_data['plan'],
            trial_period_days=product_data['trial_period_days'],
            is_active=True,
        )

        # Create prices for this product
        for price_data in product_data['prices']:
            StripePrice.objects.create(
                uuid=uuid.uuid4(),
                product=product,
                amount_cents=price_data['amount_cents'],
                billing_interval=price_data['interval'],
                is_active=True,
            )


def reverse_seed(apps, schema_editor):
    """Remove seeded products and prices."""
    StripeProduct = apps.get_model('billing', 'StripeProduct')
    StripePrice = apps.get_model('billing', 'StripePrice')

    StripePrice.objects.all().delete()
    StripeProduct.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0002_update_plan_choices'),
    ]

    operations = [
        migrations.CreateModel(
            name='StripeProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('name', models.CharField(help_text='Product name (shown to customers)', max_length=255)),
                ('description', models.TextField(blank=True, help_text='Product description')),
                ('stripe_product_id', models.CharField(blank=True, help_text='Stripe product ID (prod_...)', max_length=255, null=True, unique=True)),
                ('is_active', models.BooleanField(default=True, help_text='Whether product is active')),
                ('plan', models.CharField(choices=[('attendee', 'Attendee'), ('starter', 'Starter'), ('professional', 'Professional'), ('premium', 'Premium'), ('organizer', 'Organizer'), ('organization', 'Organization')], help_text='Which subscription plan this product represents', max_length=50, unique=True)),
                ('trial_period_days', models.PositiveIntegerField(blank=True, help_text='Trial period in days (null = use global default)', null=True)),
            ],
            options={
                'verbose_name': 'Stripe Product',
                'verbose_name_plural': 'Stripe Products',
                'db_table': 'stripe_products',
                'ordering': ['plan'],
            },
        ),
        migrations.CreateModel(
            name='StripePrice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('amount_cents', models.PositiveIntegerField(help_text='Price in cents (e.g., 9900 = $99.00)')),
                ('currency', models.CharField(default='usd', max_length=3)),
                ('billing_interval', models.CharField(choices=[('month', 'Monthly'), ('year', 'Annual')], default='month', max_length=10)),
                ('stripe_price_id', models.CharField(blank=True, help_text='Stripe price ID (price_...)', max_length=255, null=True, unique=True)),
                ('is_active', models.BooleanField(default=True, help_text='Whether price is available for new subscriptions')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prices', to='billing.stripeproduct')),
            ],
            options={
                'verbose_name': 'Stripe Price',
                'verbose_name_plural': 'Stripe Prices',
                'db_table': 'stripe_prices',
                'ordering': ['product', 'billing_interval'],
                'unique_together': {('product', 'billing_interval')},
            },
        ),
        migrations.RunPython(seed_initial_products, reverse_seed),
    ]
