"""
Diff-first file edits (S13).
"""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any, Dict, Optional

from .approval_tui import prompt_approval
from .workspace import assert_in_workspace


def unified_diff(old: str, new: str, path: str = "file") -> str:
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(old_lines, new_lines, fromfile=f"a/{path}", tofile=f"b/{path}")
    )


def apply_edit_with_diff(
    path: str | Path,
    new_content: str,
    *,
    auto_approve: bool = False,
    show: bool = True,
) -> Dict[str, Any]:
    """
    Show unified diff and apply only after approval (unless auto_approve).
    """
    resolved = assert_in_workspace(path, label="edit path")
    old = ""
    if resolved.is_file():
        old = resolved.read_text(encoding="utf-8", errors="replace")
    diff = unified_diff(old, new_content, path=str(resolved.name))
    if show:
        print(diff or "(no changes)")
    if old == new_content:
        return {"ok": True, "changed": False, "path": str(resolved), "diff": diff}
    approved = prompt_approval(
        f"Apply edit to {resolved}",
        detail=diff[:3000] if diff else new_content[:500],
        default=False,
        force=True if auto_approve else None,
    )
    if not approved:
        return {"ok": False, "changed": False, "path": str(resolved), "diff": diff, "rejected": True}
    resolved.parent.mkdir(parents=True, exist_ok=True)
    # snapshot
    try:
        from .time_travel import FileTimeTravel

        FileTimeTravel().snapshot(resolved, note="pre-diff-edit")
    except Exception:
        pass
    resolved.write_text(new_content, encoding="utf-8")
    return {"ok": True, "changed": True, "path": str(resolved), "diff": diff}
