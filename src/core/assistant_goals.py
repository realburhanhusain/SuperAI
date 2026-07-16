"""
Personal assistant goals (Phase 8 N2).

Inspired by open assistant patterns: durable goals + schedule hooks + optional messenger.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


class GoalStore:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or (Path.home() / ".superai" / "assistant_goals.json"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.path.is_file():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"goals": []}

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def add(
        self,
        title: str,
        *,
        detail: str = "",
        due_ts: Optional[float] = None,
        priority: str = "normal",
    ) -> Dict[str, Any]:
        g = {
            "id": f"goal-{uuid.uuid4().hex[:8]}",
            "title": title[:300],
            "detail": detail[:2000],
            "status": "open",
            "priority": priority,
            "created_at": time.time(),
            "due_ts": due_ts,
            "last_heartbeat": None,
            "notes": [],
        }
        self.data.setdefault("goals", []).append(g)
        self.save()
        return g

    def list(self, status: Optional[str] = "open") -> List[Dict[str, Any]]:
        goals = self.data.get("goals") or []
        if status:
            return [g for g in goals if g.get("status") == status]
        return list(goals)

    def complete(self, goal_id: str) -> bool:
        for g in self.data.get("goals") or []:
            if g.get("id") == goal_id:
                g["status"] = "done"
                g["completed_at"] = time.time()
                self.save()
                return True
        return False

    def heartbeat(self, goal_id: Optional[str] = None) -> Dict[str, Any]:
        """Mark goals due for attention; return due list."""
        now = time.time()
        due = []
        for g in self.data.get("goals") or []:
            if g.get("status") != "open":
                continue
            due_ts = g.get("due_ts")
            if due_ts is None or float(due_ts) <= now:
                g["last_heartbeat"] = now
                due.append(g)
        self.save()
        if goal_id:
            due = [g for g in due if g.get("id") == goal_id]
        return {"ok": True, "due": due, "count": len(due)}

    def schedule_reminder(
        self,
        goal_id: str,
        every_hours: float = 24.0,
        command: str = "",
    ) -> Dict[str, Any]:
        """Hook into ScheduleStore if available."""
        try:
            from .schedule_store import ScheduleStore

            g = next((x for x in self.list(None) if x.get("id") == goal_id), None)
            title = (g or {}).get("title") or goal_id
            cmd = command or f'ask:progress on goal {title}'
            store = ScheduleStore()
            job = store.add(
                name=f"goal-{goal_id}",
                command=cmd,
                every_hours=float(every_hours),
            )
            return {"ok": True, "job": job}
        except Exception as e:
            return {"ok": False, "error": str(e)[:300]}

    def notify_due(self, message: str = "") -> Dict[str, Any]:
        """Push due goals to messenger bus (file/cli)."""
        hb = self.heartbeat()
        due = hb.get("due") or []
        if not due:
            return {"ok": True, "sent": 0}
        text = message or "SuperAI assistant due goals:\n" + "\n".join(
            f"- {g.get('id')}: {g.get('title')}" for g in due[:10]
        )
        try:
            from .messengers import MessengerBus

            bus = MessengerBus()
            # prefer file outbox
            r = bus.send("file", text)
            return {"ok": True, "sent": len(due), "messenger": r}
        except Exception as e:
            return {"ok": True, "sent": 0, "due": due, "notify_error": str(e)[:200]}
