"""Configuration persistence helpers."""

import json
from pathlib import Path
from typing import Any, Dict

CONFIG_DIR = ".simplifier"
CONFIG_FILE = "ig-generation.settings.json"


def _config_path() -> Path:
    """Return the path to the config file in the current working directory."""
    return Path.cwd() / CONFIG_DIR / CONFIG_FILE


def load_config() -> Dict[str, Any]:
    """Load persisted IG configuration."""
    path = _config_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_config(cfg: Dict[str, Any]) -> None:
    """Save IG configuration to disk."""
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
