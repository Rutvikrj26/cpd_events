# CPD Events Platform - Documentation Index

Central navigation hub for all CPD Events platform documentation.

## Quick Start

- [Main README](../README.md) - Project overview and getting started
- [Architecture](../ARCHITECTURE.md) - System architecture overview
- [Technology Stack](../TECHNOLOGY_STACK.md) - Technology choices and rationale
- [Deployment Guide](../DEPLOYMENT_GUIDE.md) - How to deploy the platform
- [TLDR](../tldr.md) - Quick reference guide

## Component Documentation

### Backend
- [Backend README](../backend/README.md) - API architecture, modules, and development setup
- [API Specifications](api/) - Complete REST API documentation
- [Data Models](api/data-models.md) - Database schema and relationships

### Frontend
- [Frontend README](../frontend/README.md) - React app structure and development
- [User Workflows](workflows/frontend-user-flows.md) - Frontend user flow documentation

### CLI
- [CLI README](../cli/README.md) - Command-line interface documentation
- [CLI Documentation](../cli/docs/) - Detailed CLI guides

### Infrastructure
- [Infrastructure README](../infra/README.md) - Infrastructure as Code
- [Infrastructure Summary](deployment/infrastructure.md) - GCP infrastructure overview

## Documentation by Topic

### Setup & Configuration
- [Environment Setup](setup/environment-setup.md) - Development environment configuration
- [Environment Cheatsheet](setup/environment-cheatsheet.md) - Quick reference for env vars
- [Admin Panel Guide](setup/admin-panel-guide.md) - Admin panel usage
- [Stripe Setup](setup/stripe-setup.md) - Payment integration setup

### API Documentation
- [DRF Endpoints (Part 1)](api/drf-endpoints-part1.md) - Django REST API endpoints
- [DRF Endpoints (Part 2)](api/drf-endpoints-part2.md) - Additional endpoints
- [API Review](api/api-review.md) - API specification review
- [Data Models](api/data-models.md) - Database models and relationships

### Features
- [Accounts](features/accounts.md) - User accounts and authentication
- [Events](features/events.md) - Event management
- [Registrations](features/registrations.md) - Registration system
- [Certificates](features/certificates.md) - Certificate generation
- [Contacts](features/contacts.md) - Contact management
- [Learning](features/learning.md) - Learning management system
- [Integrations](features/integrations.md) - Third-party integrations
- [Multi-Session Events](features/multi_session_events.md) - Multi-session event support
- [Services](features/services.md) - Service layer architecture
- [Common](features/common.md) - Shared components

### Architecture
- [Architecture Overview](architecture/overview.md) - Architectural review
- [Architecture Fixes](architecture/fixes-summary.md) - Architectural improvements
- [Data Planning](architecture/data-planning.md) - Data architecture planning

### User Workflows
- [Signup Flows](workflows/signup-flows.md) - User signup workflows
- [Signup Gaps](workflows/signup-gaps.md) - Signup workflow gaps
- [Platform User Flows](workflows/platform-user-flows.md) - Platform workflows
- [Sidebar Navigation](workflows/sidebar-navigation.md) - Navigation structure
- [Platform Screens v1](workflows/platform-screens-v1.md) - Original screen architecture
- [Platform Screens v2](workflows/platform-screens-v2.md) - Updated screen architecture
- [Frontend User Flows](workflows/frontend-user-flows.md) - Frontend workflows

### CLI Documentation
See [CLI docs](../cli/docs/) for comprehensive CLI documentation:
- [Command Tree](../cli/docs/command-tree.md)
- [Cheatsheet](../cli/docs/cheatsheet.md)
- [Summary](../cli/docs/summary.md)
- [Functionality Audit](../cli/docs/functionality-audit.md)
- [Configuration](../cli/docs/config.md)
- [Cloud Features](../cli/docs/cloud-features.md)
- [Audit Index](../cli/docs/audit-index.md)

