# CPD Events - Deployment Guide

All deployment orchestration is centralized in the `cli/` directory for separation of concerns.

## 📁 Directory Structure

```
cpd_events/
├── cli/                           # Deployment orchestration hub
│   ├── docker-compose.yml         # Development environment
│   ├── docker-compose.prod.yml    # Production environment
│   ├── DOCKER.md                  # Docker documentation
│   ├── DEPLOYMENT.md              # This file
│   └── accredit/                  # CLI tool
│       └── commands/
│           ├── cloud.py           # GCP cloud deployment commands
│           ├── docker.py          # Docker orchestration commands
│           └── local.py           # Local dev commands
│
├── infra/                         # Infrastructure as Code
│   └── gcp/                       # Google Cloud Platform
│       ├── environments/          # Terraform configs (dev/staging/prod)
│       └── scripts/               # Deployment scripts
│
├── backend/                       # Django backend
├── frontend/                      # React frontend
└── README.md
```

## 🚀 Quick Start

### Install the CLI

```bash
cd cli
pipx install -e .
```

### Start Development Environment

```bash
# From anywhere in the project
accredit docker up --build --detach

# Initialize environment (GCS bucket, migrations)
accredit docker init

# View logs
accredit docker logs -f
```

---

## 🐳 Docker Commands

The `accredit docker` command provides full Docker orchestration:

### Development

```bash
# Start all services
accredit docker up                 # Foreground
accredit docker up -d              # Background (detached)
accredit docker up --build -d      # Rebuild and start

# Initialize environment (after first start)
accredit docker init               # Sets up GCS bucket, runs migrations

# View logs
accredit docker logs               # All services
accredit docker logs -f            # Follow logs
accredit docker logs backend       # Specific service

# List running services
accredit docker ps

# Execute commands in containers
accredit docker exec backend python src/manage.py createsuperuser
accredit docker exec backend poetry run python src/manage.py shell

# Restart services
accredit docker restart

# Stop services
accredit docker down               # Stop and remove
accredit docker down -v            # Stop and remove volumes (deletes data!)
```

### Production

```bash
# Start production services
accredit docker prod-up --build -d

# Stop production services
accredit docker prod-down
```

---

## 🏗️ Development Environment

**Services** (defined in `cli/docker-compose.yml`):

1. **PostgreSQL** (port 5432)
   - Database: `cpd_events`
   - User: `cpd_user`
   - Password: `cpd_password`

2. **Cloud Tasks Emulator** (port 8123)
   - Emulates GCP Cloud Tasks
   - Tasks queue asynchronously

3. **Cloud Storage Emulator** (port 4443)
   - Emulates Google Cloud Storage
   - Bucket: `cpd-events-local`

4. **Django Backend** (port 8000)
   - Development server
   - Hot reload enabled
   - API: http://localhost:8000
   - Admin: http://localhost:8000/admin
   - Docs: http://localhost:8000/api/docs/

### Environment Variables

All environment variables are pre-configured in `docker-compose.yml` for development:

- `DEBUG=True`
- `CLOUD_TASKS_EMULATOR_HOST=cloud-tasks-emulator:8123`
- `GCS_EMULATOR_HOST=http://gcs-emulator:4443`
- `GCS_BUCKET_NAME=cpd-events-local`

---

## 🚀 Production Environment

**Services** (defined in `cli/docker-compose.prod.yml`):

1. **PostgreSQL** (internal only)
2. **Django Backend** (Gunicorn)
   - 4 workers
   - 120s timeout
   - Health check enabled

**Note**: Nginx is commented out - use cloud load balancers (GCP LB, AWS ALB, etc.)

### Required Environment Variables

Create a `.env.production` file:

```bash
# Django
DJANGO_SECRET_KEY=your-secret-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DEBUG=False

# Database
DB_NAME=cpd_events
DB_USER=cpd_user
DB_PASSWORD=your-secure-password

# GCP (real services)
GCP_PROJECT_ID=your-project
GCP_LOCATION=us-central1
GCP_QUEUE_NAME=default
GCS_BUCKET_NAME=your-bucket-name
GCP_SA_EMAIL=service-account@project.iam.gserviceaccount.com

# Stripe
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_ORGANIZER=price_xxx
STRIPE_PRICE_ORGANIZATION=price_xxx

# Zoom
ZOOM_CLIENT_ID=your-zoom-client-id
ZOOM_CLIENT_SECRET=your-zoom-client-secret
ZOOM_WEBHOOK_SECRET=your-webhook-secret

# Email (SMTP provider, e.g. Brevo or Mailgun)
SMTP_LOGIN=your-smtp-login
SMTP_PASSWORD=your-smtp-password
SMTP_API_KEY=your-provider-api-key
SMTP_DOMAIN=your-domain.example
SMTP_SERVER=smtp-relay.brevo.com
SMTP_PORT=587

# Encryption
ENCRYPTION_KEY=your-encryption-key
```

