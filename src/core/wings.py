"""
Memory Wings & Rooms (Phase 8 / Track I) — palace organization layer.

Wings = major domains; Rooms = topics within a wing.
Assignments live in ~/.superai/wings.json and are also mirrored into
MemoryPalace memory metadata (wing / room) for filterable retrieval.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_WINGS = {
    "technical": {
        "description": "Code, infrastructure, debugging",
        "rooms": ["coding", "infra", "debugging", "architecture", "testing", "security"],
    },
    "operations": {
        "description": "Runtime ops, incidents, deployments",
        "rooms": ["incidents", "deployments", "monitoring", "budget", "backup"],
    },
    "product": {
        "description": "Product decisions and requirements",
        "rooms": ["requirements", "ux", "roadmap", "research"],
    },
    "learning": {
        "description": "Meta-learning and reflections",
        "rooms": ["successes", "failures", "conflicts", "patterns", "general"],
    },
    "agentic": {
        "description": "Multi-CLI / multi-agent workflows",
        "rooms": ["cli_pool", "terminals", "council", "mcp", "orchestration"],
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
                data = json.loads(self.path.read_text(encoding="utf-8"))
                # Merge new default wings without wiping user rooms
                wings = dict(DEFAULT_WINGS)
                for k, v in (data.get("wings") or {}).items():
                    if k in wings and isinstance(v, dict):
                        rooms = list(
                            dict.fromkeys(
                                list(wings[k].get("rooms") or [])
                                + list(v.get("rooms") or [])
                            )
                        )
                        wings[k] = {
                            "description": v.get("description")
                            or wings[k].get("description"),
                            "rooms": rooms,
                        }
                    else:
                        wings[k] = v
                data["wings"] = wings
                data.setdefault("assignments", [])
                return data
            except Exception:
                pass
        return {"wings": json.loads(json.dumps(DEFAULT_WINGS)), "assignments": []}

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def list_wings(self) -> Dict[str, Any]:
        return self.data.get("wings") or DEFAULT_WINGS

    def list_rooms(self, wing: str) -> List[str]:
        wings = self.list_wings()
        if wing not in wings:
            raise KeyError(f"Unknown wing: {wing}")
        return list((wings[wing] or {}).get("rooms") or [])

    def assign(
        self,
        memory_id: str,
        wing: str,
        room: str,
        note: str = "",
    ) -> Dict[str, Any]:
        wings = self.list_wings()
        if wing not in wings:
            # allow new wing
            wings[wing] = {"description": f"User wing {wing}", "rooms": [room]}
            self.data["wings"] = wings
        rooms = wings[wing].get("rooms") or []
        if room not in rooms:
            rooms.append(room)
            wings[wing]["rooms"] = rooms
            self.data["wings"] = wings
        # de-dupe latest assignment for this memory
        assigns = [
            a
            for a in (self.data.get("assignments") or [])
            if a.get("memory_id") != memory_id
        ]
        entry = {
            "memory_id": memory_id,
            "wing": wing,
            "room": room,
            "note": note,
        }
        assigns.append(entry)
        self.data["assignments"] = assigns[-5000:]  # cap growth
        self.save()
        return entry

    def for_memory(self, memory_id: str) -> List[Dict[str, Any]]:
        return [
            a
            for a in self.data.get("assignments", [])
            if a.get("memory_id") == memory_id
        ]

    def latest_for_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        items = self.for_memory(memory_id)
        return items[-1] if items else None

    def classify_task_type(
        self,
        task_type: str = "",
        *,
        content: str = "",
        tags: Optional[List[str]] = None,
        success: Optional[bool] = None,
        source: str = "",
    ) -> Dict[str, str]:
        """
        Map task_type / tags / content / source → default wing/room.
        Richer than the old if/else map.
        """
        t = (task_type or "general").lower().strip()
        src = (source or "").lower()
        tag_set = {str(x).lower() for x in (tags or [])}
        blob = f"{t} {content[:500]} {' '.join(tag_set)} {src}".lower()

        # Explicit task types take priority (orchestrator runs are often coding/etc.)
        type_map = {
            "coding": ("technical", "coding"),
            "implementation": ("technical", "coding"),
            "debug": ("technical", "debugging"),
            "debugging": ("technical", "debugging"),
            "architecture": ("technical", "architecture"),
            "testing": ("technical", "testing"),
            "security": ("technical", "security"),
            "infra": ("technical", "infra"),
            "research": ("product", "research"),
            "reasoning": ("learning", "patterns"),
            "general": ("learning", "general"),
            "agentic": ("agentic", "orchestration"),
        }
        if t in type_map and t not in {"general"}:
            wing, room = type_map[t]
            if success is False and wing == "learning":
                room = "failures"
            elif success is True and wing == "learning" and room == "general":
                room = "successes"
            return {"wing": wing, "room": room}

        # Source / agentic cues (when task_type is general/unknown)
        if any(
            x in blob
            for x in (
                "cli_pool",
                "cli:",
                "mcp_client",
                "mcp_server",
                "mcp ",
                "council",
                "term-parallel",
                "agentic",
                "cli_parallel",
            )
        ):
            if "mcp" in blob:
                return {"wing": "agentic", "room": "mcp"}
            if "council" in blob:
                return {"wing": "agentic", "room": "council"}
            if "term" in blob:
                return {"wing": "agentic", "room": "terminals"}
            if "cli" in blob:
                return {"wing": "agentic", "room": "cli_pool"}
            return {"wing": "agentic", "room": "orchestration"}

        if t in type_map:
            wing, room = type_map[t]
        else:
            # keyword rules
            if any(k in blob for k in ("pytest", "unit test", "tdd", "coverage")):
                wing, room = "technical", "testing"
            elif any(k in blob for k in ("deploy", "kubernetes", "docker", "ci/cd")):
                wing, room = "operations", "deployments"
            elif any(k in blob for k in ("incident", "outage", "oncall", "alert")):
                wing, room = "operations", "incidents"
            elif any(k in blob for k in ("budget", "cost", "spend")):
                wing, room = "operations", "budget"
            elif any(k in blob for k in ("backup", "rclone", "restore")):
                wing, room = "operations", "backup"
            elif any(k in blob for k in ("ux", "ui", "design", "user")):
                wing, room = "product", "ux"
            elif any(k in blob for k in ("requirement", "roadmap", "spec")):
                wing, room = "product", "requirements"
            elif any(k in blob for k in ("fastapi", "api", "code", "implement", "refactor")):
                wing, room = "technical", "coding"
            elif any(k in blob for k in ("architect", "design system")):
                wing, room = "technical", "architecture"
            else:
                wing, room = "learning", "general"

        if success is False and wing == "learning":
            room = "failures"
        elif success is True and wing == "learning" and room == "general":
            room = "successes"
        elif success is False and "fail" not in room:
            # keep domain wing but note failure room when learning
            if wing == "learning":
                room = "failures"

        return {"wing": wing, "room": room}

    def classify_from_metadata(
        self, metadata: Optional[Dict[str, Any]] = None, content: str = ""
    ) -> Dict[str, str]:
        meta = metadata or {}
        tags = meta.get("tags")
        if isinstance(tags, str):
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        elif isinstance(tags, list):
            tag_list = [str(t) for t in tags]
        else:
            tag_list = []
        success = meta.get("success")
        if isinstance(success, str):
            success = success.lower() in {"1", "true", "yes"}
        return self.classify_task_type(
            str(meta.get("task_type") or "general"),
            content=content,
            tags=tag_list,
            success=success if isinstance(success, bool) else None,
            source=str(meta.get("source") or ""),
        )

    def stats(self) -> Dict[str, Any]:
        """Counts from assignment log."""
        by_wing: Dict[str, int] = Counter()
        by_room: Dict[str, int] = Counter()
        for a in self.data.get("assignments") or []:
            by_wing[str(a.get("wing") or "?")] += 1
            by_room[f"{a.get('wing')}/{a.get('room')}"] += 1
        return {
            "wings": self.list_wings(),
            "assignment_count": len(self.data.get("assignments") or []),
            "by_wing": dict(by_wing),
            "by_room": dict(by_room.most_common(30)),
        }

    def browse(
        self,
        wing: Optional[str] = None,
        room: Optional[str] = None,
        limit: int = 40,
    ) -> Dict[str, Any]:
        """List recent assignments filtered by wing/room."""
        items = list(self.data.get("assignments") or [])
        if wing:
            items = [a for a in items if a.get("wing") == wing]
        if room:
            items = [a for a in items if a.get("room") == room]
        items = list(reversed(items))[:limit]
        return {
            "wing": wing,
            "room": room,
            "count": len(items),
            "assignments": items,
        }

    def sync_assignments_from_memories(
        self, memories: List[Dict[str, Any]]
    ) -> int:
        """Backfill assignment index from memory metadata wing/room fields."""
        n = 0
        for m in memories:
            mid = m.get("id")
            meta = m.get("metadata") or {}
            wing = meta.get("wing")
            room = meta.get("room")
            if mid and wing and room:
                self.assign(str(mid), str(wing), str(room), note="sync_from_metadata")
                n += 1
        return n
