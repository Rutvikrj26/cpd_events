#!/usr/bin/env python3
"""Configuration management for Accredit CLI."""

import json
from pathlib import Path

# Config file location
CONFIG_DIR = Path.home() / ".config" / "accredit"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Default configuration
DEFAULT_CONFIG = {
    "environment": "dev",
    "project_id": None,
    "region": "us-central1",
    "firebase_project_id": None,  # For Firebase Hosting deployments
    "last_sync": None,            # Last remote state sync timestamp
}


def ensure_config_dir():
    """Ensure the config directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config():
    """Load configuration from file, or return default if not exists."""
    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            # Merge with defaults to ensure all keys exist
            return {**DEFAULT_CONFIG, **config}
    except (json.JSONDecodeError, IOError):
        return DEFAULT_CONFIG.copy()


def save_config(config):
    """Save configuration to file."""
    ensure_config_dir()
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def get_config_value(key):
    """Get a specific configuration value."""
    config = load_config()
    return config.get(key)


def set_config_value(key, value):
    """Set a specific configuration value."""
    config = load_config()
    config[key] = value
    save_config(config)


def get_current_env():
    """Get the current environment."""
    return get_config_value("environment") or "dev"


def set_current_env(environment):
    """Set the current environment."""
    set_config_value("environment", environment)
