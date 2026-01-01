# Stripe Product Management via Django Admin - Setup Guide

## Overview

You can now manage all Stripe pricing directly from Django Admin instead of manually updating the Stripe Dashboard and `.env` files.

**Key Benefits:**
- ✅ Manage products and prices from one place (Django Admin)
- ✅ Auto-sync to Stripe with one click
- ✅ Configure trial periods per-product (90 days for all plans!)
- ✅ No manual `.env` editing
- ✅ Price history and auditing

---

## Quick Start

### Step 1: Run Migration

```bash
cd backend
python manage.py migrate billing
```

This will:
- Create `stripe_products` and `stripe_prices` tables
- Seed initial products (Starter, Professional, Premium)
- Set 90-day trial period for all products

### Step 2: Access Django Admin

```bash
# Make sure backend is running
python manage.py runserver

# Visit Django Admin
open http://localhost:8000/admin
```

### Step 3: Sync to Stripe

1. Go to **Billing → Stripe Products**
2. You'll see 3 pre-configured products:
   - CPD Events - Starter (90-day trial)
   - CPD Events - Professional (90-day trial)
   - CPD Events - Premium (90-day trial)
3. Click on each product
4. Click **Save** (this will auto-sync to Stripe)
5. Check success message: "✓ Product created in Stripe"
6. Copy the `stripe_product_id` shown

### Step 4: Sync Prices

1. Go to **Billing → Stripe Prices**
2. You'll see 6 pre-configured prices:
   - Starter Monthly: $49.00/month
   - Starter Annual: $41.00/month (billed $492/year)
   - Professional Monthly: $99.00/month
   - Professional Annual: $83.00/month (billed $996/year)
   - Premium Monthly: $199.00/month
   - Premium Annual: $166.00/month (billed $1,992/year)
3. Click on each price
4. Click **Save** (this will auto-sync to Stripe)
5. Check success message: "✓ Price created in Stripe"

---

## How It Works

### Database-Driven Pricing

The system now reads pricing from the database:

```python
# Old way (manual .env editing):
STRIPE_PRICE_PROFESSIONAL=price_1234567890

# New way (automatic from database):
# StripeProduct: plan='professional', trial_period_days=90
# StripePrice: amount_cents=9900, interval='month', stripe_price_id='price_...'
```

### Trial Period Configuration

Each product can have its own trial period:

- **Database value** (`StripeProduct.trial_period_days`): Used if set
- **Global fallback** (`BILLING_TRIAL_DAYS` in `.env`): Used if product value is null

**Current setup:** All products have 90-day trials (3 months)

### Auto-Sync to Stripe

When you save a product or price in Django Admin:
1. Django calls Stripe API automatically
2. Creates or updates the item in Stripe
3. Stores the Stripe ID in the database
4. Shows success/error message

---

## Managing Products & Prices

### Creating a New Product

1. Go to **Django Admin → Billing → Stripe Products → Add Product**

2. Fill in details:
   ```
   Name: CPD Events - Enterprise
   Description: For large organizations needing custom solutions
   Plan: Select a plan (or add new choice to models.py)
   Trial Period Days: 90
   Active: ✓
   ```

3. Click **Save**
   - Django creates product in Stripe
   - `stripe_product_id` is populated automatically
   - Success message appears

4. Now add prices for this product

### Creating a New Price

1. Go to **Django Admin → Billing → Stripe Prices → Add Price**

2. Fill in details:
   ```
   Product: CPD Events - Enterprise (select from dropdown)
   Amount (cents): 29900 (= $299.00)
   Currency: usd
   Billing Interval: Monthly
   Active: ✓
   ```

3. Click **Save**
   - Django creates price in Stripe
   - `stripe_price_id` is populated automatically
   - Success message appears

### Updating Prices

**Important:** Stripe doesn't allow changing price amounts on existing prices.

To change pricing:
1. **Keep old price** but set `Active = False` (grandfathers existing subscriptions)
2. **Create new price** with new amount
3. New signups use the new price
4. Existing customers keep old price

### Changing Trial Periods

To update trial period for a plan:

1. Go to **Django Admin → Billing → Stripe Products**
2. Click on the product
3. Update **Trial Period Days** (e.g., change 90 to 30)
4. Click **Save**
5. New signups get the new trial period
6. Existing trials are not affected

---

## Workflow Examples

### Example 1: Increase Professional Plan Price

**Scenario:** Increase Professional from $99/mo to $129/mo

