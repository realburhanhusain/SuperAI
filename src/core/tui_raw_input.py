"""
Live raw TTY input for SuperAI TUI (closes N210/N211 honest boundaries).

Provides:
- Cross-platform raw / cbreak key reading (Windows msvcrt, Unix termios)
- CSI / SS3 escape sequence assembly (arrows, function keys, mouse SGR)
- Line editor for INSERT mode (chars + backspace + enter)
- Mouse DECSET enable/disable when attaching the TTY
- Graceful fallback when stdin is not a TTY

Used by superai_agent.tui when vim and/or mouse modes are active.
"""

from __future__ import annotations

import os
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, Iterator, List, Optional, Tuple


# Normalized key names (stable contract with tui_vim / tui_mouse)
KEY_ESC = "Esc"
KEY_ENTER = "Enter"
KEY_BACKSPACE = "Backspace"
KEY_TAB = "Tab"
KEY_UP = "Up"
KEY_DOWN = "Down"
KEY_LEFT = "Left"
KEY_RIGHT = "Right"
KEY_HOME = "Home"
KEY_END = "End"
KEY_PAGE_UP = "PageUp"
KEY_PAGE_DOWN = "PageDown"
KEY_CTRL_C = "Ctrl-c"
KEY_CTRL_D = "Ctrl-d"
KEY_CTRL_U = "Ctrl-u"
KEY_CTRL_W = "Ctrl-w"
KEY_CTRL_L = "Ctrl-l"
KEY_CTRL_Z = "Ctrl-z"


@dataclass
class RawEvent:
    """One input event from the terminal."""

    kind: str  # "key" | "mouse" | "resize" | "timeout" | "eof"
    key: str = ""  # normalized key name or single char
    raw: str = ""  # raw bytes/chars that produced this event
    mouse_seq: str = ""  # full CSI mouse sequence when kind=mouse

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "key": self.key,
            "raw": self.raw,
            "mouse_seq": self.mouse_seq,
        }


def is_tty() -> bool:
    try:
        return bool(sys.stdin.isatty() and sys.stdout.isatty())
    except Exception:
        return False


def platform_name() -> str:
    return "windows" if sys.platform == "win32" else "unix"


# ---------------------------------------------------------------------------
# Sequence parsing (pure — fully tested without a TTY)
# ---------------------------------------------------------------------------

# Map CSI final sequences → key names
_CSI_KEYS = {
    "A": KEY_UP,
    "B": KEY_DOWN,
    "C": KEY_RIGHT,
    "D": KEY_LEFT,
    "H": KEY_HOME,
    "F": KEY_END,
    "Z": "Shift-Tab",
}
_CSI_TILDE = {
    "1": KEY_HOME,
    "2": "Insert",
    "3": "Delete",
    "4": KEY_END,
    "5": KEY_PAGE_UP,
    "6": KEY_PAGE_DOWN,
    "7": KEY_HOME,
    "8": KEY_END,
    "11": "F1",
    "12": "F2",
    "13": "F3",
    "14": "F4",
    "15": "F5",
    "17": "F6",
    "18": "F7",
    "19": "F8",
    "20": "F9",
    "21": "F10",
    "23": "F11",
    "24": "F12",
}


