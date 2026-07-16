"""
Multi-turn ask session store (Improvement Phase 2 / MoSCoW S7).

Shared root so agent-tui, MCP, and CLI `ask` use the same session files:
  SUPERAI_ASK_SESSION_ROOT or ~/.superai/ask_sessions
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


def default_session_root() -> Path:
    env = (os.getenv("SUPERAI_ASK_SESSION_ROOT") or "").strip()
    if env:
        return Path(env)
    return Path.home() / ".superai" / "ask_sessions"


class AskSessionStore:
    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root or default_session_root())
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

    def get(self, sid: str) -> Dict[str, Any]:
        """Load full session (S7 shared MCP/TUI)."""
        return self._load(sid)

    def ensure(self, sid: Optional[str] = None) -> str:
        """Return existing sid or create new shared session id."""
        if sid:
            p = self._path(sid)
            if p.is_file():
                return sid
            # allow client-provided ids
            data = {
                "id": sid,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "turns": [],
                "shared": True,
            }
            self._save(sid, data)
            return sid
        return self.create()

    def undo_turn(self, sid: str) -> Dict[str, Any]:
        """W3: remove last turn from session."""
        data = self._load(sid)
        turns = data.get("turns") or []
        if not turns:
            return {"ok": False, "error": "no_turns", "session_id": sid}
        removed = turns.pop()
        data["turns"] = turns
        self._save(sid, data)
        return {
            "ok": True,
            "session_id": sid,
            "removed": {
                "user": str(removed.get("user") or "")[:120],
                "assistant": str(removed.get("assistant") or "")[:120],
            },
            "turns_left": len(turns),
        }

    def session_totals(self, sid: str) -> Dict[str, Any]:
        """W4: aggregate tokens/cost from turn meta."""
        data = self._load(sid)
        tokens = 0
        cost = 0.0
        for t in data.get("turns") or []:
            meta = t.get("meta") if isinstance(t.get("meta"), dict) else {}
            try:
                tokens += int(meta.get("tokens") or 0)
            except (TypeError, ValueError):
                pass
            try:
                cost += float(meta.get("estimated_cost_usd") or meta.get("cost") or 0)
            except (TypeError, ValueError):
                pass
        return {
            "ok": True,
            "session_id": sid,
            "turns": len(data.get("turns") or []),
            "tokens": tokens,
            "estimated_cost_usd": round(cost, 6),
            "created_at": data.get("created_at"),
        }

    def export_markdown(
        self,
        sid: str,
        dest: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """W1: export session transcript to markdown."""
        data = self._load(sid)
        lines = [
            f"# SuperAI ask session `{sid}`",
            "",
            f"- created: {data.get('created_at')}",
            f"- turns: {len(data.get('turns') or [])}",
            "",
        ]
        for i, t in enumerate(data.get("turns") or [], 1):
            lines.append(f"## Turn {i}")
            lines.append("")
            lines.append(f"**User:** {t.get('user') or ''}")
            lines.append("")
            lines.append(f"**Assistant:** {t.get('assistant') or ''}")
            meta = t.get("meta") if isinstance(t.get("meta"), dict) else {}
            if meta:
                lines.append("")
                lines.append(f"_meta:_ `{json.dumps(meta, default=str)[:300]}`")
            lines.append("")
        body = "\n".join(lines)
        out = Path(
            dest
            or (
                Path.home()
                / ".superai"
                / "exports"
                / f"{sid}_{int(time.time())}.md"
            )
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body, encoding="utf-8")
        return {"ok": True, "session_id": sid, "path": str(out), "chars": len(body)}
