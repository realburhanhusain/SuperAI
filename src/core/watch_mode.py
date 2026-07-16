"""Watch mode foundation (V6 N205) — re-run task on file change (poll)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional


def snapshot(root: Path, glob: str = "**/*.{py,ts,js,go,rs}") -> Dict[str, float]:
    # simple mtime map; glob may be simple suffix filter
    out: Dict[str, float] = {}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in {
            ".py",
            ".ts",
            ".tsx",
            ".js",
            ".go",
            ".rs",
            ".md",
        }:
            continue
        try:
            out[str(p.relative_to(root))] = p.stat().st_mtime
        except Exception:
            continue
    return out


def watch_once(
    root: Path,
    prev: Dict[str, float],
) -> Dict[str, Any]:
    cur = snapshot(root)
    changed = [k for k, v in cur.items() if prev.get(k) != v]
    for k in prev:
        if k not in cur:
            changed.append(k)
    return {"changed": sorted(set(changed))[:50], "snapshot": cur}


def run_watch(
    task_fn: Callable[[], Dict[str, Any]],
    *,
    root: Optional[Path] = None,
    interval_sec: float = 2.0,
    max_iters: int = 3,
) -> Dict[str, Any]:
    """
    Poll a few times; invoke task_fn when changes detected.
    max_iters keeps this safe for unit tests / non-daemon use.
    """
    r = Path(root or Path.cwd())
    prev = snapshot(r)
    runs = []
    for i in range(max(1, max_iters)):
        time.sleep(max(0.05, interval_sec if i else 0.05))
        w = watch_once(r, prev)
        prev = w["snapshot"]
        if w["changed"] or i == 0:
            try:
                out = task_fn()
            except Exception as e:
                out = {"ok": False, "error": str(e)[:200]}
            runs.append({"iter": i, "changed": w["changed"], "result": out})
    return {"ok": True, "runs": runs, "iters": len(runs)}
