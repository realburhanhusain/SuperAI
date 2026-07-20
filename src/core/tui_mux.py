"""
N208 — Multiplexed sessions (tmux-like).

Manages multiple SuperAI agent sessions as "windows" in a named mux:
- new / kill / select / next / prev / rename
- attach session_id into a window
- status bar string for TUI
- persist under ~/.superai/tui/mux.json

For OS-level process panes (PTY/pipe workers), see `tui_process_mux.ProcessMux`
and CLI `superai process-mux` / agent `/pmux`.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class MuxWindow:
    id: str
    session_id: str
    title: str = ""
    agent: str = "build"
    created_at: str = ""
    last_active: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MuxWindow":
        return cls(
            id=str(d.get("id") or ""),
            session_id=str(d.get("session_id") or ""),
            title=str(d.get("title") or ""),
            agent=str(d.get("agent") or "build"),
            created_at=str(d.get("created_at") or ""),
            last_active=str(d.get("last_active") or ""),
        )


@dataclass
class MuxState:
    name: str = "default"
    active_index: int = 0
    windows: List[MuxWindow] = field(default_factory=list)
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "active_index": self.active_index,
            "windows": [w.to_dict() for w in self.windows],
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]) -> "MuxState":
        if not d or not isinstance(d, dict):
            return cls()
        wins = []
        for w in d.get("windows") or []:
            if isinstance(w, dict):
                wins.append(MuxWindow.from_dict(w))
        idx = int(d.get("active_index") or 0)
        if wins:
            idx = max(0, min(idx, len(wins) - 1))
        else:
            idx = 0
        return cls(
            name=str(d.get("name") or "default"),
            active_index=idx,
            windows=wins,
            updated_at=d.get("updated_at"),
        )


def mux_path() -> Path:
    p = Path.home() / ".superai" / "tui" / "mux.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def load_mux() -> MuxState:
    path = mux_path()
    if path.is_file():
        try:
            return MuxState.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            pass
    return MuxState()


def save_mux(state: MuxState) -> Path:
    state.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    path = mux_path()
    path.write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
    return path


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _win_id() -> str:
    return f"w-{uuid.uuid4().hex[:8]}"


class SessionMux:
    """tmux-like window manager over SuperAI agent sessions."""

    def __init__(self, state: Optional[MuxState] = None, *, persist: bool = True):
        self.state = state or load_mux()
        self.persist = persist

    def _save(self) -> None:
        if self.persist:
            save_mux(self.state)

    def status(self) -> Dict[str, Any]:
        from .spend_guard import ensure_public_result

        active = self.active_window()
        return ensure_public_result(
            {
                "ok": True,
                "name": self.state.name,
                "window_count": len(self.state.windows),
                "active_index": self.state.active_index,
                "active": active.to_dict() if active else None,
                "windows": [w.to_dict() for w in self.state.windows],
                "bar": self.status_bar(),
                "path": str(mux_path()),
            },
            ok=True,
        )

    def status_bar(self) -> str:
        if not self.state.windows:
            return f"[{self.state.name}] (no windows)"
        parts = []
        for i, w in enumerate(self.state.windows):
            mark = "*" if i == self.state.active_index else " "
            title = (w.title or w.session_id or w.id)[:18]
            parts.append(f"{mark}{i}:{title}")
        return f"[{self.state.name}] " + " | ".join(parts)

    def active_window(self) -> Optional[MuxWindow]:
        if not self.state.windows:
            return None
        i = max(0, min(self.state.active_index, len(self.state.windows) - 1))
        self.state.active_index = i
        return self.state.windows[i]

    def list_windows(self) -> List[Dict[str, Any]]:
        out = []
        for i, w in enumerate(self.state.windows):
            d = w.to_dict()
            d["index"] = i
            d["active"] = i == self.state.active_index
            out.append(d)
        return out

    def new_window(
        self,
        *,
        session_id: Optional[str] = None,
        title: str = "",
        agent: str = "build",
        create_session: bool = True,
    ) -> Dict[str, Any]:
        from .spend_guard import ensure_public_result

        sid = session_id
        if not sid and create_session:
            try:
                from .superai_agent.session import SuperAISessionStore

                st = SuperAISessionStore().create(agent=agent, title=title or "")
                sid = st.id
            except Exception:
                sid = f"sa-pending-{uuid.uuid4().hex[:8]}"
        if not sid:
            return ensure_public_result(
                {"ok": False, "error": "session_id_required"}, ok=False
            )
        w = MuxWindow(
            id=_win_id(),
            session_id=sid,
            title=(title or sid)[:80],
            agent=agent,
            created_at=_now(),
            last_active=_now(),
        )
        self.state.windows.append(w)
        self.state.active_index = len(self.state.windows) - 1
        self._save()
        return ensure_public_result(
            {
                "ok": True,
                "created": w.to_dict(),
                "active_index": self.state.active_index,
                "bar": self.status_bar(),
            },
            ok=True,
        )

    def attach(self, session_id: str, *, title: str = "") -> Dict[str, Any]:
        """Attach existing session as a window (or select if already present)."""
        from .spend_guard import ensure_public_result

        sid = (session_id or "").strip()
        if not sid:
            return ensure_public_result({"ok": False, "error": "session_id_required"}, ok=False)
        for i, w in enumerate(self.state.windows):
            if w.session_id == sid:
                self.state.active_index = i
                w.last_active = _now()
                self._save()
                return ensure_public_result(
                    {
                        "ok": True,
                        "selected": w.to_dict(),
                        "active_index": i,
                        "already": True,
                        "bar": self.status_bar(),
                    },
                    ok=True,
                )
        return self.new_window(session_id=sid, title=title or sid, create_session=False)

    def select(self, index: int) -> Dict[str, Any]:
        from .spend_guard import ensure_public_result

        if not self.state.windows:
            return ensure_public_result({"ok": False, "error": "no_windows"}, ok=False)
        if index < 0 or index >= len(self.state.windows):
            return ensure_public_result(
                {
                    "ok": False,
                    "error": "index_out_of_range",
                    "index": index,
                    "count": len(self.state.windows),
                },
                ok=False,
            )
        self.state.active_index = index
        self.state.windows[index].last_active = _now()
        self._save()
        return ensure_public_result(
            {
                "ok": True,
                "active_index": index,
                "active": self.state.windows[index].to_dict(),
                "bar": self.status_bar(),
            },
            ok=True,
        )

    def select_by_id(self, window_id: str) -> Dict[str, Any]:
        for i, w in enumerate(self.state.windows):
            if w.id == window_id or w.session_id == window_id:
                return self.select(i)
        from .spend_guard import ensure_public_result

        return ensure_public_result(
            {"ok": False, "error": "window_not_found", "id": window_id}, ok=False
        )

    def next_window(self) -> Dict[str, Any]:
        if not self.state.windows:
            from .spend_guard import ensure_public_result

            return ensure_public_result({"ok": False, "error": "no_windows"}, ok=False)
        n = (self.state.active_index + 1) % len(self.state.windows)
        return self.select(n)

    def prev_window(self) -> Dict[str, Any]:
        if not self.state.windows:
            from .spend_guard import ensure_public_result

            return ensure_public_result({"ok": False, "error": "no_windows"}, ok=False)
        n = (self.state.active_index - 1) % len(self.state.windows)
        return self.select(n)

    def kill_window(self, index: Optional[int] = None) -> Dict[str, Any]:
        from .spend_guard import ensure_public_result

        if not self.state.windows:
            return ensure_public_result({"ok": False, "error": "no_windows"}, ok=False)
        i = self.state.active_index if index is None else int(index)
        if i < 0 or i >= len(self.state.windows):
            return ensure_public_result({"ok": False, "error": "index_out_of_range"}, ok=False)
        killed = self.state.windows.pop(i)
        if not self.state.windows:
            self.state.active_index = 0
        elif self.state.active_index >= len(self.state.windows):
            self.state.active_index = len(self.state.windows) - 1
        elif i < self.state.active_index:
            self.state.active_index -= 1
        self._save()
        return ensure_public_result(
            {
                "ok": True,
                "killed": killed.to_dict(),
                "active_index": self.state.active_index,
                "window_count": len(self.state.windows),
                "bar": self.status_bar(),
            },
            ok=True,
        )

    def rename(self, title: str, *, index: Optional[int] = None) -> Dict[str, Any]:
        from .spend_guard import ensure_public_result

        if not self.state.windows:
            return ensure_public_result({"ok": False, "error": "no_windows"}, ok=False)
        i = self.state.active_index if index is None else int(index)
        if i < 0 or i >= len(self.state.windows):
            return ensure_public_result({"ok": False, "error": "index_out_of_range"}, ok=False)
        self.state.windows[i].title = (title or "")[:80]
        self._save()
        return ensure_public_result(
            {
                "ok": True,
                "window": self.state.windows[i].to_dict(),
                "bar": self.status_bar(),
            },
            ok=True,
        )

    def rename_mux(self, name: str) -> Dict[str, Any]:
        from .spend_guard import ensure_public_result

        self.state.name = (name or "default").strip()[:40] or "default"
        self._save()
        return ensure_public_result(
            {"ok": True, "name": self.state.name, "bar": self.status_bar()}, ok=True
        )

    def sync_active_session(self, session_id: str, *, title: str = "", agent: str = "") -> None:
        """Update active window metadata after agent operations."""
        w = self.active_window()
        if not w:
            self.new_window(
                session_id=session_id,
                title=title,
                agent=agent or "build",
                create_session=False,
            )
            return
        w.session_id = session_id
        if title:
            w.title = title[:80]
        if agent:
            w.agent = agent
        w.last_active = _now()
        self._save()


MUX_HELP = """
### Multiplexed sessions (N208, tmux-like)

