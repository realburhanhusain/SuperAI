"""
Multi-turn conversational memory search (Future Plan G8).
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


class MemoryConversation:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(
            path or (Path.home() / ".superai" / "memory_conversations.json")
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        return {"conversations": {}}

    def save(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=2, default=str), encoding="utf-8")

    def start(self, seed_query: Optional[str] = None) -> str:
        cid = f"mem-{uuid.uuid4().hex[:10]}"
        self._data.setdefault("conversations", {})[cid] = {
            "id": cid,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "turns": [],
        }
        if seed_query:
            self.ask(cid, seed_query)
        else:
            self.save()
        return cid

    def ask(self, conversation_id: str, query: str, top_k: int = 5) -> Dict[str, Any]:
        conv = (self._data.get("conversations") or {}).get(conversation_id)
        if not conv:
            raise KeyError(f"Unknown conversation: {conversation_id}")

        # Expand query with prior turn context
        prior = " ".join(
            t.get("query", "") for t in conv.get("turns", [])[-3:]
        )
        combined = f"{prior} {query}".strip() if prior else query

        hits: List[Dict[str, Any]] = []
        try:
            from .memory_palace import MemoryPalace

            hits = MemoryPalace().query_semantic(combined, top_k=top_k)
        except Exception as e:  # noqa: BLE001
            hits = [{"content": f"(memory error: {e})", "id": None}]

        turn = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "query": query,
            "expanded_query": combined,
            "results": [
                {
                    "id": h.get("id"),
                    "content": (h.get("content") or "")[:600],
                    "metadata": h.get("metadata"),
                }
                for h in hits
            ],
        }
        conv.setdefault("turns", []).append(turn)
        self.save()
        return {"conversation_id": conversation_id, "turn": turn, "count": len(hits)}

    def history(self, conversation_id: str) -> Dict[str, Any]:
        conv = (self._data.get("conversations") or {}).get(conversation_id)
        if not conv:
            raise KeyError(f"Unknown conversation: {conversation_id}")
        return conv
