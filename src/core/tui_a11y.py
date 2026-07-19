"""
N215 — Screen-reader friendly TUI.

- A11y mode: linear plain-text structure instead of box-drawing panels
- Semantic landmarks (banner, main, complementary, contentinfo, status)
- Live announcements queue for mode/session/cost changes
- Reduced verbosity levels: brief | normal | verbose
- Persist preference under ~/.superai/tui/a11y.json
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class A11yConfig:
    enabled: bool = False  # opt-in
    verbosity: str = "normal"  # brief | normal | verbose
    announce_live: bool = True
    include_landmarks: bool = True
    plain_tables: bool = True
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]) -> "A11yConfig":
        if not d or not isinstance(d, dict):
            return cls()
        verb = str(d.get("verbosity") or "normal").lower()
        if verb not in {"brief", "normal", "verbose"}:
            verb = "normal"
        return cls(
            enabled=bool(d.get("enabled", False)),
            verbosity=verb,
            announce_live=bool(d.get("announce_live", True)),
            include_landmarks=bool(d.get("include_landmarks", True)),
            plain_tables=bool(d.get("plain_tables", True)),
            updated_at=d.get("updated_at"),
        )


def a11y_config_path() -> Path:
    p = Path.home() / ".superai" / "tui" / "a11y.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def load_a11y_config() -> A11yConfig:
    path = a11y_config_path()
    if path.is_file():
        try:
            return A11yConfig.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            pass
    return A11yConfig()


def save_a11y_config(cfg: A11yConfig) -> Path:
    cfg.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    path = a11y_config_path()
    path.write_text(json.dumps(cfg.to_dict(), indent=2), encoding="utf-8")
    return path


def landmark(role: str, label: str, body: str, *, enabled: bool = True) -> str:
    """Wrap body with SR-friendly landmark markers."""
    if not enabled:
        return body
    role = (role or "region").strip()
    label = (label or role).strip()
    return f"[{role}: {label}]\n{body.rstrip()}\n[/{role}: {label}]"


def messages_to_text(messages: List[Dict[str, Any]], *, limit: int = 20, verbosity: str = "normal") -> str:
    lines: List[str] = []
    for m in (messages or [])[-limit:]:
        role = str(m.get("role") or "unknown")
        content = str(m.get("content") or "")
        if verbosity == "brief":
            content = content[:160]
        elif verbosity == "normal":
            content = content[:800]
        else:
            content = content[:4000]
        lines.append(f"{role}: {content}")
        if verbosity != "brief":
            for p in m.get("parts") or []:
                if p.get("type") == "tool_call":
                    lines.append(
                        f"  tool-call name={p.get('name')} "
                        f"args={json.dumps(p.get('arguments') or {}, default=str)[:120]}"
                    )
                if p.get("type") == "tool_result":
                    lines.append(f"  tool-result ok={p.get('ok')}")
    return "\n".join(lines) if lines else "(no messages)"


def events_to_text(events: List[Dict[str, Any]], *, limit: int = 12) -> str:
    lines = []
    for e in (events or [])[-limit:]:
        kind = e.get("kind") or "event"
        detail = {k: v for k, v in e.items() if k not in {"kind", "ts"}}
        lines.append(f"{kind}: {json.dumps(detail, default=str)[:100]}")
    return "\n".join(lines) if lines else "(no events)"


def tools_to_text(tools: List[Dict[str, str]], *, limit: int = 15) -> str:
    lines = []
    for t in (tools or [])[:limit]:
        lines.append(f"- {t.get('name')}: {t.get('desc') or ''}")
    return "\n".join(lines) if lines else "(no tools)"


def linearize_frame(
    *,
    state: Any = None,
    events: Optional[List[Dict[str, Any]]] = None,
    tools_info: Optional[List[Dict[str, str]]] = None,
    stream_on: bool = True,
    status: str = "",
    mux_bar: str = "",
    vim_mode: str = "",
    mouse_on: bool = False,
    cfg: Optional[A11yConfig] = None,
) -> str:
    """
    Produce a screen-reader oriented linear document for the current TUI frame.
    """
    cfg = cfg or load_a11y_config()
    lm = cfg.include_landmarks
    verb = cfg.verbosity

    sid = getattr(state, "id", "?")
    agent = getattr(state, "agent", "?")
    model = getattr(state, "model", None) or "auto"
    perm = getattr(state, "permission", "?")
    cost = float(getattr(state, "estimated_cost_usd", 0) or 0)
    tokens = int(getattr(state, "tokens", 0) or 0)
    msgs = getattr(state, "messages", None) or []

    header_body = (
        f"SuperAI agent session {sid}. "
        f"Agent {agent}. Model {model}. Permission {perm}. "
        f"Streaming {'on' if stream_on else 'off'}."
    )
    if vim_mode:
        header_body += f" Input mode {vim_mode}."
    if mouse_on:
        header_body += " Mouse enabled."
    if mux_bar:
        header_body += f" Windows: {mux_bar}."

    main_body = messages_to_text(list(msgs), verbosity=verb)
    tools_body = tools_to_text(tools_info or [])
    events_body = events_to_text(events or [])
    status_body = (
        f"Cost approximately ${cost:.6f}. Tokens {tokens}. "
        f"Message count {len(msgs)}. {status}".strip()
    )

    if verb == "brief":
        parts = [
            landmark("banner", "session", header_body, enabled=lm),
            landmark("main", "messages", main_body, enabled=lm),
            landmark("status", "status", status_body, enabled=lm),
        ]
    else:
        parts = [
            landmark("banner", "session", header_body, enabled=lm),
            landmark("main", "messages", main_body, enabled=lm),
            landmark("complementary", "tools", tools_body, enabled=lm),
            landmark("complementary", "events", events_body, enabled=lm),
            landmark("contentinfo", "status", status_body, enabled=lm),
        ]
    return "\n\n".join(parts).strip() + "\n"


def live_announce_path() -> Path:
    """File SR tools / tail can watch for live announcements."""
    p = Path.home() / ".superai" / "tui" / "a11y_live.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def write_live_announcement(text: str) -> Path:
    """Append timestamped announcement for live SR consumers."""
    path = live_announce_path()
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {text.strip()}\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)
    return path


@dataclass
class A11yController:
    cfg: A11yConfig = field(default_factory=load_a11y_config)
    announcements: List[str] = field(default_factory=list)
    live_file: bool = True
    live_bell: bool = True
    live_voice: bool = False

    def enable(self, on: bool = True, *, persist: bool = True) -> Dict[str, Any]:
        from .spend_guard import ensure_public_result

        self.cfg.enabled = bool(on)
        if persist:
            save_a11y_config(self.cfg)
        msg = "Screen reader mode on." if on else "Screen reader mode off."
        self.announce(msg)
        return ensure_public_result(
            {
                "ok": True,
                "enabled": self.cfg.enabled,
                "announcement": msg,
                "live_file": str(live_announce_path()),
            },
            ok=True,
        )

    def set_verbosity(self, level: str, *, persist: bool = True) -> Dict[str, Any]:
        from .spend_guard import ensure_public_result

        level = (level or "normal").lower()
        if level not in {"brief", "normal", "verbose"}:
            return ensure_public_result(
                {"ok": False, "error": "bad_verbosity", "allowed": ["brief", "normal", "verbose"]},
                ok=False,
            )
        self.cfg.verbosity = level
        if persist:
            save_a11y_config(self.cfg)
        self.announce(f"Verbosity {level}.")
        return ensure_public_result(
            {"ok": True, "verbosity": level}, ok=True
        )

    def announce(self, text: str, *, immediate: bool = True) -> str:
        """
        Queue announcement; when immediate, also write live file + optional bell/voice.
        """
        text = (text or "").strip()
        if not text:
            return ""
        if self.cfg.announce_live:
            self.announcements.append(text)
            self.announcements = self.announcements[-50:]
        if immediate and (self.cfg.enabled or self.cfg.announce_live):
            try:
                if self.live_file:
                    write_live_announcement(text)
            except Exception:
                pass
            if self.live_bell:
                try:
                    import sys

                    sys.stdout.write("\a")
                    sys.stdout.flush()
                except Exception:
                    pass
            if self.live_voice or (
                self.cfg.enabled and (os.getenv("SUPERAI_A11Y_VOICE") or "").lower()
                in {"1", "true", "yes"}
            ):
                try:
                    from .voice_io import speak

                    speak(text[:200])
                except Exception:
                    pass
        return text

    def pop_announcements(self) -> List[str]:
        out = list(self.announcements)
        self.announcements.clear()
        return out

    def status(self) -> Dict[str, Any]:
        from .spend_guard import ensure_public_result

        return ensure_public_result(
            {
                "ok": True,
                "enabled": self.cfg.enabled,
                "verbosity": self.cfg.verbosity,
                "announce_live": self.cfg.announce_live,
                "include_landmarks": self.cfg.include_landmarks,
                "pending_announcements": list(self.announcements),
                "path": str(a11y_config_path()),
                "live_file": str(live_announce_path()),
                "live_bell": self.live_bell,
                "live_voice_env": (os.getenv("SUPERAI_A11Y_VOICE") or ""),
            },
            ok=True,
        )

    def render(
        self,
        *,
        state: Any = None,
        events: Optional[List[Dict[str, Any]]] = None,
        tools_info: Optional[List[Dict[str, str]]] = None,
        stream_on: bool = True,
        status: str = "",
        mux_bar: str = "",
        vim_mode: str = "",
        mouse_on: bool = False,
    ) -> str:
        text = linearize_frame(
            state=state,
            events=events,
            tools_info=tools_info,
            stream_on=stream_on,
            status=status,
            mux_bar=mux_bar,
            vim_mode=vim_mode,
            mouse_on=mouse_on,
            cfg=self.cfg,
        )
        notes = self.pop_announcements()
        if notes:
            text = "ANNOUNCE: " + " ".join(notes) + "\n\n" + text
        return text


A11Y_HELP = """
### Screen-reader mode (N215)