### Deployment
- [Docker Changes](deployment/docker-changes.md) - Docker configuration changes
- [Infrastructure](deployment/infrastructure.md) - GCP infrastructure setup

### Gap Analysis
- [User Registration & Billing](gaps/user-registration-billing.md) - Registration/billing gaps
- [Holistic Analysis](gaps/holistic-analysis.md) - Complete gap analysis
- [Backend Gaps](gaps/backend-gaps.md) - Backend-specific gaps
- [Frontend Workflow Gaps](gaps/frontend-workflow-gaps.md) - Frontend gaps

### Product Documentation
- [Features Overview](product/features-overview.md) - Product features
- [Pricing Tiers](product/pricing-tiers.md) - Pricing tier structure
- [Pricing Strategy](product/pricing-strategy.md) - Pricing strategy

### Roadmap
- [LMS Features](roadmap/lms-features.md) - LMS roadmap and planning

### Integrations
- [Zoom Marketplace](integrations/zoom-marketplace.md) - Zoom marketplace submission

### History & Audits
- [Audit Findings (Jan 2026)](history/audit-findings-2026-01.md) - Recent audit results
- [Changes Summary (Jan 2026)](history/changes-summary-2026-01.md) - Recent changes
- [Documentation Sync (Jan 2026)](history/documentation-sync-2026-01.md) - Doc sync status
- [Implementation Status](history/implementation-status.md) - Implementation tracking
- [Implementation Progress](history/implementation-progress.md) - Progress updates
- [Branding Phase 8](history/branding-phase-8.md) - Branding completion
- [Frontend Audit (Jan 2026)](history/frontend-audit-2026-01.md) - Frontend audit
- [UI/UX Improvements (Jan 2026)](history/ui-ux-improvements-2026-01.md) - UI/UX updates

### Archived Documentation
- [Archive](.archive/) - Historical and legacy documentation

## Documentation Organization

This documentation is organized into the following categories:

| Category | Purpose | Location |
|----------|---------|----------|
| **setup/** | Environment and configuration guides | [docs/setup/](setup/) |
| **api/** | API specifications and data models | [docs/api/](api/) |
| **features/** | Feature-specific documentation | [docs/features/](features/) |
| **architecture/** | System architecture documents | [docs/architecture/](architecture/) |
| **workflows/** | User workflow documentation | [docs/workflows/](workflows/) |
| **cli/** | CLI tool documentation | [cli/docs/](../cli/docs/) |
| **deployment/** | Deployment guides | [docs/deployment/](deployment/) |
| **gaps/** | Gap analysis and known issues | [docs/gaps/](gaps/) |
| **product/** | Product documentation | [docs/product/](product/) |
| **roadmap/** | Future planning | [docs/roadmap/](roadmap/) |
| **integrations/** | Integration guides | [docs/integrations/](integrations/) |
| **history/** | Historical records and audits | [docs/history/](history/) |
| **.archive/** | Archived/legacy documentation | [docs/.archive/](.archive/) |

## How to Use This Documentation

1. **New to the project?** Start with the [Main README](../README.md) and [Architecture](../ARCHITECTURE.md)
2. **Setting up development?** Check [Setup & Configuration](#setup--configuration)
3. **Working on the API?** See [API Documentation](#api-documentation)
4. **Building frontend features?** Review [Frontend README](../frontend/README.md) and [Features](#features)
5. **Deploying to production?** Follow the [Deployment Guide](../DEPLOYMENT_GUIDE.md)
6. **Looking for specific docs?** Use the search above or browse by topic

## Contributing to Documentation

When adding or updating documentation:
- Place files in the appropriate subdirectory
- Update this INDEX.md with links to new documents
- Follow the existing documentation style
- Keep documentation current with code changes
- Add cross-references where helpful

## Need Help?

- Check the [TLDR](../tldr.md) for quick answers
- Review [Gap Analysis](gaps/) for known issues
- See component-specific READMEs ([Backend](../backend/README.md), [Frontend](../frontend/README.md), [CLI](../cli/README.md))
