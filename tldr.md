# Accredit CLI - TLDR

Quick reference for deploying CPD Events to GCP.

## Install CLI

```bash
# Using pipx (recommended)
cd cli
pipx install -e .

# Verify
accredit --help
```

## First-Time Setup

```bash
# 1. Configure CLI
accredit setup init --env dev --project-id YOUR_PROJECT --region us-central1

# 2. Login to GCP
gcloud auth login
gcloud auth application-default login

# 3. Bootstrap GCP project (enables APIs, creates buckets)
accredit cloud bootstrap --project-id YOUR_PROJECT --region us-central1

# 4. Upload secrets BEFORE deploying (required!)
accredit cloud secrets upload --backend --env dev
```

## Deploy Everything

```bash
accredit cloud up --env dev --auto-approve
```

This runs: terraform init → terraform apply → docker build → push image → deploy backend

## Update Backend Only

```bash
accredit cloud backend build --env dev
accredit cloud backend deploy --env dev
```

## Update Frontend Only

```bash
accredit cloud frontend deploy --env dev
```

## Update Infrastructure Only

```bash
accredit cloud infra plan --env dev      # Preview changes
accredit cloud infra apply --env dev     # Apply changes
```

## Secrets Management

```bash
# Upload backend secrets from .env.prod to Secret Manager
accredit cloud secrets upload --backend --env dev

# Upload frontend secrets
accredit cloud secrets upload --frontend --env dev

# Upload both (or custom file)
accredit cloud secrets upload --backend --frontend --env dev
accredit cloud secrets upload --file ./secrets.env --env prod

# Preview what would be uploaded (dry run)
accredit cloud secrets upload --backend --env dev --dry-run

# List secrets for an environment
accredit cloud secrets list --env dev

# Set a single secret
accredit cloud secrets set STRIPE_SECRET_KEY "sk_live_xxx" --env prod

# Get a secret value
accredit cloud secrets get DJANGO_SECRET_KEY --env dev

# Delete a secret
accredit cloud secrets delete OLD_KEY --env dev

# Download secrets back to .env file
accredit cloud secrets download --backend --env dev
```

Secrets are stored with environment prefix: `DEV_DJANGO_SECRET_KEY`, `PROD_STRIPE_SECRET_KEY`, etc.

## Architecture: What Goes Where

### Terraform Manages (auto-configured):
| Variable | Source |
|----------|--------|
| `DB_HOST`, `DB_NAME`, `DB_USER` | Cloud SQL instance |
| `DB_PASSWORD` | Auto-generated, stored in Secret Manager |
| `GCS_BUCKET_NAME` | Created bucket name |
| `GCP_PROJECT_ID`, `GCP_LOCATION` | From tfvars |
| `GCP_QUEUE_NAME` | Cloud Tasks queue |
| `CORS_ALLOWED_ORIGINS` | From tfvars |
| `SITE_URL`, `FRONTEND_URL` | From tfvars (or Cloud Run URL) |

### Secret Manager (upload via CLI):
| Secret | Description |
|--------|-------------|
| `DJANGO_SECRET_KEY` | Django security key |
| `ENCRYPTION_KEY` | Fernet key for encrypting data |
| `STRIPE_SECRET_KEY` | Stripe API secret |
| `STRIPE_PUBLISHABLE_KEY` | Stripe public key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook validation |
| `ZOOM_CLIENT_ID` | Zoom OAuth app ID |
| `ZOOM_CLIENT_SECRET` | Zoom OAuth secret |
| `ZOOM_WEBHOOK_SECRET` | Zoom webhook validation |
| `SMTP_API_KEY` | SMTP provider API key (Brevo or Mailgun) |
| `SMTP_LOGIN` | SMTP username |
| `SMTP_PASSWORD` | SMTP password |

### Files:
- `backend/.env.dev` - Local development secrets
- `backend/.env.prod` - Optional local file for uploading secrets (gitignored)
- `frontend/.env.dev` - Local frontend config
- `frontend/.env.prod` - Optional local build-time vars (gitignored)
- `.secrets` - Optional unified secrets file for CLI upload (gitignored)
- `infra/gcp/environments/<env>/terraform.tfvars` - Production config (not committed)

## Useful Commands

| Command | Description |
|---------|-------------|
| `accredit cloud status --env dev` | Show deployment status |
| `accredit cloud backend logs --env dev -f` | Tail backend logs |
| `accredit cloud backend history --env dev` | View deployment history |
| `accredit cloud secrets list --env dev` | List secrets in Secret Manager |
| `accredit setup show` | Show current config |
| `accredit setup use staging` | Switch environment |

## Environment Files

### File Convention
```
backend/
├── .env.dev              # Local development (gitignored)
├── .env.dev.template     # Template with placeholders (tracked)
├── .env.prod             # Optional local secrets file (gitignored)

frontend/
├── .env.dev              # Local development (gitignored)
├── .env.dev.template     # Template (tracked)
├── .env.prod             # Optional local build-time vars (gitignored)

.secrets                  # Optional unified secrets file (gitignored)
```

### Setup for New Developers
```bash
# Copy templates and fill in your values
cp backend/.env.dev.template backend/.env.dev
cp frontend/.env.dev.template frontend/.env.dev

# Edit with your API keys
nano backend/.env.dev
```

## Local Development

```bash
accredit local setup          # Install deps, run migrations (warns if .env.dev missing)
accredit local up             # Start backend + frontend
accredit local down           # Stop services
```

## Docker Development

```bash
accredit docker up --build -d    # Start all services
accredit docker logs -f backend  # View logs
accredit docker down             # Stop services
```

## Environments

- `dev` - Development
- `staging` - Staging
- `prod` - Production

Switch with: `accredit setup use <env>` or pass `--env <env>` to commands.

## Prerequisites

- Python 3.10+
- Terraform 1.5.0+
- Google Cloud SDK
- Node.js 18+
