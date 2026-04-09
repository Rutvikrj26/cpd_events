# Docker Compose Migration Summary

All Docker Compose files and deployment orchestration have been moved to the `cli/` directory for separation of concerns.

## ✅ What Changed

### Files Moved

```
Before:
cpd_events/
├── docker-compose.yml              # Root directory
├── backend/docker-compose.prod.yml # Backend directory
└── DOCKER.md                       # Root directory

After:
cpd_events/
└── cli/
    ├── docker-compose.yml          # Moved here
    ├── docker-compose.prod.yml     # Moved here
    └── DOCKER.md                   # Moved here
```

### Paths Updated

All `context` and `volume` paths in docker-compose files now use `../` to reference parent directories:

```yaml
# Before (when in root)
build:
  context: ./backend

# After (when in cli/)
build:
  context: ../backend
```

### New CLI Commands

Added `accredit docker` command group with full Docker orchestration:

```bash
accredit docker up                 # Start development
accredit docker init               # Initialize environment
accredit docker logs -f            # View logs
accredit docker exec ...           # Run commands
accredit docker down               # Stop services
accredit docker prod-up            # Production mode
```

## 🎯 Benefits

### 1. Separation of Concerns
- **cli/** = Deployment, orchestration, infrastructure
- **backend/** = Django application code only
- **frontend/** = React application code only

### 2. Centralized Deployment Management
- All deployment configs in one place
- Easy to find and modify
- Single source of truth

### 3. CLI-Driven Workflow
- `accredit docker` handles all Docker operations
- No need to remember docker-compose paths
- Works from anywhere in the project

### 4. Better Organization
- Clear responsibility boundaries
- Infrastructure as code in dedicated directory
- Application code stays clean

## 📝 How to Use

### Old Way (Still Works)

```bash
cd /path/to/cpd_events
docker-compose up  # ❌ Won't work - file moved!
```

### New Way (Recommended)

```bash
# From anywhere in the project
accredit docker up -d
accredit docker init
```

### Alternative (Direct Docker Compose)

```bash
cd cli
docker-compose up -d
```

## 🔄 Migration Checklist

- [x] Moved docker-compose.yml to cli/
- [x] Moved docker-compose.prod.yml to cli/
- [x] Moved DOCKER.md to cli/
- [x] Updated all paths in compose files (../ prefix)
- [x] Created `accredit docker` command group
- [x] Updated DOCKER.md documentation
- [x] Created DEPLOYMENT.md guide
- [x] Updated root README.md
- [x] Tested all commands

## 🧪 Verification

### Test Development Environment

```bash
cd cli
accredit docker up --build -d
accredit docker ps
accredit docker logs backend
accredit docker down
```

### Test Production Environment

```bash
cd cli
accredit docker prod-up --build -d
accredit docker ps
accredit docker prod-down
```

## 📚 Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide
- **[DOCKER.md](DOCKER.md)** - Docker setup and usage
- **[README.md](README.md)** - CLI tool documentation
- **[../README.md](../README.md)** - Project overview

## 🎓 Best Practices

### For Developers

```bash
# Always use the CLI
accredit docker up -d          # ✅ Good
cd cli && docker-compose up    # ⚠️ Works but verbose
```

### For CI/CD

```bash
# In CI pipeline
cd cli
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml push
```

### For Documentation

- Point developers to `cli/DEPLOYMENT.md`
- Reference `accredit docker` commands
- Keep infrastructure docs in `cli/`

## ⚡ Quick Reference

| Task | Command |
|------|---------|
| Start dev | `accredit docker up -d` |
| Initialize | `accredit docker init` |
| View logs | `accredit docker logs -f` |
| Run command | `accredit docker exec backend ...` |
| Stop dev | `accredit docker down` |
| Start prod | `accredit docker prod-up -d` |
| Stop prod | `accredit docker prod-down` |

---

**Status**: ✅ Migration complete! All deployment concerns centralized in `cli/` directory.
