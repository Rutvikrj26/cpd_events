# Stripe Setup Guide - New Pricing Structure

Complete guide for setting up Stripe products and prices for the new pricing tiers.

## Prerequisites

- Stripe account (test mode for development, live mode for production)
- Access to Stripe Dashboard
- Backend `.env` file ready for price IDs

---

## Step 1: Create Stripe Products

### In Stripe Dashboard:

1. Navigate to **Products** → **Add product**
2. Create the following products:

#### Product 1: CPD Events - Starter
- **Name**: CPD Events - Starter
- **Description**: For solo professionals getting started with CPD event management
- **Statement descriptor**: CPD Starter

#### Product 2: CPD Events - Professional
- **Name**: CPD Events - Professional
- **Description**: For established trainers and consultants managing CPD events
- **Statement descriptor**: CPD Professional
- **Add badge**: "Most Popular" or "Recommended"

#### Product 3: CPD Events - Premium
- **Name**: CPD Events - Premium
- **Description**: For power users and training organizations with unlimited needs
- **Statement descriptor**: CPD Premium

#### Product 4: CPD Events - Team
- **Name**: CPD Events - Team
- **Description**: For organizations with multiple organizers and team collaboration
- **Statement descriptor**: CPD Team

#### Product 5: Additional Seat
- **Name**: CPD Events - Additional Seat
- **Description**: Extra organizer seat for Team and Enterprise plans
- **Statement descriptor**: CPD Extra Seat

---

## Step 2: Create Prices for Each Product

### Starter Plan

**Monthly Price:**
- Product: CPD Events - Starter
- Pricing model: Standard pricing
- Price: **$49.00 USD**
- Billing period: **Monthly**
- Price description: "Starter - Monthly"
- Tax behavior: Taxable

**Annual Price:**
- Product: CPD Events - Starter
- Pricing model: Standard pricing
- Price: **$492.00 USD**
- Billing period: **Yearly**
- Price description: "Starter - Annual (Save 17%)"
- Tax behavior: Taxable

### Professional Plan

**Monthly Price:**
- Product: CPD Events - Professional
- Pricing model: Standard pricing
- Price: **$99.00 USD**
- Billing period: **Monthly**
- Price description: "Professional - Monthly"
- Tax behavior: Taxable

**Annual Price:**
- Product: CPD Events - Professional
- Pricing model: Standard pricing
- Price: **$996.00 USD**
- Billing period: **Yearly**
- Price description: "Professional - Annual (Save 17%)"
- Tax behavior: Taxable

### Premium Plan

**Monthly Price:**
- Product: CPD Events - Premium
- Pricing model: Standard pricing
- Price: **$199.00 USD**
- Billing period: **Monthly**
- Price description: "Premium - Monthly"
- Tax behavior: Taxable

**Annual Price:**
- Product: CPD Events - Premium
- Pricing model: Standard pricing
- Price: **$1,992.00 USD**
- Billing period: **Yearly**
- Price description: "Premium - Annual (Save 17%)"
- Tax behavior: Taxable

### Team Plan (Base)

**Monthly Price:**
- Product: CPD Events - Team
- Pricing model: Standard pricing
- Price: **$299.00 USD**
- Billing period: **Monthly**
- Price description: "Team - Monthly (5 seats included)"
- Tax behavior: Taxable

**Annual Price:**
- Product: CPD Events - Team
- Pricing model: Standard pricing
- Price: **$2,988.00 USD**
- Billing period: **Yearly**
- Price description: "Team - Annual (5 seats included, Save 17%)"
- Tax behavior: Taxable

### Additional Seat (for Team/Enterprise)

**Monthly Price:**
- Product: CPD Events - Additional Seat
- Pricing model: Standard pricing
- Price: **$49.00 USD**
- Billing period: **Monthly**
- Price description: "Additional Organizer Seat - Monthly"
- Tax behavior: Taxable

---

## Step 3: Copy Price IDs

After creating each price, you'll see a Price ID that starts with `price_`.

