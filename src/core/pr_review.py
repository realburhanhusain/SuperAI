"""
PR review mode (N26) — review a diff or local git range.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from .workspace import workspace_root


def get_git_diff(ref: str = "HEAD~1") -> str:
    root = workspace_root()
    proc = subprocess.run(
        ["git", "diff", ref],
        cwd=str(root),
        capture_output=True,
        text=True,
        shell=False,
    )
    return (proc.stdout or proc.stderr or "")[:50000]


def review_diff(diff: str, use_mock: bool = True) -> Dict[str, Any]:
    from .council import Council
    from .model_caller import ModelCaller
    from .model_registry import ModelRegistry

    reg = ModelRegistry()
    caller = ModelCaller(use_mock=use_mock, registry=reg)
    topic = (
        "Code review this diff. Vote on merge readiness.\n\n"
        f"```diff\n{diff[:12000]}\n```"
    )
    c = Council(caller=caller, registry=reg, voting_mode="majority")
    result = c.run(topic, with_critique=True)
    return {
        "ok": True,
        "decision": result.get("decision"),
        "proposals": result.get("proposals"),
        "stage0": result.get("stage0"),
    }


def review_local(ref: str = "HEAD~1", use_mock: bool = True) -> Dict[str, Any]:
    diff = get_git_diff(ref)
    if not diff.strip():
        return {"ok": False, "error": "empty diff", "ref": ref}
    out = review_diff(diff, use_mock=use_mock)
    out["ref"] = ref
    out["diff_chars"] = len(diff)
    return out
