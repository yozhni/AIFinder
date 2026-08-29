"""Load configuration from config.yaml."""

import os
import re
import yaml

_config = None


def _resolve_env_vars(value):
    """Resolve ${ENV_VAR} patterns in config values."""
    if isinstance(value, str):
        pattern = r'\$\{(\w+)\}'
        matches = re.findall(pattern, value)
        for var_name in matches:
            env_value = os.environ.get(var_name, '')
            value = value.replace(f'${{{var_name}}}', env_value)
        return value
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    return value


def load_config():
    """Load config.yaml from project root."""
    global _config
    if _config is None:
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        with open(config_path, "r") as f:
            _config = yaml.safe_load(f)
        _config = _resolve_env_vars(_config)
    return _config


def get(section, key=None, default=None):
    """Get config value. Example: get('database', 'url')"""
    config = load_config()
    value = config.get(section, {})
    if key:
        return value.get(key, default) if isinstance(value, dict) else default
    return value
