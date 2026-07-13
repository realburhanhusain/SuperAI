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
        task_id = record.get("task_id") or self.new_task_id()
        record = {**record, "task_id": task_id}
        path = self.history_dir / f"{task_id}.json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2, default=str)
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
