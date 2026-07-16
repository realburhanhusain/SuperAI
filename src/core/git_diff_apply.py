"""
Git-native propose/apply diffs (Sprint A M2) — Aider-inspired, workspace-jailed.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


def _root() -> Path:
    try:
        from .workspace import workspace_root

        return Path(workspace_root())
    except Exception:
        return Path.cwd().resolve()


def propose_unified_diff(path: str, old: str, new: str) -> str:
    """Build a simple unified diff string for one file."""
    import difflib

    a = old.splitlines(keepends=True)
    b = new.splitlines(keepends=True)
    rel = path.replace("\\", "/")
    return "".join(
        difflib.unified_diff(a, b, fromfile=f"a/{rel}", tofile=f"b/{rel}")
    )


def check_unified_diff(diff_text: str) -> Dict[str, Any]:
    """git apply --check for conflict preview (V3 M5)."""
    root = _root()
    if not (diff_text or "").strip():
        return {"ok": False, "error": "empty_diff"}
    try:
        proc = subprocess.run(
            ["git", "apply", "--check", "--whitespace=nowarn", "-"],
            input=diff_text,
            text=True,
            cwd=str(root),
            capture_output=True,
            timeout=60,
        )
        return {
            "ok": proc.returncode == 0,
            "check": True,
            "stderr": (proc.stderr or "")[:800],
            "stdout": (proc.stdout or "")[:400],
            "conflicts": proc.returncode != 0,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:300], "check": True}


def apply_unified_diff(
    diff_text: str,
    *,
    dry_run: bool = True,
    commit: bool = False,
    message: str = "superai: apply diff",
    check_first: bool = True,
) -> Dict[str, Any]:
    """
    Apply a unified diff via `git apply` when possible; else parse single-file rewrite.
    plan/dry_run: never write.
    """
    root = _root()
    if not (diff_text or "").strip():
        return {"ok": False, "error": "empty_diff"}
    check = check_unified_diff(diff_text) if check_first else {"ok": True}
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "preview": diff_text[:4000],
            "check": check,
            "hint": "Re-run with dry_run=False to apply",
        }
    if check_first and not check.get("ok"):
        return {
            "ok": False,
            "error": "diff_check_failed",
            "check": check,
            "hint": "Resolve conflicts or use file rewrite markers",
        }
    # Prefer git apply
    try:
        proc = subprocess.run(
            ["git", "apply", "--whitespace=nowarn", "-"],
            input=diff_text,
            text=True,
            cwd=str(root),
            capture_output=True,
            timeout=60,
        )
        if proc.returncode == 0:
            out: Dict[str, Any] = {"ok": True, "method": "git_apply", "check": check}
            if commit:
                subprocess.run(["git", "add", "-A"], cwd=str(root), check=False)
                c = subprocess.run(
                    ["git", "commit", "-m", message],
                    cwd=str(root),
                    capture_output=True,
                    text=True,
                )
                out["committed"] = c.returncode == 0
                out["commit_out"] = (c.stdout or c.stderr or "")[:500]
            return out
        git_err = (proc.stderr or proc.stdout or "")[:500]
    except Exception as e:
        git_err = str(e)[:500]

    # Fallback: single-file full replace markers
    # *** Begin File: path
    # content
    # *** End File
    m = re.search(
        r"\*\*\*\s*Begin File:\s*(.+?)\n([\s\S]*?)\*\*\*\s*End File",
        diff_text,
        re.I,
    )
    if m:
        rel = m.group(1).strip()
        content = m.group(2)
        try:
            from .agent_tools import tool_write

            w = tool_write(rel, content, dry_run=False)
            return {"ok": bool(w.get("ok")), "method": "file_rewrite", "write": w, "git_err": git_err}
        except Exception as e:
            return {"ok": False, "error": str(e)[:300], "git_err": git_err}

    return {"ok": False, "error": "apply_failed", "git_err": git_err}
