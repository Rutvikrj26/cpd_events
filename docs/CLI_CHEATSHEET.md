# Accredit CLI - Command Cheat Sheet

Quick reference for all `accredit` commands.

## Installation

```bash
# Install with pipx (recommended)
cd cli
pipx install -e .

# Verify installation
accredit --version
accredit --help
```

---

## 🏠 Local Development Commands

Manage local development without Docker.

```bash
accredit local setup          # Install dependencies & run migrations
accredit local up             # Start backend & frontend servers
accredit local logs           # View application logs
accredit local shell          # Open Django shell
```

---

## 🐳 Docker Commands

Orchestrate Docker Compose services.

### Basic Operations

```bash
accredit docker up                    # Start services (foreground)
accredit docker up -d                 # Start in background
accredit docker up --build            # Rebuild and start
accredit docker up --build -d         # Rebuild and start in background

accredit docker down                  # Stop services
accredit docker down -v               # Stop and remove volumes (deletes data!)

accredit docker restart               # Restart all services
accredit docker ps                    # List running services
```

### Logs and Debugging

```bash
accredit docker logs                  # View all logs
accredit docker logs -f               # Follow logs (live tail)
accredit docker logs backend          # Logs for specific service
accredit docker logs -f backend       # Follow specific service logs
```

### Initialization and Management

```bash
accredit docker init                  # Initialize environment (GCS bucket, migrations)
accredit docker exec SERVICE CMD...   # Execute command in container

# Examples:
accredit docker exec backend python src/manage.py createsuperuser
accredit docker exec backend poetry run python src/manage.py shell
accredit docker exec backend poetry run python src/manage.py migrate
```

### Production Docker

```bash
accredit docker prod-up --build -d    # Start production services
accredit docker prod-down             # Stop production services
```

---

## ☁️ Cloud Deployment Commands (GCP)

Deploy and manage infrastructure on Google Cloud Platform.

### Infrastructure Management (Terraform)

```bash
# Initialize Terraform
accredit cloud infra init --env dev

# Preview changes
accredit cloud infra plan --env dev
accredit cloud infra plan --env dev --out plan.tfplan

# Apply changes
accredit cloud infra apply --env dev
accredit cloud infra apply --env dev --auto-approve

# View outputs
accredit cloud infra output --env dev
accredit cloud infra output --env dev backend_url
accredit cloud infra output --env dev frontend_ip_address

# Validate configuration
accredit cloud infra validate --env dev

# Destroy infrastructure (DANGEROUS!)
accredit cloud infra destroy --env dev
accredit cloud infra destroy --env dev --auto-approve
```

### Backend Deployment

```bash
# Build and push to Google Container Registry
accredit cloud backend build --env dev
accredit cloud backend build --env dev --tag v1.0.0

# Deploy to Cloud Run
accredit cloud backend deploy --env dev
accredit cloud backend deploy --env dev --tag v1.0.0

# View logs
accredit cloud backend logs --env dev
accredit cloud backend logs --env dev --follow
accredit cloud backend logs --env dev --limit 500
```

### Frontend Deployment

```bash
# Build production bundle
accredit cloud frontend build --env dev

# Deploy to Cloud Storage + CDN
accredit cloud frontend deploy --env dev

# Invalidate CDN cache
accredit cloud frontend invalidate --env dev
```

### Utilities

```bash
# Show deployment status
accredit cloud status --env dev

# List available environments
accredit cloud list-envs

# Connect to Cloud Run service
accredit cloud ssh --env dev
```

---

## 🎯 Common Workflows

### First Time Setup

```bash
# 1. Install CLI
cd cli && pipx install -e .

# 2. Start Docker environment
accredit docker up --build -d

# 3. Initialize environment
accredit docker init

# 4. Create superuser
accredit docker exec backend poetry run python src/manage.py createsuperuser

# 5. Access application
open http://localhost:8000
```

### Daily Development (Docker)

