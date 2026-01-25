# Accredit - Project Information

**Last Updated:** 2026-01-25

---

## Project Identity

- **Name:** Accredit (formerly CPD Events)
- **Type:** SaaS Platform for CPD Event Management
- **Tech Stack:** Django + React + Google Cloud Platform
- **Repository:** /home/beyonder/projects/cpd_events

---

## Production Environment

### URLs
- **Frontend:** https://accredit-store.web.app
- **Backend API:** https://api.accredit.store
- **LinkedIn:** https://www.linkedin.com/company/accredit-store

### GCP Configuration
- **Project ID:** accredit-store
- **Project Number:** 830768164
- **Region:** us-central1
- **Environment:** prod

### Services
- **Cloud Run:** cpd-events-prod
- **Cloud SQL:** cpd-events-prod-db (PostgreSQL 15, db-f1-micro)
- **Artifact Registry:** us-central1-docker.pkg.dev/accredit-store/backend
- **Storage Buckets:**
  - `accredit-store-cpd-events-prod-media`
  - `accredit-store-cpd-events-prod-certificates`
  - `accredit-store-terraform-state`
  - `accredit-store-deployment-state`

### Current Configuration (as of 2026-01-25)
- **CPU:** 1 vCPU
- **Memory:** 1 GiB
- **Workers:** 3 Gunicorn workers
- **Min Instances:** 1 (always running)
- **Max Instances:** 4
- **Concurrency:** 80 requests per instance
- **Cache:** locmem (per-instance, no Redis)

---

## Deployment Workflow

### ✅ CORRECT Way to Deploy

**Backend:**
```bash
# 1. Build Docker image
accredit cloud backend build --env prod

# 2. Deploy to Cloud Run
accredit cloud backend deploy --env prod --tag latest

# 3. Verify
accredit cloud backend logs --env prod --limit 20
accredit cloud backend history --env prod
```

**Frontend:**
```bash
# 1. Build and deploy (from frontend directory)
cd frontend
npm run build
firebase deploy --only hosting

# 2. Verify
# Visit https://accredit-store.web.app
```

**Infrastructure (Terraform):**
```bash
cd infra/gcp/environments/prod
terraform plan
terraform apply
```

### ❌ INCORRECT Way to Deploy
- Don't use `gcloud run deploy` directly (bypasses state tracking)
- Don't use `docker push` without the Accredit CLI
- Always use Accredit CLI to maintain deployment state in GCS

---

## Key Technical Decisions

### 1. Deployment Strategy
- **Image Tag:** `:latest` (not pinned versions)
- **Traffic Routing:** `latest_revision = true` (always route to newest)
- **State Tracking:** Two-layer system (Terraform + GCS deployment state)

### 2. Caching Strategy
- **Removed Redis** (2026-01-25) - simplified architecture
- **Using:** locmem cache (per-instance)
- **Sessions:** Database-backed

### 3. Infrastructure as Code
- **Tool:** Terraform
- **Location:** `infra/gcp/environments/{dev,prod}/`
- **State:** Local files (not GCS due to VPC Service Controls)

---

## Git Workflow

### Branch Strategy
- **Main Branch:** `dev`
- **Production Tags:** Format `prod-YYYYMMDD-HHMMSS`
- **Frontend Tags:** Format `frontend-YYYYMMDD-HHMMSS`

### Recent Commits
```
c332150 - Fixed CPD Credits Logic (DEPLOYED to prod)
acb7ae2 - Updated frontend credit tracking
3ee5583 - Add LinkedIn link, remove Twitter button
90b802d - Optimize Cloud Run resources, remove Redis
```

### Latest Production Tag
- **Tag:** `prod-20260125-020053`
- **Commit:** `c332150`
- **Deployed:** 2026-01-25 04:05:43 UTC

---

## Cost Information

### Monthly Costs (Production)
```
Backend (Cloud Run):   ~$67/month (1GB RAM, 1 vCPU, 1 min instance)
Database (Cloud SQL):  ~$10/month (db-f1-micro)
VPC Connector:         ~$9/month (required for Cloud SQL)
Frontend (Firebase):   Free tier
Storage (GCS):         < $1/month
─────────────────────────────────────────────────────────
Total:                 ~$87/month
```

