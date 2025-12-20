"""Configuration management module."""

import os
from pathlib import Path
from typing import Dict, Any, Optional, Set
import yaml


def get_project_root() -> Path:
    """Gets the project root directory.

    Returns:
        Path: The absolute path to the project root.
    """
    # Look for pyproject.toml in parent directories
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    # Fallback: assume this file is 2 levels deep in src/
    return Path(__file__).resolve().parents[2]


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Loads the configuration file.

    Args:
        config_path: Path to the configuration file. If None, looks for
            config.yaml in the project root.

    Returns:
        Dict[str, Any]: A dictionary containing the configuration settings.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        yaml.YAMLError: If the configuration file is malformed.
    """
    # Default to config.yaml in project root
    config_path_obj = get_project_root() / "config.yaml"

    if not config_path_obj.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path_obj}\n"
            f"Please copy config.example.yaml to config.yaml and modify it."
        )

    with open(config_path_obj, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config


def get_extensions(config: Dict[str, Any]) -> Dict[str, Set[str]]:
    """Gets the sets of valid file extensions from configuration.

    Args:
        config: The configuration dictionary.

    Returns:
        Dict[str, Set[str]]: A dictionary with 'image', 'video', and 'all' keys,
            each containing a set of extension strings (e.g., '.jpg').
    """
    extensions = config.get("extensions", {})

    image_exts = set(extensions.get("image", []))
    video_exts = set(extensions.get("video", []))

    return {
        "image": image_exts,
        "video": video_exts,
        "all": image_exts | video_exts,
    }
