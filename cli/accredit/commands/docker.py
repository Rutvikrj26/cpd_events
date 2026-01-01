#!/usr/bin/env python3
"""Docker orchestration commands."""

import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console

console = Console()

# Determine CLI directory
# cli/accredit/commands/docker.py -> cli/accredit/commands -> cli/accredit -> cli
CLI_DIR = Path(__file__).resolve().parent.parent.parent


@click.group()
def docker():
    """Docker orchestration commands."""
    pass


@docker.command()
@click.option('--build', is_flag=True, help='Build images before starting')
@click.option('--detach', '-d', is_flag=True, help='Run in detached mode')
def up(build, detach):
    """Start development services with Docker Compose."""
    console.print("[cyan]Starting Docker services...[/cyan]")

    cmd = ["docker-compose", "up"]

    if build:
        cmd.append("--build")

    if detach:
        cmd.append("-d")

    try:
        subprocess.run(cmd, cwd=CLI_DIR, check=True)

        if detach:
            console.print("[green]✓ Services started in background[/green]")
            console.print("\nServices running:")
            console.print("  • PostgreSQL:      localhost:5432")
            console.print("  • Cloud Tasks:     localhost:8123")
            console.print("  • Cloud Storage:   localhost:4443")
            console.print("  • Backend:         localhost:8000")
            console.print("\nView logs: [cyan]accredit docker logs[/cyan]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Failed to start services: {e}[/red]")
        sys.exit(1)


@docker.command()
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.argument('service', required=False)
def logs(follow, service):
    """View Docker Compose logs."""
    cmd = ["docker-compose", "logs"]

    if follow:
        cmd.append("-f")

    if service:
        cmd.append(service)

    try:
        subprocess.run(cmd, cwd=CLI_DIR, check=True)
    except subprocess.CalledProcessError:
        pass  # User interrupted with Ctrl+C
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped following logs[/yellow]")


@docker.command()
@click.option('--volumes', '-v', is_flag=True, help='Remove volumes as well')
def down(volumes):
    """Stop and remove Docker services."""
    console.print("[yellow]Stopping Docker services...[/yellow]")

    cmd = ["docker-compose", "down"]

    if volumes:
        cmd.append("-v")
        console.print("[yellow]⚠ This will delete all data (databases, uploads, etc.)[/yellow]")

    try:
        subprocess.run(cmd, cwd=CLI_DIR, check=True)
        console.print("[green]✓ Services stopped[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Failed to stop services: {e}[/red]")
        sys.exit(1)


@docker.command()
def ps():
    """List running Docker services."""
    try:
        subprocess.run(["docker-compose", "ps"], cwd=CLI_DIR, check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Failed to list services: {e}[/red]")
        sys.exit(1)


@docker.command()
@click.argument('service')
@click.argument('command', nargs=-1, required=True)
def exec(service, command):
    """Execute a command in a running service container.

    Example: accredit docker exec backend python src/manage.py migrate
    """
    cmd = ["docker-compose", "exec", service] + list(command)

    try:
        subprocess.run(cmd, cwd=CLI_DIR, check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Command failed: {e}[/red]")
        sys.exit(1)


@docker.command()
def init():
    """Initialize Docker environment (GCS bucket, migrations, etc.)."""
    console.print("[cyan]Initializing Docker environment...[/cyan]")

    # Check if services are running
    result = subprocess.run(
        ["docker-compose", "ps", "-q"],
        cwd=CLI_DIR,
        capture_output=True,
        text=True
    )

    if not result.stdout.strip():
        console.print("[yellow]Services not running. Starting them first...[/yellow]")
        subprocess.run(["docker-compose", "up", "-d"], cwd=CLI_DIR, check=True)
        console.print("[green]Waiting for services to be ready...[/green]")
        subprocess.run(["sleep", "5"])

    # Initialize GCS emulator bucket
    console.print("[cyan]1. Initializing GCS emulator bucket...[/cyan]")
    try:
        subprocess.run(
            ["docker-compose", "exec", "backend", "python", "scripts/init_gcs_emulator.py"],
            cwd=CLI_DIR,
            check=True
        )
        console.print("[green]✓ GCS bucket created[/green]")
    except subprocess.CalledProcessError:
        console.print("[yellow]⚠ GCS initialization failed (may already exist)[/yellow]")

    # Run migrations
    console.print("[cyan]2. Running database migrations...[/cyan]")
    try:
        subprocess.run(
            ["docker-compose", "exec", "backend", "poetry", "run", "python", "src/manage.py", "migrate"],
            cwd=CLI_DIR,
            check=True
        )
        console.print("[green]✓ Migrations complete[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Migrations failed: {e}[/red]")
        sys.exit(1)

    console.print("\n[bold green]✓ Docker environment initialized successfully![/bold green]")
    console.print("\nNext steps:")
    console.print("  • Create superuser: [cyan]accredit docker exec backend poetry run python src/manage.py createsuperuser[/cyan]")
    console.print("  • Access API: [cyan]http://localhost:8000[/cyan]")


@docker.command()
def restart():
    """Restart all Docker services."""
    console.print("[yellow]Restarting Docker services...[/yellow]")

    try:
        subprocess.run(["docker-compose", "restart"], cwd=CLI_DIR, check=True)
        console.print("[green]✓ Services restarted[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Failed to restart services: {e}[/red]")
        sys.exit(1)


@docker.command(name='prod-up')
@click.option('--build', is_flag=True, help='Build images before starting')
@click.option('--detach', '-d', is_flag=True, help='Run in detached mode')
def prod_up(build, detach):
    """Start production services with Docker Compose."""
    console.print("[cyan]Starting production Docker services...[/cyan]")

    cmd = ["docker-compose", "-f", "docker-compose.prod.yml", "up"]

    if build:
        cmd.append("--build")

    if detach:
        cmd.append("-d")

    try:
        subprocess.run(cmd, cwd=CLI_DIR, check=True)

        if detach:
            console.print("[green]✓ Production services started[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Failed to start production services: {e}[/red]")
        sys.exit(1)


@docker.command(name='prod-down')
@click.option('--volumes', '-v', is_flag=True, help='Remove volumes as well')
def prod_down(volumes):
    """Stop production Docker services."""
    console.print("[yellow]Stopping production Docker services...[/yellow]")

    cmd = ["docker-compose", "-f", "docker-compose.prod.yml", "down"]

    if volumes:
        cmd.append("-v")

    try:
        subprocess.run(cmd, cwd=CLI_DIR, check=True)
        console.print("[green]✓ Production services stopped[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Failed to stop production services: {e}[/red]")
        sys.exit(1)
