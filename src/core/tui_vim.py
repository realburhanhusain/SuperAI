"""
N210 — Vim keys in TUI.

Modal keybinding engine (normal / insert / command):
- Pure state machine; no curses required
- Maps key sequences to actions consumed by agent TUI
- Optional persistence of mode preference

Actions are string tokens the TUI interprets (scroll, focus, mux, quit, …).
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Action names (stable contract for TUI)
ACTION_NONE = "none"
ACTION_INSERT = "enter_insert"
ACTION_NORMAL = "enter_normal"
ACTION_COMMAND = "enter_command"
ACTION_SCROLL_UP = "scroll_up"
ACTION_SCROLL_DOWN = "scroll_down"
ACTION_SCROLL_TOP = "scroll_top"
ACTION_SCROLL_BOTTOM = "scroll_bottom"
ACTION_PAGE_UP = "page_up"
ACTION_PAGE_DOWN = "page_down"
ACTION_FOCUS_LEFT = "focus_left"
ACTION_FOCUS_RIGHT = "focus_right"
ACTION_FOCUS_UP = "focus_up"
ACTION_FOCUS_DOWN = "focus_down"
ACTION_FOCUS_NEXT = "focus_next"
ACTION_FOCUS_PREV = "focus_prev"
ACTION_MUX_NEXT = "mux_next"
ACTION_MUX_PREV = "mux_prev"
ACTION_MUX_NEW = "mux_new"
ACTION_QUIT = "quit"
ACTION_REDRAW = "redraw"
ACTION_HELP = "help"
ACTION_YANK = "yank_status"
ACTION_SUBMIT_COMMAND = "submit_command"
ACTION_CANCEL_COMMAND = "cancel_command"
ACTION_PASSTHROUGH = "passthrough"  # insert mode: append char
ACTION_BACKSPACE = "backspace"
ACTION_UNKNOWN = "unknown"


@dataclass
class VimConfig:
    enabled: bool = True
    default_mode: str = "insert"  # insert is friendlier for chat; Esc → normal
    count_max: int = 99
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]) -> "VimConfig":
        if not d or not isinstance(d, dict):
            return cls()
        mode = str(d.get("default_mode") or "insert").lower()
        if mode not in {"insert", "normal"}:
            mode = "insert"
        return cls(
            enabled=bool(d.get("enabled", True)),
            default_mode=mode,
            count_max=int(d.get("count_max") or 99),
            updated_at=d.get("updated_at"),
        )


def vim_config_path() -> Path:
    p = Path.home() / ".superai" / "tui" / "vim.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def load_vim_config() -> VimConfig:
    path = vim_config_path()
    if path.is_file():
        try:
            return VimConfig.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            pass
    return VimConfig()


def save_vim_config(cfg: VimConfig) -> Path:
    cfg.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    path = vim_config_path()
    path.write_text(json.dumps(cfg.to_dict(), indent=2), encoding="utf-8")
    return path


@dataclass
class VimAction:
    name: str
    count: int = 1
    arg: str = ""
    mode: str = "normal"
    raw: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VimEngine:
    """
    Stateful vim key processor.

    feed(key) → VimAction
    Keys are single characters or special names: Esc, Enter, Backspace, Tab,
    Ctrl-w, Ctrl-u, Ctrl-d, etc.
    """

    mode: str = "insert"
    enabled: bool = True
    pending: str = ""
    count_buf: str = ""
    command_buf: str = ""
    last_action: str = ACTION_NONE
    config: VimConfig = field(default_factory=VimConfig)

    def status(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "enabled": self.enabled,
            "mode": self.mode,
            "pending": self.pending,
            "count_buf": self.count_buf,
            "command_buf": self.command_buf,
            "last_action": self.last_action,
            "indicator": self.mode_indicator(),
        }

    def mode_indicator(self) -> str:
        if not self.enabled:
            return ""
        if self.mode == "normal":
            return "NORMAL"
        if self.mode == "command":
            return f":{self.command_buf}"
        return "INSERT"

    def set_mode(self, mode: str) -> None:
        mode = (mode or "insert").lower()
        if mode not in {"insert", "normal", "command"}:
            mode = "insert"
        self.mode = mode
        self.pending = ""
        self.count_buf = ""
        if mode != "command":
            self.command_buf = ""

    def enable(self, on: bool = True) -> None:
        self.enabled = bool(on)

    def _count(self) -> int:
        if not self.count_buf:
            return 1
        try:
            n = int(self.count_buf)
            return max(1, min(n, self.config.count_max))
        except ValueError:
            return 1

    def _emit(self, name: str, *, arg: str = "", raw: str = "") -> VimAction:
        act = VimAction(
            name=name,
            count=self._count(),
            arg=arg,
            mode=self.mode,
            raw=raw,
        )
        self.last_action = name
        self.pending = ""
        self.count_buf = ""
        return act

    def feed(self, key: str) -> VimAction:
        """Process one key. Returns action for TUI to apply."""
        key = key if key else ""
        if not self.enabled:
            return self._emit(ACTION_PASSTHROUGH, arg=key, raw=key)

        # Special: Esc always → normal
        if key in {"Esc", "\x1b", "Escape"}:
            self.set_mode("normal")
            return self._emit(ACTION_NORMAL, raw=key)

        if self.mode == "insert":
            if key in {"Enter", "\n", "\r"}:
                return self._emit(ACTION_PASSTHROUGH, arg="\n", raw=key)
            if key in {"Backspace", "\x7f", "\b"}:
                return self._emit(ACTION_BACKSPACE, raw=key)
            if key == "Tab":
                return self._emit(ACTION_FOCUS_NEXT, raw=key)
            # Ctrl-c style
            if key in {"Ctrl-c", "\x03"}:
                return self._emit(ACTION_QUIT, raw=key)
            return self._emit(ACTION_PASSTHROUGH, arg=key, raw=key)

        if self.mode == "command":
            if key in {"Enter", "\n", "\r"}:
                cmd = self.command_buf.strip()
                self.set_mode("normal")
                return self._emit(ACTION_SUBMIT_COMMAND, arg=cmd, raw=key)
            if key in {"Esc", "\x1b"}:
                self.set_mode("normal")
                return self._emit(ACTION_CANCEL_COMMAND, raw=key)
            if key in {"Backspace", "\x7f", "\b"}:
                self.command_buf = self.command_buf[:-1]
                return self._emit(ACTION_NONE, raw=key)
            if len(key) == 1 and key.isprintable():
                self.command_buf += key
                return self._emit(ACTION_NONE, raw=key)
            return self._emit(ACTION_NONE, raw=key)

        # ---- normal mode ----
        # counts (do not clear count_buf via _emit)
        if key.isdigit() and (key != "0" or self.count_buf):
            self.count_buf += key
            self.last_action = ACTION_NONE
            return VimAction(
                name=ACTION_NONE,
                count=self._count(),
                mode=self.mode,
                raw=key,
            )

        seq = self.pending + key

        # multi-key
        if seq == "g":
            self.pending = "g"
            return VimAction(name=ACTION_NONE, mode=self.mode, raw=key)
        if seq == "gg":
            return self._emit(ACTION_SCROLL_TOP, raw=seq)
        if seq.startswith("g") and len(seq) > 1:
            self.pending = ""
            return self._emit(ACTION_UNKNOWN, arg=seq, raw=seq)

        if seq in {"Z"}:
            self.pending = "Z"
            return VimAction(name=ACTION_NONE, mode=self.mode, raw=key)
        if seq == "ZZ":
            return self._emit(ACTION_QUIT, raw=seq)
        if seq == "ZQ":
            return self._emit(ACTION_QUIT, raw=seq)

        # Ctrl-w prefix (window/pane)
        if key in {"Ctrl-w", "\x17"}:
            self.pending = "Ctrl-w"
            return VimAction(name=ACTION_NONE, mode=self.mode, raw=key)
        if self.pending == "Ctrl-w":
            self.pending = ""
            mapping = {
                "w": ACTION_FOCUS_NEXT,
                "W": ACTION_FOCUS_PREV,
                "h": ACTION_FOCUS_LEFT,
                "l": ACTION_FOCUS_RIGHT,
                "j": ACTION_FOCUS_DOWN,
                "k": ACTION_FOCUS_UP,
                "n": ACTION_MUX_NEW,
                "t": ACTION_MUX_NEXT,
                "p": ACTION_MUX_PREV,
            }
            if key in mapping:
                return self._emit(mapping[key], raw=f"Ctrl-w {key}")
            return self._emit(ACTION_UNKNOWN, arg=key, raw=key)

        # single keys
        table = {
            "i": ACTION_INSERT,
            "a": ACTION_INSERT,
            "A": ACTION_INSERT,
            "o": ACTION_INSERT,
            "I": ACTION_INSERT,
            ":": ACTION_COMMAND,
            "j": ACTION_SCROLL_DOWN,
            "k": ACTION_SCROLL_UP,
            "h": ACTION_FOCUS_LEFT,
            "l": ACTION_FOCUS_RIGHT,
            "G": ACTION_SCROLL_BOTTOM,
            "0": ACTION_SCROLL_TOP,  # when not part of count (handled above if count_buf)
            "^": ACTION_SCROLL_TOP,
            "$": ACTION_SCROLL_BOTTOM,
            "Ctrl-u": ACTION_PAGE_UP,
            "Ctrl-d": ACTION_PAGE_DOWN,
            "Ctrl-b": ACTION_PAGE_UP,
            "Ctrl-f": ACTION_PAGE_DOWN,
            "Tab": ACTION_FOCUS_NEXT,
            "gt": ACTION_MUX_NEXT,  # won't hit as single — see below
            "gT": ACTION_MUX_PREV,
            "r": ACTION_REDRAW,
            "y": ACTION_YANK,
            "?": ACTION_HELP,
            "q": ACTION_QUIT,
            " ": ACTION_SCROLL_DOWN,  # space
            "\x04": ACTION_PAGE_DOWN,  # Ctrl-d raw
            "\x15": ACTION_PAGE_UP,  # Ctrl-u raw
        }

        if key == "i" or key == "a" or key == "A" or key == "o" or key == "I":
            self.set_mode("insert")
            return self._emit(ACTION_INSERT, raw=key)
        if key == ":":
            self.set_mode("command")
            self.command_buf = ""
            return self._emit(ACTION_COMMAND, raw=key)

        if key in table:
            return self._emit(table[key], raw=key)

        # gt / gT via pending already handled for gg; support t after empty pending as mux next with g prefix done
        if key == "t" and not self.pending:
            # plain t unused
            return self._emit(ACTION_UNKNOWN, arg=key, raw=key)

        self.pending = ""
        return self._emit(ACTION_UNKNOWN, arg=key, raw=key)

    def feed_sequence(self, keys: str) -> List[VimAction]:
        """Feed a string of characters (special keys not supported here)."""
        return [self.feed(ch) for ch in keys]

    def parse_command(self, cmd: str) -> VimAction:
        """Interpret :command buffer contents."""
        c = (cmd or "").strip()
        if not c:
            return VimAction(name=ACTION_NONE, mode="normal")
        if c in {"q", "quit", "q!"}:
            return VimAction(name=ACTION_QUIT, arg=c, mode="normal")
        if c in {"w", "write"}:
            return VimAction(name=ACTION_REDRAW, arg=c, mode="normal")  # save handled by TUI session auto-save
        if c in {"wq", "x"}:
            return VimAction(name=ACTION_QUIT, arg=c, mode="normal")
        if c in {"help", "h"}:
            return VimAction(name=ACTION_HELP, arg=c, mode="normal")
        if c.startswith("e ") or c.startswith("edit "):
            return VimAction(name="open_session", arg=c.split(maxsplit=1)[-1], mode="normal")
        if c.isdigit():
            return VimAction(name="mux_select", arg=c, count=int(c), mode="normal")
        if c in {"bn", "bnext", "tabnext"}:
            return VimAction(name=ACTION_MUX_NEXT, mode="normal")
        if c in {"bp", "bprev", "tabprev"}:
            return VimAction(name=ACTION_MUX_PREV, mode="normal")
        if c in {"tabnew"}:
            return VimAction(name=ACTION_MUX_NEW, mode="normal")
        return VimAction(name=ACTION_UNKNOWN, arg=c, mode="normal")


def create_engine(cfg: Optional[VimConfig] = None) -> VimEngine:
    cfg = cfg or load_vim_config()
    return VimEngine(
        mode=cfg.default_mode if cfg.enabled else "insert",
        enabled=cfg.enabled,
        config=cfg,
    )


VIM_HELP = """
### Vim keys (N210)

