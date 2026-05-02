from __future__ import annotations

from skill_cli import __version__
from skill_cli.style import (
    ACCENT,
    BOLD,
    MUTED,
    RESET,
    color,
    enabled,
    paint,
)


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
    print()
    if enabled():
        for line, code in zip(LOGO_LINES, GRADIENT_COLORS):
            print(f"{color(code)}{line}{RESET}")
    else:
        for line in LOGO_LINES:
            print(line)

    tagline = "agent skills from skills.sh"
    meta = f"{model}  {DOT}  v{__version__}"

    print()
    print(
        "  "
        + paint(SPARKLE, ACCENT)
        + "  "
        + paint(tagline, BOLD)
        + "  "
        + paint(DOT, MUTED)
        + "  "
        + paint(meta, MUTED)
    )
    print("  " + paint("─" * 60, MUTED))
