# Environment Variables Setup - Summary

**Date**: December 28, 2025  
**Status**: ✅ Development environment configured

---

## What Was Configured

### Backend Environment (`backend/.env`)

#### ✅ Fully Configured

| Category | Variables | Status |
|----------|-----------|--------|
| **Django** | SECRET_KEY, DEBUG, SETTINGS_MODULE | ✅ Complete |
| **Database** | PostgreSQL connection (local) | ✅ Complete |
| **Redis** | Connection URL | ✅ Complete |
| **Site** | URL, CORS, Allowed Hosts | ✅ Complete |
| **Mailgun** | API Key, Domain, SMTP credentials | ✅ Complete (Sandbox) |
| **GCP** | Project ID, Location, Bucket name | ✅ Complete |
| **Zoom** | All 4 credentials | ✅ Complete |
| **Security** | Encryption key | ✅ Complete |

#### ⚠️ Needs Your Action

| Category | Variables | Action Required |
|----------|-----------|-----------------|
| **Stripe** | WEBHOOK_SECRET | Follow STRIPE_SETUP.md Step 4 |
| **Stripe** | PRICE_ORGANIZER | Follow STRIPE_SETUP.md Step 3 |
| **Stripe** | PRICE_ORGANIZATION | Follow STRIPE_SETUP.md Step 3 |

### Frontend Environment (`frontend/.env`)

| Variable | Status |
|----------|--------|
| `VITE_API_URL` | ✅ Complete |
| `VITE_GOOGLE_MAPS_API_KEY` | ✅ Complete |
| `VITE_STRIPE_PUBLISHABLE_KEY` | ✅ Complete |

---

## Configuration Details

### 🔐 Generated Secrets

The following were auto-generated securely:

- **DJANGO_SECRET_KEY**: Random 50-character token
- **ENCRYPTION_KEY**: Base64-encoded 32-byte key

### 📧 Mailgun (Development)

**Configuration**:
- Domain: `sandbox6abed37fe7424efcba793b3f8c4724c3.mailgun.org` (Sandbox)
- API Key: Set
- SMTP: Configured for port 587

**Note**: This is the sandbox domain for development. For production, you'll need to:
1. Verify your production domain in Mailgun
2. Update `MAILGUN_DOMAIN` and `MAILGUN_API_KEY`

### ☁️ GCP Configuration

**Project**: `cpd-events-481919`  
**Bucket**: `accredit`  
**Location**: `us-central1`

### 🔗 Zoom Integration

All Zoom credentials are configured:
- Client ID: Set
- Client Secret: Set
- Redirect URI: `http://localhost:8000/api/integrations/zoom/callback/`
- Webhook Secret: Set

---

## Next Steps

### 1. Complete Stripe Setup (Required for Billing)

Follow the detailed guide: **`STRIPE_SETUP.md`**

Quick steps:
1. Create Products in Stripe Dashboard (Test mode)
2. Get Price IDs
3. Set up webhooks (use Stripe CLI for local dev)
4. Update `.env` with the 3 missing values

### 2. Test Local Development

```bash
# Start backend
accredit local up --backend

# Or with Docker
accredit docker up -d
accredit docker init
```

### 3. Verify Email (Mailgun)

Test email sending:
```python
# In Django shell
python src/manage.py shell

from django.core.mail import send_mail
send_mail(
    'Test Email',
    'Testing Mailgun configuration',
    'info@accredit.store',
    ['your-email@example.com'],
)
```

During development, emails go to console (check backend logs).

### 4. Production Environment

When ready for production:

1. **Create `.env.production`** (or use Cloud Run environment variables)
2. **Update these for production**:
   - `DEBUG=False`
   - `DJANGO_SECRET_KEY` (generate new one)
   - `ALLOWED_HOSTS` (your production domain)
   - `SITE_URL` (https://accredit.store)
   - `CORS_ALLOWED_ORIGINS` (your production frontend URL)
   - `EMAIL_BACKEND` → Mailgun SMTP backend
   - `MAILGUN_DOMAIN` → Your verified production domain
   - `MAILGUN_API_KEY` → Production API key
   - `STRIPE_*` → Live mode keys and production price IDs
   - `GCS_BUCKET_NAME` → Production bucket
   - Generate new `ENCRYPTION_KEY`

---

## Security Notes

### ✅ Protected

- `.env` files are in `.gitignore`
- `.env.example` has placeholders only
- Secret keys are randomly generated
- No credentials committed to git

### ⚠️ Important

1. **Never commit `.env` files** to version control
2. **Rotate keys** if accidentally exposed
3. **Use different keys** for dev/staging/prod
4. **Enable 2FA** on Stripe and GCP accounts
5. **Review access logs** regularly

---

## File Locations

| File | Purpose | Committed to Git? |
|------|---------|-------------------|
| `backend/.env` | Active development config | ❌ No (gitignored) |
| `backend/.env.example` | Template with placeholders | ✅ Yes |
| `frontend/.env` | Active frontend config | ❌ No (gitignored) |
| `STRIPE_SETUP.md` | Stripe setup guide | ✅ Yes |
| `ENV_SETUP_SUMMARY.md` | This file | ✅ Yes |

---

## Quick Reference

### Start Development

```bash
# Backend + Frontend (native)
accredit local up

# Backend only
accredit local up --backend

# Docker stack
accredit docker up -d
accredit docker init
```

### Check Configuration

```bash
# Backend
cd backend
poetry run python src/manage.py check

# Frontend
cd frontend
npm run dev
```

### Environment-Specific Settings

Django automatically uses `config.settings.development` (from `.env`).

For production, set: `DJANGO_SETTINGS_MODULE=config.settings.production`

---

## Troubleshooting

### Issue: "Missing environment variable"

**Solution**: Check that backend/.env exists and has all required variables.

### Issue: Email not sending

**Solution**: In development, emails print to console. Check backend logs:
```bash
accredit local logs --backend
```

### Issue: Stripe webhook not working locally

**Solution**: Run Stripe CLI:
```bash
stripe listen --forward-to http://localhost:8000/api/webhooks/stripe/
```

### Issue: GCS bucket not found

**Solution**: 
1. Ensure bucket exists in GCP project `cpd-events-481919`
2. Check GCP authentication is set up
3. For local dev with Docker: `accredit docker init` creates emulator bucket

---

## Contact Info for Services

| Service | Email/Account |
|---------|---------------|
| **Mailgun** | info@accredit.store |
| **GCP** | cpd-events-481919 |
| **Stripe** | (Your Consultjes account - create Accredit Connect) |
| **Zoom** | (Configured) |

---

**Status**: Development environment ready! Complete Stripe setup to enable billing features.
