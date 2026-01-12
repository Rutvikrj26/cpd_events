# Quick Start Guide - New Pricing Implementation

## TL;DR - Get Running in 15 Minutes

This is a condensed guide to get the new pricing up and running quickly.

---

## Step 1: Update Environment (2 min)

```bash
cd backend
cp .env.example .env
```

Edit `.env` and add (use test mode keys first):

```bash
BILLING_TRIAL_DAYS=14

# You'll get these from Stripe Dashboard
STRIPE_PRICE_STARTER=price_YOUR_STARTER_MONTHLY_ID
STRIPE_PRICE_PROFESSIONAL=price_YOUR_PROFESSIONAL_MONTHLY_ID
STRIPE_PRICE_PREMIUM=price_YOUR_PREMIUM_MONTHLY_ID
STRIPE_PRICE_STARTER_ANNUAL=price_YOUR_STARTER_ANNUAL_ID
STRIPE_PRICE_PROFESSIONAL_ANNUAL=price_YOUR_PROFESSIONAL_ANNUAL_ID
STRIPE_PRICE_PREMIUM_ANNUAL=price_YOUR_PREMIUM_ANNUAL_ID
```

---

## Step 2: Run Migration (1 min)

```bash
cd backend
python manage.py migrate billing
```

Expected output:
```
Running migrations:
  Applying billing.0003_add_new_plan_tiers... OK
```

---

## Step 3: Create Stripe Products (5 min)

Go to [Stripe Dashboard](https://dashboard.stripe.com/test/products) → Products → Add product

Create 3 products:

### Product 1: Starter
- Name: **CPD Events - Starter**
- Monthly price: **$49.00**
- Annual price: **$492.00**

### Product 2: Professional
- Name: **CPD Events - Professional**
- Monthly price: **$99.00**
- Annual price: **$996.00**

### Product 3: Premium
- Name: **CPD Events - Premium**
- Monthly price: **$199.00**
- Annual price: **$1,992.00**

**Copy the Price IDs** (starts with `price_`) and paste into your `.env` file.

---

## Step 4: Test It (5 min)

### Start Servers

**Terminal 1 - Backend:**
```bash
cd backend
python manage.py runserver
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### Test the Flow

1. **Visit** http://localhost:5173/pricing
   - ✅ Should see 5 pricing tiers
   - ✅ Starter ($49), Professional ($99), Premium ($199)

2. **Sign up for trial:**
   - Click "Start Free Trial" on Professional
   - Create account
   - ✅ Should see "14 days remaining" banner

3. **Create an event:**
   - Go to Events → Create Event
   - Fill in basic info and save
   - ✅ Should work fine (you're on trial)

4. **Check limits:**
   - Go to /billing
   - ✅ Should show: "0/30 events this month"

---

## Step 5: Verify Limits Work (2 min)

### Test Event Limit

In Django shell:
```bash
python manage.py shell
```

```python
from accounts.models import User
from billing.models import Subscription

# Get your test user
user = User.objects.get(email='your-email@example.com')
sub = user.subscription

# Set to Starter plan (10 event limit)
sub.plan = 'starter'
sub.save()

# Simulate hitting the limit
sub.events_created_this_period = 10
sub.save()

# Check if limit enforced
print(sub.check_event_limit())  # Should return False
```

Now try creating an event in the UI - should be blocked with error message.

### Test Certificate Limit

```python
# Still in Django shell
sub.plan = 'starter'  # 100 cert limit
sub.certificates_issued_this_period = 100
sub.save()

print(sub.check_certificate_limit())  # Should return False
```

Try issuing a certificate - should be blocked.

---

## What You Just Did

✅ Updated environment for new pricing
✅ Migrated database to new plan structure
✅ Created Stripe products and prices
✅ Tested UI displays correctly
✅ Verified limit enforcement works

---

## Common Issues

### "Price ID not found"
**Fix:** Make sure you copied the correct Price ID from Stripe and pasted into `.env`. Restart backend.

### Migration fails
**Fix:** Make sure you're in the backend directory and have activated your virtual environment.

### Pricing page shows old prices
**Fix:** Hard refresh browser (Cmd+Shift+R on Mac, Ctrl+Shift+R on Windows)

### Event creation not blocked at limit
**Fix:** Check that subscription plan is set correctly and usage counter is at limit:
```python
user.subscription.plan  # Should be 'starter', 'professional', or 'premium'
user.subscription.events_created_this_period  # Should be at limit
```

---

## Next Steps

1. **Read full docs:**
   - `IMPLEMENTATION_SUMMARY.md` - Complete overview
   - `STRIPE_SETUP_NEW_PRICING.md` - Detailed Stripe guide
   - `PRICING_IMPLEMENTATION.md` - Implementation details

2. **Set up webhooks:**
   - Go to Stripe Dashboard → Webhooks
   - Add endpoint: `http://localhost:8000/webhooks/stripe/`
   - Select events (see STRIPE_SETUP_NEW_PRICING.md)

3. **Test subscription flow:**
   - Create test subscription with card `4242 4242 4242 4242`
   - Verify webhook delivery
   - Check subscription created in Django admin

4. **Prepare for production:**
   - Create live Stripe products (same process)
   - Update `.env` with live keys
   - Deploy and test

---

## Quick Reference

### Pricing at a Glance

| Plan | Monthly | Annual | Events | Attendees | Certs |
|------|---------|--------|--------|-----------|-------|
| Attendee | Free | Free | 0 | - | 0 |
| Starter | $49 | $41 | 10 | 100 | 100 |
| Professional | $99 | $83 | 30 | 500 | 500 |
| Premium | $199 | $166 | ∞ | 2,000 | ∞ |
| Team | $299 | $249 | ∞ | ∞ | ∞ |

### Stripe Test Cards

- **Success:** `4242 4242 4242 4242`
- **Decline:** `4000 0000 0000 0002`
- **3DS Required:** `4000 0025 0000 3155`

### Django Commands

```bash
# Run migrations
python manage.py migrate billing

# Access Django shell
python manage.py shell

# Check subscription status
python manage.py shell -c "from accounts.models import User; print(User.objects.get(email='test@example.com').subscription)"

# Reset usage counters (for testing)
python manage.py shell -c "from billing.models import Subscription; [s.reset_usage() for s in Subscription.objects.all()]"
```

---

## Success Checklist

- [ ] Environment variables updated
- [ ] Migration ran successfully
- [ ] Stripe products created
- [ ] Pricing page displays 5 tiers
- [ ] Trial signup works (14 days)
- [ ] Event limit enforced correctly
- [ ] Certificate limit enforced correctly
- [ ] Billing page shows correct plan
- [ ] Upgrade flow tested
- [ ] Webhooks configured

---

**You're all set!** 🎉

For detailed information, see `IMPLEMENTATION_SUMMARY.md`.

For Stripe setup details, see `STRIPE_SETUP_NEW_PRICING.md`.

For troubleshooting, see `PRICING_IMPLEMENTATION.md`.
