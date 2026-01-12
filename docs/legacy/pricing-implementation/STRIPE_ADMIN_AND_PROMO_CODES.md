# Stripe Product Management & Enhanced Promo Codes

## Overview

This document addresses two major feature requests:

1. **Stripe Product Management via Django Admin** - Manage Stripe products/prices from Django instead of Stripe Dashboard
2. **Enhanced Promo Codes** - Extend promo codes to support:
   - Referral tracking
   - Extended trial periods
   - Subscription discounts (e.g., "50% off for a year")

---

## Part 1: Stripe Product Management via Django Admin

### Current State

❌ **Problem**: Stripe products/prices are managed manually in Stripe Dashboard
- Price IDs are hardcoded in `.env` variables
- No way to create/update pricing from Django
- Changes require manual updates in both Stripe and `.env`

### Goal

✅ **Solution**: Manage all pricing through Django Admin Panel
- Create products in Django → Auto-sync to Stripe
- Update prices in Django → Auto-sync to Stripe
- Archive products in Django → Archive in Stripe
- Single source of truth: Django database

---

### Implementation Plan

#### Step 1: Create New Models (`billing/models.py`)

```python
class StripeProduct(BaseModel):
    """
    Represents a Stripe Product (e.g., "CPD Events - Professional").

    Syncs with Stripe via API.
    """

    name = models.CharField(
        max_length=255,
        help_text="Product name (shown to customers)"
    )
    description = models.TextField(
        blank=True,
        help_text="Product description"
    )
    stripe_product_id = models.CharField(
        max_length=255,
        unique=True,
        blank=True,
        null=True,
        help_text="Stripe product ID (prod_...)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether product is active"
    )

    # Plan association
    plan = models.CharField(
        max_length=50,
        choices=Subscription.Plan.choices,
        unique=True,
        help_text="Which subscription plan this product represents"
    )

    class Meta:
        db_table = 'stripe_products'
        ordering = ['plan']
        verbose_name = 'Stripe Product'
        verbose_name_plural = 'Stripe Products'

    def __str__(self):
        return f"{self.name} ({self.get_plan_display()})"

    def sync_to_stripe(self):
        """Create or update product in Stripe."""
        from .services import stripe_service

        if not stripe_service.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        try:
            if self.stripe_product_id:
                # Update existing product
                product = stripe_service.stripe.Product.modify(
                    self.stripe_product_id,
                    name=self.name,
                    description=self.description,
                    active=self.is_active,
                )
            else:
                # Create new product
                product = stripe_service.stripe.Product.create(
                    name=self.name,
                    description=self.description,
                    active=self.is_active,
                )
                self.stripe_product_id = product.id
                self.save(update_fields=['stripe_product_id', 'updated_at'])

            return {'success': True, 'product': product}

        except Exception as e:
            return {'success': False, 'error': str(e)}


class StripePrice(BaseModel):
    """
    Represents a Stripe Price (e.g., "$99/month" for Professional plan).

    Each product can have multiple prices (monthly, annual).
    """

    class BillingInterval(models.TextChoices):
        MONTH = 'month', 'Monthly'
        YEAR = 'year', 'Annual'

    product = models.ForeignKey(
        StripeProduct,
        on_delete=models.CASCADE,
        related_name='prices'
    )

    # Pricing details
    amount_cents = models.PositiveIntegerField(
        help_text="Price in cents (e.g., 9900 = $99.00)"
    )
    currency = models.CharField(
        max_length=3,
        default='usd'
    )
    billing_interval = models.CharField(
        max_length=10,
        choices=BillingInterval.choices,
        default=BillingInterval.MONTH
    )

    # Stripe sync
    stripe_price_id = models.CharField(
        max_length=255,
        unique=True,
        blank=True,
        null=True,
        help_text="Stripe price ID (price_...)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether price is available for new subscriptions"
    )

    class Meta:
        db_table = 'stripe_prices'
        ordering = ['product', 'billing_interval']
        unique_together = [['product', 'billing_interval']]
        verbose_name = 'Stripe Price'
        verbose_name_plural = 'Stripe Prices'

    def __str__(self):
        return f"${self.amount_display}/{self.billing_interval} - {self.product.name}"

    @property
    def amount_display(self):
        """Format amount as dollars."""
        return f"{self.amount_cents / 100:.2f}"

    def sync_to_stripe(self):
        """Create or update price in Stripe."""
        from .services import stripe_service

        if not stripe_service.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        if not self.product.stripe_product_id:
            # Product must exist in Stripe first
            result = self.product.sync_to_stripe()
            if not result['success']:
                return result

        try:
            if self.stripe_price_id:
                # Update existing price (limited - Stripe doesn't allow changing amount)
                price = stripe_service.stripe.Price.modify(
                    self.stripe_price_id,
                    active=self.is_active,
                )
            else:
                # Create new price
                price = stripe_service.stripe.Price.create(
                    product=self.product.stripe_product_id,
                    unit_amount=self.amount_cents,
                    currency=self.currency,
                    recurring={'interval': self.billing_interval},
                    active=self.is_active,
                )
                self.stripe_price_id = price.id
                self.save(update_fields=['stripe_price_id', 'updated_at'])

            return {'success': True, 'price': price}

        except Exception as e:
            return {'success': False, 'error': str(e)}
```

