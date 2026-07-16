"""
Interactive approval TUI for live side effects (M9) + member picking.
"""

from __future__ import annotations

import os
import sys
from typing import List, Optional, Sequence


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


def prompt_select_members(
    options: Sequence[str],
    *,
    title: str = "Select members",
    max_n: int = 5,
    allow_empty: bool = False,
    default: Optional[Sequence[str]] = None,
) -> List[str]:
    """
    Numbered multi-select for API/CLI member ids.

    Input: comma/space-separated numbers, ids, or 'all' / 'auto' / 'q'.
    Non-interactive: returns list(default) or first max_n options.
    """
    opts = [str(o).strip() for o in options if str(o).strip()]
    # de-dupe preserve order
    seen = set()
    uniq: List[str] = []
    for o in opts:
        if o not in seen:
            seen.add(o)
            uniq.append(o)
    opts = uniq
    if not opts:
        return []

    if not is_interactive():
        if default:
            return [str(x) for x in default][:max_n]
        return opts[: max(1, max_n)] if not allow_empty else []

    print(f"\n=== {title} (pick up to {max_n}) ===")
    width = len(str(len(opts)))
    for i, o in enumerate(opts, 1):
        print(f"  {str(i).rjust(width)}. {o}")
    print(
        "Enter numbers and/or ids (comma/space), 'all', 'auto' for first "
        f"{max_n}, or Enter to {'skip' if allow_empty else 'use auto'}."
    )
    try:
        ans = input("Selection: ").strip()
    except EOFError:
        ans = ""

    if not ans:
        if allow_empty:
            return []
        if default:
            return [str(x) for x in default][:max_n]
        return opts[: max(1, max_n)]

    low = ans.lower()
    if low in {"q", "quit", "none"} and allow_empty:
        return []
    if low in {"auto", "a"}:
        return opts[: max(1, max_n)]
    if low in {"all", "*"}:
        return opts[:max_n] if max_n else opts

    picked: List[str] = []
    tokens = [t for t in re_split_tokens(ans) if t]
    for t in tokens:
        if t.isdigit():
            idx = int(t)
            if 1 <= idx <= len(opts):
                item = opts[idx - 1]
                if item not in picked:
                    picked.append(item)
            continue
        # direct id match (case-insensitive)
        match = next((o for o in opts if o.lower() == t.lower()), None)
        if match is None:
            # prefix / contains
            cands = [o for o in opts if t.lower() in o.lower()]
            match = cands[0] if len(cands) == 1 else None
        if match and match not in picked:
            picked.append(match)

    if not picked and not allow_empty:
        return opts[: max(1, max_n)]
    return picked[:max_n] if max_n else picked


def re_split_tokens(s: str) -> List[str]:
    import re

    return [p for p in re.split(r"[\s,;]+", s.strip()) if p]


def prompt_pick_from_catalog(
    *,
    title: str = "Select workers / board members",
    max_n: int = 5,
    only_available: bool = True,
    prefer: str = "mixed",
) -> List[str]:
    """Load selectable catalog and run interactive multi-select."""
    from .member_selection import list_selectable_members, resolve_members

    data = list_selectable_members(
        only_available=only_available, with_cli_models=True
    )
    options = list(data.get("pick_ids") or data.get("selectable_ids") or [])
    defaults = [s.id for s in resolve_members(None, max_members=max_n, prefer=prefer)]
    return prompt_select_members(
        options,
        title=title,
        max_n=max_n,
        allow_empty=False,
        default=defaults,
    )
