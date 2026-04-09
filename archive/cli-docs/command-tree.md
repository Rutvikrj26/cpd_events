# Accredit CLI - Command Tree

```
accredit
├── --version                     # Show CLI version
├── --help                        # Show help
│
├── env                           # Show current environment
│
├── setup                         # Configuration management
│   ├── (default: init)          # Interactive setup wizard
│   ├── init                     # Initialize configuration
│   │   ├── --env                # Set environment (dev/staging/prod)
│   │   ├── --project-id         # Set GCP project ID
│   │   └── --region             # Set GCP region
│   ├── show                     # Display current configuration
│   ├── use <environment>        # Switch environment (dev/staging/prod)
│   ├── get <key>                # Get configuration value
│   ├── set <key> <value>        # Set configuration value
│   └── reset                    # Reset to defaults
│
├── local                         # Native local development
│   ├── up                       # Start services
│   │   ├── --backend            # Start only backend
│   │   └── --frontend           # Start only frontend
│   ├── down                     # Stop services
│   │   ├── --backend            # Stop only backend
│   │   └── --frontend           # Stop only frontend
│   ├── logs                     # Follow logs
│   │   ├── --backend            # Show only backend logs
│   │   └── --frontend           # Show only frontend logs
│   ├── status                   # Check service status
│   ├── setup                    # Install dependencies & migrate
│   └── shell                    # Open Django shell
│
├── docker                        # Docker orchestration
│   ├── up                       # Start dev services
│   │   ├── --build              # Build images first
│   │   └── -d, --detach         # Run in background
│   ├── down                     # Stop services
│   │   └── -v, --volumes        # Remove volumes
│   ├── ps                       # List running containers
│   ├── logs                     # View logs
│   │   ├── -f, --follow         # Follow log output
│   │   └── [service]            # Specific service
│   ├── exec <service> <cmd...>  # Execute command in container
│   ├── init                     # Initialize environment (GCS, migrations)
│   ├── restart                  # Restart all services
│   ├── prod-up                  # Start production services
│   │   ├── --build              # Build images first
│   │   └── -d, --detach         # Run in background
│   └── prod-down                # Stop production services
│       └── -v, --volumes        # Remove volumes
│
└── cloud                         # GCP deployment & management
    │
    ├── infra                    # Infrastructure management (Terraform)
    │   ├── init                 # Initialize Terraform
    │   │   └── --env, -e        # Environment (defaults to config)
    │   ├── plan                 # Preview changes
    │   │   ├── --env, -e        # Environment
    │   │   └── --out, -o        # Save plan to file
    │   ├── apply                # Apply changes
    │   │   ├── --env, -e        # Environment
    │   │   └── --auto-approve   # Skip confirmation
    │   ├── destroy              # Destroy infrastructure
    │   │   ├── --env, -e        # Environment
    │   │   └── --auto-approve   # Skip confirmation
    │   ├── output               # Show outputs
    │   │   ├── --env, -e        # Environment
    │   │   └── [name]           # Specific output name
    │   └── validate             # Validate configuration
    │       └── --env, -e        # Environment
    │
    ├── backend                  # Backend deployment (Cloud Run)
    │   ├── build                # Build & push Docker image
    │   │   ├── --env, -e        # Environment
    │   │   └── --tag, -t        # Image tag (default: latest)
    │   ├── deploy               # Deploy to Cloud Run
    │   │   ├── --env, -e        # Environment
    │   │   └── --tag, -t        # Image tag (default: latest)
    │   └── logs                 # View logs
    │       ├── --env, -e        # Environment
    │       ├── -f, --follow     # Follow log output
    │       └── --limit          # Number of entries (default: 100)
    │
    ├── frontend                 # Frontend deployment (Cloud Storage + CDN)
    │   ├── build                # Build production bundle
    │   │   └── --env, -e        # Environment
    │   ├── deploy               # Deploy to Cloud Storage
    │   │   └── --env, -e        # Environment
    │   └── invalidate           # Invalidate CDN cache
    │       └── --env, -e        # Environment
    │
    ├── status                   # Show deployment status
    │   └── --env, -e            # Environment
    │
    ├── list-envs                # List available environments
    │
    └── ssh                      # Connect to Cloud Run service
        └── --env, -e            # Environment
```

## Flag Legend

- `--env, -e`: Environment selection (dev/staging/prod)
  - **Defaults to configured environment** (from `accredit setup`)
  - Can be overridden for any command
  
- `--backend / --frontend`: Service selection flags (local commands)
  - If neither specified: operates on both services
  - If one specified: operates only on that service

- `--build`: Build Docker images before starting
- `-d, --detach`: Run in background/detached mode
- `-v, --volumes`: Remove volumes (data will be lost)
- `-f, --follow`: Follow/tail log output
- `--auto-approve`: Skip confirmation prompts (dangerous operations)
- `--tag, -t`: Docker image tag (default: latest)
- `--limit`: Limit number of log entries
- `--out, -o`: Output file path

## Color Coding in Output

The CLI uses Rich library for colored output:

- 🟦 **Cyan**: Informational messages, prompts
- 🟩 **Green**: Success messages, checkmarks
- 🟨 **Yellow**: Warnings, confirmations needed
- 🟥 **Red**: Errors, failures
- ⬜ **White/Default**: Normal output, table data

## Quick Reference

### Most Common Commands

```bash
# Setup
accredit setup
accredit setup use dev

# Local Development
accredit local up
accredit local logs

# Docker Development
accredit docker up -d
accredit docker logs -f

# Cloud Deployment
accredit cloud infra apply
accredit cloud backend deploy
accredit cloud frontend deploy
accredit cloud status

# Check Environment
accredit env
```

### Command Patterns

| Pattern | Meaning |
|---------|---------|
| `accredit <group>` | Show help for command group |
| `accredit <group> <command>` | Execute command with defaults |
| `accredit <group> <command> --flag` | Execute with specific flag |
| `accredit cloud <command>` | Uses configured environment |
| `accredit cloud <command> --env prod` | Override to use prod |

## Exit Codes

- `0`: Success
- `1`: Error (command failed, validation error, etc.)
- `130`: User interrupted (Ctrl+C)