---

#### Step 2: Update Admin (`billing/admin.py`)

```python
from django.contrib import admin, messages
from .models import StripeProduct, StripePrice

@admin.register(StripeProduct)
class StripeProductAdmin(admin.ModelAdmin):
    """Admin for Stripe Products."""

    list_display = [
        'name',
        'plan',
        'is_active',
        'stripe_product_id',
        'created_at',
    ]
    list_filter = ['is_active', 'plan']
    search_fields = ['name', 'stripe_product_id']
    readonly_fields = ['uuid', 'stripe_product_id', 'created_at', 'updated_at']

    fieldsets = (
        ('Product Details', {
            'fields': ('name', 'description', 'plan', 'is_active')
        }),
        ('Stripe Integration', {
            'fields': ('stripe_product_id',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('uuid', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['sync_to_stripe_action']

    def save_model(self, request, obj, form, change):
        """Auto-sync to Stripe on save."""
        super().save_model(request, obj, form, change)

        result = obj.sync_to_stripe()
        if result['success']:
            messages.success(request, f"Product synced to Stripe: {obj.stripe_product_id}")
        else:
            messages.error(request, f"Failed to sync to Stripe: {result['error']}")

    @admin.action(description='Sync selected products to Stripe')
    def sync_to_stripe_action(self, request, queryset):
        """Bulk sync products to Stripe."""
        success_count = 0
        error_count = 0

        for product in queryset:
            result = product.sync_to_stripe()
            if result['success']:
                success_count += 1
            else:
                error_count += 1
                messages.error(request, f"{product.name}: {result['error']}")

        if success_count:
            messages.success(request, f"Successfully synced {success_count} product(s)")
        if error_count:
            messages.warning(request, f"Failed to sync {error_count} product(s)")


@admin.register(StripePrice)
class StripePriceAdmin(admin.ModelAdmin):
    """Admin for Stripe Prices."""

    list_display = [
        'product',
        'amount_display',
        'billing_interval',
        'is_active',
        'stripe_price_id',
        'created_at',
    ]
    list_filter = ['is_active', 'billing_interval']
    search_fields = ['product__name', 'stripe_price_id']
    readonly_fields = ['uuid', 'stripe_price_id', 'created_at', 'updated_at']
    raw_id_fields = ['product']

    fieldsets = (
        ('Price Details', {
            'fields': ('product', 'amount_cents', 'currency', 'billing_interval', 'is_active')
        }),
        ('Stripe Integration', {
            'fields': ('stripe_price_id',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('uuid', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['sync_to_stripe_action']

    def save_model(self, request, obj, form, change):
        """Auto-sync to Stripe on save."""
        super().save_model(request, obj, form, change)

        result = obj.sync_to_stripe()
        if result['success']:
            messages.success(request, f"Price synced to Stripe: {obj.stripe_price_id}")
        else:
            messages.error(request, f"Failed to sync to Stripe: {result['error']}")

    @admin.action(description='Sync selected prices to Stripe')
    def sync_to_stripe_action(self, request, queryset):
        """Bulk sync prices to Stripe."""
        success_count = 0
        error_count = 0

        for price in queryset:
            result = price.sync_to_stripe()
            if result['success']:
                success_count += 1
            else:
                error_count += 1
                messages.error(request, f"{price}: {result['error']}")

        if success_count:
            messages.success(request, f"Successfully synced {success_count} price(s)")
        if error_count:
            messages.warning(request, f"Failed to sync {error_count} price(s)")
```

