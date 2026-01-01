# Accredit CLI - Installation Guide

## Installation Methods

### Recommended: Install with pipx (Editable Mode)

**pipx** is the recommended way to install Python CLI tools. It creates isolated environments for each tool and makes them available globally.

#### 1. Install pipx (if not already installed)

```bash
# macOS
brew install pipx
pipx ensurepath

# Linux
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Verify installation
pipx --version
```

#### 2. Install accredit in editable mode

```bash
# Navigate to the CLI directory
cd /Users/rutvikrj26/Desktop/cpd_events/cli

# Install in editable mode
pipx install -e .
```

**Editable mode** means any changes you make to the source code will immediately be reflected in the installed CLI - perfect for development!

#### 3. Verify installation

```bash
# Check that accredit is available
accredit --version
accredit --help

# Test a command
accredit local --help
```

#### 4. Upgrading/Reinstalling

```bash
# Reinstall after making changes
pipx reinstall accredit

# Or force reinstall
pipx uninstall accredit
pipx install -e /Users/rutvikrj26/Desktop/cpd_events/cli
```

#### 5. Uninstallation

```bash
pipx uninstall accredit
```

---

### Alternative 1: Install with Poetry

```bash
cd cli
poetry install

# Use with poetry run
poetry run accredit --help

# Or activate the virtualenv
poetry shell
accredit --help
```

---

### Alternative 2: Install with pip (Editable)

```bash
cd cli
pip install -e .

# Now accredit is available globally
accredit --help
```

---

## Usage

Once installed, the `accredit` command is available globally in your terminal.

### Available Commands

```bash
# Show help
accredit --help

# Show version
accredit --version

# Local development commands
accredit local setup      # Install dependencies and migrate database
accredit local up         # Start backend and frontend servers
accredit local logs       # Tail server logs
accredit local shell      # Open Django shell
```

---

## Troubleshooting

### Command not found: accredit

If you installed with pipx:
```bash
# Ensure pipx path is in your shell
pipx ensurepath

# Restart your terminal or reload shell config
source ~/.bashrc  # or ~/.zshrc
```

If you installed with pip:
```bash
# Check if installation directory is in PATH
which accredit

# If not found, add pip's bin directory to PATH
export PATH="$HOME/.local/bin:$PATH"  # Linux
export PATH="$HOME/Library/Python/3.x/bin:$PATH"  # macOS
```

### Changes not reflecting (editable mode)

```bash
# Reinstall with pipx
pipx reinstall accredit

# Or with pip
pip install -e . --force-reinstall --no-deps
```

### Permission denied

```bash
# Don't use sudo with pipx or pip --user
# If you did, uninstall and reinstall without sudo
pipx uninstall accredit
pipx install -e .
```

---

## Development Workflow

### Making Changes

1. Edit code in `accredit/` directory
2. Changes are immediately available (editable mode)
3. Test: `accredit --help`

### Adding New Commands

1. Create a new file in `accredit/commands/`
2. Define commands using `@click.command()` or `@click.group()`
3. Import and register in `accredit/main.py`

Example:
```python
# accredit/commands/deploy.py
import click

@click.group()
def deploy():
    """Deployment commands."""
    pass

@deploy.command()
def production():
    """Deploy to production."""
    click.echo("Deploying to production...")

# accredit/main.py
from accredit.commands import deploy

cli.add_command(deploy.deploy)
```

### Running Tests

```bash
cd cli
poetry run pytest
```

### Code Formatting

```bash
poetry run black accredit/
poetry run ruff check accredit/
```

---

## Comparison: pipx vs Poetry vs pip

| Feature | pipx | Poetry | pip |
|---------|------|--------|-----|
| Isolated environment | ✅ | ✅ | ❌ |
| Global CLI access | ✅ | ❌ (needs `poetry run`) | ✅ |
| Editable mode | ✅ | ✅ | ✅ |
| Easy uninstall | ✅ | ✅ | ⚠️ |
| Best for | Production use | Development | Quick testing |

**Recommendation**: Use **pipx** for daily use, **Poetry** for development and testing.

---

## Next Steps

After installation, run:

```bash
# Set up the CPD Events project
accredit local setup

# Start development servers
accredit local up

# View logs
accredit local logs
```

For more information, see [README.md](README.md)