def parse_escape_buffer(buf: str) -> Tuple[Optional[RawEvent], str]:
    """
    Try to parse a complete escape sequence from the front of buf.

    Returns (event_or_None_if_incomplete, remaining_buffer).
    """
    if not buf:
        return None, buf
    if buf[0] != "\x1b":
        # not an escape — single char handled elsewhere
        return None, buf

    # bare Esc
    if len(buf) == 1:
        return None, buf  # incomplete (may get more); caller times out → Esc

    # Alt+key: ESC + printable
    if len(buf) >= 2 and buf[1] not in {"[", "O"}:
        ch = buf[1]
        return RawEvent(kind="key", key=f"Alt-{ch}", raw=buf[:2]), buf[2:]

    # SS3: ESC O A
    if buf[1] == "O":
        if len(buf) < 3:
            return None, buf
        final = buf[2]
        key = _CSI_KEYS.get(final, f"SS3-{final}")
        return RawEvent(kind="key", key=key, raw=buf[:3]), buf[3:]

    # CSI: ESC [
    if buf[1] != "[":
        return RawEvent(kind="key", key=KEY_ESC, raw="\x1b"), buf[1:]

    # Mouse SGR: ESC [ < … M/m
    if len(buf) >= 3 and buf[2] == "<":
        for i in range(3, len(buf)):
            if buf[i] in {"M", "m"}:
                seq = buf[: i + 1]
                return (
                    RawEvent(kind="mouse", key="Mouse", raw=seq, mouse_seq=seq),
                    buf[i + 1 :],
                )
        return None, buf  # incomplete mouse

    # Mouse X10: ESC [ M Cb Cx Cy (3 bytes after M)
    if len(buf) >= 3 and buf[2] == "M" and (len(buf) == 3 or (len(buf) > 3 and not buf[3].isdigit() and buf[3] not in {";", "<"})):
        # X10 form ESC [ M + 3 bytes
        if len(buf) < 6:
            # could be incomplete X10 or start of something else
            # if we only have ESC[M wait for more
            if len(buf) == 3:
                return None, buf
        if len(buf) >= 6:
            seq = buf[:6]
            return (
                RawEvent(kind="mouse", key="Mouse", raw=seq, mouse_seq=seq),
                buf[6:],
            )

    # General CSI: collect until final byte 0x40–0x7E
    i = 2
    while i < len(buf):
        ch = buf[i]
        if "@" <= ch <= "~":
            seq = buf[: i + 1]
            body = buf[2:i]  # params + intermediate
            final = ch
            # tilde form: ESC [ n ~
            if final == "~" and body:
                num = body.split(";")[0]
                key = _CSI_TILDE.get(num, f"CSI-{body}~")
                return RawEvent(kind="key", key=key, raw=seq), buf[i + 1 :]
            if final in _CSI_KEYS and (not body or body.replace(";", "").isdigit() or body == ""):
                # arrows sometimes have modifiers: ESC [ 1 ; 2 A
                key = _CSI_KEYS[final]
                if ";" in body:
                    key = f"{key}-mod"
                return RawEvent(kind="key", key=key, raw=seq), buf[i + 1 :]
            # other CSI
            return RawEvent(kind="key", key=f"CSI-{body}{final}", raw=seq), buf[i + 1 :]
        i += 1
    return None, buf  # incomplete


def decode_byte_key(ch: str) -> RawEvent:
    """Map a single character / control code to RawEvent."""
    if not ch:
        return RawEvent(kind="eof")
    o = ord(ch) if len(ch) == 1 else -1
    if ch in {"\r", "\n"}:
        return RawEvent(kind="key", key=KEY_ENTER, raw=ch)
    if ch in {"\x7f", "\b"}:
        return RawEvent(kind="key", key=KEY_BACKSPACE, raw=ch)
    if ch == "\t":
        return RawEvent(kind="key", key=KEY_TAB, raw=ch)
    if ch == "\x1b":
        return RawEvent(kind="key", key=KEY_ESC, raw=ch)
    if ch == "\x03":
        return RawEvent(kind="key", key=KEY_CTRL_C, raw=ch)
    if ch == "\x04":
        return RawEvent(kind="key", key=KEY_CTRL_D, raw=ch)
    if ch == "\x15":
        return RawEvent(kind="key", key=KEY_CTRL_U, raw=ch)
    if ch == "\x17":
        return RawEvent(kind="key", key=KEY_CTRL_W, raw=ch)
    if ch == "\x0c":
        return RawEvent(kind="key", key=KEY_CTRL_L, raw=ch)
    if ch == "\x1a":
        return RawEvent(kind="key", key=KEY_CTRL_Z, raw=ch)
    if o >= 0 and o < 32:
        # other ctrl
        letter = chr(ord("a") + o - 1) if 1 <= o <= 26 else "?"
        return RawEvent(kind="key", key=f"Ctrl-{letter}", raw=ch)
    return RawEvent(kind="key", key=ch, raw=ch)


