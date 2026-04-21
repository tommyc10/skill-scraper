from __future__ import annotations

import os
import sys

from skill_cli import __version__


LOGO_LINES = [
    "  ███████╗██╗  ██╗██╗██╗     ██╗             ██████╗██╗     ██╗",
    "  ██╔════╝██║ ██╔╝██║██║     ██║            ██╔════╝██║     ██║",
    "  ███████╗█████╔╝ ██║██║     ██║     █████╗ ██║     ██║     ██║",
    "  ╚════██║██╔═██╗ ██║██║     ██║     ╚════╝ ██║     ██║     ██║",
    "  ███████║██║  ██╗██║███████╗███████╗       ╚██████╗███████╗██║",
    "  ╚══════╝╚═╝  ╚═╝╚═╝╚══════╝╚══════╝        ╚═════╝╚══════╝╚═╝",
]

GRADIENT_COLORS = [69, 75, 81, 87, 123, 159]

SPARKLE = "✦"
DOT = "·"


def print_banner(model: str) -> None:
    if not _color_supported():
        _print_plain(model)
        return

    reset = "\033[0m"
    dim = "\033[2m"
    bold = "\033[1m"

    for line, color_code in zip(LOGO_LINES, GRADIENT_COLORS):
        color = f"\033[38;5;{color_code}m"
        print(f"{color}{line}{reset}")

    accent = f"\033[38;5;{GRADIENT_COLORS[-2]}m"
    print()
    print(
        f"  {accent}{SPARKLE}{reset}  "
        f"{bold}agent skills from{reset} "
        f"{accent}skills.sh{reset}"
        f"  {dim}{DOT}{reset}  "
        f"{dim}v{__version__}{reset}"
    )
    print(
        f"  {accent}{SPARKLE}{reset}  "
        f"{dim}model:{reset} {bold}{model}{reset} "
        f"{dim}on foundry{reset}"
    )
    print()


def _print_plain(model: str) -> None:
    for line in LOGO_LINES:
        print(line)
    print()
    print(f"  agent skills from skills.sh  ·  v{__version__}")
    print(f"  model: {model} on foundry")
    print()


def _color_supported() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if not sys.stdout.isatty():
        return False
    return os.environ.get("TERM", "") != "dumb"
