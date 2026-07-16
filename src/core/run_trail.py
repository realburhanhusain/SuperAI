"""
Unified run trail (V4 M7) — one run_id linking session, tools, cost, models.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


def new_run_id() -> str:
    return f"run-{uuid.uuid4().hex[:12]}"


def _path() -> Path:
    p = Path.home() / ".superai" / "run_trails.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def append_event(
    run_id: str,
    kind: str,
    **payload: Any,
) -> Dict[str, Any]:
    row = {
        "run_id": run_id,
        "ts": time.time(),
        "kind": kind,
        **{k: v for k, v in payload.items() if v is not None},
    }
    try:
        with open(_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(row, default=str) + "\n")
    except Exception:
        pass
    try:
        from .side_effect_audit import record_side_effect

        record_side_effect(
            "run_trail",
            name=kind,
            ok=bool(payload.get("ok", True)),
            dry_run=bool(payload.get("dry_run", False)),
            detail=f"{run_id}:{str(payload.get('detail') or '')[:160]}",
        )
    except Exception:
        pass
    return row


def recent_for_run(run_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    p = _path()
    if not p.is_file():
        return []
    rows: List[Dict[str, Any]] = []
    try:
        for line in p.read_text(encoding="utf-8").splitlines()[-2000:]:
            try:
                o = json.loads(line)
            except Exception:
                continue
            if o.get("run_id") == run_id:
                rows.append(o)
    except Exception:
        return []
    return rows[-limit:]
