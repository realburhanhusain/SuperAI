"""
Permission modes for side effects (Improvement Phase 2).

plan  — no file-modifying tools/CLIs; dry-run only
ask   — prompt for approval (default)
auto  — auto-approve when config allows; still respect require_human_approval=false
yolo  — auto-approve all CLI/tool side effects
"""

from __future__ import annotations

from typing import Any, Dict, Optional

MODES = ("plan", "ask", "auto", "yolo")


def normalize_mode(mode: Optional[str], default: str = "ask") -> str:
    m = (mode or default or "ask").strip().lower()
    if m in {"yes", "y"}:
        return "auto"
    if m not in MODES:
        return default if default in MODES else "ask"
    return m


def mode_from_config(config: Any = None) -> str:
    try:
        if config is None:
            from .config import Config

            config = Config()
        return normalize_mode(config.get("permission_mode"), "ask")
    except Exception:
        return "ask"


def allows_live_side_effects(mode: str) -> bool:
    return normalize_mode(mode) != "plan"


def should_auto_approve(mode: str) -> bool:
    return normalize_mode(mode) in {"auto", "yolo"}


def force_dry_run(mode: str) -> bool:
    return normalize_mode(mode) == "plan"


def apply_to_cli_tool_kwargs(
    mode: Optional[str],
    *,
    dry_run: bool = False,
    auto_approve: bool = False,
) -> Dict[str, bool]:
    """Return dry_run/auto_approve adjusted for permission mode."""
    m = normalize_mode(mode)
    if m == "plan":
        return {"dry_run": True, "auto_approve": True}
    if m == "yolo":
        return {"dry_run": bool(dry_run), "auto_approve": True}
    if m == "auto":
        return {"dry_run": bool(dry_run), "auto_approve": True}
    # ask
    return {"dry_run": bool(dry_run), "auto_approve": bool(auto_approve)}
