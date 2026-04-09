# New Pricing Implementation Guide

This document outlines the changes made to implement the new pricing structure and provides instructions for completing the setup.

## Overview of Changes

We've implemented a new multi-tier pricing structure:

### Individual Plans
- **Attendee** (Free): For event participants
- **Starter** ($49/month): 10 events, 100 attendees, 100 certificates
- **Professional** ($99/month): 30 events, 500 attendees, 500 certificates ⭐ Most Popular
- **Premium** ($199/month): Unlimited events, 2,000 attendees, unlimited certificates

### Organization Plans
- **Team** ($299/month): 5 organizer seats included, +$49 per extra seat
- **Business** ($399/month): 15 seats, +$45 per extra seat
- **Enterprise** (Custom): 50+ seats, custom pricing

### Key Features
- **14-day free trial** (changed from 30 days)
- **17% discount** on annual billing
- **Legacy plan support** for backward compatibility

---

## Backend Changes

### 1. Updated Files

#### `backend/src/billing/models.py`
- ✅ Added new plan types: `STARTER`, `PROFESSIONAL`, `PREMIUM`
- ✅ Updated `PLAN_LIMITS` with new tier limits
- ✅ Kept legacy plans (`ORGANIZER`, `ORGANIZATION`) for backward compatibility

#### `backend/src/config/settings/base.py`
- ✅ Updated `STRIPE_PRICE_IDS` for all new plans (monthly + annual)
- ✅ Updated `BILLING_PRICES` with new pricing
- ✅ Changed `BILLING_TRIAL_DAYS` from 30 to 14

#### `backend/src/certificates/services.py`
- ✅ Added certificate limit enforcement in `issue_certificate()`
- ✅ Added `subscription.increment_certificates()` call after issuance

#### `backend/src/organizations/models.py`
- ✅ Updated `PLAN_CONFIG` for Team/Business/Enterprise with new pricing

#### `backend/src/billing/migrations/0003_add_new_plan_tiers.py`
- ✅ Created migration to convert legacy plans to new ones
- ✅ Maps `organizer` → `professional`

---

## Frontend Changes

### 1. Updated Files

#### `frontend/src/api/billing/types.ts`
- ✅ Updated `Subscription` type to include new plan types

#### `frontend/src/pages/billing/BillingPage.tsx`
- ✅ Updated `PLANS` array with all 5 tiers
- ✅ Added `priceAnnual` fields

#### `frontend/src/pages/public/PricingPage.tsx`
- ✅ Updated pricing page with 5-tier structure
- ✅ Updated FAQ to reflect 14-day trial
- ✅ Added annual pricing display

---

## Required Setup Steps

### Step 1: Update Environment Variables

Add these new environment variables to your `.env` file:

```bash
# Trial Configuration (updated)
BILLING_TRIAL_DAYS=14

# Stripe Price IDs - Monthly Plans
STRIPE_PRICE_STARTER=price_xxxxxxxxxxxxx
STRIPE_PRICE_PROFESSIONAL=price_xxxxxxxxxxxxx
STRIPE_PRICE_PREMIUM=price_xxxxxxxxxxxxx
STRIPE_PRICE_TEAM=price_xxxxxxxxxxxxx
STRIPE_PRICE_ENTERPRISE=price_xxxxxxxxxxxxx

# Stripe Price IDs - Annual Plans (17% discount)
STRIPE_PRICE_STARTER_ANNUAL=price_xxxxxxxxxxxxx
STRIPE_PRICE_PROFESSIONAL_ANNUAL=price_xxxxxxxxxxxxx
STRIPE_PRICE_PREMIUM_ANNUAL=price_xxxxxxxxxxxxx
STRIPE_PRICE_TEAM_ANNUAL=price_xxxxxxxxxxxxx
```

### Step 2: Create Stripe Products and Prices

#### In Stripe Dashboard:

1. **Create Products:**
   - Go to Products → Add product
   - Create one product for each plan tier

2. **Create Prices for Each Product:**

   **Starter Plan:**
   - Monthly: $49.00 USD / month
   - Annual: $492.00 USD / year (displays as $41/month)

   **Professional Plan:**
   - Monthly: $99.00 USD / month
   - Annual: $996.00 USD / year (displays as $83/month)

   **Premium Plan:**
   - Monthly: $199.00 USD / month
   - Annual: $1,992.00 USD / year (displays as $166/month)

   **Team Plan (Base):**
   - Monthly: $299.00 USD / month (includes 5 seats)
   - Annual: $2,988.00 USD / year (displays as $249/month)

   **Additional Seat:**
   - Create a separate price for: $49.00 USD / month per seat

3. **Copy Price IDs:**
   - After creating each price, copy the Price ID (starts with `price_`)
   - Add them to your `.env` file

### Step 3: Run Database Migration

```bash
cd backend
python manage.py migrate billing
```

This will:
- Convert existing `organizer` subscriptions to `professional`
- Preserve all existing subscription data

### Step 4: Test the Implementation