---

#### Step 3: Update StripeService (`billing/services.py`)

```python
def get_price_id(self, plan: str, annual: bool = False) -> Optional[str]:
    """
    Get Stripe price ID for a plan.

    Now reads from database instead of environment variables.
    """
    if not self.is_configured:
        return None

    try:
        from .models import StripeProduct, StripePrice

        # Find product for this plan
        product = StripeProduct.objects.get(plan=plan, is_active=True)

        # Find price for billing interval
        interval = 'year' if annual else 'month'
        price = product.prices.get(billing_interval=interval, is_active=True)

        return price.stripe_price_id

    except (StripeProduct.DoesNotExist, StripePrice.DoesNotExist):
        # Fallback to environment variables (for backward compatibility)
        price_key = f"{plan}_annual" if annual else plan
        return self.price_ids.get(price_key)
```

---

#### Step 4: Migration

```python
# backend/src/billing/migrations/0004_stripe_product_models.py

from django.db import migrations, models

def seed_initial_products(apps, schema_editor):
    """Create initial Stripe products from current pricing."""
    StripeProduct = apps.get_model('billing', 'StripeProduct')
    StripePrice = apps.get_model('billing', 'StripePrice')

    # Define current pricing
    products_data = [
        {
            'name': 'CPD Events - Starter',
            'plan': 'starter',
            'prices': [
                {'amount_cents': 4900, 'interval': 'month'},   # $49/mo
                {'amount_cents': 4100, 'interval': 'year'},    # $41/mo annual
            ]
        },
        {
            'name': 'CPD Events - Professional',
            'plan': 'professional',
            'prices': [
                {'amount_cents': 9900, 'interval': 'month'},   # $99/mo
                {'amount_cents': 8300, 'interval': 'year'},    # $83/mo annual
            ]
        },
        {
            'name': 'CPD Events - Premium',
            'plan': 'premium',
            'prices': [
                {'amount_cents': 19900, 'interval': 'month'},  # $199/mo
                {'amount_cents': 16600, 'interval': 'year'},   # $166/mo annual
            ]
        },
    ]

    for product_data in products_data:
        product = StripeProduct.objects.create(
            name=product_data['name'],
            plan=product_data['plan'],
            is_active=True,
        )

        for price_data in product_data['prices']:
            StripePrice.objects.create(
                product=product,
                amount_cents=price_data['amount_cents'],
                billing_interval=price_data['interval'],
                is_active=True,
            )

class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0003_add_new_plan_tiers'),
    ]

    operations = [
        # Create StripeProduct model
        migrations.CreateModel(
            name='StripeProduct',
            fields=[
                # ... model fields
            ],
        ),
        # Create StripePrice model
        migrations.CreateModel(
            name='StripePrice',
            fields=[
                # ... model fields
            ],
        ),
        # Seed initial data
        migrations.RunPython(seed_initial_products),
    ]
```

---

### Usage Workflow

#### Creating a New Pricing Plan

1. **Go to Django Admin** → Billing → Stripe Products → Add Product
2. **Fill in details**:
   - Name: "CPD Events - Enterprise"
   - Plan: Select "enterprise" (add to choices first)
   - Active: ✓
3. **Click Save**
4. **Django automatically**:
   - Creates product in Stripe
   - Stores `stripe_product_id`
   - Shows success message

#### Adding Prices to Product

