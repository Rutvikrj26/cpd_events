# CLI Documentation

This directory contains comprehensive documentation for the Accredit CLI tool.

## Files

- [command-tree.md](command-tree.md) - Complete command tree and structure
- [cheatsheet.md](cheatsheet.md) - Quick reference for common commands
- [summary.md](summary.md) - CLI overview and capabilities summary
- [functionality-audit.md](functionality-audit.md) - Functionality audit and analysis
- [config.md](config.md) - Configuration guide
- [cloud-features.md](cloud-features.md) - Cloud deployment features
- [audit-index.md](audit-index.md) - Audit index and findings

## Quick Start

### Installation
```bash
pip install -e cli/
```

### Basic Usage
```bash
# Get help
accredit --help

# Local development
accredit local start
accredit local stop

# Docker operations
accredit docker up
accredit docker down

# Cloud deployment
accredit cloud backend deploy --env dev
accredit cloud frontend deploy --env dev
```

## Documentation Overview

### Command Tree
[command-tree.md](command-tree.md) - Complete hierarchical view of all CLI commands and subcommands.

### Cheatsheet
[cheatsheet.md](cheatsheet.md) - Quick reference for the most common CLI operations.

### Summary
[summary.md](summary.md) - Overview of CLI capabilities and features.

### Configuration
[config.md](config.md) - How to configure the CLI for your environment.

### Cloud Features
[cloud-features.md](cloud-features.md) - Detailed guide for cloud deployment commands.

### Audits
- [functionality-audit.md](functionality-audit.md) - Functionality audit
- [audit-index.md](audit-index.md) - Audit index

## Key Features

### Local Development
- Start/stop development servers
- Database management
- Environment setup
- Log viewing

### Docker Operations
- Build and manage containers
- Docker Compose orchestration
- Volume management
- Network configuration

### Cloud Deployment
- Infrastructure provisioning (Terraform)
- Backend deployment to Cloud Run
- Frontend deployment to Cloud Storage + CDN
- Environment management (dev/staging/prod)
- Status monitoring
- Log viewing

## Command Categories

### `accredit local`
Local development server management

### `accredit docker`
Docker and Docker Compose operations

### `accredit cloud`
Cloud deployment and infrastructure management

### `accredit cloud infra`
Infrastructure provisioning with Terraform

### `accredit cloud backend`
Backend deployment to Cloud Run

### `accredit cloud frontend`
Frontend deployment to Cloud Storage + CDN

## Related Documentation

- [CLI README](../README.md) - CLI tool overview
- [Deployment Guide](../../DEPLOYMENT_GUIDE.md) - Deployment instructions
- [Infrastructure Documentation](../../docs/deployment/infrastructure.md) - Infrastructure setup
- [Backend README](../../backend/README.md) - Backend development
- [Frontend README](../../frontend/README.md) - Frontend development

## Getting Help

```bash
# General help
accredit --help

# Command-specific help
accredit cloud --help
accredit cloud backend --help
accredit cloud backend deploy --help
```

## Contributing

When updating CLI documentation:
1. Keep command examples current
2. Update the command tree when adding new commands
3. Add new commands to the cheatsheet if commonly used
4. Update related documentation (README, deployment guides)
