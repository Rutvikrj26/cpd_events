# Stripe Setup Guide for Accredit

This guide walks you through setting up Stripe for both development and production environments.

## Overview

You'll need to:
1. Create a Stripe Connect account for Accredit under your Consultjes account
2. Set up Products and Pricing
3. Configure Webhooks
4. Update environment variables

---

## Step 1: Create Stripe Connect Account (Recommended)

Since you want to keep Accredit separate from Consultjes:

### Option A: Stripe Connect (Recommended for separate accounting)

1. **Go to Stripe Dashboard**: https://dashboard.stripe.com
2. **Navigate to**: Settings → Connect → Get started
3. **Create a new platform** for Accredit
4. This gives you separate financials while managing from one Consultjes account

### Option B: Separate Stripe Account

1. **Sign up**: https://dashboard.stripe.com/register
2. Use a different email: `stripe@accredit.store`
3. Completely independent from Consultjes

**Recommendation**: Use Option A (Connect) for easier management.

---

## Step 2: Get API Keys

### Development (Test Mode)

1. **Go to**: https://dashboard.stripe.com/test/apikeys
2. **Copy**:
   - **Secret key** (starts with `sk_test_`)
   - **Publishable key** (starts with `pk_test_`)

You already have these in your `.env`:
```
STRIPE_SECRET_KEY=sk_test_51SUJCj2dJZiu6MtI...
STRIPE_PUBLISHABLE_KEY=pk_test_51SUJCj2dJZiu6MtI...
```

### Production (Live Mode)

1. **Complete Stripe account activation** (add business details, banking info)
2. **Go to**: https://dashboard.stripe.com/apikeys (without /test/)
3. **Copy**:
   - **Secret key** (starts with `sk_live_`)
   - **Publishable key** (starts with `pk_live_`)

---

## Step 3: Create Products and Pricing

You need to create subscription products for your billing plans.

### Plans Needed

Based on your code, you have these plans:
- **Attendee** (free/default) - No Stripe product needed
- **Organizer** (paid plan) - Individual event creators
- **LMS** (paid plan) - Individual course creators
- **Organization** (paid plan) - Team plan with $199/month base + $129/seat for additional members

### Create Products (Test Mode)

1. **Go to**: https://dashboard.stripe.com/test/products
2. **Click**: "+ Add product"

#### Product 1: Organizer Plan
- **Name**: CPD Events - Organizer
- **Description**: Individual event organizer subscription
- **Pricing**:
  - Model: Recurring
  - Price: $XX.XX per month (set your pricing)
  - Billing period: Monthly (or Annual)
  - Currency: CAD, USD, or other
- **Click**: "Save product"

#### Product 2: LMS Plan
- **Name**: CPD Events - LMS
- **Description**: Individual course creator subscription
- **Pricing**:
  - Model: Recurring
  - Price: $XX.XX per month (set your pricing)
  - Billing period: Monthly (or Annual)
  - Currency: CAD, USD, or other
- **Click**: "Save product"

#### Product 3: Organization Plan
- **Name**: CPD Events - Organization
- **Description**: Team subscription with unlimited events and courses
- **Pricing**:
  - Base: $199.00 per month (includes 1 admin)
  - Additional seats: $129.00 per seat per month
  - Billing period: Monthly (or Annual)
  - Currency: CAD, USD, or other
- **Click**: "Save product"

### Sync Products from Django Admin

Create Stripe Products/Prices in Django Admin (Billing → Stripe Products/Prices) and click **Save** to sync to Stripe.

### Repeat for Production (Live Mode)

Do the same steps at https://dashboard.stripe.com/products (without /test/)

---

## Step 4: Set Up Webhooks

Webhooks allow Stripe to notify your app about events (payment succeeded, subscription canceled, etc.)

### Development Webhooks (Local Testing)

For local development, use Stripe CLI:

#### Install Stripe CLI

```bash
# macOS
brew install stripe/stripe-cli/stripe

# Or download from: https://stripe.com/docs/stripe-cli
```

#### Login and Forward Webhooks

```bash
# Login to Stripe
stripe login

# Forward webhooks to local backend
stripe listen --forward-to http://localhost:8000/api/webhooks/stripe/
```

This will output a webhook signing secret like: `whsec_xxxxxxxxxxxxx`

#### Update .env

```bash
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx
```

### Production Webhooks

1. **Go to**: https://dashboard.stripe.com/webhooks
2. **Click**: "+ Add endpoint"
3. **Endpoint URL**: `https://your-production-domain.com/api/webhooks/stripe/`
4. **Events to send**:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
5. **Click**: "Add endpoint"
6. **Click**: "Reveal" under "Signing secret"
7. **Copy**: `whsec_xxxxxxxxxxxxx`