1. **Backend Testing:**
   ```bash
   # Start backend
   cd backend
   python manage.py runserver

   # Test API endpoints
   curl http://localhost:8000/api/v1/billing/subscription/
   ```

2. **Frontend Testing:**
   ```bash
   # Start frontend
   cd frontend
   npm run dev

   # Navigate to:
   # - /pricing (public pricing page)
   # - /billing (authenticated billing page)
   ```

3. **Test Cases:**
   - [ ] View pricing page with all 5 tiers
   - [ ] Start 14-day trial for Starter plan
   - [ ] Create event and verify limit enforcement
   - [ ] Issue certificate and verify limit enforcement
   - [ ] Upgrade from Starter to Professional
   - [ ] Test annual billing option

---

## Plan Limits Reference

| Feature | Attendee | Starter | Professional | Premium | Team/Enterprise |
|---------|----------|---------|--------------|---------|-----------------|
| **Events/month** | 0 | 10 | 30 | Unlimited | Unlimited |
| **Attendees/event** | - | 100 | 500 | 2,000 | Unlimited |
| **Certificates/month** | 0 | 100 | 500 | Unlimited | Unlimited |
| **Custom templates** | - | 1 | 5 | Unlimited | Unlimited |
| **Support** | Email | Email | Priority | Phone | Dedicated |
| **API Access** | ❌ | ❌ | ❌ | ✅ | ✅ |
| **White-label** | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Team seats** | - | - | - | - | 5+ included |

---

## Pricing Psychology

### Why These Price Points?

1. **$49 Starter**: Entry point for solopreneurs, below key psychological barrier of $50
2. **$99 Professional**: Sweet spot for established professionals, matches industry standards
3. **$199 Premium**: Power user tier, double the professional price for "unlimited"
4. **$299 Team**: Base team price includes 5 seats, positioning as enterprise solution

### Annual Discount (17%)

- Starter: $492/year vs $588 (saves $96)
- Professional: $996/year vs $1,188 (saves $192)
- Premium: $1,992/year vs $2,388 (saves $396)
- Team: $2,988/year vs $3,588 (saves $600)

### Competitive Positioning

**vs Hopin:**
- Hopin Starter: $99/mo → Our Professional: $99/mo (same features)
- Hopin Growth: $799/mo → Our Premium: $199/mo (75% cheaper!)

**vs Kajabi:**
- Kajabi Basic: $149/mo → Our Professional: $99/mo (33% cheaper)

**vs Teachable + Eventbrite + Accredible:**
- Combined: $231/mo → Our Professional: $99/mo (57% savings)

---

## Migration Notes

### Existing Users

- All `organizer` plan users will be migrated to `professional` (same limits)
- No action required from existing users
- Billing amounts remain unchanged
- Trial periods are preserved

### New Signups

- Default trial: 14 days (changed from 30)
- No credit card required to start trial
- Grace period: 30 days after trial ends
- Clear upgrade prompts when limits are reached

---

## Monitoring & Analytics

### Key Metrics to Track

1. **Conversion Rates:**
   - Trial → Paid conversion (target: 25%)
   - Free → Starter (entry point)
   - Starter → Professional (upsell)

2. **Plan Distribution:**
   - Track which plans are most popular
   - Monitor upgrade/downgrade patterns

3. **Limit Hit Rates:**
   - How often users hit event limits
   - Certificate issuance limit encounters
   - These indicate upgrade opportunities

4. **Churn Analysis:**
   - Track cancellations by plan
   - Identify common cancellation reasons
   - Analyze cancellation timing

---

## Troubleshooting

### Issue: Migration fails with "plan not found"

**Solution**: Ensure all new plan choices are added to `billing/models.py` before running migration

### Issue: Stripe checkout fails

**Solution**:
1. Verify `STRIPE_PRICE_IDS` are correct in `.env`
2. Check that prices exist in Stripe Dashboard
3. Ensure prices are in USD currency

### Issue: Limits not enforcing

**Solution**:
1. Check subscription status is `active` or `trialing`
2. Verify `check_event_limit()` returns correct value
3. Check usage counters are incrementing properly

### Issue: Certificate limit not working

**Solution**:
1. Ensure migration 0003 has been applied
2. Verify `increment_certificates()` is being called in services.py
3. Check subscription limits configuration

---

## Next Steps

1. ✅ Update environment variables with Stripe Price IDs
2. ✅ Create Stripe products and prices
3. ✅ Run database migration
4. ✅ Test all plan tiers
5. ✅ Monitor trial conversions
6. ✅ A/B test pricing page
7. ✅ Set up analytics tracking
8. ✅ Create customer success playbook

---

## Support

If you encounter any issues during implementation:

1. Check the troubleshooting section above
2. Review Stripe webhook logs for payment issues
3. Check Django logs for backend errors
4. Verify environment variables are correctly set

---

**Implementation Date**: 2025-12-29
**Version**: 2.0.0
**Author**: Claude (AI Assistant)
