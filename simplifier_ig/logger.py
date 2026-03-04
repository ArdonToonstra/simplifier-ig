"""Colored console output for simplifier-ig."""

import sys

import colorama
from colorama import Fore, Style

colorama.init(autoreset=True, strip=not sys.stdout.isatty())

# Status tags — can appear anywhere in a line
_TAG_COLORS: dict[str, str] = {
    "[OK]":        Fore.GREEN,
    "[SUCCESS]":   Fore.GREEN + Style.BRIGHT,
    "[WARNING]":   Fore.YELLOW,
    "[ERROR]":     Fore.RED + Style.BRIGHT,
    "[CANCELLED]": Fore.RED,
    "[INFO]":      Fore.CYAN,
}

# Section / phase tags — always appear at the start of a line
_SECTION_TAGS = {
    "[INIT]", "[FOLDERS]", "[FILES]", "[TARGET]", "[SETUP]",
    "[COPY]", "[TRANSFORM]", "[ARTIFACTS]", "[TOC]", "[VALIDATE]",
    "[MENU]", "[TEMPLATES]", "[IG-RESOURCE]", "[NEXT STEPS]",
    "[OUTPUT]", "[STATS]",
}

_SECTION_COLOR = Fore.BLUE + Style.BRIGHT
_SEPARATOR_COLOR = Style.DIM


def _colorize(msg: str) -> str:
    stripped = msg.lstrip()

    # Separator lines: "=" * N  or  "-" * N
    if stripped and all(c == "=" for c in stripped):
        return _SEPARATOR_COLOR + msg
    if stripped and all(c == "-" for c in stripped):
        return _SEPARATOR_COLOR + msg

    # Status tags (may appear mid-line)
    for tag, color in _TAG_COLORS.items():
        if tag in msg:
            return color + msg

    # Section tags (always at line start)
    for tag in _SECTION_TAGS:
        if stripped.startswith(tag):
            return _SECTION_COLOR + msg

    return msg


def make_printer():
    """Return a log callable that prints colorized output to stdout."""

    def _printer(msg: str) -> None:
        print(_colorize(msg))

    return _printer
