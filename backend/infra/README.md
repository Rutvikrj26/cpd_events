# CPD Events Infrastructure

This directory contains infrastructure-as-code and architecture documentation for the CPD Events platform.

## Structure

```
infra/
├── terraform/          # Terraform configurations
│   ├── environments/   # Environment-specific configs (dev, staging, prod)
│   ├── modules/        # Reusable Terraform modules
│   └── main.tf         # Root module
├── docs/               # Architecture documentation
│   └── architecture.md # High-level architecture diagram
└── scripts/            # Deployment and utility scripts
```

## Quick Start

1. Install Terraform
2. Configure GCP credentials
3. Initialize: `cd terraform && terraform init`
4. Plan: `terraform plan -var-file=environments/dev.tfvars`
5. Apply: `terraform apply -var-file=environments/dev.tfvars`