**Steps:**
1. Go to **Stripe Prices**
2. Find "Professional Monthly - $99.00"
3. Set **Active = False**
4. Click **Save**
5. Click **Add Price**
6. Create new price:
   ```
   Product: CPD Events - Professional
   Amount: 12900 (= $129.00)
   Interval: Monthly
   Active: ✓
   ```
7. Save

**Result:**
- Existing customers keep $99/mo
- New signups pay $129/mo

### Example 2: Extend Trial to 90 Days for Starter Plan

**Scenario:** Marketing wants 90-day trial for Starter plan

**Steps:**
1. Go to **Stripe Products**
2. Click "CPD Events - Starter"
3. Update **Trial Period Days = 90**
4. Click **Save**

**Result:**
- New Starter signups get 90-day trial
- System automatically uses this when creating Stripe checkout sessions

### Example 3: Create Limited-Time Promotion Price

**Scenario:** Holiday special - Professional at $79/mo for 3 months

**Steps:**
1. Create new price (as in Example 1)
2. Manually update in code to use this price for holiday signups
3. After promotion ends, deactivate the price

---

## Testing

### Verify Database-Driven Pricing Works

```bash
cd backend
python manage.py shell
```

```python
from billing.services import stripe_service

# Test get_price_id reads from database
price_id = stripe_service.get_price_id('professional', annual=False)
print(f"Professional monthly price: {price_id}")

# Test trial days from database
trial_days = stripe_service.get_trial_days('starter')
print(f"Starter trial days: {trial_days}")  # Should be 90
```

### Verify Stripe Sync

1. Go to [Stripe Dashboard](https://dashboard.stripe.com/test/products)
2. You should see 3 products:
   - CPD Events - Starter
   - CPD Events - Professional
   - CPD Events - Premium
3. Each product should have 2 prices (monthly + annual)

---

## Migration from .env to Database

### If You Already Have Stripe Products

1. **Get your existing Stripe product/price IDs** from Stripe Dashboard
2. **Update migration** before running:
   ```python
   # In migration 0004_stripe_product_models.py
   # Add stripe_product_id and stripe_price_id values
   ```
3. **Or manually update** after migration:
   - Django Admin → Stripe Products → Edit each product
   - Paste `stripe_product_id` from Stripe
   - Save
   - Repeat for Stripe Prices

### Fallback to .env

If database is empty, system falls back to `.env` values:
- `STRIPE_PRICE_STARTER`
- `STRIPE_PRICE_PROFESSIONAL`
- etc.

This ensures backward compatibility.

---

## Troubleshooting

### "Failed to sync to Stripe: ..."

**Check:**
1. Is `STRIPE_SECRET_KEY` set in `.env`?
2. Is it a valid test/live key?
3. Is Stripe API accessible (check internet connection)?

### "No StripeProduct found for plan 'professional'"

**Solution:**
1. Run migration: `python manage.py migrate billing`
2. Check products exist: Django Admin → Billing → Stripe Products
3. Verify `plan` field matches (e.g., 'professional' not 'Professional')

### Prices not updating in checkout

**Check:**
1. Is `stripe_price_id` populated? (View in Django Admin)
2. Is price marked as `Active = True`?
3. Clear any caches
4. Check logs for "No active price found" warnings

---

## Advanced Usage

### Bulk Update All Products

Django Admin → Stripe Products → Select all → Actions → "Sync selected products to Stripe"

This will:
- Loop through all selected products
- Sync each to Stripe
- Show success/error count

### Query Current Pricing

```python
from billing.models import StripeProduct, StripePrice

# Get all active products
products = StripeProduct.objects.filter(is_active=True)

for product in products:
    print(f"\n{product.name}:")
    print(f"  Trial: {product.get_trial_days()} days")

    for price in product.prices.filter(is_active=True):
        print(f"  {price.billing_interval}: ${price.amount_display}/mo")
```

Output:
```
CPD Events - Starter:
  Trial: 90 days
  month: $49.00/mo
  year: $41.00/mo

CPD Events - Professional:
  Trial: 90 days
  month: $99.00/mo
  year: $83.00/mo
```

---

## Summary

### Before (Manual Process)
1. Create product in Stripe Dashboard
2. Copy product ID
3. Paste into `.env` file
4. Restart backend
5. Repeat for each price

### After (Automated)
1. Create product in Django Admin
2. Click Save
3. ✨ Done! Auto-synced to Stripe

---

## Next Steps

1. **Run the migration** to create tables and seed data
2. **Sync products/prices** via Django Admin
3. **Test signup flow** with 90-day trial
4. **Remove old .env price IDs** (optional - kept for fallback)

Need help? Check the full implementation guide: `STRIPE_ADMIN_AND_PROMO_CODES.md`
