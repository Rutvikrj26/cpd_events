#!/usr/bin/env python3
"""Remote deployment state management via GCS.

This module handles pushing and pulling deployment state to/from Google Cloud Storage,
enabling CLI state synchronization across different systems.
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


def get_state_bucket_name(project_id: str) -> str:
    """Get the deployment state bucket name for a project."""
    return f"{project_id}-deployment-state"


def get_git_info() -> dict:
    """Get current git commit info."""
    try:
        commit_hash = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True
        ).stdout.strip()
        
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, check=True
        ).stdout.strip()
        
        return {"commit": commit_hash, "branch": branch}
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {"commit": "unknown", "branch": "unknown"}


def get_deployer_info() -> str:
    """Get current user's email from gcloud."""
    try:
        result = subprocess.run(
            ["gcloud", "config", "get-value", "account"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def push_deployment_state(project_id: str, component: str, record: dict) -> dict:
    """Push a deployment record to GCS.
    
    Args:
        project_id: GCP project ID
        component: 'frontend' or 'backend'
        record: Deployment record to add (version, target, etc.)
    
    Returns:
        The complete record with timestamp added
    """
    bucket_name = get_state_bucket_name(project_id)
    blob_name = "cli-deployment-state.json"
    
    # Get existing state
    state = pull_deployment_state(project_id)
    
    # Add metadata to record
    git_info = get_git_info()
    record["timestamp"] = datetime.utcnow().isoformat() + "Z"
    record["deployer"] = get_deployer_info()
    record["commit"] = git_info["commit"]
    record["branch"] = git_info["branch"]
    
    # Append to component history
    if component not in state:
        state[component] = []
    state[component].append(record)
    
    # Keep last 20 records per component
    state[component] = state[component][-20:]
    
    # Upload to GCS
    try:
        # Write to temp file
        temp_file = Path("/tmp/cli-deployment-state.json")
        temp_file.write_text(json.dumps(state, indent=2))
        
        # Upload via gsutil
        subprocess.run(
            ["gsutil", "cp", str(temp_file), f"gs://{bucket_name}/{blob_name}"],
            check=True,
            capture_output=True
        )
        
        console.print(f"[green]✓ Deployment state pushed to gs://{bucket_name}[/green]")
        return record
    except subprocess.CalledProcessError as e:
        console.print(f"[yellow]⚠ Could not push state to GCS: {e}[/yellow]")
        return record


def pull_deployment_state(project_id: str) -> dict:
    """Pull all deployment state from GCS.
    
    Args:
        project_id: GCP project ID
    
    Returns:
        Dict with 'frontend' and 'backend' deployment histories
    """
    bucket_name = get_state_bucket_name(project_id)
    blob_name = "cli-deployment-state.json"
    
    try:
        result = subprocess.run(
            ["gsutil", "cat", f"gs://{bucket_name}/{blob_name}"],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError:
        # Bucket or blob doesn't exist yet
        return {"frontend": [], "backend": []}
    except json.JSONDecodeError:
        return {"frontend": [], "backend": []}


def get_latest_deployment(project_id: str, component: str) -> Optional[dict]:
    """Get the most recent deployment for a component.
    
    Args:
        project_id: GCP project ID
        component: 'frontend' or 'backend'
    
    Returns:
        Latest deployment record or None
    """
    state = pull_deployment_state(project_id)
    deployments = state.get(component, [])
    return deployments[-1] if deployments else None


def get_deployment_history(project_id: str, component: str, limit: int = 10) -> list:
    """Get deployment history for a component.
    
    Args:
        project_id: GCP project ID
        component: 'frontend' or 'backend'
        limit: Maximum number of records to return
    
    Returns:
        List of deployment records (most recent last)
    """
    state = pull_deployment_state(project_id)
    deployments = state.get(component, [])
    return deployments[-limit:]


def ensure_state_bucket(project_id: str, region: str = "us-central1") -> bool:
    """Ensure the deployment state bucket exists.
    
    Args:
        project_id: GCP project ID
        region: GCS bucket region
    
    Returns:
        True if bucket exists or was created
    """
    bucket_name = get_state_bucket_name(project_id)
    
    try:
        # Check if bucket exists
        result = subprocess.run(
            ["gsutil", "ls", "-b", f"gs://{bucket_name}"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return True
        
        # Create bucket
        subprocess.run(
            ["gsutil", "mb", "-l", region, f"gs://{bucket_name}"],
            check=True,
            capture_output=True
        )
        
        # Enable versioning
        subprocess.run(
            ["gsutil", "versioning", "set", "on", f"gs://{bucket_name}"],
            check=True,
            capture_output=True
        )
        
        console.print(f"[green]✓ Created deployment state bucket: {bucket_name}[/green]")
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Could not create state bucket: {e}[/red]")
        return False
