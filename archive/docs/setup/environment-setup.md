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
| **SMTP Provider** | API Key, Domain, SMTP credentials | ✅ Complete (Sandbox) |
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

### 📧 SMTP Provider (Development)

**Configuration**:
- Domain: Sandbox domain (example)
- API Key: Set
- SMTP: Configured for port 587

**Note**: For production, use your SMTP provider (e.g., Brevo) and set:
1. `SMTP_SERVER`/`SMTP_PORT` via Terraform tfvars
2. `SMTP_LOGIN`/`SMTP_PASSWORD` in Secret Manager
3. Optional: `SMTP_API_KEY` if using provider API features

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
5. Enable Stripe Tax on the **platform** account and add your GST/HST registration (ticketing uses destination charges)

### 2. Test Local Development

```bash
# Start backend
accredit local up --backend

# Or with Docker
accredit docker up -d
accredit docker init
```

### 3. Verify Email (SMTP)

Test email sending:
```python
# In Django shell
python src/manage.py shell

from django.core.mail import send_mail
send_mail(
    'Test Email',
    'Testing SMTP configuration',
    'info@accredit.store',
    ['your-email@example.com'],
)
```

During development, emails go to console (check backend logs).

### 4. Production Environment

Production configuration now lives in **Terraform tfvars + Secret Manager** (no prod env files in repo).

1. **Create `infra/gcp/environments/prod/terraform.tfvars`** (gitignored) with:
   - `project_id = "accredit-store"`
   - `frontend_url`, `cors_origins`, optional `site_url`
   - Email defaults (`default_from_email`, `server_email`, `admin_email`, `smtp_domain`)
   - Billing overrides (`platform_fee_percent`, `billing_default_plan`)
   - Frontend build vars (`frontend_google_maps_api_key`, `frontend_stripe_publishable_key`)
2. **Upload secrets to Secret Manager**:
   - `accredit cloud secrets upload --file .secrets --env prod` (from repo root)
   - or `accredit cloud secrets upload --backend --env prod` (from a local `backend/.env.prod`)
   - or `accredit cloud secrets set <KEY> <VALUE> --env prod`
3. **Apply Terraform and deploy**:
   - `accredit cloud infra apply --env prod`
   - `accredit cloud backend deploy --env prod`
   - `accredit cloud frontend deploy --env prod`

Terraform fills in generated values (DB credentials, bucket names, service URLs) at deploy time.

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
