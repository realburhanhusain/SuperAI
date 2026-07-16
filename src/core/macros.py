"""Command macros / aliases (V6 N203)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


def _path() -> Path:
    p = Path.home() / ".superai" / "macros.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def load() -> Dict[str, str]:
    path = _path()
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except Exception:
            pass
    return {}


def save(macros: Dict[str, str]) -> None:
    _path().write_text(json.dumps(macros, indent=2), encoding="utf-8")


def set_macro(name: str, command: str) -> Dict[str, Any]:
    m = load()
    m[name] = command
    save(m)
    return {"ok": True, "name": name, "command": command}


def get_macro(name: str) -> Optional[str]:
    return load().get(name)


def list_macros() -> Dict[str, Any]:
    m = load()
    return {"ok": True, "macros": m, "count": len(m)}
