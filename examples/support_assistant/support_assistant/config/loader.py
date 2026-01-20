"""Support assistant configuration loader."""
from __future__ import annotations

from pathlib import Path

from agent_contracts.config import FrameworkConfig, load_config, set_config

DEFAULT_CONFIG_PATH = Path(__file__).with_name("defaults.yaml")


def load_support_config(path: Path | str = DEFAULT_CONFIG_PATH) -> FrameworkConfig:
    """Load and apply support assistant configuration.

    Args:
        path: Path to YAML config file.

    Returns:
        Parsed FrameworkConfig instance.
    """
    config = load_config(path)
    set_config(config)
    return config