| Mode | Enter | Notes |
|------|-------|-------|
| INSERT | default / `i` `a` | Type normally; `Esc` → NORMAL |
| NORMAL | `Esc` | Navigation bindings |
| COMMAND | `:` in NORMAL | Ex-style; Enter runs |

**NORMAL bindings**

| Key | Action |
|-----|--------|
| `j` / `k` | Scroll messages down / up |
| `Ctrl-d` / `Ctrl-u` | Page down / up |
| `gg` / `G` | Top / bottom |
| `h` `l` | Focus pane left / right |
| `Tab` | Next pane |
| `Ctrl-w` `w` | Next pane |
| `Ctrl-w` `h/j/k/l` | Pane direction |
| `Ctrl-w` `t` / `p` | Mux next / prev window |
| `Ctrl-w` `n` | Mux new window |
| `i` | Insert mode |
| `:` | Command mode |
| `r` | Redraw |
| `?` | Help |
| `q` / `ZZ` | Quit |

**COMMAND examples:** `:q` `:help` `:tabnew` `:bn` `:bp` `:<n>` select window n

CLI: `superai vim-keys status|enable|disable|help`
Toggle in TUI: `/vim on|off|status|help`
"""


def handle_vim_slash(arg: str = "", *, engine: Optional[VimEngine] = None) -> Dict[str, Any]:
    from .spend_guard import ensure_public_result

    eng = engine or create_engine()
    parts = (arg or "").strip().split(maxsplit=1)
    sub = (parts[0] if parts else "status").lower()
    if sub in {"", "status", "st"}:
        return ensure_public_result({"ok": True, "handled": True, **eng.status()}, ok=True)
    if sub in {"on", "enable", "1", "true"}:
        eng.enable(True)
        cfg = load_vim_config()
        cfg.enabled = True
        save_vim_config(cfg)
        return ensure_public_result({"ok": True, "handled": True, **eng.status()}, ok=True)
    if sub in {"off", "disable", "0", "false"}:
        eng.enable(False)
        cfg = load_vim_config()
        cfg.enabled = False
        save_vim_config(cfg)
        return ensure_public_result({"ok": True, "handled": True, **eng.status()}, ok=True)
    if sub in {"normal", "insert"}:
        eng.set_mode(sub)
        return ensure_public_result({"ok": True, "handled": True, **eng.status()}, ok=True)
    if sub in {"help", "?"}:
        return ensure_public_result({"ok": True, "handled": True, "help": VIM_HELP}, ok=True)
    if sub in {"feed"} and len(parts) > 1:
        acts = [a.to_dict() for a in eng.feed_sequence(parts[1])]
        return ensure_public_result(
            {"ok": True, "handled": True, "actions": acts, **eng.status()}, ok=True
        )
    return ensure_public_result(
        {
            "ok": False,
            "handled": True,
            "error": "unknown_vim_subcommand",
            "help": "status|on|off|normal|insert|help|feed <keys>",
        },
        ok=False,
    )