---

## 🔄 Typical Workflows

### First Time Setup

```bash
# 1. Install CLI
cd cli
pipx install -e .

# 2. Start Docker services
accredit docker up --build -d

# 3. Initialize environment
accredit docker init

# 4. Create superuser
accredit docker exec backend poetry run python src/manage.py createsuperuser

# 5. Access application
open http://localhost:8000
```

### Daily Development

```bash
# Start services (if not running)
accredit docker up -d

# View logs
accredit docker logs -f backend

# Run migrations after model changes
accredit docker exec backend poetry run python src/manage.py makemigrations
accredit docker exec backend poetry run python src/manage.py migrate

# Django shell
accredit docker exec backend poetry run python src/manage.py shell

# Stop when done
accredit docker down
```

### Complete Reset

```bash
# Stop and remove all data
accredit docker down -v

# Rebuild and restart
accredit docker up --build -d

# Re-initialize
accredit docker init
```

---

## ☁️ Cloud Deployment (GCP)

The CLI provides complete cloud deployment management through the `accredit cloud` command group.

### Prerequisites

1. **Install Google Cloud SDK:**
   ```bash
   brew install google-cloud-sdk  # macOS
   # or follow: https://cloud.google.com/sdk/docs/install
   ```

2. **Authenticate:**
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```

3. **Enable required APIs:**
   ```bash
   gcloud services enable \
     run.googleapis.com \
     sql-component.googleapis.com \
     sqladmin.googleapis.com \
     cloudtasks.googleapis.com \
     storage-api.googleapis.com \
     compute.googleapis.com \
     vpcaccess.googleapis.com \
     secretmanager.googleapis.com
   ```

### Complete Deployment Workflow

#### 1. Configure Environment
```bash
# Copy Terraform config
cd infra/gcp/environments/dev
cp terraform.tfvars.example terraform.tfvars

# Edit with your GCP details
vim terraform.tfvars
# Update: project_id, region, frontend_domains, etc.
```

#### 2. Deploy Infrastructure (Terraform)
```bash
# Initialize Terraform
accredit cloud infra init --env dev

# Preview changes
accredit cloud infra plan --env dev

# Apply infrastructure
accredit cloud infra apply --env dev
```

This creates:
- Cloud Run service (backend)
- Cloud SQL (PostgreSQL)
- Cloud Storage (media, certificates, frontend)
- Cloud Tasks queue
- Cloud CDN + Load Balancer (frontend)
- VPC + networking
- IAM service accounts
- Secret Manager secrets

#### 3. Deploy Backend
```bash
# Build and push Docker image to Google Container Registry
accredit cloud backend build --env dev

# Deploy to Cloud Run
accredit cloud backend deploy --env dev
```

#### 4. Deploy Frontend
```bash
# Build and deploy to Cloud Storage + CDN
accredit cloud frontend deploy --env dev
```

This automatically:
- Installs dependencies
- Builds production bundle
- Uploads to Cloud Storage
- Sets cache headers
- Invalidates CDN cache

#### 5. Configure DNS
```bash
# Get load balancer IP
accredit cloud infra output --env dev frontend_ip_address

# Configure DNS A records at your domain registrar:
# yourdomain.com        -> LOAD_BALANCER_IP
# www.yourdomain.com    -> LOAD_BALANCER_IP
```

The SSL certificate will automatically provision once DNS propagates (5-30 minutes).

#### 6. Verify Deployment
```bash
# Check overall status
accredit cloud status --env dev

# View backend logs
accredit cloud backend logs --env dev --follow

# Test endpoints
curl https://api.yourdomain.com/api/health/
curl https://yourdomain.com
```

### Quick Update Workflows

#### Update Backend
```bash
# After code changes
accredit cloud backend build --env dev
accredit cloud backend deploy --env dev
```

#### Update Frontend
```bash
# After code changes
accredit cloud frontend deploy --env dev
```

#### Update Infrastructure
```bash
# After terraform changes
accredit cloud infra plan --env dev
accredit cloud infra apply --env dev
```

#### Clear CDN Cache
```bash
accredit cloud frontend invalidate --env dev
```

### Environment Management

Deploy to multiple environments:

```bash
# Development
accredit cloud infra apply --env dev
accredit cloud backend deploy --env dev
accredit cloud frontend deploy --env dev

# Staging
accredit cloud infra apply --env staging
accredit cloud backend deploy --env staging
accredit cloud frontend deploy --env staging

