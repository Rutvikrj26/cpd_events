# Environment Variables - Quick Cheat Sheet

## ✅ What's Done

**Backend `.env`**:
- ✅ Django (SECRET_KEY, DEBUG, etc.)
- ✅ Database (PostgreSQL local)
- ✅ SMTP provider (Sandbox for dev)
- ✅ GCP (Project: cpd-events-481919, Bucket: accredit)
- ✅ Zoom (All credentials)
- ✅ Stripe (Test keys already there)
- ✅ Security (Encryption key generated)

**Frontend `.env`**:
- ✅ All set (API URL, Google Maps, Stripe key)

## ⚠️ What You Need to Do

### 1. Stripe Setup (3 values needed)

Run these commands after creating products in Stripe:

```bash
cd backend

# After creating products in Stripe Dashboard
# Update these 3 values in .env:
# - STRIPE_WEBHOOK_SECRET (from Stripe CLI: stripe listen)
# - STRIPE_PRICE_ORGANIZER (from Products page)
# - STRIPE_PRICE_ORGANIZATION (from Products page)
```

**Full instructions**: See `STRIPE_SETUP.md`

### 1b. Stripe Tax (Ticketing)

Ticketing uses **destination charges**, so Stripe Tax runs on the **platform** account.
Enable Stripe Tax and add your GST/HST registration in test and live:

- https://dashboard.stripe.com/test/tax
- https://dashboard.stripe.com/tax

### 2. Test Everything Works

```bash
# Start development
accredit local up

# Check backend is running
curl http://localhost:8000/api/v1/

# Check frontend
open http://localhost:5173
```

## 📝 Quick Copy-Paste

### Test Stripe Webhooks Locally

```bash
# Terminal 1: Start webhook listener
stripe listen --forward-to http://localhost:8000/api/webhooks/stripe/

# Copy the webhook secret (whsec_...) and add to backend/.env:
# STRIPE_WEBHOOK_SECRET=whsec_xxxxx

# Terminal 2: Start backend
accredit local up --backend
```

### Create Stripe Products

1. Go to: https://dashboard.stripe.com/test/products
2. Click "+ Add product"
3. Create "Accredit Organizer" ($29/month or your price)
4. Copy Price ID → Update `STRIPE_PRICE_ORGANIZER` in `.env`
5. Create "Accredit Organization" ($99/month or your price)
6. Copy Price ID → Update `STRIPE_PRICE_ORGANIZATION` in `.env`

## 🚀 Production TODO (Later)

When deploying to production:
1. Generate new DJANGO_SECRET_KEY
2. Generate new ENCRYPTION_KEY
3. Get SMTP provider domain & API key (Brevo, Mailgun, etc.)
4. Get Stripe live keys (sk_live_, pk_live_)
5. Create production Stripe products
6. Set up production webhooks
7. Update GCS_BUCKET_NAME to production bucket
8. Set DEBUG=False

## 📋 Files Reference

- `backend/.env` - Your active development config (DO NOT COMMIT)
- `backend/.env.example` - Template (safe to commit)
- `STRIPE_SETUP.md` - Detailed Stripe guide
- `ENV_SETUP_SUMMARY.md` - Complete setup documentation
- `ENV_CHEATSHEET.md` - This quick reference