1. **Go to Django Admin** → Billing → Stripe Prices → Add Price
2. **Fill in details**:
   - Product: Select the product
   - Amount (cents): 29900 (= $299.00)
   - Billing Interval: Monthly
   - Active: ✓
3. **Click Save**
4. **Django automatically**:
   - Creates price in Stripe
   - Stores `stripe_price_id`
   - Associates with product

#### Updating Pricing

**Important**: Stripe doesn't allow changing price amounts on existing prices.

To change pricing:
1. **Deactivate old price** (set Active = False)
2. **Create new price** with new amount
3. **Old subscriptions** keep old price (grandfathered)
4. **New subscriptions** use new price

---

## Part 2: Enhanced Promo Codes

### Current Promo Code Limitations

✅ **What Works**:
- Event registration discounts
- Percentage and fixed amount discounts
- Usage limits
- Date validity
- First-time buyer only

❌ **What's Missing**:
- Referral tracking
- Extended trial periods
- Subscription billing discounts

---

### Feature 1: Referral System

#### Database Changes (`promo_codes/models.py`)

```python
class PromoCode(BaseModel):
    # ... existing fields ...

    # New referral fields
    is_referral_code = models.BooleanField(
        default=False,
        help_text="Is this a referral code?"
    )
    referrer = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referral_codes',
        help_text="User who owns this referral code"
    )
    referral_reward_type = models.CharField(
        max_length=20,
        choices=[
            ('trial_extension', 'Trial Extension'),
            ('discount', 'Subscription Discount'),
            ('credits', 'Account Credits'),
        ],
        null=True,
        blank=True,
        help_text="Reward type for referrer"
    )
    referral_reward_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Reward amount (days, percentage, or dollar amount)"
    )

    def generate_referral_code(user):
        """Generate unique referral code for user."""
        import random
        import string

        # Generate code like: JOHNDOE2024XYZ
        base = user.email.split('@')[0].upper()[:8]
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        code = f"{base}{suffix}"

        # Ensure uniqueness
        while PromoCode.objects.filter(code=code).exists():
            suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            code = f"{base}{suffix}"

        return PromoCode.objects.create(
            owner=user,
            referrer=user,
            code=code,
            is_referral_code=True,
            discount_type='percentage',
            discount_value=Decimal('10'),  # 10% off for referee
            referral_reward_type='trial_extension',
            referral_reward_value=Decimal('7'),  # 7 extra days for referrer
            is_active=True,
        )


class ReferralReward(BaseModel):
    """
    Track referral rewards earned.
    """

    referrer = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='referral_rewards'
    )
    referee = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='referred_by_rewards'
    )
    promo_code = models.ForeignKey(
        PromoCode,
        on_delete=models.CASCADE,
        related_name='referral_rewards'
    )

    reward_type = models.CharField(max_length=20)
    reward_value = models.DecimalField(max_digits=10, decimal_places=2)
    applied = models.BooleanField(default=False)
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'referral_rewards'
```

#### Referral API Endpoints (`accounts/views.py`)

```python
@action(detail=False, methods=['get'])
def referral_code(self, request):
    """
    Get or create referral code for current user.

    GET /users/me/referral-code/
    """
    user = request.user

    # Get or create referral code
    referral_code = PromoCode.objects.filter(
        referrer=user,
        is_referral_code=True
    ).first()

    if not referral_code:
        referral_code = PromoCode.generate_referral_code(user)

    return Response({
        'code': referral_code.code,
        'referral_link': f"{request.scheme}://{request.get_host()}/signup?ref={referral_code.code}",
        'total_referrals': referral_code.usages.count(),
        'rewards_earned': ReferralReward.objects.filter(referrer=user, applied=True).count(),
    })
```

---

### Feature 2: Extended Trials via Promo Codes

#### Update Subscription Model (`billing/models.py`)