# Production
accredit cloud infra apply --env prod
accredit cloud backend deploy --env prod
accredit cloud frontend deploy --env prod
```

List available environments:
```bash
accredit cloud list-envs
```

### Infrastructure Management

```bash
# View Terraform outputs
accredit cloud infra output --env dev
accredit cloud infra output --env dev backend_url

# Validate Terraform config
accredit cloud infra validate --env dev

# Destroy infrastructure (DANGEROUS!)
accredit cloud infra destroy --env dev
```

### Monitoring and Logs

```bash
# Backend logs (Cloud Run)
accredit cloud backend logs --env dev            # Last 100 entries
accredit cloud backend logs --env dev --follow   # Live tail
accredit cloud backend logs --env dev --limit 500

# View deployment status
accredit cloud status --env dev

# Connect to Cloud Run service
accredit cloud ssh --env dev
```

### Cost Management

Estimated costs per environment:

**Development (~$20-30/month)**
- Cloud Run: $5-10 (scales to zero)
- Cloud SQL: $10-15 (db-f1-micro)
- Cloud Storage: $1-2
- Cloud CDN: $1-2
- Cloud Tasks: Free tier

**Production (~$200-350/month)**
- Cloud Run: $50-100 (high traffic)
- Cloud SQL: $100-200 (HA enabled)
- Cloud Storage: $5-10
- Cloud CDN: $10-20
- Cloud Tasks: $1-5
- Load Balancer: $18

**Cost optimization tips:**
- Development scales to zero when idle
- Use smaller Cloud SQL tier for dev/staging
- Disable high availability for non-prod environments
- Set up budget alerts in GCP Console

### Troubleshooting Cloud Deployments

#### Terraform Issues
```bash
# Check if terraform.tfvars exists
ls infra/gcp/environments/dev/terraform.tfvars

# Re-initialize if needed
accredit cloud infra init --env dev

# View detailed plan
accredit cloud infra plan --env dev
```

#### Backend Deployment Issues
```bash
# Check Cloud Run logs
accredit cloud backend logs --env dev --limit 500

# Verify image was pushed
gcloud container images list --repository=gcr.io/PROJECT_ID

# Check service status
gcloud run services describe cpd-events-dev --region=us-central1
```

#### Frontend Issues
```bash
# Check bucket contents
gsutil ls gs://BUCKET_NAME/

# Verify CDN configuration
gcloud compute backend-buckets describe cpd-events-dev-frontend-backend

# Manually invalidate cache
accredit cloud frontend invalidate --env dev
```

#### DNS/SSL Issues
```bash
# Check SSL certificate status
gcloud compute ssl-certificates describe cpd-events-dev-frontend-cert

# Check DNS propagation
dig yourdomain.com
nslookup yourdomain.com

# Wait for SSL provisioning (can take 15-30 minutes after DNS is configured)
```

---

## 🐛 Troubleshooting

### Services won't start

```bash
# Check logs
accredit docker logs

# Check if ports are in use
lsof -i :5432  # PostgreSQL
lsof -i :8000  # Backend

# Rebuild from scratch
accredit docker down -v
accredit docker up --build
```

### Database connection errors

```bash
# Ensure database is healthy
accredit docker ps

# Restart database
docker restart cpd_postgres

# Check logs
accredit docker logs db
```

### GCS bucket not found

```bash
# Re-initialize
accredit docker exec backend python scripts/init_gcs_emulator.py
```

### Permission errors

```bash
# On Linux, fix volume permissions
sudo chown -R $USER:$USER ../backend/staticfiles ../backend/mediafiles
```

---

## 📊 Monitoring

### View Service Status

```bash
accredit docker ps
```

### View Logs

```bash
# All services
accredit docker logs -f

# Specific service
accredit docker logs -f backend
accredit docker logs -f db

# Last 100 lines
accredit docker logs --tail=100 backend
```

### Resource Usage

```bash
docker stats
```

---

## 🔐 Security Best Practices

1. **Never commit `.env` files** - Use `.env.example` as template
2. **Use secrets management** in production (GCP Secret Manager, AWS Secrets Manager)
3. **Run as non-root user** (already configured in production Dockerfile)
4. **Keep images updated** - Regularly rebuild with latest base images
5. **Scan for vulnerabilities:**
   ```bash
   docker scan cpd_backend_prod
   ```

---

## 📚 Additional Resources

- [DOCKER.md](DOCKER.md) - Detailed Docker setup guide
- [README.md](README.md) - CLI usage guide
- [INSTALL.md](INSTALL.md) - CLI installation guide

---

**Status**: ✅ All deployment orchestration centralized in `cli/` directory!
