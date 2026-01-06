#!/usr/bin/env python3
"""Cloud deployment and management commands for GCP."""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from accredit.utils.config import get_current_env, get_config_value, set_config_value
from accredit.utils.state import (
    push_deployment_state,
    pull_deployment_state,
    get_deployment_history,
    get_latest_deployment,
    ensure_state_bucket,
)

console = Console()

# Determine paths
CLI_DIR = Path(__file__).resolve().parent.parent.parent
INFRA_DIR = CLI_DIR.parent / "infra" / "gcp"
FRONTEND_DIR = CLI_DIR.parent / "frontend"
BACKEND_DIR = CLI_DIR.parent / "backend"


def get_default_env():
    """Get the default environment from config."""
    return get_current_env()


def get_env_dir(environment):
    """Get the environment directory path."""
    env_dir = INFRA_DIR / "environments" / environment
    if not env_dir.exists():
        console.print(f"[red]✗ Environment '{environment}' not found at {env_dir}[/red]")
        sys.exit(1)
    return env_dir


def run_terraform_command(env_dir, command, auto_approve=False):
    """Run a terraform command in the specified environment directory."""
    cmd = ["terraform"] + command

    if auto_approve and command[0] in ["apply", "destroy"]:
        cmd.append("-auto-approve")

    try:
        subprocess.run(cmd, cwd=env_dir, check=True)
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Terraform command failed: {e}[/red]")
        return False


@click.group()
def cloud():
    """Cloud deployment and management commands for GCP."""
    pass


@cloud.command()
@click.option('--env', '-e', default=None, help='Environment (dev/staging/prod). Defaults to configured environment.')
def sync(env):
    """Sync deployment state from GCS.
    
    Use this command on a new system to pull the latest deployment state
    from the remote GCS bucket. This allows you to see deployment history
    and continue managing deployments from any machine.
    """
    env = env or get_default_env()
    project_id = get_config_value("project_id")
    
    if not project_id:
        console.print("[red]✗ Project ID not configured. Run: accredit setup init[/red]")
        sys.exit(1)

    console.print(f"[cyan]Syncing deployment state from GCS for {env}...[/cyan]")
    
    try:
        state = pull_deployment_state(project_id)
        
        frontend_count = len(state.get("frontend", []))
        backend_count = len(state.get("backend", []))
        
        # Update last_sync timestamp
        set_config_value("last_sync", datetime.now().isoformat())
        
        console.print(f"[green]✓ Synced deployment state from {project_id}[/green]")
        console.print(f"  Frontend deployments: {frontend_count}")
        console.print(f"  Backend deployments: {backend_count}")
        
        # Show latest deployment for each
        latest_frontend = get_latest_deployment(project_id, "frontend")
        latest_backend = get_latest_deployment(project_id, "backend")
        
        if latest_frontend:
            console.print(f"\n[cyan]Latest frontend:[/cyan] {latest_frontend.get('timestamp', 'N/A')[:19]} → {latest_frontend.get('target', 'N/A')}")
        if latest_backend:
            console.print(f"[cyan]Latest backend:[/cyan] {latest_backend.get('timestamp', 'N/A')[:19]} → {latest_backend.get('url', 'N/A')}")
            
    except Exception as e:
        console.print(f"[red]✗ Sync failed: {e}[/red]")
        sys.exit(1)


@cloud.command()
@click.option('--project-id', '-p', required=True, help='GCP Project ID')
@click.option('--region', '-r', default='us-central1', help='GCP Region')
def bootstrap(project_id, region):
    """Bootstrap GCP project for deployment (one-time setup).
    
    Enables required APIs and creates the Terraform state bucket.
    This is idempotent - safe to run multiple times.
    """
    console.print(f"[cyan]Bootstrapping GCP project: {project_id}[/cyan]\n")
    
    # Set gcloud project
    console.print("[cyan]Setting gcloud project...[/cyan]")
    subprocess.run(["gcloud", "config", "set", "project", project_id], check=True)
    
    # Enable required APIs
    apis = [
        "compute.googleapis.com",
        "run.googleapis.com",
        "sqladmin.googleapis.com",
        "cloudtasks.googleapis.com",
        "secretmanager.googleapis.com",
        "servicenetworking.googleapis.com",
        "cloudbuild.googleapis.com",
        "storage.googleapis.com",
        "vpcaccess.googleapis.com",
    ]
    
    console.print("[cyan]Enabling required APIs (this may take a minute)...[/cyan]")
    try:
        subprocess.run(
            ["gcloud", "services", "enable"] + apis,
            check=True
        )
        console.print("[green]✓ APIs enabled[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Failed to enable APIs: {e}[/red]")
        sys.exit(1)
    
    # Create Terraform state bucket
    state_bucket = f"gs://{project_id}-terraform-state"
    console.print(f"[cyan]Creating Terraform state bucket: {state_bucket}[/cyan]")
    
    # Check if bucket exists
    result = subprocess.run(
        ["gsutil", "ls", "-b", state_bucket],
        capture_output=True
    )
    
    if result.returncode != 0:
        try:
            subprocess.run(["gsutil", "mb", "-l", region, state_bucket], check=True)
            subprocess.run(["gsutil", "versioning", "set", "on", state_bucket], check=True)
            console.print("[green]✓ State bucket created[/green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]✗ Failed to create state bucket: {e}[/red]")
            sys.exit(1)
    else:
        console.print("[yellow]State bucket already exists[/yellow]")
    
    # Save to CLI config
    set_config_value("project_id", project_id)
    set_config_value("region", region)
    
    console.print(f"\n[bold green]✓ Bootstrap complete![/bold green]")
    console.print(f"\nNext step: [cyan]accredit cloud up --env dev[/cyan]")