def feed_chars_to_events(chars: str, *, pending: str = "") -> Tuple[List[RawEvent], str]:
    """
    Convert a string of raw input (possibly partial CSI) into events.

    Pure function for tests. Returns (events, new_pending).
    """
    buf = pending + (chars or "")
    events: List[RawEvent] = []
    while buf:
        if buf[0] == "\x1b":
            ev, buf = parse_escape_buffer(buf)
            if ev is None:
                # incomplete — keep as pending
                return events, buf
            events.append(ev)
            continue
        events.append(decode_byte_key(buf[0]))
        buf = buf[1:]
    return events, ""


def finalize_pending_esc(pending: str) -> Tuple[List[RawEvent], str]:
    """If pending is bare Esc (timeout), emit Esc event."""
    if pending == "\x1b":
        return [RawEvent(kind="key", key=KEY_ESC, raw="\x1b")], ""
    if pending.startswith("\x1b"):
        # force-parse or dump as Esc + rest
        ev, rest = parse_escape_buffer(pending + "\x00")  # unlikely complete
        if ev:
            return [ev], rest.lstrip("\x00")
        return [RawEvent(kind="key", key=KEY_ESC, raw="\x1b")], pending[1:]
    return [], pending


# ---------------------------------------------------------------------------
# Line editor (INSERT mode live typing)
# ---------------------------------------------------------------------------


@dataclass
class LineEditor:
    buf: str = ""
    cursor: int = 0

    def clear(self) -> None:
        self.buf = ""
        self.cursor = 0

    def insert(self, ch: str) -> None:
        if not ch:
            return
        self.buf = self.buf[: self.cursor] + ch + self.buf[self.cursor :]
        self.cursor += len(ch)

    def backspace(self) -> None:
        if self.cursor <= 0:
            return
        self.buf = self.buf[: self.cursor - 1] + self.buf[self.cursor :]
        self.cursor -= 1

    def delete(self) -> None:
        if self.cursor >= len(self.buf):
            return
        self.buf = self.buf[: self.cursor] + self.buf[self.cursor + 1 :]

    def left(self) -> None:
        self.cursor = max(0, self.cursor - 1)

    def right(self) -> None:
        self.cursor = min(len(self.buf), self.cursor + 1)

    def home(self) -> None:
        self.cursor = 0

    def end(self) -> None:
        self.cursor = len(self.buf)

    def handle_key(self, key: str) -> Optional[str]:
        """
        Apply key. Returns submitted line on Enter, None otherwise.
        Empty string on Enter is a valid submit.
        """
        if key == KEY_ENTER:
            out = self.buf
            self.clear()
            return out
        if key == KEY_BACKSPACE:
            self.backspace()
            return None
        if key == "Delete":
            self.delete()
            return None
        if key == KEY_LEFT:
            self.left()
            return None
        if key == KEY_RIGHT:
            self.right()
            return None
        if key == KEY_HOME:
            self.home()
            return None
        if key == KEY_END:
            self.end()
            return None
        if key == KEY_CTRL_U:
            self.buf = self.buf[self.cursor :]
            self.cursor = 0
            return None
        if key == KEY_CTRL_W:
            # delete word backward
            i = self.cursor
            while i > 0 and self.buf[i - 1].isspace():
                i -= 1
            while i > 0 and not self.buf[i - 1].isspace():
                i -= 1
            self.buf = self.buf[:i] + self.buf[self.cursor :]
            self.cursor = i
            return None
        if len(key) == 1 and key.isprintable():
            self.insert(key)
            return None
        return None

    def display(self) -> str:
        return self.buf


# ---------------------------------------------------------------------------
# Platform readers
# ---------------------------------------------------------------------------