```python
class Subscription(BaseModel):
    # ... existing fields ...

    # New trial extension field
    trial_extension_days = models.PositiveIntegerField(
        default=0,
        help_text="Additional trial days from promo codes"
    )

    @property
    def total_trial_days(self):
        """Total trial days including extensions."""
        from django.conf import settings
        base_trial = settings.BILLING_TRIAL_DAYS
        return base_trial + self.trial_extension_days

    def extend_trial(self, days: int):
        """Extend trial period by additional days."""
        if self.status == self.Status.TRIALING and self.trial_ends_at:
            from datetime import timedelta

            self.trial_ends_at += timedelta(days=days)
            self.trial_extension_days += days
            self.save(update_fields=['trial_ends_at', 'trial_extension_days', 'updated_at'])

            return True
        return False
```

#### Update PromoCode Model

```python
class PromoCode(BaseModel):
    # ... existing fields ...

    # New subscription-related fields
    applies_to_subscriptions = models.BooleanField(
        default=False,
        help_text="Can be applied to subscription billing?"
    )
    trial_extension_days = models.PositiveIntegerField(
        default=0,
        help_text="Extra trial days granted by this code"
    )
```

#### Apply Trial Extension on Signup

```python
# In accounts/views.py or billing/services.py

def apply_signup_promo_code(user, promo_code_string):
    """
    Apply promo code during signup.

    Can extend trial period or provide discount.
    """
    from promo_codes.models import PromoCode

    try:
        promo_code = PromoCode.objects.get(
            code__iexact=promo_code_string,
            is_active=True
        )

        # Check validity
        if not promo_code.is_valid:
            return {'success': False, 'error': 'Invalid or expired promo code'}

        # Extend trial if applicable
        if promo_code.trial_extension_days > 0:
            subscription = user.subscription
            subscription.extend_trial(promo_code.trial_extension_days)

            # Record usage
            PromoCodeUsage.objects.create(
                promo_code=promo_code,
                user=user,
                user_email=user.email,
            )
            promo_code.increment_usage()

            return {
                'success': True,
                'trial_extended': True,
                'extra_days': promo_code.trial_extension_days,
                'new_trial_end': subscription.trial_ends_at,
            }

        return {'success': False, 'error': 'Code does not extend trial'}

    except PromoCode.DoesNotExist:
        return {'success': False, 'error': 'Code not found'}
```

---

### Feature 3: Subscription Discounts (Stripe Coupons)

**Important**: Subscription discounts require **Stripe Coupons**, which are different from event promo codes.

#### Create Stripe Coupon Model (`billing/models.py`)

```python
class StripeCoupon(BaseModel):
    """
    Represents a Stripe Coupon for subscription discounts.

    Different from PromoCode (event discounts).
    """

    class DiscountType(models.TextChoices):
        PERCENTAGE = 'percentage', 'Percentage Off'
        FIXED = 'fixed', 'Fixed Amount Off'

    class Duration(models.TextChoices):
        ONCE = 'once', 'Once'
        REPEATING = 'repeating', 'Repeating'
        FOREVER = 'forever', 'Forever'

    # Coupon details
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Coupon code (e.g., SAVE50)"
    )
    name = models.CharField(
        max_length=255,
        help_text="Internal name"
    )

    # Discount configuration
    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.PERCENTAGE
    )
    amount_off = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Fixed amount off in cents (for 'fixed' type)"
    )
    percent_off = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Percentage off (for 'percentage' type)"
    )

    # Duration
    duration = models.CharField(
        max_length=20,
        choices=Duration.choices,
        default=Duration.ONCE
    )
    duration_in_months = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of months for 'repeating' duration (e.g., 12 for 1 year)"
    )

    # Validity
    is_active = models.BooleanField(default=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    max_redemptions = models.PositiveIntegerField(null=True, blank=True)

    # Stripe sync
    stripe_coupon_id = models.CharField(
        max_length=255,
        unique=True,
        blank=True,
        null=True
    )

    class Meta:
        db_table = 'stripe_coupons'
        verbose_name = 'Stripe Coupon'
        verbose_name_plural = 'Stripe Coupons'

    def __str__(self):
        return f"{self.code} - {self.get_discount_display()}"

    def get_discount_display(self):
        """Human-readable discount."""
        if self.discount_type == self.DiscountType.PERCENTAGE:
            return f"{self.percent_off}% off"
        else:
            return f"${self.amount_off/100:.2f} off"

    def sync_to_stripe(self):
        """Create or update coupon in Stripe."""
        from .services import stripe_service

        if not stripe_service.is_configured:
            return {'success': False, 'error': 'Stripe not configured'}

        try:
            coupon_data = {
                'id': self.code,  # Use code as Stripe ID
                'name': self.name,
                'duration': self.duration,
            }

            if self.discount_type == self.DiscountType.PERCENTAGE:
                coupon_data['percent_off'] = float(self.percent_off)
            else:
                coupon_data['amount_off'] = self.amount_off
                coupon_data['currency'] = 'usd'

            if self.duration == self.Duration.REPEATING:
                coupon_data['duration_in_months'] = self.duration_in_months

            if self.valid_until:
                coupon_data['redeem_by'] = int(self.valid_until.timestamp())

            if self.max_redemptions:
                coupon_data['max_redemptions'] = self.max_redemptions

            if self.stripe_coupon_id:
                # Update (Stripe has limited update capabilities)
                coupon = stripe_service.stripe.Coupon.retrieve(self.stripe_coupon_id)
            else:
                # Create
                coupon = stripe_service.stripe.Coupon.create(**coupon_data)
                self.stripe_coupon_id = coupon.id
                self.save(update_fields=['stripe_coupon_id', 'updated_at'])

            return {'success': True, 'coupon': coupon}

        except Exception as e:
            return {'success': False, 'error': str(e)}
```

