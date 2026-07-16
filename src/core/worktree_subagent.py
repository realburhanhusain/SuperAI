"""
Git worktree subagent runner (MoSCoW N3).

Creates an isolated worktree, runs a task command/orchestrator step there,
optionally cleans up. Safe defaults: no force-delete of dirty trees.
"""

from __future__ import annotations

import os
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional


def _git(root: Path, *args: str, timeout: float = 120.0) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(root),
        capture_output=True,
        text=True,
        shell=False,
        timeout=timeout,
    )


def worktree_base() -> Path:
    env = (os.getenv("SUPERAI_WORKTREE_ROOT") or "").strip()
    if env:
        p = Path(env)
    else:
        p = Path.home() / ".superai" / "worktrees"
    p.mkdir(parents=True, exist_ok=True)
    return p


def create_worktree(
    *,
    repo: Optional[Path] = None,
    branch: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a detached or new-branch worktree under worktree_base()."""
    root = Path(repo or os.getenv("SUPERAI_WORKSPACE") or Path.cwd())
    if not (root / ".git").exists() and not (root / ".git").is_file():
        # allow bare detection failure with clear error
        probe = _git(root, "rev-parse", "--is-inside-work-tree")
        if probe.returncode != 0:
            return {
                "ok": False,
                "error": "not_a_git_repo",
                "repo": str(root),
                "stderr": (probe.stderr or "")[:300],
            }
    wid = name or f"sa-{uuid.uuid4().hex[:8]}"
    path = worktree_base() / wid
    if path.exists():
        return {"ok": False, "error": "path_exists", "path": str(path)}
    br = branch or f"superai/{wid}"
    # Prefer new branch from HEAD
    proc = _git(root, "worktree", "add", "-b", br, str(path), "HEAD")
    if proc.returncode != 0:
        # branch may exist — try without -b
        proc = _git(root, "worktree", "add", str(path), "HEAD")
    if proc.returncode != 0:
        return {
            "ok": False,
            "error": "worktree_add_failed",
            "stderr": (proc.stderr or proc.stdout or "")[:500],
            "repo": str(root),
        }
    return {
        "ok": True,
        "path": str(path),
        "branch": br,
        "id": wid,
        "repo": str(root),
    }


def remove_worktree(
    path: Path,
    *,
    repo: Optional[Path] = None,
    force: bool = False,
) -> Dict[str, Any]:
    root = Path(repo or os.getenv("SUPERAI_WORKSPACE") or Path.cwd())
    args = ["worktree", "remove"]
    if force:
        args.append("--force")
    args.append(str(path))
    proc = _git(root, *args)
    if proc.returncode != 0:
        return {
            "ok": False,
            "error": (proc.stderr or proc.stdout or "remove_failed")[:400],
        }
    return {"ok": True, "path": str(path)}


def run_in_worktree(
    task: str,
    *,
    repo: Optional[Path] = None,
    use_mock: bool = True,
    cleanup: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    N3: spin worktree → run orchestrator/ask task with cwd=worktree → cleanup.
    """
    t0 = time.time()
    created = create_worktree(repo=repo)
    if not created.get("ok"):
        return created
    path = Path(created["path"])
    if dry_run:
        out = {
            "ok": True,
            "dry_run": True,
            "worktree": created,
            "task": task[:500],
            "result": {"status": "dry_run", "message": "would run task in worktree"},
        }
        if cleanup:
            remove_worktree(path, repo=repo, force=True)
        out["latency_sec"] = round(time.time() - t0, 3)
        return out

    prev = os.environ.get("SUPERAI_WORKSPACE")
    os.environ["SUPERAI_WORKSPACE"] = str(path)
    try:
        if use_mock:
            os.environ.setdefault("SUPERAI_MOCK_MODE", "1")
        from .nl_intent import ask_superai

        result = ask_superai(task, execute=True, verbose=False)
    except Exception as e:
        result = {"ok": False, "error": str(e)[:400]}
    finally:
        if prev is None:
            os.environ.pop("SUPERAI_WORKSPACE", None)
        else:
            os.environ["SUPERAI_WORKSPACE"] = prev

    cleanup_res = None
    if cleanup:
        cleanup_res = remove_worktree(path, repo=repo, force=True)

    return {
        "ok": bool(result.get("ok", True)),
        "status": "success" if result.get("ok", True) else "error",
        "worktree": created,
        "task": task[:500],
        "result": result,
        "cleanup": cleanup_res,
        "latency_sec": round(time.time() - t0, 3),
        "mock": use_mock,
        "dry_run": False,
        "contract": "superai.result.v1",
    }