class RawTTY:
    """
    Live raw terminal session.

    Usage:
        with RawTTY(mouse=True) as tty:
            for ev in tty.events(timeout=0.05):
                ...
    """

    def __init__(
        self,
        *,
        mouse: bool = False,
        esc_timeout: float = 0.05,
    ):
        self.mouse = mouse
        self.esc_timeout = esc_timeout
        self._active = False
        self._old_term = None
        self._fd = None
        self._pending = ""
        self._win_mode = False
        self.available = is_tty()
        self.platform = platform_name()
        self.line = LineEditor()
        self.stats: Dict[str, int] = {
            "keys": 0,
            "mouse": 0,
            "fallbacks": 0,
        }

    def status(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "available": self.available,
            "active": self._active,
            "platform": self.platform,
            "mouse": self.mouse,
            "stats": dict(self.stats),
            "live": self._active and self.available,
        }

    def __enter__(self) -> "RawTTY":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()

    def start(self) -> bool:
        if not self.available:
            return False
        if self._active:
            return True
        try:
            if sys.platform == "win32":
                self._start_windows()
            else:
                self._start_unix()
            self._active = True
            if self.mouse:
                self._write_mouse(True)
            return True
        except Exception:
            self.available = False
            self._active = False
            return False

    def stop(self) -> None:
        if not self._active:
            return
        try:
            if self.mouse:
                self._write_mouse(False)
            if sys.platform == "win32":
                self._stop_windows()
            else:
                self._stop_unix()
        finally:
            self._active = False

    def _write_mouse(self, on: bool) -> None:
        from .tui_mouse import disable_mouse_ansi, enable_mouse_ansi

        try:
            sys.stdout.write(enable_mouse_ansi() if on else disable_mouse_ansi())
            sys.stdout.flush()
        except Exception:
            pass

    def _start_windows(self) -> None:
        # msvcrt needs no termios; mark active
        self._win_mode = True

    def _stop_windows(self) -> None:
        self._win_mode = False

    def _start_unix(self) -> None:
        import termios
        import tty

        self._fd = sys.stdin.fileno()
        self._old_term = termios.tcgetattr(self._fd)
        tty.setcbreak(self._fd)

    def _stop_unix(self) -> None:
        if self._old_term is not None and self._fd is not None:
            import termios

            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old_term)
            self._old_term = None

    def _read_chunk(self, timeout: float) -> str:
        """Read available input (possibly empty) within timeout seconds."""
        if sys.platform == "win32":
            return self._read_windows(timeout)
        return self._read_unix(timeout)

    def _read_windows(self, timeout: float) -> str:
        import msvcrt

        end = time.time() + max(0.0, timeout)
        out: List[str] = []
        win_map = {
            "H": "\x1b[A",
            "P": "\x1b[B",
            "K": "\x1b[D",
            "M": "\x1b[C",
            "G": "\x1b[H",
            "O": "\x1b[F",
            "I": "\x1b[5~",
            "Q": "\x1b[6~",
            "S": "\x1b[3~",
        }

        def _pull_one() -> None:
            ch = msvcrt.getwch()
            if ch in {"\x00", "\xe0"}:
                code = msvcrt.getwch()
                out.append(win_map.get(code, ""))
            else:
                out.append(ch)

        while True:
            if msvcrt.kbhit():
                _pull_one()
                while msvcrt.kbhit():
                    _pull_one()
                break
            if time.time() >= end:
                break
            time.sleep(0.01)
        return "".join(out)

    def _read_unix(self, timeout: float) -> str:
        import select

        fd = self._fd if self._fd is not None else sys.stdin.fileno()
        r, _, _ = select.select([fd], [], [], max(0.0, timeout))
        if not r:
            return ""
        try:
            data = os.read(fd, 1024)
        except Exception:
            return ""
        if not data:
            return ""
        try:
            return data.decode("utf-8", errors="replace")
        except Exception:
            return data.decode("latin-1", errors="replace")

    def read_event(self, timeout: float = 0.5) -> RawEvent:
        """Block up to timeout for one logical event."""
        if not self._active:
            self.stats["fallbacks"] += 1
            return RawEvent(kind="timeout")

        deadline = time.time() + max(0.0, timeout)
        while True:
            remaining = max(0.0, deadline - time.time())
            # if we have pending incomplete ESC, use short esc_timeout
            t = min(remaining, self.esc_timeout if self._pending.startswith("\x1b") else remaining)
            if t <= 0 and not self._pending:
                return RawEvent(kind="timeout")
            chunk = self._read_chunk(t if t > 0 else 0.0)
            if chunk:
                events, self._pending = feed_chars_to_events(chunk, pending=self._pending)
                if events:
                    # push rest back by only taking first; re-pending rest as synthetic
                    # simpler: process all into queue
                    self._queue = getattr(self, "_queue", [])
                    self._queue.extend(events)
            elif self._pending.startswith("\x1b") and time.time() >= deadline - 0.001:
                # timeout with pending esc
                events, self._pending = finalize_pending_esc(self._pending)
                self._queue = getattr(self, "_queue", [])
                self._queue.extend(events)

            q = getattr(self, "_queue", [])
            if q:
                ev = q.pop(0)
                self._queue = q
                if ev.kind == "key":
                    self.stats["keys"] += 1
                elif ev.kind == "mouse":
                    self.stats["mouse"] += 1
                return ev

            if time.time() >= deadline:
                if self._pending == "\x1b":
                    events, self._pending = finalize_pending_esc(self._pending)
                    if events:
                        self.stats["keys"] += 1
                        return events[0]
                return RawEvent(kind="timeout")

    def events(self, timeout: float = 0.05) -> Iterator[RawEvent]:
        """Yield events until timeout with no data (one idle)."""
        while True:
            ev = self.read_event(timeout=timeout)
            if ev.kind == "timeout":
                return
            yield ev
            # after first event, drain quickly
            timeout = 0.01


