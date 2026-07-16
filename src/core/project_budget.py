"""Per-project budget policies (V6 S131)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


def _root() -> Path:
    p = Path.home() / ".superai" / "project_budgets"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _key(project: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in (project or "default"))[:80]
    return _root() / f"{safe}.json"


def get_policy(project: str = "default") -> Dict[str, Any]:
    path = _key(project)
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "project": project or "default",
        "daily_usd_limit": 5.0,
        "run_usd_limit": 1.0,
        "daily_token_limit": 500_000,
        "cheap_mode": False,
    }


def set_policy(project: str, **kwargs: Any) -> Dict[str, Any]:
    data = get_policy(project)
    for k, v in kwargs.items():
        if v is not None:
            data[k] = v
    data["project"] = project or "default"
    _key(project).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def apply_to_global(project: str = "default") -> Dict[str, Any]:
    """Push project policy into BudgetGuard limits."""
    pol = get_policy(project)
    from .budget import BudgetGuard

    g = BudgetGuard()
    g.configure(
        daily_usd=float(pol.get("daily_usd_limit") or 5),
        run_usd=float(pol.get("run_usd_limit") or 1),
        daily_tokens=int(pol.get("daily_token_limit") or 500_000),
    )
    if pol.get("cheap_mode"):
        try:
            from .config import Config

            Config().set("prefer_cheap", True)
        except Exception:
            pass
    return {"ok": True, "policy": pol, "snapshot": g.snapshot()}
