"""
Audit log for tool/CLI side effects (V3 Sprint C S8).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def _path() -> Path:
    p = Path.home() / ".superai" / "side_effects.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def record_side_effect(
    kind: str,
    *,
    name: str = "",
    ok: bool = True,
    dry_run: bool = False,
    detail: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    entry = {
        "ts": time.time(),
        "kind": kind,
        "name": name,
        "ok": ok,
        "dry_run": dry_run,
        "detail": detail[:500],
        "extra": extra or {},
    }
    try:
        with open(_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception:
        pass
    try:
        from .audit_log import AuditLog

        AuditLog().record("side_effect", entry)
    except Exception:
        pass


def recent(limit: int = 50) -> List[Dict[str, Any]]:
    p = _path()
    if not p.is_file():
        return []
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    out = []
    for line in lines[-limit:]:
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out
