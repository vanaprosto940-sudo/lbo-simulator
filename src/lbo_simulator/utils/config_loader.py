"""Configuration loader from YAML files."""

from __future__ import annotations

from pathlib import Path

import yaml

from lbo_simulator.models.schemas import LBOConfigSchema


def load_config(config_path: str | Path) -> LBOConfigSchema:
    """Load and validate LBO configuration from YAML file.

    Args:
        config_path: Path to YAML configuration file.

    Returns:
        Validated LBOConfigSchema.
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        raw_config = yaml.safe_load(f)

    return LBOConfigSchema(**raw_config)


def load_config_from_dict(config_dict: dict) -> LBOConfigSchema:
    """Load and validate LBO configuration from dictionary.

    Args:
        config_dict: Dictionary with configuration.

    Returns:
        Validated LBOConfigSchema.
    """
    return LBOConfigSchema(**config_dict)


def save_config(config: LBOConfigSchema, output_path: str | Path) -> None:
    """Save configuration to YAML file.

    Args:
        config: LBOConfigSchema to save.
        output_path: Output file path.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    config_dict = config.model_dump()
    with open(output_path, "w") as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
