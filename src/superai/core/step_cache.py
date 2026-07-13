"""
Persistent step-result cache and execution resume (Future Plan G3).
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class StepResultCache:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(
            path or (Path.home() / ".superai" / "step_cache.json")
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        return {"entries": {}, "runs": {}}

    def save(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=2, default=str), encoding="utf-8")

    @staticmethod
    def cache_key(step_description: str, model: Optional[str] = None) -> str:
        raw = f"{model or 'auto'}::{(step_description or '').strip().lower()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    def get(self, step_description: str, model: Optional[str] = None) -> Optional[Dict[str, Any]]:
        key = self.cache_key(step_description, model)
        entry = (self._data.get("entries") or {}).get(key)
        if not entry:
            return None
        # Optional TTL 7 days
        if time.time() - float(entry.get("ts") or 0) > 7 * 86400:
            return None
        return entry.get("result")

    def put(
        self,
        step_description: str,
        result: Dict[str, Any],
        model: Optional[str] = None,
    ) -> str:
        key = self.cache_key(step_description, model)
        self._data.setdefault("entries", {})[key] = {
            "ts": time.time(),
            "model": model,
            "description": step_description[:200],
            "result": result,
        }
        # Cap size
        entries = self._data["entries"]
        if len(entries) > 500:
            # drop oldest
            ordered = sorted(entries.items(), key=lambda kv: kv[1].get("ts") or 0)
            for k, _ in ordered[: len(entries) - 500]:
                entries.pop(k, None)
        self.save()
        return key

    def save_run_checkpoint(
        self,
        task_id: str,
        task: str,
        completed_steps: List[Dict[str, Any]],
        remaining_step_ids: List[int],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._data.setdefault("runs", {})[task_id] = {
            "task": task,
            "completed_steps": completed_steps,
            "remaining_step_ids": remaining_step_ids,
            "metadata": metadata or {},
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self.save()

    def get_run(self, task_id: str) -> Optional[Dict[str, Any]]:
        return (self._data.get("runs") or {}).get(task_id)

    def list_runs(self) -> List[Dict[str, Any]]:
        out = []
        for tid, r in (self._data.get("runs") or {}).items():
            out.append({"task_id": tid, **r})
        out.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
        return out

    def clear_run(self, task_id: str) -> bool:
        runs = self._data.get("runs") or {}
        if task_id in runs:
            del runs[task_id]
            self.save()
            return True
        return False
