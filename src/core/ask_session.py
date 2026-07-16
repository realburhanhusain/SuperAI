"""
Multi-turn ask session store (Improvement Phase 2).
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


class AskSessionStore:
    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root or (Path.home() / ".superai" / "ask_sessions"))
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, sid: str) -> Path:
        return self.root / f"{sid}.json"

    def create(self) -> str:
        sid = f"ask-{uuid.uuid4().hex[:10]}"
        data = {
            "id": sid,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "turns": [],
        }
        self._save(sid, data)
        return sid

    def _load(self, sid: str) -> Dict[str, Any]:
        p = self._path(sid)
        if not p.is_file():
            raise KeyError(f"Unknown ask session: {sid}")
        return json.loads(p.read_text(encoding="utf-8"))

    def _save(self, sid: str, data: Dict[str, Any]) -> None:
        self._path(sid).write_text(json.dumps(data, indent=2), encoding="utf-8")

    def append_turn(
        self,
        sid: str,
        user: str,
        assistant_summary: str,
        *,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        data = self._load(sid)
        data.setdefault("turns", []).append(
            {
                "ts": time.time(),
                "user": user[:4000],
                "assistant": assistant_summary[:4000],
                "meta": meta or {},
            }
        )
        # keep last 40 turns
        data["turns"] = data["turns"][-40:]
        self._save(sid, data)
        return data

    def context_preface(self, sid: str, max_turns: int = 6) -> str:
        try:
            data = self._load(sid)
        except KeyError:
            return ""
        turns = (data.get("turns") or [])[-max_turns:]
        if not turns:
            return ""
        lines = ["[Prior ask session context]"]
        for t in turns:
            lines.append(f"User: {t.get('user', '')[:500]}")
            lines.append(f"Assistant: {t.get('assistant', '')[:500]}")
        return "\n".join(lines)

    def list_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        rows = []
        for p in sorted(self.root.glob("ask-*.json"), reverse=True)[:limit]:
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                rows.append(
                    {
                        "id": d.get("id"),
                        "turns": len(d.get("turns") or []),
                        "created_at": d.get("created_at"),
                    }
                )
            except Exception:
                continue
        return rows
