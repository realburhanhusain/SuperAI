"""
Full message session store for SuperAI agent (multi-session).
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


def _root() -> Path:
    import os

    env = (os.getenv("SUPERAI_SESSIONS_ROOT") or "").strip()
    if env:
        p = Path(env)
    else:
        p = Path.home() / ".superai" / "superai_sessions"
    p.mkdir(parents=True, exist_ok=True)
    return p


@dataclass
class SessionState:
    id: str
    created_at: str
    agent: str = "build"
    model: Optional[str] = None
    permission: str = "ask"
    title: str = ""
    messages: List[Dict[str, Any]] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)
    tokens: int = 0
    estimated_cost_usd: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SessionState":
        return cls(
            id=str(d.get("id") or ""),
            created_at=str(d.get("created_at") or ""),
            agent=str(d.get("agent") or "build"),
            model=d.get("model"),
            permission=str(d.get("permission") or "ask"),
            title=str(d.get("title") or ""),
            messages=list(d.get("messages") or []),
            meta=dict(d.get("meta") or {}),
            tokens=int(d.get("tokens") or 0),
            estimated_cost_usd=float(d.get("estimated_cost_usd") or 0),
        )


class SuperAISessionStore:
    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root or _root())
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, sid: str) -> Path:
        return self.root / f"{sid}.json"

    def create(
        self,
        *,
        agent: str = "build",
        model: Optional[str] = None,
        permission: str = "ask",
        title: str = "",
    ) -> SessionState:
        sid = f"sa-{uuid.uuid4().hex[:10]}"
        st = SessionState(
            id=sid,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            agent=agent,
            model=model,
            permission=permission,
            title=title[:120],
        )
        self.save(st)
        return st

    def save(self, state: SessionState) -> None:
        self._path(state.id).write_text(
            json.dumps(state.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )

    def load(self, sid: str) -> SessionState:
        p = self._path(sid)
        if not p.is_file():
            # try legacy oc- prefix path under same root
            raise KeyError(f"Unknown SuperAI agent session: {sid}")
        return SessionState.from_dict(json.loads(p.read_text(encoding="utf-8")))

    def list_sessions(self, limit: int = 30) -> List[Dict[str, Any]]:
        rows = []
        paths = list(self.root.glob("sa-*.json"))
        for p in sorted(paths, reverse=True)[:limit]:
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                rows.append(
                    {
                        "id": d.get("id"),
                        "agent": d.get("agent"),
                        "model": d.get("model"),
                        "messages": len(d.get("messages") or []),
                        "title": d.get("title") or "",
                        "created_at": d.get("created_at"),
                        "tokens": d.get("tokens") or 0,
                        "estimated_cost_usd": d.get("estimated_cost_usd") or 0,
                    }
                )
            except Exception:
                continue
        return rows

    def append_message(
        self,
        state: SessionState,
        role: str,
        content: str,
        *,
        parts: Optional[List[Dict[str, Any]]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> SessionState:
        state.messages.append(
            {
                "id": uuid.uuid4().hex[:8],
                "ts": time.time(),
                "role": role,
                "content": (content or "")[:20000],
                "parts": parts or [{"type": "text", "text": content or ""}],
                "meta": meta or {},
            }
        )
        state.messages = state.messages[-80:]
        if not state.title and role == "user":
            state.title = (content or "")[:80]
        self.save(state)
        return state

    def undo_last_user_assistant(self, state: SessionState) -> SessionState:
        if not state.messages:
            return state
        if state.messages and state.messages[-1].get("role") == "assistant":
            state.messages.pop()
        if state.messages and state.messages[-1].get("role") == "user":
            state.messages.pop()
        self.save(state)
        return state

    def export_markdown(self, state: SessionState, dest: Optional[Path] = None) -> Path:
        lines = [
            f"# SuperAI agent session `{state.id}`",
            "",
            f"- agent: {state.agent}",
            f"- model: {state.model or 'auto'}",
            f"- permission: {state.permission}",
            f"- tokens: {state.tokens}",
            f"- cost≈${state.estimated_cost_usd:.6f}",
            "",
        ]
        for m in state.messages:
            role = m.get("role")
            lines.append(f"## {role}")
            lines.append("")
            lines.append(str(m.get("content") or "")[:8000])
            for p in m.get("parts") or []:
                if p.get("type") == "tool_call":
                    lines.append(
                        f"\n_tool:_ `{p.get('name')}` "
                        f"`{json.dumps(p.get('arguments') or {})[:200]}`"
                    )
                if p.get("type") == "tool_result":
                    lines.append(f"\n_result ok={p.get('ok')}_")
            lines.append("")
        body = "\n".join(lines)
        out = Path(
            dest
            or (
                Path.home()
                / ".superai"
                / "exports"
                / f"{state.id}_{int(time.time())}.md"
            )
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body, encoding="utf-8")
        return out