### Traffic (Pre-launch)
- ~7 requests/day
- ~210 requests/month
- Currently in testing phase

---

## Secrets Management

### Secret Manager Prefixes
- Production: `PROD_*`
- Development: `DEV_*`

### Required Secrets
- Django: `PROD_DJANGO_SECRET_KEY`, `PROD_ENCRYPTION_KEY`
- Stripe: `PROD_STRIPE_SECRET_KEY`, `PROD_STRIPE_PUBLISHABLE_KEY`, `PROD_STRIPE_WEBHOOK_SECRET`
- Zoom: `PROD_ZOOM_CLIENT_ID`, `PROD_ZOOM_CLIENT_SECRET`, `PROD_ZOOM_WEBHOOK_SECRET`
- Email: `PROD_SMTP_API_KEY`, `PROD_SMTP_LOGIN`, `PROD_SMTP_PASSWORD`
- Monitoring: `PROD_SENTRY_DSN`
- Database: `cpd-events-prod-db-password`

---

## Team & Contacts

### Deployer
- **Name:** Rutvik
- **Email:** rutvik@consultjes.ca

### Superuser Account
- **Email:** info@accredit.store
- **Created:** Pre-configured in production

---

## Important Notes

### 1. Terraform State Management
- **Terraform will NOT revert deployments** because:
  - Image uses `:latest` tag (not pinned)
  - Traffic routing uses `latest_revision = true`
  - Only cosmetic metadata may show drift
- See `DEPLOYMENT_STATE_ANALYSIS.md` for full analysis

### 2. LinkedIn Integration
- Footer link added to frontend (2026-01-25)
- Twitter button removed
- Company page content prepared (needs user action to complete)

### 3. CPD Credits Feature
- Logic fixed in commit `c332150`
- Currently deployed in production
- **TODO:** User needs to test in production

---

## Quick Reference Commands

### Check Deployment Status
```bash
accredit cloud backend history --env prod
gcloud run services describe cpd-events-prod --region=us-central1
```

### View Logs
```bash
accredit cloud backend logs --env prod --follow
```

### Check Infrastructure
```bash
cd infra/gcp/environments/prod
terraform plan
terraform show
```

### Test Endpoints
```bash
curl https://api.accredit.store/api/v1/
# Expected: 401 Unauthorized (correct for unauthenticated request)
```

---

## Files to Reference

### Documentation
- `/home/beyonder/projects/cpd_events/DEPLOYMENT_STATE_ANALYSIS.md` - Terraform state analysis
- `/home/beyonder/projects/cpd_events/cli/README.md` - CLI usage guide
- `/home/beyonder/projects/cpd_events/cli/DEPLOYMENT.md` - Deployment guide
- `/home/beyonder/projects/cpd_events/infra/gcp/README.md` - Infrastructure docs

### Configuration
- `/home/beyonder/projects/cpd_events/infra/gcp/environments/prod/main.tf` - Terraform config
- `/home/beyonder/projects/cpd_events/infra/gcp/environments/prod/terraform.tfvars` - Variables
- `/home/beyonder/projects/cpd_events/backend/src/config/settings/production.py` - Django settings

### CLI
- `/home/beyonder/projects/cpd_events/cli/accredit/commands/cloud.py` - Cloud commands

---

## TODOs & Follow-ups

### User Actions Required
1. ✅ Test CPD Credits feature in production
2. ⏳ Complete LinkedIn company page setup
3. ⏳ Upload LinkedIn cover image (specs provided)
4. ⏳ Publish first LinkedIn post

### Future Enhancements
- Consider adding `lifecycle.ignore_changes` to Terraform for metadata
- Set up automated deployment tracking reports
- Consider switching to image digests instead of `:latest` (optional)

---

**Document Purpose:** This file contains project-specific information that should be read at the start of each AI session to maintain context about the Accredit project.