@cloud.command()
@click.option('--env', '-e', default=None, help='Environment (dev/staging/prod)')
@click.option('--auto-approve', '-y', is_flag=True, help='Skip confirmation prompts')
@click.option('--skip-backend', is_flag=True, help='Skip backend build and deploy')
def up(env, auto_approve, skip_backend):
    """Deploy full infrastructure and application.
    
    Runs: terraform init → terraform apply → backend build → backend deploy
    """
    env = env or get_default_env()
    project_id = get_config_value("project_id")
    
    if not project_id:
        console.print("[red]✗ Project ID not configured. Run: accredit cloud bootstrap --project-id YOUR_PROJECT[/red]")
        sys.exit(1)
    
    env_dir = get_env_dir(env)
    
    console.print(f"[bold cyan]═══ Deploying {env} environment ═══[/bold cyan]\n")
    
    # Step 1: Terraform init
    console.print("[cyan]Step 1/4: Initializing Terraform...[/cyan]")
    try:
        subprocess.run(["terraform", "init"], cwd=env_dir, check=True)
        console.print("[green]✓ Terraform initialized[/green]\n")
    except subprocess.CalledProcessError:
        console.print("[red]✗ Terraform init failed[/red]")
        sys.exit(1)
    
    # Step 2: Terraform apply
    console.print("[cyan]Step 2/4: Applying infrastructure...[/cyan]")
    cmd = ["terraform", "apply"]
    if auto_approve:
        cmd.append("-auto-approve")
    
    try:
        subprocess.run(cmd, cwd=env_dir, check=True)
        console.print("[green]✓ Infrastructure created[/green]\n")
    except subprocess.CalledProcessError:
        console.print("[red]✗ Terraform apply failed[/red]")
        sys.exit(1)
    
    if skip_backend:
        console.print("[yellow]Skipping backend deployment (--skip-backend)[/yellow]")
    else:
        # Step 3: Build backend image
        console.print("[cyan]Step 3/4: Building backend Docker image...[/cyan]")
        
        # Configure docker for Artifact Registry
        region = get_config_value("region") or "us-central1"
        ar_repo = f"{region}-docker.pkg.dev"
        try:
            subprocess.run(
                ["gcloud", "auth", "configure-docker", ar_repo, "--quiet"],
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError:
            console.print(f"[yellow]⚠ Failed to configure docker for {ar_repo}, continuing...[/yellow]")

        # Generate tag based on timestamp
        tag = datetime.now().strftime("%Y%m%d-%H%M%S")
        image_name = f"{region}-docker.pkg.dev/{project_id}/backend/cpd-backend:{tag}"
        latest_image_name = f"{region}-docker.pkg.dev/{project_id}/backend/cpd-backend:latest"
        
        try:
            # Build and push with specific tag and latest
            # We use 'docker build' + 'docker push' or 'gcloud builds submit'
            # gcloud builds submit is easier as it handles auth and remote build
            subprocess.run(
                ["gcloud", "builds", "submit", "--tag", image_name, "--tag", latest_image_name, "."],
                cwd=BACKEND_DIR,
                check=True
            )
            console.print(f"[green]✓ Backend image built and pushed: {image_name}[/green]\n")
        except subprocess.CalledProcessError:
            console.print("[red]✗ Backend build failed[/red]")
            sys.exit(1)
        
        # Step 4: Deploy to Cloud Run
        console.print("[cyan]Step 4/4: Deploying to Cloud Run...[/cyan]")
        service_name = f"cpd-events-{env}"
        
        try:
            subprocess.run(
                [
                    "gcloud", "run", "deploy", service_name,
                    "--image", latest_image_name,
                    "--region", region,
                    "--platform", "managed",
                    "--allow-unauthenticated",
                    "--quiet"  # Non-interactive
                ],
                check=True
            )
            console.print("[green]✓ Backend deployed to Cloud Run[/green]\n")
            
            # Get service URL
            result = subprocess.run(
                ["terraform", "output", "-raw", "backend_url"],
                cwd=env_dir,
                capture_output=True,
                text=True
            )
            backend_url = result.stdout.strip() if result.returncode == 0 else "N/A"
            
            # Push deployment state
            record = {
                "environment": env,
                "image": image_name,
                "tag": tag,
                "service": service_name,
                "url": backend_url,
                "status": "success",
            }
            push_deployment_state(project_id, "backend", record)
            
        except subprocess.CalledProcessError:
            console.print("[red]✗ Cloud Run deployment failed[/red]")
            sys.exit(1)
    
    # Get outputs
    console.print("[cyan]Getting deployment outputs...[/cyan]")
    result = subprocess.run(
        ["terraform", "output", "-raw", "backend_url"],
        cwd=env_dir,
        capture_output=True,
        text=True
    )
    backend_url = result.stdout.strip() if result.returncode == 0 else "N/A"
    
    console.print(f"\n[bold green]═══ Deployment Complete! ═══[/bold green]")
    console.print(f"\n[cyan]Backend URL:[/cyan] {backend_url}")
    console.print(f"\n[dim]To tear down: accredit cloud down --env {env} --auto-approve[/dim]")


@cloud.command()
@click.option('--env', '-e', default=None, help='Environment (dev/staging/prod)')
@click.option('--auto-approve', '-y', is_flag=True, help='Skip confirmation prompts')
@click.option('--include-state', is_flag=True, help='Also delete Terraform state bucket')
def down(env, auto_approve, include_state):
    """Tear down all infrastructure.
    
    Destroys all Terraform-managed resources. Use --include-state to also
    delete the Terraform state bucket (irreversible).
    """
    env = env or get_default_env()
    project_id = get_config_value("project_id")
    
    if not project_id:
        console.print("[red]✗ Project ID not configured[/red]")
        sys.exit(1)
    
    env_dir = get_env_dir(env)
    
    console.print(f"[bold red]═══ Tearing Down {env} Environment ═══[/bold red]\n")
    
    if not auto_approve:
        console.print("[yellow]⚠ This will DESTROY all infrastructure in this environment![/yellow]")
        if not click.confirm("Are you sure you want to continue?"):
            console.print("[yellow]Cancelled[/yellow]")
            return
    
    # Step 1: Terraform destroy
    console.print("[cyan]Step 1/2: Destroying infrastructure...[/cyan]")
    cmd = ["terraform", "destroy"]
    if auto_approve:
        cmd.append("-auto-approve")
    
    try:
        subprocess.run(cmd, cwd=env_dir, check=True)
        console.print("[green]✓ Infrastructure destroyed[/green]\n")
    except subprocess.CalledProcessError:
        console.print("[red]✗ Terraform destroy failed[/red]")
        sys.exit(1)
    
    # Step 2: Optionally delete state bucket
    if include_state:
        console.print("[cyan]Step 2/2: Deleting state bucket...[/cyan]")
        state_bucket = f"gs://{project_id}-terraform-state"
        
        try:
            subprocess.run(
                ["gsutil", "-m", "rm", "-r", state_bucket],
                check=True
            )
            console.print("[green]✓ State bucket deleted[/green]")
        except subprocess.CalledProcessError:
            console.print("[yellow]⚠ Could not delete state bucket (may not exist)[/yellow]")
    else:
        console.print("[dim]Step 2/2: Skipping state bucket deletion (use --include-state to delete)[/dim]")
    
    console.print(f"\n[bold green]═══ Teardown Complete! ═══[/bold green]")
    console.print(f"\n[dim]To redeploy: accredit cloud up --env {env} --auto-approve[/dim]")


@cloud.group()
def infra():
    """Infrastructure management commands (Terraform)."""
    pass


@infra.command()
@click.option('--env', '-e', default=None, help='Environment (dev/staging/prod). Defaults to configured environment.')
def init(env):
    """Initialize Terraform for an environment."""
    env = env or get_default_env()
    console.print(f"[cyan]Initializing Terraform for {env}...[/cyan]")

    env_dir = get_env_dir(env)

    if run_terraform_command(env_dir, ["init"]):
        console.print(f"[green]✓ Terraform initialized for {env}[/green]")
    else:
        sys.exit(1)


@infra.command()
@click.option('--env', '-e', default=None, help='Environment (dev/staging/prod). Defaults to configured environment.')
@click.option('--out', '-o', help='Save plan to file')
def plan(env, out):
    """Show Terraform execution plan."""
    env = env or get_default_env()
    console.print(f"[cyan]Planning infrastructure changes for {env}...[/cyan]")

    env_dir = get_env_dir(env)

    # Check if tfvars exists
    tfvars_file = env_dir / "terraform.tfvars"
    if not tfvars_file.exists():
        console.print(f"[yellow]⚠ terraform.tfvars not found. Copy from terraform.tfvars.example first.[/yellow]")
        console.print(f"[cyan]cd {env_dir} && cp terraform.tfvars.example terraform.tfvars[/cyan]")
        sys.exit(1)

    cmd = ["plan"]
    if out:
        cmd.extend(["-out", out])

    if run_terraform_command(env_dir, cmd):
        console.print(f"[green]✓ Plan complete[/green]")
    else:
        sys.exit(1)


@infra.command()
@click.option('--env', '-e', default=None, help='Environment (dev/staging/prod). Defaults to configured environment.')
@click.option('--auto-approve', is_flag=True, help='Skip confirmation prompt')
def apply(env, auto_approve):
    """Apply Terraform infrastructure changes."""
    env = env or get_default_env()
    console.print(f"[cyan]Applying infrastructure changes for {env}...[/cyan]")

    if not auto_approve:
        console.print("[yellow]⚠ This will create/modify cloud resources and may incur costs.[/yellow]")

    env_dir = get_env_dir(env)

    # Check if tfvars exists
    tfvars_file = env_dir / "terraform.tfvars"
    if not tfvars_file.exists():
        console.print(f"[yellow]⚠ terraform.tfvars not found. Copy from terraform.tfvars.example first.[/yellow]")
        console.print(f"[cyan]cd {env_dir} && cp terraform.tfvars.example terraform.tfvars[/cyan]")
        sys.exit(1)

    if run_terraform_command(env_dir, ["apply"], auto_approve):
        console.print(f"[bold green]✓ Infrastructure deployed successfully for {env}![/bold green]")
        console.print("\n[cyan]Next steps:[/cyan]")
        console.print(f"  • Deploy backend:  [cyan]accredit cloud backend deploy[/cyan]")
        console.print(f"  • Deploy frontend: [cyan]accredit cloud frontend deploy[/cyan]")
    else:
        sys.exit(1)


@infra.command()
@click.option('--env', '-e', default=None, help='Environment (dev/staging/prod). Defaults to configured environment.')
@click.option('--auto-approve', is_flag=True, help='Skip confirmation prompt')
def destroy(env, auto_approve):
    """Destroy Terraform-managed infrastructure."""
    env = env or get_default_env()
    console.print(f"[red]⚠ This will DESTROY all infrastructure for {env}![/red]")

    if not auto_approve:
        if not click.confirm("Are you sure you want to continue?"):
            console.print("[yellow]Cancelled[/yellow]")
            return

    env_dir = get_env_dir(env)

    if run_terraform_command(env_dir, ["destroy"], auto_approve):
        console.print(f"[green]✓ Infrastructure destroyed for {env}[/green]")
    else:
        sys.exit(1)


@infra.command()
@click.option('--env', '-e', default=None, help='Environment (dev/staging/prod). Defaults to configured environment.')
@click.argument('output_name', required=False)
def output(env, output_name):
    """Show Terraform outputs."""
    env = env or get_default_env()
    env_dir = get_env_dir(env)

    cmd = ["output"]
    if output_name:
        cmd.extend(["-raw", output_name])

    run_terraform_command(env_dir, cmd)


@infra.command()
@click.option('--env', '-e', default=None, help='Environment (dev/staging/prod). Defaults to configured environment.')
def validate(env):
    """Validate Terraform configuration."""
    env = env or get_default_env()
    console.print(f"[cyan]Validating Terraform configuration for {env}...[/cyan]")

    env_dir = get_env_dir(env)

    if run_terraform_command(env_dir, ["validate"]):
        console.print(f"[green]✓ Configuration is valid[/green]")
    else:
        sys.exit(1)


@cloud.group()
def backend():
    """Backend deployment commands."""
    pass


@backend.command()
@click.option('--env', '-e', default=None, help='Environment (dev/staging/prod). Defaults to configured environment.')
@click.option('--tag', '-t', default=None, help='Docker image tag (defaults to timestamp)')
def build(env, tag):
    """Build and push backend Docker image to Artifact Registry."""
    env = env or get_default_env()
    console.print(f"[cyan]Building backend image for {env}...[/cyan]")

    env_dir = get_env_dir(env)

    # Get project ID from Terraform
    result = subprocess.run(
        ["terraform", "output", "-raw", "project_id"],
        cwd=env_dir,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        console.print("[red]✗ Could not get project_id from Terraform. Run 'terraform apply' first.[/red]")
        sys.exit(1)

    project_id = result.stdout.strip()
    
    # Get region
    result = subprocess.run(
        ["terraform", "output", "-raw", "region"],
        cwd=env_dir,
        capture_output=True,
        text=True
    )
    region = result.stdout.strip() if result.returncode == 0 else "us-central1"

    # Configure Artifact Registry path
    tag = tag or datetime.now().strftime("%Y%m%d-%H%M%S")
    image_name = f"{region}-docker.pkg.dev/{project_id}/backend/cpd-backend:{tag}"
    latest_image_name = f"{region}-docker.pkg.dev/{project_id}/backend/cpd-backend:latest"

    console.print(f"[cyan]Building image: {image_name}[/cyan]")
    console.print(f"[dim]Also tagging as: {latest_image_name}[/dim]")

    # Build and push using gcloud
    try:
        subprocess.run(
            ["gcloud", "builds", "submit", "--tag", image_name, "--tag", latest_image_name, "."],
            cwd=BACKEND_DIR,
            check=True
        )
        console.print(f"[green]✓ Image built and pushed: {image_name}[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Build failed: {e}[/red]")
        sys.exit(1)


@backend.command()
@click.option('--env', '-e', default=None, help='Environment (dev/staging/prod). Defaults to configured environment.')
@click.option('--tag', '-t', default='latest', help='Docker image tag')
def deploy(env, tag):
    """Deploy backend to Cloud Run."""
    env = env or get_default_env()
    console.print(f"[cyan]Deploying backend to {env}...[/cyan]")

    env_dir = get_env_dir(env)

    # Get project ID and service name from Terraform
    result = subprocess.run(
        ["terraform", "output", "-raw", "project_id"],
        cwd=env_dir,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        console.print("[red]✗ Could not get project_id. Run 'terraform apply' first.[/red]")
        sys.exit(1)

    project_id = result.stdout.strip()
    service_name = f"cpd-events-{env}"

    # Get region
    result = subprocess.run(
        ["terraform", "output", "-raw", "region"],
        cwd=env_dir,
        capture_output=True,
        text=True
    )
    region = result.stdout.strip() if result.returncode == 0 else "us-central1"
    
    # Artifact Registry image path
    image_name = f"{region}-docker.pkg.dev/{project_id}/backend/cpd-backend:{tag}"

    console.print(f"[cyan]Deploying to Cloud Run service: {service_name}[/cyan]")
    console.print(f"[dim]Using image: {image_name}[/dim]")

    try:
        subprocess.run(
            [
                "gcloud", "run", "deploy", service_name,
                "--image", image_name,
                "--region", region,
                "--platform", "managed",
                "--allow-unauthenticated",
                "--quiet"
            ],
            check=True
        )
        console.print(f"[bold green]✓ Backend deployed successfully![/bold green]")

        # Get service URL
        result = subprocess.run(
            ["terraform", "output", "-raw", "backend_url"],
            cwd=env_dir,
            capture_output=True,
            text=True
        )
        backend_url = result.stdout.strip() if result.returncode == 0 else "unknown"
        if backend_url != "unknown":
            console.print(f"\n[cyan]Backend URL: {backend_url}[/cyan]")

        # Push deployment state
        record = {
            "environment": env,
            "image": image_name,
            "tag": tag,
            "service": service_name,
            "url": backend_url,
            "status": "success",
        }
        push_deployment_state(project_id, "backend", record)
        
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Deployment failed: {e}[/red]")
        sys.exit(1)


@backend.command()
@click.option('--env', '-e', default=None, help='Environment (dev/staging/prod). Defaults to configured environment.')
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.option('--limit', default=100, help='Number of log entries')
def logs(env, follow, limit):
    env = env or get_default_env()
    """View backend Cloud Run logs."""
    env_dir = get_env_dir(env)
    service_name = f"cpd-events-{env}"

    # Get region
    result = subprocess.run(
        ["terraform", "output", "-raw", "region"],
        cwd=env_dir,
        capture_output=True,
        text=True
    )
    region = result.stdout.strip() if result.returncode == 0 else "us-central1"

    cmd = [
        "gcloud", "run", "services", "logs", "read", service_name,
        "--region", region,
        "--limit", str(limit)
    ]

    if follow:
        cmd.append("--follow")

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped following logs[/yellow]")


@backend.command()
@click.option('--env', '-e', default=None, help='Environment (dev/staging/prod). Defaults to configured environment.')
@click.option('--limit', '-n', default=10, help='Number of records to show')
def history(env, limit):
    """Show backend deployment history."""
    env = env or get_default_env()
    project_id = get_config_value("project_id")
    
    if not project_id:
        console.print("[red]✗ Project ID not configured. Run: accredit setup init[/red]")
        sys.exit(1)

    console.print(f"[cyan]Backend deployment history for {env}:[/cyan]\n")
    
    deployments = get_deployment_history(project_id, "backend", limit)
    
    if not deployments:
        console.print("[yellow]No deployments found. Run: accredit cloud sync[/yellow]")
        return

    table = Table()
    table.add_column("Timestamp", style="dim")
    table.add_column("Image", style="cyan")
    table.add_column("Commit", style="green")
    table.add_column("Deployer", style="white")
    table.add_column("Status", style="green")

    for dep in reversed(deployments):  # Most recent first
        if dep.get("environment") == env:
            image = dep.get("image", "N/A")
            # Extract just the tag from the image
            image_tag = image.split(":")[-1] if ":" in image else image
            table.add_row(
                dep.get("timestamp", "N/A")[:19],
                image_tag,
                dep.get("commit", "N/A"),
                dep.get("deployer", "N/A").split("@")[0],
                dep.get("status", "N/A")
            )

    console.print(table)


@cloud.group()
def frontend():
    """Frontend deployment commands."""
    pass


@frontend.command()
@click.option('--env', '-e', default=None, help='Environment (dev/staging/prod). Defaults to configured environment.')
def build(env):
    env = env or get_default_env()
    """Build frontend for production."""
    console.print(f"[cyan]Building frontend for {env}...[/cyan]")

    # Check if frontend directory exists
    if not FRONTEND_DIR.exists():
        console.print(f"[red]✗ Frontend directory not found: {FRONTEND_DIR}[/red]")
        sys.exit(1)

    try:
        # Install dependencies
        console.print("[cyan]Installing dependencies...[/cyan]")
        subprocess.run(["npm", "install"], cwd=FRONTEND_DIR, check=True)

        # Build
        console.print("[cyan]Building production bundle...[/cyan]")
        subprocess.run(["npm", "run", "build"], cwd=FRONTEND_DIR, check=True)

        console.print("[green]✓ Frontend built successfully[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Build failed: {e}[/red]")
        sys.exit(1)


@frontend.command()
@click.option('--env', '-e', default=None, help='Environment (dev/staging/prod). Defaults to configured environment.')
def deploy(env):
    """Deploy frontend to Firebase Hosting or Cloud Storage."""
    env = env or get_default_env()
    console.print(f"[cyan]Deploying frontend to {env}...[/cyan]")

    # Get project ID from config
    project_id = get_config_value("project_id")
    if not project_id:
        console.print("[red]✗ Project ID not configured. Run: accredit setup init[/red]")
        sys.exit(1)

    # Check if frontend directory exists
    if not FRONTEND_DIR.exists():
        console.print(f"[red]✗ Frontend directory not found: {FRONTEND_DIR}[/red]")
        sys.exit(1)

    # Get backend URL from Terraform output
    env_dir = get_env_dir(env)
    result = subprocess.run(
        ["terraform", "output", "-raw", "backend_url"],
        cwd=env_dir,
        capture_output=True,
        text=True
    )

    backend_url = result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else None

    if not backend_url:
        console.print("[yellow]⚠ Could not get backend_url from Terraform. Using .env.prod if available.[/yellow]")

    try:
        # Install dependencies
        console.print("[cyan]Installing dependencies...[/cyan]")
        subprocess.run(["npm", "install"], cwd=FRONTEND_DIR, check=True)

        # Build with environment variables from Terraform
        console.print("[cyan]Building production bundle...[/cyan]")

        # Set build-time environment variables
        build_env = os.environ.copy()
        terraform_keys = set()

        if backend_url:
            # Auto-set API URL from Terraform output
            api_url = f"{backend_url}/api/v1"
            build_env["VITE_API_URL"] = api_url
            console.print(f"  [dim]VITE_API_URL={api_url}[/dim]")

        # Load frontend build vars from Terraform outputs (tfvars source of truth)
        try:
            result = subprocess.run(
                ["terraform", "output", "-json", "frontend_env"],
                cwd=env_dir,
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                frontend_env = json.loads(result.stdout)
                if isinstance(frontend_env, dict):
                    for key, value in frontend_env.items():
                        if value:
                            build_env[key] = value
                            terraform_keys.add(key)
                            console.print(f"  [dim]{key} set from Terraform[/dim]")
        except (json.JSONDecodeError, TypeError):
            console.print("[yellow]⚠ Could not parse frontend_env Terraform output[/yellow]")

        # Load additional vars from .env.prod if exists
        env_prod_file = FRONTEND_DIR / ".env.prod"
        if env_prod_file.exists():
            console.print(f"  [dim]Loading additional vars from .env.prod[/dim]")
            with open(env_prod_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        # Don't override vars set by Terraform or API URL from Terraform
                        if key in terraform_keys:
                            continue
                        if key == "VITE_API_URL" and backend_url:
                            continue
                        build_env[key] = value.strip()

        subprocess.run(["npm", "run", "build"], cwd=FRONTEND_DIR, check=True, env=build_env)

        # Check for Firebase configuration
        firebase_json = FRONTEND_DIR / "firebase.json"
        if firebase_json.exists():
            # Deploy to Firebase Hosting
            console.print("[cyan]Deploying to Firebase Hosting...[/cyan]")
            subprocess.run(["firebase", "deploy", "--only", "hosting", "--project", project_id], cwd=FRONTEND_DIR, check=True)
            target = "firebase"
        else:
            # Deploy to GCS bucket
            bucket_name = f"{project_id}-cpd-events-{env}-frontend"
            console.print(f"[cyan]Uploading to bucket: {bucket_name}[/cyan]")
            
            build_dir = FRONTEND_DIR / "dist"
            subprocess.run(
                ["gsutil", "-m", "rsync", "-r", "-d", str(build_dir), f"gs://{bucket_name}"],
                check=True
            )
            
            # Set cache headers for assets
            subprocess.run(
                ["gsutil", "-m", "setmeta", "-h", "Cache-Control:public, max-age=31536000, immutable",
                 f"gs://{bucket_name}/assets/**"],
                check=False  # May fail if no assets
            )
            
            # Set cache headers for index.html
            subprocess.run(
                ["gsutil", "setmeta", "-h", "Cache-Control:public, max-age=300, must-revalidate",
                 f"gs://{bucket_name}/index.html"],
                check=True
            )
            target = "gcs"

        # Push deployment state
        record = {
            "environment": env,
            "target": target,
            "status": "success",
        }
        push_deployment_state(project_id, "frontend", record)
        
        console.print(f"[bold green]✓ Frontend deployed successfully to {target}![/bold green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Deployment failed: {e}[/red]")
        sys.exit(1)


@frontend.command()
@click.option('--env', '-e', default=None, help='Environment (dev/staging/prod). Defaults to configured environment.')
@click.option('--limit', '-n', default=10, help='Number of records to show')
def history(env, limit):
    """Show frontend deployment history."""
    env = env or get_default_env()
    project_id = get_config_value("project_id")
    
    if not project_id:
        console.print("[red]✗ Project ID not configured. Run: accredit setup init[/red]")
        sys.exit(1)

    console.print(f"[cyan]Frontend deployment history for {env}:[/cyan]\n")
    
    deployments = get_deployment_history(project_id, "frontend", limit)
    
    if not deployments:
        console.print("[yellow]No deployments found. Run: accredit cloud sync[/yellow]")
        return

    table = Table()
    table.add_column("Timestamp", style="dim")
    table.add_column("Target", style="cyan")
    table.add_column("Commit", style="green")
    table.add_column("Deployer", style="white")
    table.add_column("Status", style="green")

    for dep in reversed(deployments):  # Most recent first
        if dep.get("environment") == env:
            table.add_row(
                dep.get("timestamp", "N/A")[:19],  # Truncate microseconds
                dep.get("target", "N/A"),
                dep.get("commit", "N/A"),
                dep.get("deployer", "N/A").split("@")[0],  # Just username
                dep.get("status", "N/A")
            )

    console.print(table)


@cloud.command()
@click.option('--env', '-e', default=None, help='Environment (dev/staging/prod). Defaults to configured environment.')
def status(env):
    env = env or get_default_env()
    """Show deployment status for an environment."""
    console.print(f"[cyan]Checking status for {env}...[/cyan]\n")

    env_dir = get_env_dir(env)

    table = Table(title=f"Deployment Status - {env.upper()}")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Info", style="white")

    # Check Terraform state
    result = subprocess.run(
        ["terraform", "show", "-json"],
        cwd=env_dir,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        table.add_row("Infrastructure", "✓ Deployed", "Terraform state exists")

        # Get outputs
        outputs = {}
        for output_name in ["backend_url", "frontend_url", "frontend_ip_address"]:
            result = subprocess.run(
                ["terraform", "output", "-raw", output_name],
                cwd=env_dir,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                outputs[output_name] = result.stdout.strip()

        if "backend_url" in outputs:
            table.add_row("Backend", "✓ Running", outputs["backend_url"])

        if "frontend_url" in outputs:
            table.add_row("Frontend", "✓ Deployed", outputs["frontend_url"])

        if "frontend_ip_address" in outputs:
            table.add_row("Load Balancer IP", "✓ Active", outputs["frontend_ip_address"])
    else:
        table.add_row("Infrastructure", "✗ Not deployed", "Run: accredit cloud infra apply")

    console.print(table)

    # Show next steps if not fully deployed
    if result.returncode != 0:
        console.print("\n[yellow]To deploy infrastructure:[/yellow]")
        console.print(f"  [cyan]accredit cloud infra init --env {env}[/cyan]")
        console.print(f"  [cyan]accredit cloud infra apply --env {env}[/cyan]")


@cloud.command()
@click.option('--env', '-e', default=None, help='Environment (dev/staging/prod). Defaults to configured environment.')
def ssh(env):
    env = env or get_default_env()
    """SSH into Cloud Run service (requires Cloud Run proxy)."""
    console.print(f"[cyan]Connecting to {env} backend...[/cyan]")

    service_name = f"cpd-events-{env}"

    env_dir = get_env_dir(env)
    result = subprocess.run(
        ["terraform", "output", "-raw", "region"],
        cwd=env_dir,
        capture_output=True,
        text=True
    )
    region = result.stdout.strip() if result.returncode == 0 else "us-central1"

    console.print("[yellow]Note: This requires gcloud auth and appropriate IAM permissions[/yellow]")

    try:
        subprocess.run(
            [
                "gcloud", "run", "services", "proxy", service_name,
                "--region", region
            ],
            check=True
        )
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Connection failed: {e}[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Connection closed[/yellow]")


@cloud.command()
def list_envs():
    """List available environments."""
    console.print("[cyan]Available environments:[/cyan]\n")

    envs_dir = INFRA_DIR / "environments"

    if not envs_dir.exists():
        console.print("[red]✗ No environments directory found[/red]")
        sys.exit(1)

    table = Table()
    table.add_column("Environment", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Path", style="dim")

    for env_path in sorted(envs_dir.iterdir()):
        if env_path.is_dir() and not env_path.name.startswith('.'):
            # Check if terraform state exists
            terraform_dir = env_path / ".terraform"
            status = "✓ Initialized" if terraform_dir.exists() else "Not initialized"

            table.add_row(
                env_path.name,
                status,
                str(env_path.relative_to(CLI_DIR.parent))
            )

    console.print(table)


# =============================================================================
# SECRETS MANAGEMENT
# =============================================================================

@cloud.group()
def secrets():
    """Manage secrets in Google Secret Manager."""
    pass


def get_secret_name(key: str, env: str) -> str:
    """Generate secret name with environment prefix."""
    return f"{env}_{key}".upper()


def parse_env_file(env_file: Path) -> dict:
    """Parse a .env file and return key-value pairs."""
    secrets = {}
    if not env_file.exists():
        return secrets

    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            # Parse KEY=VALUE
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                # Remove quotes if present
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                secrets[key] = value
    return secrets


@secrets.command('list')
@click.option('--env', '-e', default=None, help='Environment (dev/staging/prod)')
@click.option('--filter', '-f', 'filter_str', default=None, help='Filter secrets by prefix')
def secrets_list(env, filter_str):
    """List all secrets in Secret Manager."""
    env = env or get_default_env()
    project_id = get_config_value("project_id")

    if not project_id:
        console.print("[red]✗ Project ID not configured. Run: accredit setup init[/red]")
        sys.exit(1)

    console.print(f"[cyan]Listing secrets for {env} in {project_id}...[/cyan]\n")

    prefix = f"{env.upper()}_"

    try:
        result = subprocess.run(
            ["gcloud", "secrets", "list", "--project", project_id, "--format", "value(name)"],
            capture_output=True,
            text=True,
            check=True
        )

        secrets_list = result.stdout.strip().split('\n') if result.stdout.strip() else []

        # Filter by environment prefix
        env_secrets = [s for s in secrets_list if s.startswith(prefix)]

        # Apply additional filter if provided
        if filter_str:
            env_secrets = [s for s in env_secrets if filter_str.upper() in s]

        if not env_secrets:
            console.print(f"[yellow]No secrets found for {env} environment[/yellow]")
            console.print(f"\n[dim]Upload secrets with: accredit cloud secrets upload --env {env}[/dim]")
            return

        table = Table(title=f"Secrets - {env.upper()}")
        table.add_column("Secret Name", style="cyan")
        table.add_column("Key (without prefix)", style="white")

        for secret in sorted(env_secrets):
            # Remove prefix to show original key name
            key = secret[len(prefix):] if secret.startswith(prefix) else secret
            table.add_row(secret, key)

        console.print(table)
        console.print(f"\n[dim]Total: {len(env_secrets)} secrets[/dim]")

    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Failed to list secrets: {e.stderr}[/red]")
        sys.exit(1)


@secrets.command('set')
@click.argument('key')
@click.argument('value', required=False)
@click.option('--env', '-e', default=None, help='Environment (dev/staging/prod)')
@click.option('--from-stdin', is_flag=True, help='Read value from stdin')
def secrets_set(key, value, env, from_stdin):
    """Set a secret in Secret Manager.

    Examples:
        accredit cloud secrets set DJANGO_SECRET_KEY "my-secret-key"
        accredit cloud secrets set API_KEY --from-stdin
        echo "secret" | accredit cloud secrets set API_KEY --from-stdin
    """
    env = env or get_default_env()
    project_id = get_config_value("project_id")

    if not project_id:
        console.print("[red]✗ Project ID not configured. Run: accredit setup init[/red]")
        sys.exit(1)

    # Get value from stdin if requested
    if from_stdin:
        import sys as sys_module
        value = sys_module.stdin.read().strip()

    if not value:
        console.print("[red]✗ Value is required. Provide as argument or use --from-stdin[/red]")
        sys.exit(1)

    secret_name = get_secret_name(key, env)

    console.print(f"[cyan]Setting secret: {secret_name}[/cyan]")

    try:
        # Check if secret exists
        result = subprocess.run(
            ["gcloud", "secrets", "describe", secret_name, "--project", project_id],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            # Secret exists, add new version
            process = subprocess.Popen(
                ["gcloud", "secrets", "versions", "add", secret_name,
                 "--project", project_id, "--data-file=-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            _, stderr = process.communicate(input=value)

            if process.returncode != 0:
                console.print(f"[red]✗ Failed to update secret: {stderr}[/red]")
                sys.exit(1)

            console.print(f"[green]✓ Secret updated: {secret_name}[/green]")
        else:
            # Create new secret
            subprocess.run(
                ["gcloud", "secrets", "create", secret_name, "--project", project_id,
                 "--replication-policy", "automatic"],
                check=True,
                capture_output=True
            )

            # Add the value
            process = subprocess.Popen(
                ["gcloud", "secrets", "versions", "add", secret_name,
                 "--project", project_id, "--data-file=-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            _, stderr = process.communicate(input=value)

            if process.returncode != 0:
                console.print(f"[red]✗ Failed to set secret value: {stderr}[/red]")
                sys.exit(1)

            console.print(f"[green]✓ Secret created: {secret_name}[/green]")

    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Failed to set secret: {e}[/red]")
        sys.exit(1)


@secrets.command('get')
@click.argument('key')
@click.option('--env', '-e', default=None, help='Environment (dev/staging/prod)')
@click.option('--version', '-v', default='latest', help='Secret version (default: latest)')
def secrets_get(key, env, version):
    """Get a secret value from Secret Manager."""
    env = env or get_default_env()
    project_id = get_config_value("project_id")

    if not project_id:
        console.print("[red]✗ Project ID not configured. Run: accredit setup init[/red]")
        sys.exit(1)

    secret_name = get_secret_name(key, env)

    try:
        result = subprocess.run(
            ["gcloud", "secrets", "versions", "access", version,
             "--secret", secret_name, "--project", project_id],
            capture_output=True,
            text=True,
            check=True
        )

        # Print raw value (useful for piping)
        print(result.stdout, end='')

    except subprocess.CalledProcessError as e:
        if "NOT_FOUND" in e.stderr:
            console.print(f"[red]✗ Secret not found: {secret_name}[/red]")
        else:
            console.print(f"[red]✗ Failed to get secret: {e.stderr}[/red]")
        sys.exit(1)


@secrets.command('delete')
@click.argument('key')
@click.option('--env', '-e', default=None, help='Environment (dev/staging/prod)')
@click.option('--force', '-f', is_flag=True, help='Skip confirmation')
def secrets_delete(key, env, force):
    """Delete a secret from Secret Manager."""
    env = env or get_default_env()
    project_id = get_config_value("project_id")

    if not project_id:
        console.print("[red]✗ Project ID not configured. Run: accredit setup init[/red]")
        sys.exit(1)

    secret_name = get_secret_name(key, env)

    if not force:
        if not click.confirm(f"Delete secret '{secret_name}'? This cannot be undone."):
            console.print("[yellow]Cancelled[/yellow]")
            return

    try:
        subprocess.run(
            ["gcloud", "secrets", "delete", secret_name, "--project", project_id, "--quiet"],
            check=True,
            capture_output=True
        )
        console.print(f"[green]✓ Secret deleted: {secret_name}[/green]")

    except subprocess.CalledProcessError as e:
        if "NOT_FOUND" in e.stderr.decode() if isinstance(e.stderr, bytes) else e.stderr:
            console.print(f"[red]✗ Secret not found: {secret_name}[/red]")
        else:
            console.print(f"[red]✗ Failed to delete secret: {e}[/red]")
        sys.exit(1)


@secrets.command('upload')
@click.option('--env', '-e', default=None, help='Environment (dev/staging/prod)')
@click.option('--file', '-f', 'env_file', type=click.Path(exists=True), help='Path to .env file')
@click.option('--backend', is_flag=True, help='Upload backend/.env.prod')
@click.option('--frontend', is_flag=True, help='Upload frontend/.env.prod')
@click.option('--dry-run', is_flag=True, help='Show what would be uploaded without uploading')
@click.option('--skip-existing', is_flag=True, help='Skip secrets that already exist')
def secrets_upload(env, env_file, backend, frontend, dry_run, skip_existing):
    """Upload secrets from .env file to Secret Manager.

    Examples:
        accredit cloud secrets upload --backend --env dev
        accredit cloud secrets upload --file ./secrets.env --env prod
        accredit cloud secrets upload --backend --frontend --env dev
    """
    env = env or get_default_env()
    project_id = get_config_value("project_id")

    if not project_id:
        console.print("[red]✗ Project ID not configured. Run: accredit setup init[/red]")
        sys.exit(1)

    files_to_upload = []

    if env_file:
        files_to_upload.append(Path(env_file))
    if backend:
        files_to_upload.append(BACKEND_DIR / ".env.prod")
    if frontend:
        files_to_upload.append(FRONTEND_DIR / ".env.prod")

    if not files_to_upload:
        console.print("[yellow]No files specified. Use --backend, --frontend, or --file[/yellow]")
        console.print("\nExamples:")
        console.print("  accredit cloud secrets upload --backend --env dev")
        console.print("  accredit cloud secrets upload --file ./secrets.env")
        return

    # Collect all secrets from files
    all_secrets = {}
    for file_path in files_to_upload:
        if not file_path.exists():
            console.print(f"[yellow]⚠ File not found: {file_path}[/yellow]")
            continue

        console.print(f"[cyan]Reading: {file_path}[/cyan]")
        secrets = parse_env_file(file_path)
        all_secrets.update(secrets)
        console.print(f"  Found {len(secrets)} variables")

    if not all_secrets:
        console.print("[yellow]No secrets found in files[/yellow]")
        return

    # Get existing secrets
    existing_secrets = set()
    if skip_existing:
        result = subprocess.run(
            ["gcloud", "secrets", "list", "--project", project_id, "--format", "value(name)"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            existing_secrets = set(result.stdout.strip().split('\n'))

    # Show what will be uploaded
    console.print(f"\n[cyan]{'Would upload' if dry_run else 'Uploading'} {len(all_secrets)} secrets to {env}:[/cyan]\n")

    table = Table()
    table.add_column("Key", style="white")
    table.add_column("Secret Name", style="cyan")
    table.add_column("Value Preview", style="dim")
    table.add_column("Status", style="yellow")

    secrets_to_upload = []
    for key, value in sorted(all_secrets.items()):
        secret_name = get_secret_name(key, env)
        # Mask sensitive values
        preview = value[:20] + "..." if len(value) > 20 else value
        if any(sensitive in key.upper() for sensitive in ['SECRET', 'PASSWORD', 'KEY', 'TOKEN']):
            preview = "****" + value[-4:] if len(value) > 4 else "****"

        status = "skip (exists)" if secret_name in existing_secrets else "upload"

        if secret_name not in existing_secrets or not skip_existing:
            secrets_to_upload.append((key, value, secret_name))
            status = "upload" if not dry_run else "would upload"

        table.add_row(key, secret_name, preview, status)

    console.print(table)

    if dry_run:
        console.print(f"\n[yellow]Dry run - no changes made[/yellow]")
        console.print(f"[dim]Remove --dry-run to upload secrets[/dim]")
        return

    if not secrets_to_upload:
        console.print("\n[yellow]No new secrets to upload[/yellow]")
        return

    # Confirm upload
    if not click.confirm(f"\nUpload {len(secrets_to_upload)} secrets to {project_id}?"):
        console.print("[yellow]Cancelled[/yellow]")
        return

    # Upload secrets
    console.print(f"\n[cyan]Uploading secrets...[/cyan]")
    success = 0
    failed = 0

    for key, value, secret_name in secrets_to_upload:
        try:
            # Check if secret exists
            result = subprocess.run(
                ["gcloud", "secrets", "describe", secret_name, "--project", project_id],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                # Update existing secret
                process = subprocess.Popen(
                    ["gcloud", "secrets", "versions", "add", secret_name,
                     "--project", project_id, "--data-file=-"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                process.communicate(input=value)
                if process.returncode != 0:
                    raise Exception("Failed to add version")
            else:
                # Create new secret
                subprocess.run(
                    ["gcloud", "secrets", "create", secret_name, "--project", project_id,
                     "--replication-policy", "automatic"],
                    check=True,
                    capture_output=True
                )

                process = subprocess.Popen(
                    ["gcloud", "secrets", "versions", "add", secret_name,
                     "--project", project_id, "--data-file=-"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                process.communicate(input=value)
                if process.returncode != 0:
                    raise Exception("Failed to add version")

            console.print(f"  [green]✓[/green] {secret_name}")
            success += 1

        except Exception as e:
            console.print(f"  [red]✗[/red] {secret_name}: {e}")
            failed += 1

    console.print(f"\n[bold green]✓ Upload complete: {success} succeeded, {failed} failed[/bold green]")

    if success > 0:
        console.print(f"\n[dim]Secrets are available in Secret Manager with prefix '{env.upper()}_'[/dim]")
        console.print(f"[dim]View secrets: accredit cloud secrets list --env {env}[/dim]")


@secrets.command('download')
@click.option('--env', '-e', default=None, help='Environment (dev/staging/prod)')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--backend', is_flag=True, help='Download to backend/.env.prod')
@click.option('--format', 'fmt', type=click.Choice(['env', 'json']), default='env', help='Output format')
def secrets_download(env, output, backend, fmt):
    """Download secrets from Secret Manager to a file.

    Examples:
        accredit cloud secrets download --env dev --output .env
        accredit cloud secrets download --env prod --backend
        accredit cloud secrets download --env dev --format json
    """
    import json as json_module

    env = env or get_default_env()
    project_id = get_config_value("project_id")

    if not project_id:
        console.print("[red]✗ Project ID not configured. Run: accredit setup init[/red]")
        sys.exit(1)

    prefix = f"{env.upper()}_"

    console.print(f"[cyan]Downloading secrets for {env}...[/cyan]")

    try:
        # Get list of secrets
        result = subprocess.run(
            ["gcloud", "secrets", "list", "--project", project_id, "--format", "value(name)"],
            capture_output=True,
            text=True,
            check=True
        )

        all_secrets = result.stdout.strip().split('\n') if result.stdout.strip() else []
        env_secrets = [s for s in all_secrets if s.startswith(prefix)]

        if not env_secrets:
            console.print(f"[yellow]No secrets found for {env} environment[/yellow]")
            return

        # Download each secret
        secrets_dict = {}
        for secret_name in env_secrets:
            result = subprocess.run(
                ["gcloud", "secrets", "versions", "access", "latest",
                 "--secret", secret_name, "--project", project_id],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                # Remove prefix to get original key
                key = secret_name[len(prefix):]
                secrets_dict[key] = result.stdout

        console.print(f"[green]✓ Downloaded {len(secrets_dict)} secrets[/green]")

        # Determine output path
        if backend:
            output = str(BACKEND_DIR / ".env.prod")

        # Format output
        if fmt == 'json':
            content = json_module.dumps(secrets_dict, indent=2)
        else:
            lines = [f"{key}={value}" for key, value in sorted(secrets_dict.items())]
            content = '\n'.join(lines) + '\n'

        if output:
            with open(output, 'w') as f:
                f.write(content)
            console.print(f"[green]✓ Written to: {output}[/green]")
        else:
            print(content)

    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Failed to download secrets: {e.stderr}[/red]")
        sys.exit(1)