@contextmanager
def raw_tty_session(*, mouse: bool = False) -> Generator[RawTTY, None, None]:
    tty = RawTTY(mouse=mouse)
    tty.start()
    try:
        yield tty
    finally:
        tty.stop()


def read_line_live(
    prompt: str = "",
    *,
    mouse: bool = False,
    on_event=None,
    tty: Optional[RawTTY] = None,
) -> Optional[str]:
    """
    Read a full line with live editing using raw mode.

    on_event(ev) can return "quit" to abort, or "redraw" to refresh.
    Returns None on Ctrl-c / eof abort.
    """
    owns = tty is None
    rt = tty or RawTTY(mouse=mouse)
    if owns:
        if not rt.start():
            # fallback
            try:
                return input(prompt)
            except (EOFError, KeyboardInterrupt):
                return None
    try:
        if prompt:
            sys.stdout.write(prompt)
            sys.stdout.flush()
        editor = rt.line
        editor.clear()
        while True:
            ev = rt.read_event(timeout=1.0)
            if ev.kind == "timeout":
                continue
            if on_event:
                r = on_event(ev)
                if r == "quit":
                    return None
            if ev.kind == "mouse":
                if on_event:
                    on_event(ev)
                continue
            if ev.kind != "key":
                continue
            key = ev.key
            if key == KEY_CTRL_C:
                sys.stdout.write("\n")
                sys.stdout.flush()
                return None
            if key == KEY_ESC:
                # leave to caller via on_event; still return None for line?
                if on_event:
                    on_event(ev)
                # don't submit
                continue
            submitted = editor.handle_key(key)
            # redraw line
            sys.stdout.write("\r\x1b[K" + prompt + editor.display())
            sys.stdout.flush()
            if submitted is not None:
                sys.stdout.write("\n")
                sys.stdout.flush()
                return submitted
    finally:
        if owns:
            rt.stop()


def live_capabilities() -> Dict[str, Any]:
    """Public capability report (CLI / doctor)."""
    from .spend_guard import ensure_public_result

    tty = is_tty()
    return ensure_public_result(
        {
            "ok": True,
            "tty": tty,
            "platform": platform_name(),
            "live_keys": tty,
            "live_mouse": tty,
            "fallback": "line-input" if not tty else None,
            "modules": {
                "raw": "core.tui_raw_input",
                "vim": "core.tui_vim",
                "mouse": "core.tui_mouse",
                "mux": "core.tui_mux",
                "a11y": "core.tui_a11y",
            },
            "hint": (
                "superai agent uses live raw input when vim and/or mouse enabled on a TTY"
            ),
        },
        ok=True,
    )
