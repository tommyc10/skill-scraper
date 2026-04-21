from __future__ import annotations

import os
import sys


RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"


def color(code: int) -> str:
    return f"\033[38;5;{code}m"


ACCENT = color(75)
ACCENT_SOFT = color(123)
MUTED = color(244)
SUCCESS = color(84)
WARN = color(215)
ERROR = color(203)


_ENABLED: bool | None = None


def enabled() -> bool:
    global _ENABLED
    if _ENABLED is not None:
        return _ENABLED
    if os.environ.get("NO_COLOR"):
        _ENABLED = False
    elif not sys.stdout.isatty():
        _ENABLED = False
    elif os.environ.get("TERM", "") == "dumb":
        _ENABLED = False
    else:
        _ENABLED = True
    return _ENABLED


def paint(text: str, *codes: str) -> str:
    if not enabled() or not codes:
        return text
    return "".join(codes) + text + RESET


def status(message: str) -> None:
    icon = paint("⋯", ACCENT)
    print(f"  {icon} {paint(message, MUTED)}")


def section(title: str) -> None:
    bar = paint("│", ACCENT)
    print()
    print(f"  {bar} {paint(title, BOLD)}")


def card(index: int, slug: str, repo: str, reason: str, url: str) -> None:
    bar = paint("▎", ACCENT)
    num = paint(f"{index}", BOLD, ACCENT_SOFT)
    slug_styled = paint(slug, BOLD)
    repo_styled = paint(repo, MUTED)
    reason_styled = paint(reason, ITALIC)
    url_styled = paint(url, MUTED)

    print()
    print(f"  {num}  {bar} {slug_styled}")
    print(f"     {bar} {repo_styled}")
    print(f"     {bar} {reason_styled}")
    print(f"     {bar} {url_styled}")


def ask(prompt_text: str) -> str:
    icon = paint("✦", ACCENT)
    print()
    print(f"  {icon}  {paint(prompt_text, BOLD)}")
    arrow = paint("❯", ACCENT)
    return input(f"  {arrow} ").strip()


def confirm(prompt_text: str) -> bool:
    icon = paint("◆", ACCENT_SOFT)
    print()
    hint = paint("[y/N]", MUTED)
    reply = input(f"  {icon}  {paint(prompt_text, BOLD)} {hint} ").strip().lower()
    return reply in {"y", "yes"}


def success(message: str) -> None:
    mark = paint("✓", SUCCESS)
    print(f"  {mark} {message}")


def skipped(message: str) -> None:
    mark = paint("⊘", MUTED)
    print(f"  {mark} {paint(message, MUTED)}")


def error(message: str) -> None:
    mark = paint("✗", ERROR)
    print(f"  {mark} {paint(message, ERROR)}", file=sys.stderr)


def rule() -> None:
    width = min(64, max(40, (os.get_terminal_size().columns if sys.stdout.isatty() else 60) - 4))
    print(paint("  " + "─" * width, MUTED))
