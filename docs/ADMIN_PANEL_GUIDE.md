# Django Admin Panel - Pricing Management Guide

**Last Updated**: 2026-01-11

**Note**: Trial periods are fully configurable per product. Examples in this guide use placeholder values - set your actual trial duration based on your business needs.

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
- Name (e.g., "CPD Events - Organizer")
- Plan (organizer, lms, organization)
- Trial period days (configurable per product)
- **Show contact sales** ✓/✗
- Is active ✓/✗
- Stripe product ID
- Created at

### When You Click on a Product, You'll See These Sections:

#### 1. **Product Details**
- **Name**: Product name (shown to customers)
- **Description**: Product description
- **Plan**: Which subscription plan (Organizer, LMS, Organization)
- **Is active**: ✓ Active products appear on pricing page

#### 2. **Pricing Display** (NEW!)
- **Show contact sales**: ☐ Check this box to:
  - Hide pricing on frontend
  - Show "Custom Pricing" text
  - Change CTA to "Contact Sales" button
  - Perfect for enterprise/custom plans

#### 3. **Trial Configuration**
- **Trial period days**: e.g., 90
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

- **Courses per month**:
  - Empty/null = Unlimited
  - Example: 30
  - Shown as "30 courses per month"

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

### Organizer Plan
After migration, you should see:

**Name**: CPD Events - Organizer
**Plan**: Organizer
**Trial period days**: (configurable, e.g., 30, 90, or custom)
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
- "Custom certificate templates"
- "Priority email support"
- Trial period (configurable, e.g., "30-day free trial" or "90-day free trial")

### LMS Plan
After migration, you should see:

**Name**: CPD Events - LMS
**Plan**: LMS
**Trial period days**: (configurable, e.g., 30, 90, or custom)
**Show contact sales**: ☐ (unchecked)

**Feature Limits**:
- Courses per month: **30**
- Certificates per month: **500**

**Features shown on pricing page**:
- "30 courses per month"
- "500 certificates/month"
- "Self-paced course builder"
- "Course certificates"
- "Learner progress tracking"
- Trial period (configurable per product)

### Organization Plan
After migration, you should see:

**Name**: CPD Events - Organization
**Plan**: Organization
**Trial period days**: (configurable, e.g., 30, 90, or custom)
**Show contact sales**: ☐ (unchecked)

**Feature Limits**:
- Events per month: **(blank - unlimited)**
- Courses per month: **(blank - unlimited)**
- Certificates per month: **(blank - unlimited)**
- Max attendees per event: **2000**

**Features shown on pricing page**:
- "Unlimited events"
- "Unlimited courses"
- "2,000 attendees per event"
- "Unlimited certificates"
- "Multi-user team access"
- "White-label options"
- "API access"
- "Priority support"
- "Team collaboration"
- "Shared templates"
- "Dedicated account manager"
- Trial period (configurable per product)

---

## How to Use These Features

### Example 1: Change Event Limit
1. Django Admin → Stripe Products → "CPD Events - Organizer"
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

### Example 3: Customize Trial Period
1. Django Admin → Stripe Products → Select product
2. Scroll to "Trial Configuration"
3. Set "Trial period days" to your desired value (e.g., **30**, **90**, or **180**)
4. Click **Save**
5. Result:
   - New signups get the configured trial period
   - Pricing page shows "{N}-day free trial"
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
p = StripeProduct.objects.get(plan='organizer')
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
