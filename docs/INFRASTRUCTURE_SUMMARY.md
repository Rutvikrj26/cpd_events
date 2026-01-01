# Infrastructure Setup Summary

Complete infrastructure-as-code setup for the CPD Events platform with proper separation of concerns.

## 📁 Final Project Structure

```
cpd_events/
├── cli/                           # Deployment orchestration
│   ├── accredit/                 # CLI tool
│   │   └── commands/
│   │       ├── docker.py         # Docker commands
│   │       └── local.py          # Local dev commands
│   ├── docker-compose.yml        # Development
│   ├── docker-compose.prod.yml   # Production
│   └── DEPLOYMENT.md
│
├── infra/                         # Infrastructure as Code ⭐
│   ├── gcp/                      # Google Cloud Platform
│   │   ├── modules/              # Reusable Terraform modules
│   │   ├── environments/
│   │   │   ├── dev/
│   │   │   │   ├── main.tf          # Core infrastructure
│   │   │   │   ├── frontend.tf      # Frontend + Cloud CDN
│   │   │   │   ├── variables.tf
│   │   │   │   └── terraform.tfvars.example
│   │   │   ├── staging/
│   │   │   └── prod/
│   │   └── scripts/
│   │       └── deploy-frontend.sh   # Frontend deployment
│   ├── aws/                      # Future: AWS configs
│   ├── azure/                    # Future: Azure configs
│   └── README.md
│
├── backend/                       # Django application
├── frontend/                      # React application
└── README.md
```

## 🎯 Separation of Concerns

