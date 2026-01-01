#!/usr/bin/env python3
"""Local development commands."""

import subprocess
import os
import signal
import sys
from pathlib import Path

import click
from rich.console import Console

console = Console()

# Determine Repo Root
# cli/accredit/commands/local.py -> cli/accredit/commands -> cli/accredit -> cli -> root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"
CLI_DIR = REPO_ROOT / ".cli"
LOGS_DIR = CLI_DIR / "logs"
PIDS_DIR = CLI_DIR / "pids"

def ensure_dirs():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    PIDS_DIR.mkdir(parents=True, exist_ok=True)

def start_process(name, cmd, cwd, log_file, pid_file):
    with open(log_file, "w") as out:
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=out,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid  # Create new session
        )
    with open(pid_file, "w") as f:
        f.write(str(process.pid))
    return process

def is_running(pid_file):
    if not pid_file.exists():
        return False
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0) # Check if process exists
        return True
    except (ValueError, OSError):
        return False

@click.group(invoke_without_command=True)
@click.pass_context
def local(ctx):
    """Local development commands."""
    # If no subcommand is provided, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

@local.command()
@click.option('--backend', is_flag=True, help='Start only the backend service')
@click.option('--frontend', is_flag=True, help='Start only the frontend service')
def up(backend, frontend):
    """Start local development services (Backend + Frontend by default)."""
    ensure_dirs()

    # If no flags specified, start both
    start_backend = backend or (not backend and not frontend)
    start_frontend = frontend or (not backend and not frontend)

    # Backend
    if start_backend:
        backend_pid = PIDS_DIR / "backend.pid"
        if is_running(backend_pid):
            console.print("[yellow]Backend is already running.[/yellow]")
        else:
            console.print("[green]Starting Backend...[/green]")
            start_process(
                "backend",
                ["poetry", "run", "python", "src/manage.py", "runserver"],
                BACKEND_DIR,
                LOGS_DIR / "backend.log",
                backend_pid
            )

    # Frontend
    if start_frontend:
        frontend_pid = PIDS_DIR / "frontend.pid"
        if is_running(frontend_pid):
            console.print("[yellow]Frontend is already running.[/yellow]")
        else:
            console.print("[green]Starting Frontend...[/green]")
            start_process(
                "frontend",
                ["npm", "run", "dev"],
                FRONTEND_DIR,
                LOGS_DIR / "frontend.log",
                frontend_pid
            )

    console.print(f"[bold green]Services started![/bold green] Logs are being written to {LOGS_DIR}")
    console.print("Run [bold cyan]accredit local logs[/bold cyan] to follow them.")

@local.command()
@click.option('--backend', is_flag=True, help='Show only backend logs')
@click.option('--frontend', is_flag=True, help='Show only frontend logs')
def logs(backend, frontend):
    """Follow logs of running services."""
    ensure_dirs()
    backend_log = LOGS_DIR / "backend.log"
    frontend_log = LOGS_DIR / "frontend.log"

    # Ensure files exist before tailing
    backend_log.touch(exist_ok=True)
    frontend_log.touch(exist_ok=True)

    # Determine which logs to tail
    logs_to_tail = []
    if backend or (not backend and not frontend):
        logs_to_tail.append(str(backend_log))
    if frontend or (not backend and not frontend):
        logs_to_tail.append(str(frontend_log))

    console.print(f"[blue]Tailing logs from {', '.join(logs_to_tail)}...[/blue]")
    try:
        subprocess.run(["tail", "-f"] + logs_to_tail)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped following logs.[/yellow]")

@local.command()
@click.option('--backend', is_flag=True, help='Stop only the backend service')
@click.option('--frontend', is_flag=True, help='Stop only the frontend service')
def down(backend, frontend):
    """Stop local development services."""
    ensure_dirs()

    # If no flags specified, stop both
    stop_backend = backend or (not backend and not frontend)
    stop_frontend = frontend or (not backend and not frontend)

    stopped_any = False

    # Stop Backend
    if stop_backend:
        backend_pid = PIDS_DIR / "backend.pid"
        if is_running(backend_pid):
            try:
                pid = int(backend_pid.read_text().strip())
                os.killpg(os.getpgid(pid), signal.SIGTERM)
                backend_pid.unlink()
                console.print("[green]Backend stopped.[/green]")
                stopped_any = True
            except (ValueError, OSError, ProcessLookupError) as e:
                console.print(f"[red]Error stopping backend: {e}[/red]")
                if backend_pid.exists():
                    backend_pid.unlink()
        else:
            console.print("[yellow]Backend is not running.[/yellow]")

    # Stop Frontend
    if stop_frontend:
        frontend_pid = PIDS_DIR / "frontend.pid"
        if is_running(frontend_pid):
            try:
                pid = int(frontend_pid.read_text().strip())
                os.killpg(os.getpgid(pid), signal.SIGTERM)
                frontend_pid.unlink()
                console.print("[green]Frontend stopped.[/green]")
                stopped_any = True
            except (ValueError, OSError, ProcessLookupError) as e:
                console.print(f"[red]Error stopping frontend: {e}[/red]")
                if frontend_pid.exists():
                    frontend_pid.unlink()
        else:
            console.print("[yellow]Frontend is not running.[/yellow]")

    if stopped_any:
        console.print("[bold green]Services stopped successfully.[/bold green]")

@local.command()
def status():
    """Check status of local development services."""
    ensure_dirs()

    backend_pid = PIDS_DIR / "backend.pid"
    frontend_pid = PIDS_DIR / "frontend.pid"

    console.print("[bold]Service Status:[/bold]\n")

    # Backend status
    if is_running(backend_pid):
        pid = backend_pid.read_text().strip()
        console.print(f"[green]✓ Backend: Running (PID: {pid})[/green]")
        console.print(f"  URL: http://localhost:8000")
        console.print(f"  Log: {LOGS_DIR / 'backend.log'}")
    else:
        console.print("[red]✗ Backend: Stopped[/red]")

    # Frontend status
    if is_running(frontend_pid):
        pid = frontend_pid.read_text().strip()
        console.print(f"[green]✓ Frontend: Running (PID: {pid})[/green]")
        console.print(f"  URL: http://localhost:5173")
        console.print(f"  Log: {LOGS_DIR / 'frontend.log'}")
    else:
        console.print("[red]✗ Frontend: Stopped[/red]")

@local.command()
def shell():
    """Open Django shell for the backend."""
    console.print("[green]Opening Django Shell...[/green]")
    try:
        subprocess.run(
            ["poetry", "run", "python", "src/manage.py", "shell"],
            cwd=BACKEND_DIR,
            check=False
        )
    except KeyboardInterrupt:
        pass

@local.command()
def setup():
    """Run initial setup (install dependencies, migrate)."""
    console.print("[bold]Running setup...[/bold]")

    # Backend Setup
    console.print("[cyan]Backend: Installing dependencies...[/cyan]")
    subprocess.run(["poetry", "install"], cwd=BACKEND_DIR)

    console.print("[cyan]Backend: Running migrations...[/cyan]")
    subprocess.run(["poetry", "run", "python", "src/manage.py", "migrate"], cwd=BACKEND_DIR)

    # Frontend Setup
    console.print("[cyan]Frontend: Installing dependencies...[/cyan]")
    subprocess.run(["npm", "install"], cwd=FRONTEND_DIR)

    console.print("[bold green]Setup complete![/bold green]")
