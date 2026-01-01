#!/usr/bin/env python3
"""Accredit CLI - CPD Events platform management tool."""

import click
from rich.console import Console
from accredit.commands import local as local_commands
from accredit.commands import docker as docker_commands
from accredit.commands import cloud as cloud_commands
from accredit.commands import setup as setup_commands
from accredit.utils.config import get_current_env

console = Console()

@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Accredit - CPD Events platform management CLI."""
    pass

# Register command groups
cli.add_command(local_commands.local)
cli.add_command(docker_commands.docker)
cli.add_command(cloud_commands.cloud)
cli.add_command(setup_commands.setup)

@cli.command()
def env():
    """Show current environment."""
    current_env = get_current_env()
    console.print(f"[cyan]Current environment:[/cyan] [green]{current_env}[/green]")

def main():
    """Entry point for the CLI."""
    cli()

if __name__ == "__main__":
    main()
