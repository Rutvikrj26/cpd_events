# Accredit CLI

A Python-based CLI tool for managing the CPD Events platform - streamlines local development, deployment, and operations.

## Installation

### Recommended: Install with uv tool (Editable Mode)

**uv** is a fast Python package and project manager - perfect for development!

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh
# or on macOS: brew install uv

# Install accredit in editable mode
cd cli
uv tool install --editable .

# Verify installation
accredit --version
accredit --help
```

**Editable mode** means changes to the source code are immediately reflected - no reinstall needed!

### Alternative: Local Development Environment

```bash
cd cli
uv sync  # Install dependencies

# Run commands directly
.venv/bin/accredit --help

# Or use uv run
uv run accredit --help
```

## Usage

```bash
accredit [COMMAND] [OPTIONS]
```

### Available Command Groups

#### 🏠 `accredit local` - Local Development
Manage local development environment without Docker.

```bash
accredit local setup    # Install dependencies & run migrations
accredit local up       # Start backend & frontend servers
accredit local logs     # View application logs
accredit local shell    # Open Django shell
```

#### 🐳 `accredit docker` - Docker Development
Orchestrate Docker Compose services for local development.

```bash
accredit docker up [-d] [--build]    # Start services
accredit docker down [-v]            # Stop services (optionally remove volumes)
accredit docker ps                   # List running services
accredit docker logs [-f] [service]  # View logs
accredit docker exec SERVICE CMD...  # Execute command in container
accredit docker init                 # Initialize environment (buckets, migrations)
accredit docker restart              # Restart all services
```

#### ☁️ `accredit cloud` - Cloud Deployment (GCP)
Deploy and manage infrastructure on Google Cloud Platform.

##### Infrastructure Management (Terraform)
```bash
accredit cloud infra init --env dev        # Initialize Terraform
accredit cloud infra plan --env dev        # Preview infrastructure changes
accredit cloud infra apply --env dev       # Apply infrastructure changes
accredit cloud infra destroy --env dev     # Destroy infrastructure
accredit cloud infra output --env dev      # Show Terraform outputs
accredit cloud infra validate --env dev    # Validate configuration
```

##### Backend Deployment
```bash
accredit cloud backend build --env dev     # Build & push Docker image to GCR
accredit cloud backend deploy --env dev    # Deploy to Cloud Run
accredit cloud backend logs --env dev      # View Cloud Run logs
```

##### Frontend Deployment
```bash
accredit cloud frontend build --env dev    # Build production bundle
accredit cloud frontend deploy --env dev   # Deploy to Cloud Storage + CDN
accredit cloud frontend invalidate --env dev  # Invalidate CDN cache
```

##### Utilities
```bash
accredit cloud status --env dev      # Show deployment status
accredit cloud list-envs             # List available environments
accredit cloud ssh --env dev         # Connect to Cloud Run service
```

## Project Structure

```
cli/
├── accredit/              # Main package
│   ├── __init__.py
│   ├── main.py           # CLI entry point
│   ├── commands/         # Command modules
│   │   ├── __init__.py
│   │   ├── local.py      # Local dev commands
│   │   ├── docker.py     # Docker orchestration
│   │   └── cloud.py      # GCP deployment
│   └── utils/            # Utility functions
├── docker-compose.yml        # Development environment
├── docker-compose.prod.yml   # Production-like environment
├── pyproject.toml            # Poetry configuration
└── README.md
```

## Deployment Workflows

### Complete Deployment from Scratch

#### 1. Set up Infrastructure
```bash
# Copy example config
cd infra/gcp/environments/dev
cp terraform.tfvars.example terraform.tfvars

# Edit with your GCP project details
vim terraform.tfvars

# Initialize and apply infrastructure
accredit cloud infra init --env dev
accredit cloud infra plan --env dev
accredit cloud infra apply --env dev
```

#### 2. Deploy Backend
```bash
# Build and push Docker image
accredit cloud backend build --env dev

# Deploy to Cloud Run
accredit cloud backend deploy --env dev
```

#### 3. Deploy Frontend
```bash
# Build and deploy (runs build automatically)
accredit cloud frontend deploy --env dev
```

#### 4. Configure DNS
```bash
# Get the load balancer IP
accredit cloud infra output --env dev frontend_ip_address

# Configure DNS A records:
# yourdomain.com -> FRONTEND_IP
# www.yourdomain.com -> FRONTEND_IP
```

#### 5. Verify Deployment
```bash
# Check overall status
accredit cloud status --env dev

# View backend logs
accredit cloud backend logs --env dev --follow
```

### Quick Update Workflows

#### Update Backend Code
```bash
accredit cloud backend build --env dev
accredit cloud backend deploy --env dev
```

#### Update Frontend
```bash
accredit cloud frontend deploy --env dev
# CDN cache is automatically invalidated
```

#### Update Infrastructure
```bash
accredit cloud infra plan --env dev    # Preview changes
accredit cloud infra apply --env dev   # Apply changes
```

### Environment Management

Easily switch between environments:
```bash
# Development
accredit cloud status --env dev
accredit cloud backend deploy --env dev

# Staging
accredit cloud status --env staging
accredit cloud backend deploy --env staging

# Production
accredit cloud status --env prod
accredit cloud backend deploy --env prod
```

## Development

### Adding New Commands

1. Create a new command module in `accredit/commands/`
2. Import and register it in `accredit/main.py`

Example:
```python
# accredit/commands/deploy.py
import typer

app = typer.Typer()

@app.command()
def production():
    """Deploy to production."""
    typer.echo("Deploying to production...")

# accredit/main.py
from accredit.commands import deploy

app.add_typer(deploy.app, name="deploy", help="Deployment commands")
```

### Running Tests

```bash
uv run pytest
```

### Code Formatting

```bash
uv run black accredit/
uv run ruff check accredit/
```

## Troubleshooting

- **Logs**: Located in `.cli/logs/`
- **PIDs**: Process IDs stored in `.cli/pids/`
- **Command not found**: Ensure `~/.local/bin` is in your PATH or use `uv run accredit`

## Uninstallation

```bash
# If installed with uv tool
uv tool uninstall accredit

# Or remove the local venv
rm -rf .venv uv.lock
```
