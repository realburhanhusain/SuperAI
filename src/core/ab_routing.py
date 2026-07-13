"""
A/B routing experiments (N21).
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class ABRouter:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or (Path.home() / ".superai" / "ab_experiments.json"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        return {"experiments": {}, "results": []}

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def create(
        self,
        name: str,
        model_a: str,
        model_b: str,
        traffic_b_pct: float = 10.0,
        task_type: str = "coding",
    ) -> Dict[str, Any]:
        exp = {
            "name": name,
            "model_a": model_a,
            "model_b": model_b,
            "traffic_b_pct": float(traffic_b_pct),
            "task_type": task_type,
            "enabled": True,
        }
        self.data.setdefault("experiments", {})[name] = exp
        self.save()
        return exp

    def pick(self, task_type: str = "general") -> Optional[str]:
        for exp in (self.data.get("experiments") or {}).values():
            if not exp.get("enabled"):
                continue
            if exp.get("task_type") not in {task_type, "general", "*"}:
                continue
            if random.random() * 100 < float(exp.get("traffic_b_pct") or 0):
                return exp.get("model_b")
            return exp.get("model_a")
        return None

    def record(self, name: str, model: str, success: bool) -> None:
        self.data.setdefault("results", []).append(
            {
                "ts": time.time(),
                "experiment": name,
                "model": model,
                "success": success,
            }
        )
        # cap
        self.data["results"] = self.data["results"][-2000:]
        self.save()

    def stats(self) -> Dict[str, Any]:
        by: Dict[str, Dict[str, int]] = {}
        for r in self.data.get("results") or []:
            key = f"{r.get('experiment')}:{r.get('model')}"
            by.setdefault(key, {"ok": 0, "n": 0})
            by[key]["n"] += 1
            if r.get("success"):
                by[key]["ok"] += 1
        return {
            "experiments": self.data.get("experiments"),
            "results": {
                k: {"n": v["n"], "success_rate": round(v["ok"] / max(1, v["n"]), 3)}
                for k, v in by.items()
            },
        }
