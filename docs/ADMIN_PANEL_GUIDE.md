# Django Admin Panel - Pricing Management Guide

**Last Updated**: 2025-12-29

---

## What You'll See After Running Migration

### 1. Run the Migration First

```bash
cd backend/src
python manage.py migrate billing
# Should apply: 0007_add_contact_sales_and_features
```

---

## Stripe Products Admin

### Location
Django Admin → Billing → Stripe Products

### List View Shows:
- Name (e.g., "CPD Events - Professional")
- Plan (professional, organization, etc.)
- Trial period days (e.g., 90)
- **Show contact sales** ✓/✗ (NEW!)
- Is active ✓/✗
- Stripe product ID
- Created at

### When You Click on a Product, You'll See These Sections:

#### 1. **Product Details**
- **Name**: Product name (shown to customers)
- **Description**: Product description
- **Plan**: Which subscription plan (Professional, Organization, etc.)
- **Is active**: ✓ Active products appear on pricing page

#### 2. **Pricing Display** (NEW!)
- **Show contact sales**: ☐ Check this box to:
  - Hide pricing on frontend
  - Show "Custom Pricing" text
  - Change CTA to "Contact Sales" button
  - Perfect for enterprise/custom plans

#### 3. **Trial Configuration**
- **Trial period days**: e.g., 90
  - Leave blank = use global default (14 days)
  - Set value = custom trial for this product

#### 4. **Feature Limits** (NEW!)
This section controls BOTH:
- Subscription enforcement (what users can actually do)
- Pricing page features display (what's shown to customers)

Fields:
- **Events per month**:
  - Empty/null = Unlimited
  - Example: 30
  - Shown on pricing page as "30 events per month"

- **Certificates per month**:
  - Empty/null = Unlimited
  - Example: 500
  - Shown as "500 certificates/month"

- **Max attendees per event**:
  - Empty/null = Unlimited
  - Example: 500
  - Shown as "500 attendees per event"

#### 5. **Stripe Integration** (collapsed)
- Stripe product ID (auto-populated)

#### 6. **Metadata** (collapsed)
- UUID, Created at, Updated at

---

## Current Setup After Migration

### Professional Plan
After migration, you should see:

**Name**: CPD Events - Professional
**Plan**: Professional
**Trial period days**: 90
**Show contact sales**: ☐ (unchecked)

**Feature Limits**:
- Events per month: **30**
- Certificates per month: **500**
- Max attendees per event: **500**

**Features shown on pricing page**:
- "30 events per month"
- "500 attendees per event"
- "500 certificates/month"
- "Zoom integration"
- "Advanced analytics"
- "Custom certificate templates"
- "Priority email support"
- "90-day free trial"

### Organization Plan
After migration, you should see:

**Name**: CPD Events - Organization
**Plan**: Organization
**Trial period days**: 90
**Show contact sales**: ☐ (unchecked)

**Feature Limits**:
- Events per month: **(blank - unlimited)**
- Certificates per month: **(blank - unlimited)**
- Max attendees per event: **2000**

**Features shown on pricing page**:
- "Unlimited events"
- "2,000 attendees per event"
- "Unlimited certificates"
- "Multi-user team access"
- "Advanced analytics & reporting"
- "White-label options"
- "API access"
- "Priority support"
- "Team collaboration"
- "Shared templates"
- "Dedicated account manager"
- "90-day free trial"

---

## How to Use These Features

### Example 1: Change Event Limit
1. Django Admin → Stripe Products → "CPD Events - Professional"
2. Scroll to "Feature Limits"
3. Change "Events per month" from **30** to **50**
4. Click **Save**
5. Result:
   - Pricing page shows "50 events per month"
   - Subscription enforcement allows 50 events/month
   - Users can create up to 50 events

### Example 2: Make Organization "Contact Sales" Only
1. Django Admin → Stripe Products → "CPD Events - Organization"
2. Scroll to "Pricing Display"
3. Check ✓ **Show contact sales**
4. Click **Save**
5. Result:
   - Pricing page shows "Custom Pricing" (no $199)
   - Button says "Contact Sales" (links to /contact)
   - Features still displayed
   - Good for custom/enterprise plans

### Example 3: Add Enterprise Plan
1. Django Admin → Stripe Products → **Add Stripe Product**
2. Fill in:
   - Name: "CPD Events - Enterprise"
   - Description: "Custom enterprise solution for large teams"
   - Plan: "organization" (or add new choice to model)
   - Is active: ✓
   - **Show contact sales**: ✓
   - Trial period days: (blank or 0)
   - Events per month: (blank = unlimited)
   - Certificates per month: (blank = unlimited)
   - Max attendees per event: (blank = unlimited)
3. Click **Save**
4. Create prices if needed (optional if using Contact Sales)
5. Result:
   - Shows on pricing page with "Custom Pricing"
   - "Contact Sales" button
   - All features listed

### Example 4: Extend Trial Period
1. Django Admin → Stripe Products → Select product
2. Scroll to "Trial Configuration"
3. Change "Trial period days" from **90** to **180**
4. Click **Save**
5. Result:
   - New signups get 180-day trial
   - Pricing page shows "180-day free trial"
   - Existing subscriptions unchanged

---

## What Happens When You Click "Save"

1. **Database updated** ✓
2. **Stripe synced** ✓ (if configured)
3. **Features auto-generated** ✓
4. **Pricing page updates immediately** ✓ (on next page load)
5. **Subscription limits enforced** ✓ (immediately for all users)

---

## Troubleshooting

### I don't see the new fields!
**Solution**: Run the migration:
```bash
cd backend/src
python manage.py migrate billing
```

### The features aren't showing on the pricing page
**Check**:
1. Is the product **active**? (checkbox)
2. Did you set the feature limits?
3. Did you refresh the pricing page?
4. Check browser console for errors

### The limits aren't being enforced
**Check**:
1. Did you save the product after setting limits?
2. Check the `Subscription.limits` property is reading from database
3. Verify in Django shell:
```python
from billing.models import StripeProduct
p = StripeProduct.objects.get(plan='professional')
print(p.get_feature_limits())
print(p.get_features_list())
```

---

## Summary

After running the migration, you'll have **full control** over:

✅ **Pricing display** - Show prices or "Contact Sales"
✅ **Trial periods** - Per product, customizable
✅ **Event limits** - How many events users can create
✅ **Certificate limits** - How many certificates can be issued
✅ **Attendee limits** - Max attendees per event
✅ **Features display** - Auto-generated from limits + plan-specific features
✅ **Subscription enforcement** - Limits are enforced in real-time

**All managed from Django Admin, no code deployments needed!**
