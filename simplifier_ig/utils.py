"""Shared utility helpers."""

from pathlib import Path


def is_subpath(child: Path, parent: Path) -> bool:
    """Check if *child* is equal to or under *parent*."""
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def format_title(name: str) -> str:
    if not name:
        return name
    if name.lower() == "index":
        return "Index"
    return name.replace("-", " ").replace("_", " ").title()
