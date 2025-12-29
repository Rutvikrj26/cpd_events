#!/usr/bin/env python3
"""Setup and configuration commands."""

import click
from rich.console import Console
from rich.table import Table

from accredit.utils.config import (
    load_config,
    save_config,
    get_current_env,
    set_current_env,
    CONFIG_FILE,
)

console = Console()


@click.group(invoke_without_command=True)
@click.pass_context
def setup(ctx):
    """Setup and manage CLI configuration."""
    # If no subcommand is provided, run init
    if ctx.invoked_subcommand is None:
        ctx.invoke(init)


@setup.command()
@click.option('--env', '-e', help='Default environment (dev/staging/prod)')
@click.option('--project-id', '-p', help='GCP project ID')
@click.option('--region', '-r', help='GCP region (default: us-central1)')
def init(env, project_id, region):
    """Initialize CLI configuration."""
    console.print("[cyan]Setting up Accredit CLI configuration...[/cyan]\n")

    config = load_config()

    # Interactive prompts if not provided
    if not env:
        env = click.prompt(
            "Default environment",
            default=config.get("environment", "dev"),
            type=click.Choice(['dev', 'staging', 'prod'])
        )

    if not project_id:
        current_project = config.get("project_id")
        project_id = click.prompt(
            "GCP project ID (optional, press Enter to skip)",
            default=current_project if current_project else "",
            show_default=True
        )
        if not project_id:
            project_id = None

    if not region:
        region = click.prompt(
            "GCP region",
            default=config.get("region", "us-central1")
        )

    # Save configuration
    config["environment"] = env
    config["project_id"] = project_id
    config["region"] = region
    save_config(config)

    console.print(f"\n[green]✓ Configuration saved to {CONFIG_FILE}[/green]")
    console.print("\n[cyan]Current settings:[/cyan]")
    show_config_table(config)


@setup.command()
def show():
    """Show current configuration."""
    config = load_config()
    console.print(f"[cyan]Configuration file: {CONFIG_FILE}[/cyan]\n")
    show_config_table(config)


@setup.command()
@click.argument('environment', type=click.Choice(['dev', 'staging', 'prod']))
def use(environment):
    """Switch to a different environment."""
    set_current_env(environment)
    console.print(f"[green]✓ Switched to environment: {environment}[/green]")


@setup.command()
@click.argument('key')
@click.argument('value')
def set(key, value):
    """Set a configuration value."""
    config = load_config()

    # Convert 'None' string to actual None
    if value.lower() == 'none':
        value = None

    config[key] = value
    save_config(config)
    console.print(f"[green]✓ Set {key} = {value}[/green]")


@setup.command()
@click.argument('key')
def get(key):
    """Get a configuration value."""
    config = load_config()
    value = config.get(key)

    if value is None:
        console.print(f"[yellow]'{key}' is not set[/yellow]")
    else:
        console.print(f"{key} = {value}")


@setup.command()
def reset():
    """Reset configuration to defaults."""
    if click.confirm("Are you sure you want to reset configuration to defaults?"):
        from accredit.utils.config import DEFAULT_CONFIG
        save_config(DEFAULT_CONFIG)
        console.print("[green]✓ Configuration reset to defaults[/green]")
    else:
        console.print("[yellow]Cancelled[/yellow]")


def show_config_table(config):
    """Display configuration as a table."""
    table = Table()
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Environment", config.get("environment", "Not set"))
    table.add_row("GCP Project ID", config.get("project_id") or "[dim]Not set[/dim]")
    table.add_row("GCP Region", config.get("region", "Not set"))

    console.print(table)
