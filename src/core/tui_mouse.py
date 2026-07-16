"""
N211 — Optional mouse support for SuperAI TUI.

- Enable/disable preference (persisted)
- Parse common terminal mouse encodings (SGR / X10-style CSI)
- Hit-test regions → pane focus / scroll actions
- Scroll delta → scroll_up / scroll_down

Does not require a live terminal for unit tests; parsing is pure.
When enabled, TUI may emit DECSET 1000/1002/1006 sequences (documented).
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Mouse button codes (SGR)
BTN_LEFT = 0
BTN_MID = 1
BTN_RIGHT = 2
BTN_RELEASE = 3
BTN_WHEEL_UP = 64
BTN_WHEEL_DOWN = 65


@dataclass
class MouseConfig:
    enabled: bool = False  # opt-in
    scroll_lines: int = 3
    click_focus: bool = True
    wheel_scroll: bool = True
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]) -> "MouseConfig":
        if not d or not isinstance(d, dict):
            return cls()
        return cls(
            enabled=bool(d.get("enabled", False)),
            scroll_lines=max(1, int(d.get("scroll_lines") or 3)),
            click_focus=bool(d.get("click_focus", True)),
            wheel_scroll=bool(d.get("wheel_scroll", True)),
            updated_at=d.get("updated_at"),
        )


def mouse_config_path() -> Path:
    p = Path.home() / ".superai" / "tui" / "mouse.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def load_mouse_config() -> MouseConfig:
    path = mouse_config_path()
    if path.is_file():
        try:
            return MouseConfig.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            pass
    return MouseConfig()


def save_mouse_config(cfg: MouseConfig) -> Path:
    cfg.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    path = mouse_config_path()
    path.write_text(json.dumps(cfg.to_dict(), indent=2), encoding="utf-8")
    return path


@dataclass
class MouseEvent:
    button: int
    x: int  # 1-based column
    y: int  # 1-based row
    pressed: bool = True
    drag: bool = False
    wheel: Optional[str] = None  # "up" | "down" | None
    raw: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PaneRegion:
    """Screen rectangle for a named pane (1-based inclusive coords)."""

    name: str
    x1: int
    y1: int
    x2: int
    y2: int

    def contains(self, x: int, y: int) -> bool:
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# SGR: CSI < Cb ; Cx ; Cy M/m
_SGR_RE = re.compile(r"\x1b\[<(\d+);(\d+);(\d+)([Mm])")
# X10: CSI M Cb Cx Cy (bytes with +32 offset) — we accept escaped form
_X10_RE = re.compile(r"\x1b\[M(.)(.)(.)", re.DOTALL)


def parse_mouse_sgr(seq: str) -> Optional[MouseEvent]:
    m = _SGR_RE.search(seq or "")
    if not m:
        return None
    cb, cx, cy, mm = m.groups()
    button = int(cb)
    x, y = int(cx), int(cy)
    pressed = mm == "M"
    wheel = None
    # wheel encoded as 64/65 (+32 modifiers sometimes)
    b = button & 0xC3  # rough mask
    if button in (64, 96) or (button & 0x40 and (button & 0x03) == 0 and button >= 64):
        # 64 = wheel up, 65 = wheel down (common)
        if button % 2 == 0 and button >= 64:
            wheel = "up" if button in (64, 96) else "up"
        if button in (64,):
            wheel = "up"
        if button in (65, 97):
            wheel = "down"
    if button == BTN_WHEEL_UP:
        wheel = "up"
    if button == BTN_WHEEL_DOWN:
        wheel = "down"
    drag = bool(button & 32) and wheel is None
    return MouseEvent(
        button=button,
        x=x,
        y=y,
        pressed=pressed,
        drag=drag,
        wheel=wheel,
        raw=m.group(0),
    )


def parse_mouse_x10(seq: str) -> Optional[MouseEvent]:
    m = _X10_RE.search(seq or "")
    if not m:
        return None
    cb = ord(m.group(1)) - 32
    cx = ord(m.group(2)) - 32
    cy = ord(m.group(3)) - 32
    wheel = None
    if cb == 64:
        wheel = "up"
    elif cb == 65:
        wheel = "down"
    return MouseEvent(
        button=cb,
        x=cx,
        y=cy,
        pressed=cb != 3,
        wheel=wheel,
        raw=m.group(0),
    )


def parse_mouse_event(seq: str) -> Optional[MouseEvent]:
    """Try SGR then X10."""
    return parse_mouse_sgr(seq) or parse_mouse_x10(seq)


def enable_mouse_ansi() -> str:
    """DECSET sequences: 1000 click, 1002 drag, 1006 SGR, 1003 any-event optional skip."""
    return "\x1b[?1000h\x1b[?1002h\x1b[?1006h"


def disable_mouse_ansi() -> str:
    return "\x1b[?1006l\x1b[?1002l\x1b[?1000l"


def hit_test(x: int, y: int, regions: List[PaneRegion]) -> Optional[str]:
    """Return pane name containing (x,y), last match wins for overlaps."""
    found = None
    for r in regions or []:
        if r.contains(x, y):
            found = r.name
    return found


def default_regions(
    width: int = 80,
    height: int = 24,
    layout: str = "agent",
) -> List[PaneRegion]:
    """
    Approximate pane regions for common layouts (1-based).
    Good enough for click-to-focus without a full layout engine.
    """
    w, h = max(20, width), max(10, height)
    if layout in {"focus", "classic"} and layout == "focus":
        return [PaneRegion("messages", 1, 1, w, h)]
    if layout == "classic" or layout == "v-split":
        mid = max(2, w * 3 // 4)
        return [
            PaneRegion("messages", 1, 1, mid, h),
            PaneRegion("tools", mid + 1, 1, w, h),
        ]
    if layout == "h-split":
        mid = max(2, h * 3 // 4)
        return [
            PaneRegion("messages", 1, 1, w, mid),
            PaneRegion("tools", 1, mid + 1, w, h),
        ]
    if layout == "triple":
        a, b = w // 2, w * 3 // 4
        return [
            PaneRegion("messages", 1, 1, a, h),
            PaneRegion("tools", a + 1, 1, b, h),
            PaneRegion("events", b + 1, 1, w, h),
        ]
    if layout == "quad":
        mx, my = w // 2, h // 2
        return [
            PaneRegion("messages", 1, 1, mx, my),
            PaneRegion("tools", mx + 1, 1, w, my),
            PaneRegion("events", 1, my + 1, mx, h),
            PaneRegion("cost", mx + 1, my + 1, w, h),
        ]
    # agent / ide default: header 3, footer 3, body split
    header_h, footer_h = 3, 3
    body_y1 = header_h + 1
    body_y2 = h - footer_h
    mid = max(2, w * 3 // 4)
    return [
        PaneRegion("header", 1, 1, w, header_h),
        PaneRegion("messages", 1, body_y1, mid, body_y2),
        PaneRegion("tools", mid + 1, body_y1, w, (body_y1 + body_y2) // 2),
        PaneRegion("events", mid + 1, (body_y1 + body_y2) // 2 + 1, w, body_y2),
        PaneRegion("status", 1, body_y2 + 1, w, h),
    ]


@dataclass
class MouseAction:
    name: str  # focus_pane | scroll_up | scroll_down | none | click
    pane: Optional[str] = None
    lines: int = 1
    event: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "pane": self.pane,
            "lines": self.lines,
            "event": self.event,
        }


class MouseController:
    def __init__(self, cfg: Optional[MouseConfig] = None):
        self.cfg = cfg or load_mouse_config()
        self.regions: List[PaneRegion] = default_regions()
        self.last_event: Optional[MouseEvent] = None

    def set_regions(self, regions: List[PaneRegion]) -> None:
        self.regions = list(regions or [])

    def set_layout(self, layout: str, width: int = 80, height: int = 24) -> None:
        self.regions = default_regions(width, height, layout)

    def enable(self, on: bool = True, *, persist: bool = True) -> Dict[str, Any]:
        from .spend_guard import ensure_public_result

        self.cfg.enabled = bool(on)
        if persist:
            save_mouse_config(self.cfg)
        return ensure_public_result(
            {
                "ok": True,
                "enabled": self.cfg.enabled,
                "ansi_enable": enable_mouse_ansi() if on else "",
                "ansi_disable": disable_mouse_ansi() if not on else "",
                "hint": "Write enable_mouse_ansi() to stdout when attaching a raw terminal",
            },
            ok=True,
        )

    def status(self) -> Dict[str, Any]:
        from .spend_guard import ensure_public_result

        return ensure_public_result(
            {
                "ok": True,
                "enabled": self.cfg.enabled,
                "scroll_lines": self.cfg.scroll_lines,
                "click_focus": self.cfg.click_focus,
                "wheel_scroll": self.cfg.wheel_scroll,
                "regions": [r.to_dict() for r in self.regions],
                "path": str(mouse_config_path()),
            },
            ok=True,
        )

    def handle_sequence(self, seq: str) -> MouseAction:
        if not self.cfg.enabled:
            return MouseAction(name="none", event=None)
        ev = parse_mouse_event(seq)
        if not ev:
            return MouseAction(name="none")
        self.last_event = ev
        return self.handle_event(ev)

    def handle_event(self, ev: MouseEvent) -> MouseAction:
        if not self.cfg.enabled:
            return MouseAction(name="none", event=ev.to_dict())
        if ev.wheel and self.cfg.wheel_scroll:
            name = "scroll_up" if ev.wheel == "up" else "scroll_down"
            return MouseAction(
                name=name,
                lines=self.cfg.scroll_lines,
                event=ev.to_dict(),
            )
        if self.cfg.click_focus and ev.pressed and ev.wheel is None:
            pane = hit_test(ev.x, ev.y, self.regions)
            if pane:
                return MouseAction(name="focus_pane", pane=pane, event=ev.to_dict())
            return MouseAction(name="click", event=ev.to_dict())
        return MouseAction(name="none", event=ev.to_dict())


MOUSE_HELP = """
### Mouse support (N211, opt-in)

