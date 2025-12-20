import typer
import subprocess
import os
import signal
import sys
from pathlib import Path
from rich.console import Console

app = typer.Typer()
console = Console()

# Determine Repo Root
# cli/commands/local.py -> cli/commands -> cli -> root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
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

@app.command()
def up():
    """Start local development services (Backend + Frontend)."""
    ensure_dirs()
    
    # Backend
    backend_pid = PIDS_DIR / "backend.pid"
    if is_running(backend_pid):
        console.print("[yellow]Backend is already running.[/yellow]")
    else:
        console.print("[green]Starting setup: Backend...[/green]")
        start_process(
            "backend",
            ["poetry", "run", "python", "src/manage.py", "runserver"],
            BACKEND_DIR,
            LOGS_DIR / "backend.log",
            backend_pid
        )

    # Frontend
    frontend_pid = PIDS_DIR / "frontend.pid"
    if is_running(frontend_pid):
        console.print("[yellow]Frontend is already running.[/yellow]")
    else:
        console.print("[green]Starting setup: Frontend...[/green]")
        start_process(
            "frontend",
            ["npm", "run", "dev"],
            FRONTEND_DIR,
            LOGS_DIR / "frontend.log",
            frontend_pid
        )
    
    console.print(f"[bold green]Services started![/bold green] Logs are being written to {LOGS_DIR}")
    console.print("Run [bold cyan]cli local logs[/bold cyan] to follow them.")

@app.command()
def logs():
    """Follow logs of running services."""
    ensure_dirs()
    backend_log = LOGS_DIR / "backend.log"
    frontend_log = LOGS_DIR / "frontend.log"
    
    # Ensure files exist before tailing
    backend_log.touch(exist_ok=True)
    frontend_log.touch(exist_ok=True)
    
    console.print(f"[blue]Tailing logs from {backend_log} and {frontend_log}...[/blue]")
    try:
        subprocess.run(["tail", "-f", str(backend_log), str(frontend_log)])
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped following logs.[/yellow]")

@app.command()
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

@app.command()
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
