"""
Memory Wings & Rooms (Phase 8 / Track I).

Organizational layer over Memory Palace topics.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_WINGS = {
    "technical": {
        "description": "Code, infrastructure, debugging",
        "rooms": ["coding", "infra", "debugging", "architecture"],
    },
    "operations": {
        "description": "Runtime ops, incidents, deployments",
        "rooms": ["incidents", "deployments", "monitoring"],
    },
    "product": {
        "description": "Product decisions and requirements",
        "rooms": ["requirements", "ux", "roadmap"],
    },
    "learning": {
        "description": "Meta-learning and reflections",
        "rooms": ["successes", "failures", "conflicts"],
    },
}


class WingsManager:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or (Path.home() / ".superai" / "wings.json"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"wings": DEFAULT_WINGS, "assignments": []}

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def list_wings(self) -> Dict[str, Any]:
        return self.data.get("wings") or DEFAULT_WINGS

    def assign(
        self,
        memory_id: str,
        wing: str,
        room: str,
        note: str = "",
    ) -> Dict[str, Any]:
        wings = self.list_wings()
        if wing not in wings:
            raise KeyError(f"Unknown wing: {wing}")
        rooms = wings[wing].get("rooms") or []
        if room not in rooms:
            # allow dynamic room creation
            rooms.append(room)
            wings[wing]["rooms"] = rooms
            self.data["wings"] = wings
        entry = {
            "memory_id": memory_id,
            "wing": wing,
            "room": room,
            "note": note,
        }
        self.data.setdefault("assignments", []).append(entry)
        self.save()
        return entry

    def for_memory(self, memory_id: str) -> List[Dict[str, Any]]:
        return [
            a
            for a in self.data.get("assignments", [])
            if a.get("memory_id") == memory_id
        ]

    def classify_task_type(self, task_type: str) -> Dict[str, str]:
        """Map task_type to default wing/room."""
        t = (task_type or "general").lower()
        if t in {"coding", "implementation"}:
            return {"wing": "technical", "room": "coding"}
        if t in {"research"}:
            return {"wing": "product", "room": "requirements"}
        if t in {"reasoning"}:
            return {"wing": "learning", "room": "successes"}
        return {"wing": "learning", "room": "successes"}
