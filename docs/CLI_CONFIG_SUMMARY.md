# CLI Configuration System

The Accredit CLI now includes a configuration system to track your working environment and project settings.

## Configuration File

Configuration is stored in: `~/.config/accredit/config.json`

## Setup Commands

### Initialize Configuration
```bash
# Interactive setup
accredit setup

# Or with options
accredit setup init --env dev --project-id my-gcp-project --region us-central1
```

### View Configuration
```bash
# Show all settings
accredit setup show

# Show current environment only
accredit env
```

### Switch Environment
```bash
# Switch to a different environment
accredit setup use dev
accredit setup use staging
accredit setup use prod
```

### Get/Set Individual Values
```bash
# Get a value
accredit setup get environment
accredit setup get project_id

# Set a value
accredit setup set environment staging
accredit setup set project_id my-project-123
accredit setup set region europe-west1
```

### Reset Configuration
```bash
# Reset to defaults
accredit setup reset
```

## Configuration Values

| Setting | Description | Default |
|---------|-------------|---------|
| `environment` | Current working environment (dev/staging/prod) | `dev` |
| `project_id` | GCP project ID | `null` |
| `region` | GCP region | `us-central1` |

## Using Configured Environment

All cloud commands now default to the configured environment:

### Before (required --env flag):
```bash
accredit cloud infra plan --env dev
accredit cloud backend deploy --env dev
accredit cloud frontend deploy --env dev
```

### After (uses configured environment):
```bash
# Setup once
accredit setup use dev

# Then run without --env flag
accredit cloud infra plan
accredit cloud backend deploy
accredit cloud frontend deploy
```

### Override when needed:
```bash
# Use configured env (dev)
accredit cloud status

# Override to check staging
accredit cloud status --env staging
```

## Workflow Example

```bash
# 1. Initial setup
accredit setup init

# 2. Set environment to dev
accredit setup use dev

# 3. Deploy to dev (no --env needed)
accredit cloud infra init
accredit cloud infra apply
accredit cloud backend build
accredit cloud backend deploy

# 4. Switch to staging
accredit setup use staging

# 5. Deploy to staging (automatically uses staging)
accredit cloud backend deploy

# 6. Check current environment
accredit env
# Output: Current environment: staging
```

## Benefits

1. **Less typing**: No need to specify `--env` on every command
2. **Context awareness**: CLI remembers which environment you're working with
3. **Reduced errors**: Less chance of accidentally deploying to the wrong environment
4. **Quick switching**: Easy to switch between environments with `accredit setup use`
5. **Visibility**: Always know your current environment with `accredit env`

## Commands Affected

All cloud commands now use the configured environment as default:

**Infrastructure:**
- `accredit cloud infra init`
- `accredit cloud infra plan`
- `accredit cloud infra apply`
- `accredit cloud infra destroy`
- `accredit cloud infra output`
- `accredit cloud infra validate`

**Backend:**
- `accredit cloud backend build`
- `accredit cloud backend deploy`
- `accredit cloud backend logs`

**Frontend:**
- `accredit cloud frontend build`
- `accredit cloud frontend deploy`
- `accredit cloud frontend invalidate`

**Utilities:**
- `accredit cloud status`
- `accredit cloud ssh`

All commands still support `--env` flag to override the configured environment when needed.