#### Apply Coupon to Checkout (`billing/services.py`)

```python
def create_checkout_session(
    self,
    user,
    plan: str,
    success_url: str,
    cancel_url: str,
    coupon_code: Optional[str] = None  # NEW parameter
) -> dict[str, Any]:
    """
    Create Stripe checkout session.

    Args:
        coupon_code: Optional coupon code to apply discount
    """
    # ... existing code ...

    checkout_params = {
        'customer': customer_id,
        'mode': 'subscription',
        'line_items': [{
            'price': price_id,
            'quantity': 1,
        }],
        'success_url': success_url,
        'cancel_url': cancel_url,
        'subscription_data': {
            'trial_period_days': settings.BILLING_TRIAL_DAYS,
            'metadata': {'user_id': str(user.id)},
        },
    }

    # Apply coupon if provided
    if coupon_code:
        from .models import StripeCoupon

        try:
            coupon = StripeCoupon.objects.get(code__iexact=coupon_code, is_active=True)
            if coupon.stripe_coupon_id:
                checkout_params['discounts'] = [{
                    'coupon': coupon.stripe_coupon_id
                }]
        except StripeCoupon.DoesNotExist:
            pass  # Silently ignore invalid coupons

    session = self.stripe.checkout.Session.create(**checkout_params)
    # ... rest of code ...
```

---

## Implementation Roadmap

### Phase 1: Stripe Admin Management (Week 1)

**Priority**: 🔴 HIGH

**Tasks**:
1. Create `StripeProduct` and `StripePrice` models
2. Add admin interfaces with auto-sync
3. Create migration to seed initial products
4. Update `get_price_id()` to read from database
5. Test creating new products/prices
6. Document workflow

**Estimated Time**: 6-8 hours

---

### Phase 2: Trial Extensions (Week 2)

**Priority**: 🟡 MEDIUM

**Tasks**:
1. Add `trial_extension_days` to `PromoCode` model
2. Add `extend_trial()` method to `Subscription`
3. Create signup promo code application flow
4. Update frontend signup to accept promo codes
5. Test trial extension workflow
6. Document usage

**Estimated Time**: 4-6 hours

---

### Phase 3: Referral System (Week 3)

**Priority**: 🟢 NICE TO HAVE

**Tasks**:
1. Add referral fields to `PromoCode`
2. Create `ReferralReward` model
3. Add referral code generation
4. Create `/users/me/referral-code/` API endpoint
5. Build referral dashboard in frontend
6. Add reward tracking and application
7. Test referral workflow

