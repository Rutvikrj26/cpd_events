# Infrastructure as Code

This directory contains all infrastructure-as-code configurations for deploying the CPD Events platform across different cloud providers.

## 📁 Directory Structure

```
infra/
├── gcp/                    # Google Cloud Platform
│   ├── modules/           # Reusable Terraform modules
│   ├── environments/      # Environment-specific configs
│   │   ├── dev/          # Development
│   │   ├── staging/      # Staging
│   │   └── prod/         # Production
│   └── README.md
│
├── aws/                    # Amazon Web Services (future)
├── azure/                  # Microsoft Azure (future)
└── docs/                   # Architecture docs
```

## 🎯 Purpose

**Separation of Concerns:**
- `cli/` - Deployment orchestration (Docker Compose, local dev)
- `infra/` - Cloud infrastructure (Terraform, cloud resources)
- `backend/` - Application code
- `frontend/` - Application code

## 🚀 Quick Start

### Google Cloud Platform

```bash
cd infra/gcp/environments/dev
terraform init
terraform plan
terraform apply
```

See [gcp/README.md](gcp/README.md) for detailed instructions.

## 📚 Documentation

- [GCP Deployment](gcp/README.md)
- [Architecture Overview](docs/architecture.md)

## 🔐 Prerequisites

- Terraform >= 1.5.0
- Google Cloud SDK
- GCP Project with billing enabled
- Service account with appropriate permissions

## 🏗️ Resources Managed

### GCP
- Cloud Run (Backend API)
- Cloud SQL (PostgreSQL)
- Cloud Storage (Media, certificates)
- Cloud Tasks (Job queue)
- Load Balancer
- VPC & Networking
- IAM & Service Accounts
- Secret Manager
