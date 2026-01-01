# GCP Infrastructure - CPD Events Platform

Terraform configuration for deploying the CPD Events platform on Google Cloud Platform.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Cloud Load Balancer                      │
│                         (HTTPS/SSL)                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼────────┐          ┌─────────▼────────┐
│   Cloud Run    │          │   Cloud Storage  │
│   (Backend)    │          │   (Static/Media) │
└───────┬────────┘          └──────────────────┘
        │
        ├─────────┐
        │         │
┌───────▼────┐  ┌─▼────────────┐
│  Cloud SQL │  │ Cloud Tasks  │
│ (Postgres) │  │ (Job Queue)  │
└────────────┘  └──────────────┘
```

## 📁 Directory Structure

```
gcp/
├── modules/              # Reusable Terraform modules
│   ├── cloud-run/       # Cloud Run service
│   ├── cloud-sql/       # PostgreSQL database
│   ├── storage/         # Cloud Storage buckets
│   ├── networking/      # VPC, subnets, firewall
│   ├── iam/            # Service accounts, roles
│   └── monitoring/      # Logging, alerting
│
├── environments/        # Environment-specific configs
│   ├── dev/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── terraform.tfvars
│   │   └── backend.tf
│   ├── staging/
│   └── prod/
│
└── README.md           # This file
```

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Install Terraform
brew install terraform

# Install Google Cloud SDK
brew install google-cloud-sdk

# Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### 2. Initialize Terraform

```bash
cd infra/gcp/environments/dev
terraform init
```

### 3. Plan Infrastructure

```bash
terraform plan
```

### 4. Apply Infrastructure

```bash
terraform apply
```

### 5. Destroy Infrastructure (when needed)

```bash
terraform destroy
```

## 🔧 Configuration

### Environment Variables

Create `terraform.tfvars` in each environment:

```hcl
# environments/dev/terraform.tfvars
project_id = "cpd-events-dev"
region     = "us-central1"
environment = "dev"

# App config
app_name = "cpd-events"
domain   = "dev.cpdevents.com"

# Database
db_tier = "db-f1-micro"
db_name = "cpd_events"

# Cloud Run
cloud_run_cpu    = "1"
cloud_run_memory = "512Mi"
min_instances    = 0
max_instances    = 10

# Secrets (reference Secret Manager)
django_secret_key_secret = "projects/PROJECT_ID/secrets/django-secret-key"
stripe_secret_key_secret = "projects/PROJECT_ID/secrets/stripe-secret-key"
```

### Backend Configuration

Store Terraform state in GCS:

```hcl
# environments/dev/backend.tf
terraform {
  backend "gcs" {
    bucket = "cpd-events-terraform-state"
    prefix = "dev/state"
  }
}
```

## 📦 Resources Created

### Core Services

- **Cloud Run**: Serverless container deployment
  - Auto-scaling (0-10 instances for dev)
  - CPU: 1 vCPU, Memory: 512Mi
  - Timeout: 300s

- **Cloud SQL**: Managed PostgreSQL
  - Version: PostgreSQL 15
  - Tier: db-f1-micro (dev)
  - Backups: Daily
  - High availability: Disabled (dev)

- **Cloud Storage**: Object storage
  - Media bucket (public read)
  - Certificate bucket (private)
  - Static files bucket (public read)

- **Cloud Tasks**: Async job queue
  - Queue: default
  - Max concurrent: 100
  - Retry config: exponential backoff

### Networking

- VPC with private subnet
- Cloud SQL Private IP
- Cloud NAT for outbound traffic
- Firewall rules

### Security

- Service accounts with least privilege
- Secret Manager for sensitive data
- IAM policies
- SSL/TLS termination at load balancer

### Monitoring

- Cloud Logging
- Cloud Monitoring
- Uptime checks
- Error reporting

## 🔐 Secrets Management

Secrets are stored in GCP Secret Manager and referenced in Terraform:

```bash
# Create secrets
echo -n "your-django-secret-key" | gcloud secrets create django-secret-key --data-file=-
echo -n "sk_live_xxx" | gcloud secrets create stripe-secret-key --data-file=-
echo -n "zoom-client-secret" | gcloud secrets create zoom-client-secret --data-file=-

# Grant Cloud Run access
gcloud secrets add-iam-policy-binding django-secret-key \
  --member="serviceAccount:cloud-run-sa@PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## 💰 Cost Estimation

### Development Environment
- Cloud Run: ~$5-10/month (low traffic)
- Cloud SQL: ~$10-15/month (db-f1-micro)
- Cloud Storage: ~$1-2/month (<10GB)
- Cloud Tasks: Free tier
- **Total: ~$16-27/month**

### Production Environment
- Cloud Run: ~$50-100/month (high traffic)
- Cloud SQL: ~$100-200/month (db-n1-standard-1 + HA)
- Cloud Storage: ~$5-10/month
- Cloud Tasks: ~$1-5/month
- Load Balancer: ~$18/month
- **Total: ~$174-333/month**

## 🔄 CI/CD Integration

### GitHub Actions

```yaml
name: Deploy to GCP

on:
  push:
    branches: [main]

jobs:
  terraform:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v2

      - name: Terraform Init
        run: |
          cd infra/gcp/environments/dev
          terraform init

      - name: Terraform Plan
        run: terraform plan

      - name: Terraform Apply
        if: github.ref == 'refs/heads/main'
        run: terraform apply -auto-approve
```

## 🐛 Troubleshooting

### Cloud SQL Connection Issues

```bash
# Check Cloud SQL status
gcloud sql instances describe INSTANCE_NAME

# Test connection via Cloud SQL Proxy
cloud_sql_proxy -instances=PROJECT:REGION:INSTANCE=tcp:5432
```

### Cloud Run Deployment Fails

```bash
# Check Cloud Run logs
gcloud run services logs read cpd-backend --region=us-central1

# Check Cloud Run service
gcloud run services describe cpd-backend --region=us-central1
```

### Terraform State Lock

```bash
# Force unlock (use with caution)
terraform force-unlock LOCK_ID
```

## 📊 Monitoring

### View Logs

```bash
# Cloud Run logs
gcloud run services logs read cpd-backend --region=us-central1 --limit=50

# Cloud SQL logs
gcloud sql operations list --instance=cpd-db

# Cloud Tasks logs
gcloud tasks queues describe default --location=us-central1
```

### Metrics Dashboard

Access Cloud Console:
- https://console.cloud.google.com/run
- https://console.cloud.google.com/sql
- https://console.cloud.google.com/cloudtasks

## 🔄 Updates

### Deploy New Version

```bash
# Build and push image
gcloud builds submit --tag gcr.io/PROJECT_ID/cpd-backend:latest

# Deploy to Cloud Run (automatic via Terraform)
terraform apply
```

### Update Database

```bash
# Run migrations via Cloud Run
gcloud run jobs execute migrate-db \
  --region us-central1 \
  --wait
```

## 📚 Additional Resources

- [GCP Cloud Run Docs](https://cloud.google.com/run/docs)
- [GCP Cloud SQL Docs](https://cloud.google.com/sql/docs)
- [Terraform GCP Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [GCP Best Practices](https://cloud.google.com/architecture/framework)

---

**Status**: Ready for Terraform module development!
