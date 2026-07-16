"""
Task history store (Phase 1)

Persists each run under ~/.superai/history/ as JSON.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .errors import HistoryError


class TaskHistory:
    def __init__(self, history_dir: Optional[Path] = None):
        self.history_dir = Path(history_dir or (Path.home() / ".superai" / "history"))
        self.history_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def new_task_id() -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        return f"{stamp}-{uuid.uuid4().hex[:8]}"

    def save(self, record: Dict[str, Any]) -> Path:
        import re

        task_id = record.get("task_id") or self.new_task_id()
        task_id = str(task_id)
        if not re.fullmatch(r"[A-Za-z0-9._-]+", task_id):
            raise HistoryError(f"Invalid task_id: {task_id!r}")
        record = {**record, "task_id": task_id}
        path = self.history_dir / f"{task_id}.json"
        try:
            from .secrets import redact_obj

            safe = redact_obj(record)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(safe, f, indent=2, default=str)
        except OSError as e:
            raise HistoryError(f"Failed to write history: {e}") from e
        return path

    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        path = self.history_dir / f"{task_id}.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list(self, limit: int = 20) -> List[Dict[str, Any]]:
        files = sorted(self.history_dir.glob("*.json"), reverse=True)
        records: List[Dict[str, Any]] = []
        for path in files[: max(limit, 0)]:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    records.append(json.load(f))
            except (OSError, json.JSONDecodeError):
                continue
        return records

    def count(self) -> int:
        return len(list(self.history_dir.glob("*.json")))

    def search(
        self,
        *,
        task: Optional[str] = None,
        model: Optional[str] = None,
        min_cost: Optional[float] = None,
        max_cost: Optional[float] = None,
        success: Optional[bool] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search run history by task text, model, cost, success (V6 M067)."""
        q_task = (task or "").lower().strip()
        q_model = (model or "").lower().strip()
        out: List[Dict[str, Any]] = []
        for rec in self.list(limit=max(limit * 5, 100)):
            if q_task:
                blob = " ".join(
                    str(rec.get(k) or "")
                    for k in ("task", "prompt", "description", "subject", "kind")
                ).lower()
                if q_task not in blob:
                    continue
            if q_model:
                if q_model not in str(rec.get("model") or "").lower():
                    continue
            cost = float(rec.get("estimated_cost_usd") or rec.get("cost") or 0)
            if min_cost is not None and cost < float(min_cost):
                continue
            if max_cost is not None and cost > float(max_cost):
                continue
            if success is not None and bool(rec.get("success")) != bool(success):
                continue
            out.append(rec)
            if len(out) >= limit:
                break
        return out
