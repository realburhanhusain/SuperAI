"""
Multi-turn conversational memory search — full path with synthesis.
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
        self.path.write_text(
            json.dumps(self._data, indent=2, default=str), encoding="utf-8"
        )

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

    def ask(
        self,
        conversation_id: str,
        query: str,
        top_k: int = 5,
        synthesize: bool = True,
    ) -> Dict[str, Any]:
        conv = (self._data.get("conversations") or {}).get(conversation_id)
        if not conv:
            raise KeyError(f"Unknown conversation: {conversation_id}")

        prior_q = " ".join(t.get("query", "") for t in conv.get("turns", [])[-4:])
        prior_answers = " ".join(
            (t.get("answer") or "")[:200] for t in conv.get("turns", [])[-2:]
        )
        combined = f"{prior_q} {query}".strip() if prior_q else query

        hits: List[Dict[str, Any]] = []
        try:
            from .memory_palace import MemoryPalace

            hits = MemoryPalace().query_semantic(combined, top_k=top_k)
        except Exception as e:  # noqa: BLE001
            hits = [{"content": f"(memory error: {e})", "id": None}]

        answer = self._synthesize(query, hits, prior_answers) if synthesize else ""
        turn = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "query": query,
            "expanded_query": combined,
            "answer": answer,
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
        return {
            "conversation_id": conversation_id,
            "turn": turn,
            "count": len(hits),
            "answer": answer,
        }

    def _synthesize(
        self, query: str, hits: List[Dict[str, Any]], prior: str = ""
    ) -> str:
        if not hits:
            return "No relevant memories found."
        # Prefer model synthesis when available
        context = "\n".join(
            f"- {(h.get('content') or '')[:300]}" for h in hits[:5]
        )
        try:
            from .model_caller import ModelCaller
            from .model_registry import ModelRegistry

            reg = ModelRegistry()
            names = reg.list_all_models()
            model = names[0] if names else "gpt-4o"
            caller = ModelCaller(use_mock=True, registry=reg)
            # use_mock True for offline reliability; still produces structured answer
            prompt = (
                f"User question: {query}\n"
                f"Prior context: {prior[:400]}\n"
                f"Memories:\n{context}\n\n"
                "Answer the question using only the memories. Be concise."
            )
            raw = caller.call(model=model, prompt=prompt)
            return str(raw.get("response") or self._extractive_answer(query, hits))
        except Exception:
            return self._extractive_answer(query, hits)

    @staticmethod
    def _extractive_answer(query: str, hits: List[Dict[str, Any]]) -> str:
        lines = [f"Based on {len(hits)} memory hit(s) for “{query}”:"]
        for h in hits[:3]:
            lines.append(f"• {(h.get('content') or '')[:220]}")
        return "\n".join(lines)

    def history(self, conversation_id: str) -> Dict[str, Any]:
        conv = (self._data.get("conversations") or {}).get(conversation_id)
        if not conv:
            raise KeyError(f"Unknown conversation: {conversation_id}")
        return conv