| Directory | Purpose | Contents |
|-----------|---------|----------|
| **cli/** | Deployment orchestration | Docker Compose, CLI tool |
| **infra/** | Cloud infrastructure | Terraform, IaC configs |
| **backend/** | Application code | Django, business logic |
| **frontend/** | Application code | React, UI components |

---

## 🏗️ GCP Infrastructure

### Resources Managed by Terraform

#### Backend Infrastructure
- ✅ **Cloud Run** - Serverless container deployment
  - Auto-scaling (0-10 instances)
  - CPU: 1 vCPU, Memory: 512Mi
  - Timeout: 300s
  - Cloud SQL connection via Unix socket

- ✅ **Cloud SQL** - Managed PostgreSQL 15
  - Tier: db-f1-micro (dev)
  - Daily backups
  - Private IP in VPC
  - SSL required

- ✅ **Cloud Storage** - 3 buckets
  - Media files (public read)
  - Certificates (private)
  - Frontend static files (public + CDN)

- ✅ **Cloud Tasks** - Async job queue
  - Max concurrent: 100
  - Retry: 5 attempts with exponential backoff

#### Frontend Infrastructure (NEW!)
- ✅ **Cloud CDN** - Content delivery network
  - Cache mode: CACHE_ALL_STATIC
  - TTL: 3600s (1 hour)
  - Serve while stale: 24 hours
  - Custom response headers (security)

- ✅ **Load Balancer** - Global HTTPS load balancer
  - Managed SSL certificate
  - HTTP → HTTPS redirect
  - Reserved external IP
  - Backend: Cloud Storage bucket

#### Networking
- ✅ **VPC** - Private network
- ✅ **Subnet** - Private subnet (10.0.0.0/24)
- ✅ **VPC Connector** - Serverless VPC access
- ✅ **Cloud SQL Private IP** - Database in VPC
- ✅ **Service Networking** - VPC peering

#### Security
- ✅ **IAM** - Service accounts & roles
- ✅ **Secret Manager** - Sensitive data storage
- ✅ **SSL Certificates** - Managed by Google
- ✅ **Firewall Rules** - Network security

---

## 🚀 Deployment Workflow

### Using the Accredit CLI (Recommended)

The `accredit` CLI provides streamlined deployment commands:

#### 1. Infrastructure Setup

```bash
# Copy and configure terraform.tfvars
cd infra/gcp/environments/dev
cp terraform.tfvars.example terraform.tfvars
vim terraform.tfvars

# Initialize and deploy infrastructure
accredit cloud infra init --env dev
accredit cloud infra plan --env dev
accredit cloud infra apply --env dev
```

#### 2. Backend Deployment

```bash
# Build and push Docker image to GCR
accredit cloud backend build --env dev

# Deploy to Cloud Run
accredit cloud backend deploy --env dev
```

#### 3. Frontend Deployment

```bash
# Build and deploy to Cloud Storage + CDN
accredit cloud frontend deploy --env dev
```

#### 4. DNS Configuration

```bash
# Get the frontend IP
accredit cloud infra output --env dev frontend_ip_address

# Configure DNS A records at your domain registrar:
# yourdomain.com     -> FRONTEND_IP
# www.yourdomain.com -> FRONTEND_IP

# SSL certificate activates automatically once DNS propagates
```

#### 5. Verify Deployment

```bash
# Check deployment status
accredit cloud status --env dev

# View backend logs
accredit cloud backend logs --env dev --follow
```

### Manual Deployment (Alternative)

If you prefer not to use the CLI:

```bash
# Infrastructure
cd infra/gcp/environments/dev
terraform init && terraform apply

# Backend
gcloud builds submit --tag gcr.io/PROJECT_ID/cpd-backend:latest
gcloud run deploy cpd-events-dev --image gcr.io/PROJECT_ID/cpd-backend:latest

# Frontend
cd infra/gcp/scripts
./deploy-frontend.sh dev
```

---

## 💰 Cost Breakdown

### Development Environment (~$20-30/month)
- Cloud Run: $5-10 (minimal traffic)
- Cloud SQL: $10-15 (db-f1-micro)
- Cloud Storage: $1-2 (< 10GB)
- Cloud CDN: $1-2 (minimal traffic)
- Cloud Tasks: Free tier
- Load Balancer: Free tier (1 rule)

### Production Environment (~$200-350/month)
- Cloud Run: $50-100 (high traffic)
- Cloud SQL: $100-200 (db-n1-standard-1 + HA)
- Cloud Storage: $5-10
- Cloud CDN: $10-20 (global traffic)
- Cloud Tasks: $1-5
- Load Balancer: $18

---

## 🔐 Secrets Management

Secrets are stored in GCP Secret Manager:

```bash
# Create secrets
echo -n "secret-value" | gcloud secrets create SECRET_NAME --data-file=-

# Grant access
gcloud secrets add-iam-policy-binding SECRET_NAME \
  --member="serviceAccount:SA@PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Reference in Terraform
env {
  name = "DB_PASSWORD"
  value_from {
    secret_key_ref {
      name = google_secret_manager_secret.db_password.secret_id
      key  = "latest"
    }
  }
}
```

---

## 📊 Monitoring & Logging

### Cloud Run Logs
```bash
gcloud run services logs read cpd-events-dev --limit=100
```

### Cloud SQL Logs
```bash
gcloud sql operations list --instance=cpd-events-dev-db
```

### CDN Cache Metrics
```bash
# View in Cloud Console
https://console.cloud.google.com/net-services/cdn/list
```

---

## 🔄 CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy Infrastructure

on:
  push:
    branches: [main]
    paths:
      - 'infra/gcp/**'

jobs:
  terraform:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v2

      - name: Terraform Apply
        working-directory: infra/gcp/environments/dev
        run: |
          terraform init
          terraform apply -auto-approve

  frontend:
    needs: terraform
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build Frontend
        working-directory: frontend
        run: |
          npm install
          npm run build

      - name: Deploy to GCS
        run: |
          BUCKET=$(cd infra/gcp/environments/dev && terraform output -raw frontend_bucket_name)
          gsutil -m rsync -r frontend/dist/ "gs://$BUCKET/"
```

---

## 🎓 Best Practices Implemented

✅ **Infrastructure as Code** - All resources defined in Terraform
✅ **Separation of Concerns** - Clear directory structure
✅ **Environment Isolation** - Separate configs for dev/staging/prod
✅ **Secrets Management** - No hardcoded credentials
✅ **Auto-scaling** - Scales to zero in dev, auto-scales in prod
✅ **CDN Caching** - Fast global content delivery
✅ **SSL/TLS** - Managed certificates with auto-renewal
✅ **Private Networking** - Database in VPC
✅ **Cost Optimization** - Minimal resources in dev
✅ **Monitoring** - Cloud Logging & Monitoring enabled

---

## 📚 Documentation

- [infra/README.md](infra/README.md) - Infrastructure overview
- [infra/gcp/README.md](infra/gcp/README.md) - GCP-specific guide
- [cli/DEPLOYMENT.md](cli/DEPLOYMENT.md) - Deployment orchestration
- [cli/DOCKER.md](cli/DOCKER.md) - Docker setup

---

## ✅ What's Ready

- [x] Infrastructure directory structure
- [x] GCP Terraform configuration (dev environment)
- [x] Backend infrastructure (Cloud Run, Cloud SQL, Cloud Tasks)
- [x] Frontend infrastructure (Cloud CDN, Cloud Storage, Load Balancer)
- [x] Networking (VPC, subnets, private IP)
- [x] Security (IAM, Secret Manager, SSL)
- [x] Frontend deployment script
- [x] Documentation

## 📝 Next Steps

1. **Copy terraform.tfvars.example** to terraform.tfvars
2. **Configure your GCP project ID** and other variables
3. **Run terraform apply** to create infrastructure
4. **Deploy backend** to Cloud Run
5. **Deploy frontend** to Cloud Storage + CDN
6. **Configure DNS** A records to point to load balancer IP
7. **Repeat for staging/prod** environments

---

**Status**: ✅ Complete infrastructure setup with Cloud CDN for frontend!
