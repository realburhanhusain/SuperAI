"""Per-tool timeout configs (V6 S161)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


DEFAULTS = {
    "read": 30.0,
    "write": 30.0,
    "grep": 60.0,
    "glob": 30.0,
    "bash": 120.0,
    "diff_apply": 60.0,
    "model": 180.0,
    "cli": 300.0,
}


def _path() -> Path:
    p = Path.home() / ".superai" / "tool_timeouts.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def load() -> Dict[str, float]:
    data = dict(DEFAULTS)
    if _path().is_file():
        try:
            raw = json.loads(_path().read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for k, v in raw.items():
                    data[str(k)] = float(v)
        except Exception:
            pass
    return data


def get(name: str) -> float:
    return float(load().get(name, DEFAULTS.get(name, 60.0)))


def set_timeout(name: str, seconds: float) -> Dict[str, Any]:
    data = load()
    data[name] = float(seconds)
    _path().write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"ok": True, "timeouts": data}