#### Update Production .env

```bash
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx
```

---

## Step 5: Update Environment Variables

### Development (.env)

```bash
# Stripe Payment Configuration
STRIPE_SECRET_KEY=sk_test_51SUJCj2dJZiu6MtI...
STRIPE_PUBLISHABLE_KEY=pk_test_51SUJCj2dJZiu6MtI...
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx  # From Stripe CLI
```

### Production (Terraform tfvars + Secret Manager)

```bash
# Stripe Payment Configuration (LIVE KEYS)
# Store secrets in Secret Manager (uploaded via CLI)
STRIPE_SECRET_KEY=sk_live_xxxxxxxxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx  # From webhook endpoint
```

### Frontend (.env)

Already set:
```bash
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_51SUJCj2dJZiu6MtI...
```

For production, set via `infra/gcp/environments/prod/terraform.tfvars`:
```bash
frontend_stripe_publishable_key=pk_live_xxxxxxxxxxxxx
```

---

## Step 6: Testing

### Test in Development

1. **Start webhook listener**:
   ```bash
   stripe listen --forward-to http://localhost:8000/api/webhooks/stripe/
   ```

2. **Start your backend**:
   ```bash
   accredit local up --backend
   ```

3. **Use test card numbers**:
   - Success: `4242 4242 4242 4242`
   - Decline: `4000 0000 0000 0002`
   - 3D Secure: `4000 0025 0000 3155`
   - Any future expiry date, any CVC

4. **Test payment flow** in your app

### Monitor Webhooks

Dashboard: https://dashboard.stripe.com/test/webhooks
- See all webhook deliveries
- Replay failed webhooks
- Check event details

---

## Stripe Tax for Ticketing (Platform MoR)

Ticketing uses **destination charges**, which means the platform is the
merchant of record and Stripe Tax is calculated on the **platform account**.

Do this on the platform Stripe account (test and live):
1. Enable Stripe Tax: https://dashboard.stripe.com/test/tax
2. Add your tax registration (e.g., Canada GST/HST).

Connected accounts do **not** need Stripe Tax enabled in this model.

---

## Step 7: Production Checklist

Before going live:

- [ ] Complete Stripe account activation
- [ ] Add business details and banking information
- [ ] Switch to live mode keys
- [ ] Create production products and pricing
- [ ] Set up production webhook endpoint
- [ ] Update production environment variables
- [ ] Test with live mode test cards (before real payments)
- [ ] Enable Stripe Radar for fraud prevention
- [ ] Set up tax collection (if applicable)
- [ ] Review Terms of Service and Privacy Policy

---

## Pricing Recommendations

Based on typical SaaS models for event management:

### Suggested Pricing (CAD)

- **Attendee**: Free (default)
- **Organizer**: $29/month
  - Create unlimited events
  - Up to 100 attendees per event
  - Basic analytics
- **Organization**: $99/month
  - Everything in Organizer
  - Unlimited attendees
  - Team collaboration
  - Advanced analytics
  - White-label branding

Adjust based on your market research and value proposition.

---

## Quick Reference

### Test Card Numbers

| Card Number | Scenario |
|-------------|----------|
| `4242 4242 4242 4242` | Successful payment |
| `4000 0000 0000 0002` | Card declined |
| `4000 0025 0000 3155` | 3D Secure authentication |
| `4000 0000 0000 9995` | Insufficient funds |

### Webhook Events

Common events your app should handle:
- `checkout.session.completed` - Payment successful
- `customer.subscription.updated` - Plan changed
- `customer.subscription.deleted` - Subscription canceled
- `invoice.payment_failed` - Payment failed

### Useful Links

- **Stripe Dashboard**: https://dashboard.stripe.com
- **Test Mode**: https://dashboard.stripe.com/test/
- **API Docs**: https://stripe.com/docs/api
- **Webhooks**: https://stripe.com/docs/webhooks
- **Testing**: https://stripe.com/docs/testing

---

## Current Status

✅ **Completed**:
- Test API keys added to `.env`
- Publishable key added to frontend `.env`

⚠️ **TODO** (You need to do these):
1. Configure Stripe Products/Prices in Django Admin and sync to Stripe
2. Set up webhook endpoint (use Stripe CLI for local dev)
3. Update `STRIPE_WEBHOOK_SECRET` in backend `.env`
4. Test payment flow with test cards
5. Repeat for production when ready to launch

---

## Need Help?

- **Stripe Support**: https://support.stripe.com
- **Stripe Discord**: https://discord.gg/stripe
- **Billing Code**: Check `backend/src/billing/` for implementation details
