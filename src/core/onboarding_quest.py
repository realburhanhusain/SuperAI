"""Onboarding quest — first wins checklist (V6 S199)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


STEPS = [
    {"id": "doctor", "title": "Run doctor", "cmd": "superai doctor"},
    {"id": "members", "title": "List members", "cmd": "superai members --available"},
    {"id": "do-mock", "title": "One-shot mock task", "cmd": 'superai do "hello"'},
    {"id": "status-cost", "title": "Check cost status", "cmd": "superai status --cost"},
    {"id": "eval", "title": "Run golden eval", "cmd": "superai eval-golden"},
]


def _path() -> Path:
    p = Path.home() / ".superai" / "onboarding.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def status() -> Dict[str, Any]:
    done = set()
    if _path().is_file():
        try:
            done = set(json.loads(_path().read_text(encoding="utf-8")).get("done") or [])
        except Exception:
            pass
    steps = []
    for s in STEPS:
        steps.append({**s, "done": s["id"] in done})
    return {
        "ok": True,
        "steps": steps,
        "completed": sum(1 for s in steps if s["done"]),
        "total": len(steps),
    }


def mark(step_id: str) -> Dict[str, Any]:
    st = status()
    done = {s["id"] for s in st["steps"] if s["done"]}
    done.add(step_id)
    _path().write_text(json.dumps({"done": sorted(done)}, indent=2), encoding="utf-8")
    return status()
