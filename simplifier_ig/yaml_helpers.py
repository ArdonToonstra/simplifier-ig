"""YAML I/O helpers (lazy-import so we fail gracefully when PyYAML is absent)."""

from pathlib import Path
from typing import Any


def load_yaml(file_path: Path) -> Any:
    """Load and parse a YAML file."""
    import yaml

    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def dump_yaml(data: Any, file_path: Path) -> None:
    """Write *data* as YAML to *file_path*."""
    import yaml

    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