```bash
# Start services
accredit docker up -d

# View logs
accredit docker logs -f backend

# Django shell
accredit docker exec backend poetry run python src/manage.py shell

# Stop when done
accredit docker down
```

### Complete Cloud Deployment

```bash
# 1. Configure infrastructure
cd infra/gcp/environments/dev
cp terraform.tfvars.example terraform.tfvars
vim terraform.tfvars

# 2. Deploy infrastructure
accredit cloud infra init --env dev
accredit cloud infra apply --env dev

# 3. Deploy backend
accredit cloud backend build --env dev
accredit cloud backend deploy --env dev

# 4. Deploy frontend
accredit cloud frontend deploy --env dev

# 5. Configure DNS
accredit cloud infra output --env dev frontend_ip_address
# Point yourdomain.com -> IP_ADDRESS

# 6. Verify
accredit cloud status --env dev
```

### Update Backend in Cloud

```bash
# After code changes
accredit cloud backend build --env dev
accredit cloud backend deploy --env dev

# Check logs
accredit cloud backend logs --env dev --follow
```

### Update Frontend in Cloud

```bash
# After code changes
accredit cloud frontend deploy --env dev

# Verify cache cleared
accredit cloud frontend invalidate --env dev
```

### Multi-Environment Deployment

```bash
# Development
accredit cloud backend deploy --env dev
accredit cloud frontend deploy --env dev

# Staging
accredit cloud backend deploy --env staging
accredit cloud frontend deploy --env staging

# Production
accredit cloud backend deploy --env prod
accredit cloud frontend deploy --env prod
```

---

## 🔍 Environment Flags

Most cloud commands accept the `--env` flag:

```bash
--env dev        # Development (default)
--env staging    # Staging
--env prod       # Production
```

Examples:
```bash
accredit cloud status --env dev
accredit cloud status --env staging
accredit cloud status --env prod
```

---

## 🐛 Troubleshooting Commands

### Docker Issues

```bash
# Check service status
accredit docker ps

# View all logs
accredit docker logs

# Restart specific service
docker restart cpd_postgres

# Complete reset (deletes all data!)
accredit docker down -v
accredit docker up --build -d
accredit docker init
```

### Cloud Issues

```bash
# Check deployment status
accredit cloud status --env dev

# View detailed logs
accredit cloud backend logs --env dev --limit 1000

# Verify Terraform state
accredit cloud infra validate --env dev

# Check outputs
accredit cloud infra output --env dev
```

---

## 📊 Monitoring Commands

### Docker Environment

```bash
# Service status
accredit docker ps

# Live logs
accredit docker logs -f

# Resource usage
docker stats
```

### Cloud Environment

```bash
# Deployment overview
accredit cloud status --env dev

# Backend logs (live)
accredit cloud backend logs --env dev --follow

# Infrastructure outputs
accredit cloud infra output --env dev

# GCP Console checks
gcloud run services list
gcloud sql instances list
gcloud compute backend-buckets list
```

---

## 🚀 CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy to Dev
on:
  push:
    branches: [dev]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install CLI
        run: |
          cd cli
          pip install -e .

      - name: Deploy Backend
        run: |
          accredit cloud backend build --env dev
          accredit cloud backend deploy --env dev

      - name: Deploy Frontend
        run: |
          accredit cloud frontend deploy --env dev
```

---

## 📚 Additional Resources

- [CLI README](cli/README.md) - Detailed usage guide
- [Deployment Guide](cli/DEPLOYMENT.md) - Complete deployment workflows
- [Infrastructure Summary](INFRASTRUCTURE_SUMMARY.md) - Infrastructure overview
- [Docker Guide](cli/DOCKER.md) - Docker setup details

---

**Quick Help:**
```bash
accredit --help                    # Main help
accredit docker --help             # Docker commands
accredit cloud --help              # Cloud commands
accredit cloud infra --help        # Infrastructure commands
accredit cloud backend --help      # Backend commands
accredit cloud frontend --help     # Frontend commands
```