| Command | Action |
|---------|--------|
| `/a11y` `/a11y status` | Config + pending announcements |
| `/a11y on` | Enable linear SR-friendly output |
| `/a11y off` | Disable (Rich panels resume) |
| `/a11y brief\\|normal\\|verbose` | Verbosity |
| `/a11y help` | This help |

**When enabled**
- Frame is printed as plain text with landmarks:
  `[banner: session]…[/banner: session]`, `[main: messages]`, etc.
- Live announcements prefixed with `ANNOUNCE:`
- Avoids reliance on color or box-drawing for structure

CLI: `superai a11y status|on|off|verbosity|render|help`
"""


def handle_a11y_slash(arg: str = "", *, ctl: Optional[A11yController] = None) -> Dict[str, Any]:
    from .spend_guard import ensure_public_result

    ctl = ctl or A11yController()
    parts = (arg or "").strip().split(maxsplit=1)
    sub = (parts[0] if parts else "status").lower()
    rest = parts[1] if len(parts) > 1 else ""

    if sub in {"", "status", "st"}:
        return {**ctl.status(), "handled": True}
    if sub in {"on", "enable", "1", "true"}:
        return {**ctl.enable(True), "handled": True}
    if sub in {"off", "disable", "0", "false"}:
        return {**ctl.enable(False), "handled": True}
    if sub in {"brief", "normal", "verbose"}:
        return {**ctl.set_verbosity(sub), "handled": True}
    if sub in {"verbosity", "verb"} and rest:
        return {**ctl.set_verbosity(rest.strip()), "handled": True}
    if sub in {"help", "?"}:
        return ensure_public_result({"ok": True, "handled": True, "help": A11Y_HELP}, ok=True)
    if sub in {"announce"} and rest:
        msg = ctl.announce(rest)
        return ensure_public_result({"ok": True, "handled": True, "announcement": msg}, ok=True)
    return ensure_public_result(
        {
            "ok": False,
            "handled": True,
            "error": "unknown_a11y_subcommand",
            "help": "status|on|off|brief|normal|verbose|announce|help",
        },
        ok=False,
    )
