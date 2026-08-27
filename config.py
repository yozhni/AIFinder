"""Load configuration from config.yaml."""

import os
import yaml

_config = None


def load_config():
    """Load config.yaml from project root."""
    global _config
    if _config is None:
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        with open(config_path, "r") as f:
            _config = yaml.safe_load(f)
    return _config


def get(section, key=None, default=None):
    """Get config value. Example: get('database', 'url')"""
    config = load_config()
    value = config.get(section, {})
    if key:
        return value.get(key, default) if isinstance(value, dict) else default
    return value
