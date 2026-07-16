"""Agent-maintained todo list across a long task (V6 S101)."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


class AgentTodoStore:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or (Path.home() / ".superai" / "agent_todos.json"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.path.is_file():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"lists": {}}

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def ensure(self, list_id: Optional[str] = None) -> str:
        lid = list_id or f"todo-{uuid.uuid4().hex[:8]}"
        self.data.setdefault("lists", {}).setdefault(
            lid, {"id": lid, "items": [], "created_at": time.time()}
        )
        self.save()
        return lid

    def add(self, list_id: str, text: str) -> Dict[str, Any]:
        self.ensure(list_id)
        item = {
            "id": f"i-{uuid.uuid4().hex[:6]}",
            "text": text[:500],
            "status": "open",
            "ts": time.time(),
        }
        self.data["lists"][list_id]["items"].append(item)
        self.save()
        return item

    def complete(self, list_id: str, item_id: str) -> bool:
        lst = (self.data.get("lists") or {}).get(list_id) or {}
        for it in lst.get("items") or []:
            if it.get("id") == item_id:
                it["status"] = "done"
                it["done_at"] = time.time()
                self.save()
                return True
        return False

    def list_items(self, list_id: str) -> List[Dict[str, Any]]:
        return list(((self.data.get("lists") or {}).get(list_id) or {}).get("items") or [])

    def open_count(self, list_id: str) -> int:
        return sum(1 for i in self.list_items(list_id) if i.get("status") == "open")
