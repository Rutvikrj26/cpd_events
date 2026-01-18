# Documentation Directory

This directory contains organized documentation for the CPD Events platform.

## Navigation

For a complete index of all documentation, see [INDEX.md](INDEX.md).

## Directory Structure

```
docs/
├── INDEX.md                    # Central navigation hub - START HERE
├── README.md                   # This file
│
├── setup/                      # Setup & Configuration
│   ├── environment-setup.md
│   ├── environment-cheatsheet.md
│   ├── admin-panel-guide.md
│   └── stripe-setup.md
│
├── api/                        # API Specifications
│   ├── drf-endpoints-part1.md
│   ├── drf-endpoints-part2.md
│   ├── api-review.md
│   └── data-models.md
│
├── features/                   # Feature Documentation
│   ├── accounts.md
│   ├── events.md
│   ├── registrations.md
│   ├── certificates.md
│   ├── contacts.md
│   ├── learning.md
│   ├── integrations.md
│   ├── multi_session_events.md
│   ├── services.md
│   └── common.md
│
├── architecture/               # Architecture Documentation
│   ├── overview.md
│   ├── fixes-summary.md
│   └── data-planning.md
│
├── workflows/                  # User Workflows
│   ├── signup-flows.md
│   ├── signup-gaps.md
│   ├── platform-user-flows.md
│   ├── sidebar-navigation.md
│   ├── platform-screens-v1.md
│   ├── platform-screens-v2.md
│   └── frontend-user-flows.md
│
├── deployment/                 # Deployment Documentation
│   ├── docker-changes.md
│   └── infrastructure.md
│
├── gaps/                       # Gap Analysis
│   ├── user-registration-billing.md
│   ├── holistic-analysis.md
│   ├── backend-gaps.md
│   └── frontend-workflow-gaps.md
│
├── product/                    # Product Documentation
│   ├── features-overview.md
│   ├── pricing-tiers.md
│   └── pricing-strategy.md
│
├── roadmap/                    # Roadmaps
│   └── lms-features.md
│
├── integrations/               # Integration Guides
│   └── zoom-marketplace.md
│
├── history/                    # Historical Tracking
│   ├── audit-findings-2026-01.md
│   ├── changes-summary-2026-01.md
│   ├── documentation-sync-2026-01.md
│   ├── implementation-status.md
│   ├── implementation-progress.md
│   ├── branding-phase-8.md
│   ├── frontend-audit-2026-01.md
│   └── ui-ux-improvements-2026-01.md
│
└── .archive/                   # Archived Documentation
    └── legacy/                 # Legacy documentation (pre-reorganization)
```

## Documentation Categories

### Setup & Configuration
Development environment setup, configuration guides, and admin panel documentation.

### API Specifications
Complete REST API documentation, endpoint specifications, and data models.

### Features
Detailed documentation for each feature area of the platform (accounts, events, certificates, etc.).

### Architecture
System architecture, architectural decisions, and data planning.

### Workflows
User workflow documentation, signup flows, and UI screen architecture.

### Deployment
Deployment guides, infrastructure setup, and Docker configuration.

### Gap Analysis
Known issues, missing features, and areas for improvement.

### Product
Product feature descriptions, pricing information, and business documentation.

### Roadmap
Future feature planning and roadmaps.

### Integrations
Third-party integration guides and documentation.

### History
Historical records, audit findings, implementation tracking, and change summaries.

### Archive
Legacy and outdated documentation preserved for historical reference.

## Quick Links

### For Developers
- [Backend README](../backend/README.md)
- [Frontend README](../frontend/README.md)
- [CLI README](../cli/README.md)
- [Setup Guide](setup/environment-setup.md)
- [API Documentation](api/)

### For DevOps
- [Deployment Guide](../DEPLOYMENT_GUIDE.md)
- [Infrastructure Setup](deployment/infrastructure.md)
- [Docker Changes](deployment/docker-changes.md)

### For Product/Business
- [Product Features](product/features-overview.md)
- [Pricing Strategy](product/pricing-strategy.md)
- [Roadmap](roadmap/)

### For Project Management
- [Gap Analysis](gaps/)
- [Implementation Status](history/implementation-status.md)
- [Audit Findings](history/audit-findings-2026-01.md)

## CLI Documentation

CLI-specific documentation is located in the CLI directory for better organization:
- [CLI Documentation](../cli/docs/)

This keeps CLI docs close to the CLI code while maintaining the overall documentation structure.

## Finding Documentation

1. **Browse by Category**: Navigate to the appropriate subdirectory above
2. **Use the Index**: Check [INDEX.md](INDEX.md) for a complete list
3. **Search**: Use your editor's search or `grep -r "search term" docs/`

## Contributing

When adding documentation:
1. Place files in the appropriate subdirectory
2. Use clear, descriptive filenames (kebab-case)
3. Update [INDEX.md](INDEX.md) with links to new documents
4. Add cross-references to related documentation
5. Follow existing formatting conventions

### Documentation Standards
- Use Markdown format
- Include a clear title (# heading)
- Add a brief description at the top
- Use proper heading hierarchy
- Link to related documents
- Keep documentation current with code

## Maintenance

### When to Archive
Move documentation to `.archive/legacy/` when:
- It's superseded by newer documentation
- It describes removed features
- It's no longer relevant but has historical value

### When to Delete
Delete documentation when:
- It's completely obsolete with no historical value
- It duplicates other documentation exactly
- It was created in error

## Getting Help

If you can't find what you're looking for:
1. Check [INDEX.md](INDEX.md) - the central navigation hub
2. Review the [Main README](../README.md)
3. Check component-specific READMEs ([Backend](../backend/README.md), [Frontend](../frontend/README.md))
4. Search the codebase for inline documentation