**Estimated Time**: 8-10 hours

---

### Phase 4: Subscription Coupons (Week 4)

**Priority**: 🟡 MEDIUM

**Tasks**:
1. Create `StripeCoupon` model
2. Add coupon admin with Stripe sync
3. Update checkout to accept coupons
4. Add coupon validation API
5. Update frontend checkout flow
6. Test coupon application
7. Document coupon creation process

**Estimated Time**: 6-8 hours

---

## Testing Checklist

### Stripe Product Management

- [ ] Create product in Django → Syncs to Stripe
- [ ] Update product name → Updates in Stripe
- [ ] Deactivate product → Archives in Stripe
- [ ] Create monthly price → Creates in Stripe
- [ ] Create annual price → Creates in Stripe
- [ ] Deactivate price → Archives in Stripe
- [ ] New checkout uses database price IDs
- [ ] Fallback to .env works if DB empty

### Trial Extensions

- [ ] Apply promo code during signup
- [ ] Trial period extended correctly
- [ ] Extended trial shown in UI
- [ ] Trial expires at correct time
- [ ] Usage tracked in PromoCodeUsage

### Referrals

- [ ] User can generate referral code
- [ ] Referral link works
- [ ] Referee gets discount
- [ ] Referrer gets reward
- [ ] Rewards tracked accurately
- [ ] Dashboard shows referral stats

### Subscription Coupons

- [ ] Create coupon in Django → Syncs to Stripe
- [ ] Apply coupon at checkout
- [ ] Percentage discount applied correctly
- [ ] Fixed discount applied correctly
- [ ] Duration limits enforced (once/repeating/forever)
- [ ] Max redemptions enforced
- [ ] Expired coupons rejected

---

## Migration from Current Setup

### Step 1: Seed Database with Existing Prices

```bash
python manage.py migrate billing  # Run migration
python manage.py shell
```

```python
from billing.models import StripeProduct, StripePrice

# Create products
starter = StripeProduct.objects.create(
    name="CPD Events - Starter",
    plan="starter",
    stripe_product_id="prod_YOUR_EXISTING_STARTER_PRODUCT_ID",  # From Stripe
    is_active=True
)

# Create prices
StripePrice.objects.create(
    product=starter,
    amount_cents=4900,
    billing_interval="month",
    stripe_price_id="price_YOUR_EXISTING_MONTHLY_ID",  # From .env
    is_active=True
)

StripePrice.objects.create(
    product=starter,
    amount_cents=4100,
    billing_interval="year",
    stripe_price_id="price_YOUR_EXISTING_ANNUAL_ID",  # From .env
    is_active=True
)

# Repeat for professional and premium...
```

### Step 2: Test Database-Driven Pricing

```python
# Test get_price_id() now reads from database
from billing.services import stripe_service

price_id = stripe_service.get_price_id('starter', annual=False)
print(price_id)  # Should match database stripe_price_id
```

### Step 3: Remove Environment Variables (Optional)

Once confirmed working:
- Keep `.env` variables as fallback
- Or remove them and rely solely on database

---

## Summary

### What You'll Get

✅ **Stripe Product Management**:
- Create/update products from Django Admin
- Auto-sync to Stripe
- No manual .env editing
- Single source of truth

✅ **Extended Trials**:
- Promo codes can extend trial periods
- "WELCOME30" = 30 extra trial days
- Applied during signup

✅ **Referral System**:
- Each user gets unique referral code
- Referee gets discount
- Referrer gets rewards (extra trial days, credits, etc.)
- Full tracking and analytics

✅ **Subscription Discounts**:
- Stripe Coupons for subscription billing
- "SAVE50" = 50% off for 12 months
- Percentage or fixed amount
- One-time, repeating, or forever

---

## Questions?

1. **Do you want all 4 phases implemented?**
2. **Which phase should I prioritize first?**
3. **Any specific referral reward types needed?** (trial extension, account credits, percentage off, etc.)
4. **What coupon durations are most important?** (one-time, 3 months, 12 months, forever?)

Let me know and I'll start implementation! 🚀
