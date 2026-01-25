# Accredit - Session Context Guide

**Purpose:** This file tells AI assistants what information to load at the start of each session.

---

## Quick Start for AI Sessions

At the beginning of each new session working on this project, read these files:

1. **`.project/PROJECT_INFO.md`** - Core project information
   - Production URLs and configuration
   - Deployment workflow
   - Git strategy
   - Cost information
   - Key decisions

2. **`DEPLOYMENT_STATE_ANALYSIS.md`** - Terraform state management
   - How Terraform and deployments interact
   - Why deployments are safe
   - Rollback strategies

3. **`cli/DEPLOYMENT.md`** - Deployment procedures
   - Step-by-step deployment guides
   - Troubleshooting

---

## Session Continuity Pattern

```bash
# At session start, run:
cd /home/beyonder/projects/cpd_events

# Read core context
cat .project/PROJECT_INFO.md

# Check current state
git status
git log --oneline -5
accredit cloud backend history --env prod
```

---

## Project Structure Quick Reference

```
cpd_events/
├── .project/                    # 📋 Session context files (read these first!)
│   ├── PROJECT_INFO.md          # Core project information
│   └── README.md                # This file
│
├── backend/                     # Django backend
├── frontend/                    # React frontend  
├── cli/                         # Accredit CLI tool
│   ├── accredit/
│   ├── DEPLOYMENT.md            # Deployment guide
│   └── README.md                # CLI usage
│
├── infra/                       # Infrastructure as Code
│   └── gcp/
│       └── environments/
│           ├── dev/
│           └── prod/            # Production Terraform
│
├── DEPLOYMENT_STATE_ANALYSIS.md # Terraform analysis
└── README.md                    # Project overview
```

---

## Key Concepts to Remember

### 1. Always Use Accredit CLI for Deployments
```bash
✅ accredit cloud backend deploy --env prod
❌ gcloud run deploy cpd-events-prod ...
```

### 2. Two-Layer State System
- **Terraform:** Manages infrastructure (what exists)
- **Accredit CLI:** Manages deployments (what code version)

### 3. Deployment Won't Be Reverted
- Image uses `:latest` tag
- Traffic routing uses `latest_revision = true`
- Terraform accepts whatever is deployed

---

## Updating This Context

When significant changes occur, update `.project/PROJECT_INFO.md`:

- New production deployments
- Infrastructure changes
- Configuration updates
- Important decisions
- Cost changes
- New team members

---

**Last Updated:** 2026-01-25