| Command | Action |
|---------|--------|
| `/mux` `/mux status` | Show windows + status bar |
| `/mux new [title]` | New window (+ new agent session) |
| `/mux attach <session_id>` | Attach existing session |
| `/mux select <n\\|id>` | Select window by index or id |
| `/mux next` `/mux prev` | Cycle windows |
| `/mux kill [n]` | Kill window (default: active) |
| `/mux rename <title>` | Rename active window |
| `/mux name <mux_name>` | Rename the mux itself |
| `/mux list` | List windows JSON |
| `/w` `/window` | Alias for `/mux next` |

CLI: `superai mux status|new|list|select|next|prev|kill|rename|attach`
"""


def handle_mux_slash(arg: str = "", *, mux: Optional[SessionMux] = None) -> Dict[str, Any]:
    """Parse `/mux …` argument string. Always returns M008 result envelope."""
    from .foundation_safety import tui_envelope

    mux = mux or SessionMux()
    parts = (arg or "").strip().split(maxsplit=1)
    sub = (parts[0] if parts else "status").lower()
    rest = parts[1] if len(parts) > 1 else ""

    if sub in {"", "status", "st"}:
        return tui_envelope({**mux.status(), "handled": True})
    if sub in {"list", "ls"}:
        return tui_envelope(
            {"ok": True, "handled": True, "windows": mux.list_windows(), "bar": mux.status_bar()},
        )
    if sub in {"new", "c", "create"}:
        return tui_envelope({**mux.new_window(title=rest), "handled": True})
    if sub in {"attach", "a"}:
        return tui_envelope({**mux.attach(rest), "handled": True})
    if sub in {"select", "s", "goto"}:
        if rest.isdigit() or (rest.startswith("-") and rest[1:].isdigit()):
            return tui_envelope({**mux.select(int(rest)), "handled": True})
        return tui_envelope({**mux.select_by_id(rest), "handled": True})
    if sub in {"next", "n", "+"}:
        return tui_envelope({**mux.next_window(), "handled": True})
    if sub in {"prev", "p", "previous", "-"}:
        return tui_envelope({**mux.prev_window(), "handled": True})
    if sub in {"kill", "x", "close"}:
        idx = int(rest) if rest.strip().isdigit() else None
        return tui_envelope({**mux.kill_window(idx), "handled": True})
    if sub in {"rename", "r"}:
        return tui_envelope({**mux.rename(rest), "handled": True})
    if sub in {"name", "mux-name"}:
        return tui_envelope({**mux.rename_mux(rest), "handled": True})
    if sub in {"help", "?"}:
        return tui_envelope({"ok": True, "handled": True, "help": MUX_HELP})
    return tui_envelope(
        {
            "ok": False,
            "handled": True,
            "error": "unknown_mux_subcommand",
            "sub": sub,
            "help": "status|new|attach|select|next|prev|kill|rename|list|name|help",
        },
        ok=False,
    )