### Update your `.env` file:

```bash
# Individual Plans - Monthly
STRIPE_PRICE_STARTER=price_1234567890abcdefghij
STRIPE_PRICE_PROFESSIONAL=price_abcdefghij1234567890
STRIPE_PRICE_PREMIUM=price_9876543210jihgfedcba

# Individual Plans - Annual
STRIPE_PRICE_STARTER_ANNUAL=price_annual1234567890ab
STRIPE_PRICE_PROFESSIONAL_ANNUAL=price_annualabcdefghij12
STRIPE_PRICE_PREMIUM_ANNUAL=price_annual9876543210ji

# Organization Plans
STRIPE_PRICE_TEAM=price_team1234567890abcdef
STRIPE_PRICE_TEAM_ANNUAL=price_teamannual12345678
STRIPE_PRICE_ENTERPRISE=price_enterprise123456

# Additional Seat
STRIPE_PRICE_ADDITIONAL_SEAT=price_seat1234567890ab
```

---

## Step 4: Configure Free Trial

### In Stripe Dashboard:

1. Go to **Settings** → **Billing**
2. Under **Subscriptions**, configure:
   - **Default trial period**: 14 days
   - **Require payment method for trials**: No (optional)
   - **Send email receipts**: Yes

---

## Step 5: Set Up Webhooks

### Create Webhook Endpoint:

1. Go to **Developers** → **Webhooks**
2. Click **Add endpoint**
3. Enter endpoint URL:
   - Dev: `http://localhost:8000/webhooks/stripe/`
   - Prod: `https://your-domain.com/webhooks/stripe/`

4. Select events to send:
   - ✅ `customer.created`
   - ✅ `customer.updated`
   - ✅ `customer.deleted`
   - ✅ `customer.subscription.created`
   - ✅ `customer.subscription.updated`
   - ✅ `customer.subscription.deleted`
   - ✅ `customer.subscription.trial_will_end`
   - ✅ `invoice.created`
   - ✅ `invoice.payment_succeeded`
   - ✅ `invoice.payment_failed`
   - ✅ `payment_intent.succeeded`
   - ✅ `payment_intent.payment_failed`
   - ✅ `checkout.session.completed`

5. Copy the **Signing secret** (starts with `whsec_`)
6. Add to `.env`:
   ```bash
   STRIPE_WEBHOOK_SECRET=whsec_1234567890abcdefghij
   ```

---

## Step 6: Configure Customer Portal

### In Stripe Dashboard:

1. Go to **Settings** → **Customer portal**
2. Enable the portal
3. Configure features:
   - ✅ **Cancel subscription**: Allow
   - ✅ **Update payment method**: Allow
   - ✅ **Update subscription**: Allow (upgrade/downgrade)
   - ✅ **Invoice history**: Show
   - ✅ **Update billing information**: Allow

4. Set cancellation behavior:
   - **Cancellation effective**: At period end
   - **Save payment method**: Yes
   - **Proration**: Create prorations for changes

---

## Step 7: Test the Integration

### Test Mode Checklist:

1. **Create Test Subscription:**
   ```bash
   # Use Stripe test card
   Card number: 4242 4242 4242 4242
   Exp: Any future date
   CVC: Any 3 digits
   ZIP: Any 5 digits
   ```

2. **Test Scenarios:**
   - [ ] Start 14-day trial for Starter plan
   - [ ] Start 14-day trial for Professional plan
   - [ ] Upgrade from Starter to Professional
   - [ ] Downgrade from Premium to Professional
   - [ ] Cancel subscription (should end at period end)
   - [ ] Reactivate canceled subscription
   - [ ] Test annual billing cycle
   - [ ] Test webhook delivery

3. **Verify Webhooks:**
   - Go to **Developers** → **Webhooks** → Your endpoint
   - Check **Webhook logs** for successful deliveries
   - Status should be `200 OK`

---

## Step 8: Pricing Table (Optional)

### Create Embedded Pricing Table:

