"""
Interactive approval TUI for live side effects (M9).
"""

from __future__ import annotations

import os
import sys
from typing import Optional


def is_interactive() -> bool:
    if os.getenv("SUPERAI_NON_INTERACTIVE", "").lower() in {"1", "true", "yes"}:
        return False
    return sys.stdin.isatty() and sys.stdout.isatty()


def prompt_approval(
    title: str,
    detail: str = "",
    *,
    default: bool = False,
    force: Optional[bool] = None,
) -> bool:
    """
    Ask user y/n. Returns True if approved.
    force: if set, skip prompt.
    Non-interactive: returns default (usually False for safety).
    """
    if force is not None:
        return bool(force)
    if not is_interactive():
        return default
    print(f"\n=== APPROVAL REQUIRED: {title} ===")
    if detail:
        print(detail[:2000])
    hint = "Y/n" if default else "y/N"
    try:
        ans = input(f"Approve? [{hint}]: ").strip().lower()
    except EOFError:
        return default
    if not ans:
        return default
    return ans in {"y", "yes", "1", "true"}
