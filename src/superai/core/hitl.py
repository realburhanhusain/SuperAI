"""
Human-in-the-loop: clarification requests + veto (Future Plan G11).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class HITLStore:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or (Path.home() / ".superai" / "hitl.json"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        return {"clarifications": [], "vetoes": []}

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def request_clarification(
        self,
        task_id: str,
        question: str,
        context: str = "",
    ) -> Dict[str, Any]:
        entry = {
            "id": f"cl-{int(time.time()*1000)}",
            "task_id": task_id,
            "question": question,
            "context": context,
            "status": "open",
            "answer": None,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self.data.setdefault("clarifications", []).append(entry)
        self.save()
        return entry

    def answer_clarification(self, clar_id: str, answer: str) -> Optional[Dict[str, Any]]:
        for c in self.data.get("clarifications") or []:
            if c.get("id") == clar_id:
                c["answer"] = answer
                c["status"] = "answered"
                c["answered_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                self.save()
                return c
        return None

    def veto(self, task_id: str, reason: str = "") -> Dict[str, Any]:
        entry = {
            "task_id": task_id,
            "reason": reason,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self.data.setdefault("vetoes", []).append(entry)
        # also mark open clarifications cancelled
        for c in self.data.get("clarifications") or []:
            if c.get("task_id") == task_id and c.get("status") == "open":
                c["status"] = "vetoed"
        self.save()
        return entry

    def is_vetoed(self, task_id: str) -> bool:
        return any(v.get("task_id") == task_id for v in (self.data.get("vetoes") or []))

    def open_clarifications(self, task_id: Optional[str] = None) -> List[Dict[str, Any]]:
        out = []
        for c in self.data.get("clarifications") or []:
            if c.get("status") != "open":
                continue
            if task_id and c.get("task_id") != task_id:
                continue
            out.append(c)
        return out

    def list_all(self) -> Dict[str, Any]:
        return {
            "clarifications": list(self.data.get("clarifications") or [])[-20:],
            "vetoes": list(self.data.get("vetoes") or [])[-20:],
        }