1. Go to **Products** → **Pricing tables**
2. Click **Create pricing table**
3. Add your products:
   - Starter (monthly + annual)
   - Professional (monthly + annual)
   - Premium (monthly + annual)
4. Customize styling to match your brand
5. Copy embed code
6. Add to your website (optional alternative to custom pricing page)

---

## Pricing Quick Reference

### Monthly Pricing

| Plan | Price | Stripe Amount |
|------|-------|---------------|
| Attendee | Free | $0.00 |
| Starter | $49/mo | $49.00 |
| Professional | $99/mo | $99.00 |
| Premium | $199/mo | $199.00 |
| Team | $299/mo | $299.00 |
| Additional Seat | $49/seat | $49.00 |

### Annual Pricing (17% discount)

| Plan | Annual Price | Monthly Equivalent | Savings |
|------|-------------|-------------------|---------|
| Starter | $492/year | $41/mo | $96 |
| Professional | $996/year | $83/mo | $192 |
| Premium | $1,992/year | $166/mo | $396 |
| Team | $2,988/year | $249/mo | $600 |

---

## Testing Card Numbers

### Successful Payments
- **Visa**: `4242 4242 4242 4242`
- **Mastercard**: `5555 5555 5555 4444`
- **Amex**: `3782 822463 10005`

### Failed Payments
- **Card declined**: `4000 0000 0000 0002`
- **Insufficient funds**: `4000 0000 0000 9995`
- **Requires authentication**: `4000 0027 6000 3184`

### 3D Secure Authentication
- **Success**: `4000 0025 0000 3155`
- **Failure**: `4000 0000 0000 3220`

---

## Troubleshooting

### Issue: Price ID not found

**Cause**: Price ID not set in `.env` or incorrect
**Solution**:
1. Copy exact Price ID from Stripe Dashboard
2. Ensure no extra spaces
3. Restart backend after updating `.env`

### Issue: Webhook signature verification failed

**Cause**: Incorrect webhook secret
**Solution**:
1. Copy signing secret from webhook endpoint in Stripe
2. Update `STRIPE_WEBHOOK_SECRET` in `.env`
3. Restart backend

### Issue: Trial not starting

**Cause**: Price doesn't have trial period configured
**Solution**:
1. Check Stripe Dashboard → Billing settings
2. Ensure trial is 14 days
3. Or handle trial period in backend code

### Issue: Payment succeeds but subscription not created

**Cause**: Webhook not being processed
**Solution**:
1. Check webhook logs in Stripe Dashboard
2. Verify endpoint URL is correct
3. Check backend logs for errors
4. Test webhook delivery manually

---

## Security Best Practices

1. **Never commit API keys**: Keep `.env` out of version control
2. **Use test mode first**: Fully test before switching to live mode
3. **Verify webhook signatures**: Already implemented in backend
4. **Use HTTPS in production**: Required for live mode
5. **Rotate keys periodically**: Change API keys every 6-12 months
6. **Monitor for fraud**: Set up Stripe Radar rules
7. **Implement 3D Secure**: Already handled by Stripe.js

---

## Going Live Checklist

Before switching to live mode:

- [ ] All test scenarios pass
- [ ] Webhook endpoint uses HTTPS
- [ ] Live API keys obtained from Stripe
- [ ] Live webhook secret configured
- [ ] Customer portal configured
- [ ] Email templates reviewed
- [ ] Tax settings configured (if applicable)
- [ ] Pricing confirmed and approved
- [ ] Legal terms & privacy policy updated
- [ ] Backup plan for failed payments
- [ ] Customer support process defined
- [ ] Monitoring and alerts set up

---

## Support Resources

- **Stripe Documentation**: https://stripe.com/docs
- **Stripe Support**: https://support.stripe.com
- **Testing Guide**: https://stripe.com/docs/testing
- **Webhook Guide**: https://stripe.com/docs/webhooks
- **Customer Portal**: https://stripe.com/docs/billing/subscriptions/customer-portal

---

**Last Updated**: 2025-12-29
**Version**: 2.0.0