| Command | Action |
|---------|--------|
| `/mouse` `/mouse status` | Show mouse config |
| `/mouse on` | Enable mouse mode |
| `/mouse off` | Disable |
| `/mouse help` | This help |

**Behavior when enabled**
- **Click** a pane region → focus that pane (N209)
- **Wheel** → scroll messages (configurable lines)
- Terminal: emit DECSET 1000/1002/1006 (`enable_mouse_ansi()`)

**Note:** Line-oriented `input()` loops cannot consume raw mouse CSI without a
raw terminal reader. Parsing + hit-test are fully implemented and used when
a raw reader is attached; `/mouse demo-click x y` simulates a click for tests.

CLI: `superai mouse status|on|off|parse|hit|help`
"""


def handle_mouse_slash(arg: str = "", *, ctl: Optional[MouseController] = None) -> Dict[str, Any]:
    from .spend_guard import ensure_public_result

    ctl = ctl or MouseController()
    parts = (arg or "").strip().split()
    sub = (parts[0] if parts else "status").lower()
    if sub in {"", "status", "st"}:
        return {**ctl.status(), "handled": True}
    if sub in {"on", "enable", "1", "true"}:
        return {**ctl.enable(True), "handled": True}
    if sub in {"off", "disable", "0", "false"}:
        return {**ctl.enable(False), "handled": True}
    if sub in {"help", "?"}:
        return ensure_public_result({"ok": True, "handled": True, "help": MOUSE_HELP}, ok=True)
    if sub in {"parse"} and len(parts) >= 2:
        # parts[1] may be escaped; allow sgr:btn;x;y or sgr:btn:x:y
        seq = " ".join(parts[1:])
        if seq.startswith("sgr:"):
            body = seq[4:]
            if ";" in body:
                btn, x, y = body.split(";")[:3]
            else:
                bits = body.split(":")
                btn, x, y = bits[0], bits[1], bits[2]
            seq = f"\x1b[<{btn};{x};{y}M"
        ev = parse_mouse_event(seq)
        return ensure_public_result(
            {
                "ok": True,
                "handled": True,
                "event": ev.to_dict() if ev else None,
            },
            ok=True,
        )
    if sub in {"hit", "click", "demo-click"} and len(parts) >= 3:
        x, y = int(parts[1]), int(parts[2])
        if len(parts) >= 4:
            ctl.set_layout(parts[3])
        pane = hit_test(x, y, ctl.regions)
        act = ctl.handle_event(
            MouseEvent(button=0, x=x, y=y, pressed=True)
        )
        return ensure_public_result(
            {
                "ok": True,
                "handled": True,
                "pane": pane,
                "action": act.to_dict(),
            },
            ok=True,
        )
    if sub in {"layout"} and len(parts) >= 2:
        ctl.set_layout(parts[1])
        return ensure_public_result(
            {
                "ok": True,
                "handled": True,
                "regions": [r.to_dict() for r in ctl.regions],
            },
            ok=True,
        )
    return ensure_public_result(
        {
            "ok": False,
            "handled": True,
            "error": "unknown_mouse_subcommand",
            "help": "status|on|off|parse|hit|layout|help",
        },
        ok=False,
    )
