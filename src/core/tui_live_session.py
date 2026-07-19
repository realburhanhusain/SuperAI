"""
Live interactive session loop for SuperAI agent TUI.

Closes honest boundaries for N208–N215:
- Single-keystroke vim (NORMAL) via raw TTY
- Live mouse CSI → focus / scroll
- INSERT line editor with arrows/backspace without waiting for cooked mode
- Live a11y announcements on nav/mode changes
- Mux status reflected immediately

Falls back to console.input when not a TTY or SUPERAI_TUI_LIVE=0.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

from .tui_raw_input import (
    KEY_CTRL_C,
    KEY_CTRL_L,
    KEY_ENTER,
    KEY_ESC,
    LineEditor,
    RawEvent,
    RawTTY,
    is_tty,
    live_capabilities,
)


def live_enabled() -> bool:
    force = (os.getenv("SUPERAI_TUI_LIVE") or "").strip().lower()
    if force in {"0", "false", "off", "no"}:
        return False
    if force in {"1", "true", "on", "yes"}:
        return is_tty()
    # Default: live on real TTY
    return is_tty()


@dataclass
class LiveReadResult:
    """Outcome of one interactive read cycle."""

    kind: str  # "line" | "quit" | "redraw" | "empty"
    line: str = ""
    meta: Optional[Dict[str, Any]] = None


def _prompt_text(vim_eng, mouse_on: bool, live: bool) -> str:
    mode = ""
    if vim_eng and vim_eng.enabled:
        ind = vim_eng.mode_indicator()
        if vim_eng.mode == "normal":
            return f"NORMAL{('·live' if live else '')}> "
        if vim_eng.mode == "command":
            return f":{vim_eng.command_buf}"
        mode = f"INSERT{('·live' if live else '')}"
    else:
        mode = f"you{('·live' if live else '')}"
    mouse = "·mouse" if mouse_on else ""
    return f"{mode}{mouse}> "


def read_line_or_action(
    *,
    vim_eng,
    mouse_ctl,
    a11y,
    apply_nav: Callable[..., bool],
    console=None,
    force_cooked: bool = False,
) -> LiveReadResult:
    """
    Read user interaction once.

    - Live path: raw keys / mouse until a full line is submitted (Enter in INSERT)
      or quit action.
    - Cooked path: classic input() line.
    """
    use_live = live_enabled() and not force_cooked
    mouse_on = bool(mouse_ctl and mouse_ctl.cfg.enabled)

    if not use_live:
        return _cooked_read(vim_eng, console)

    return _live_read(
        vim_eng=vim_eng,
        mouse_ctl=mouse_ctl,
        a11y=a11y,
        apply_nav=apply_nav,
        mouse_on=mouse_on,
    )


def _cooked_read(vim_eng, console) -> LiveReadResult:
    prompt = _prompt_text(vim_eng, False, False)
    try:
        if console is not None:
            # Rich markup prompts
            if vim_eng and vim_eng.enabled and vim_eng.mode == "normal":
                line = console.input("[bold yellow]NORMAL>[/bold yellow] ")
            elif vim_eng and vim_eng.enabled and vim_eng.mode == "command":
                line = console.input(
                    f"[bold magenta]:{vim_eng.command_buf}[/bold magenta] "
                )
            else:
                line = console.input("[bold green]you>[/bold green] ")
        else:
            line = input(prompt)
    except (EOFError, KeyboardInterrupt):
        return LiveReadResult(kind="quit")
    return LiveReadResult(kind="line", line=line.rstrip("\n"))


def _live_read(
    *,
    vim_eng,
    mouse_ctl,
    a11y,
    apply_nav: Callable[..., bool],
    mouse_on: bool,
) -> LiveReadResult:
    """
    Live raw TTY interaction.

    Vim INSERT (or vim disabled): line editor until Enter → return line.
    Vim NORMAL: each key → vim engine → nav actions; i → insert; : → command; q → quit.
    Vim COMMAND: build :cmd until Enter.
    Mouse: always handled when enabled.
    """
    editor = LineEditor()
    with RawTTY(mouse=mouse_on) as tty:
        if not tty._active:
            # could not enter raw — cooked fallback
            return _cooked_read(vim_eng, None)

        def _show_prompt() -> None:
            p = _prompt_text(vim_eng, mouse_on, True)
            if vim_eng and vim_eng.enabled and vim_eng.mode == "insert":
                sys.stdout.write("\r\x1b[K" + p + editor.display())
            elif vim_eng and vim_eng.enabled and vim_eng.mode == "command":
                sys.stdout.write("\r\x1b[K" + f":{vim_eng.command_buf}")
            elif vim_eng and vim_eng.enabled and vim_eng.mode == "normal":
                sys.stdout.write("\r\x1b[K" + p)
            else:
                sys.stdout.write("\r\x1b[K" + p + editor.display())
            sys.stdout.flush()

        _show_prompt()
        if a11y:
            a11y.announce("Live input ready.", immediate=True)

        while True:
            ev = tty.read_event(timeout=0.5)
            if ev.kind == "timeout":
                continue

            # --- mouse ---
            if ev.kind == "mouse" and mouse_ctl and mouse_ctl.cfg.enabled:
                act = mouse_ctl.handle_sequence(ev.mouse_seq or ev.raw)
                if act.name == "focus_pane" and act.pane:
                    apply_nav("focus_pane", count=1, arg=act.pane or "")
                    if a11y:
                        a11y.announce(f"Focus {act.pane}.", immediate=True)
                    return LiveReadResult(
                        kind="redraw",
                        meta={"mouse": act.to_dict()},
                    )
                if act.name in {"scroll_up", "scroll_down"}:
                    apply_nav(act.name, count=act.lines)
                    if a11y:
                        a11y.announce(act.name.replace("_", " "), immediate=True)
                    return LiveReadResult(
                        kind="redraw",
                        meta={"mouse": act.to_dict()},
                    )
                continue

            if ev.kind != "key":
                continue
            key = ev.key

            if key == KEY_CTRL_C:
                sys.stdout.write("\n")
                sys.stdout.flush()
                return LiveReadResult(kind="quit")

            if key == KEY_CTRL_L:
                apply_nav("redraw")
                return LiveReadResult(kind="redraw")

            # ---- vim disabled: simple line editor ----
            if not vim_eng or not vim_eng.enabled:
                if key == KEY_ESC:
                    continue
                submitted = editor.handle_key(key)
                _show_prompt()
                if submitted is not None:
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    return LiveReadResult(kind="line", line=submitted)
                continue

            # ---- vim NORMAL ----
            if vim_eng.mode == "normal":
                act = vim_eng.feed(key)
                if act.name == "quit":
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    return LiveReadResult(kind="quit")
                if act.name == "enter_insert":
                    editor.clear()
                    if a11y:
                        a11y.announce("Insert mode.", immediate=True)
                    _show_prompt()
                    continue
                if act.name == "enter_command":
                    if a11y:
                        a11y.announce("Command mode.", immediate=True)
                    _show_prompt()
                    continue
                if act.name in {
                    "scroll_up",
                    "scroll_down",
                    "scroll_top",
                    "scroll_bottom",
                    "page_up",
                    "page_down",
                    "focus_next",
                    "focus_prev",
                    "focus_left",
                    "focus_right",
                    "focus_up",
                    "focus_down",
                    "mux_next",
                    "mux_prev",
                    "mux_new",
                    "redraw",
                    "help",
                }:
                    apply_nav(act.name, count=act.count, arg=act.arg)
                    if a11y:
                        a11y.announce(act.name.replace("_", " "), immediate=True)
                    return LiveReadResult(
                        kind="redraw",
                        meta={"vim": act.to_dict()},
                    )
                if act.name == "submit_command":
                    # shouldn't happen in normal without :
                    pass
                _show_prompt()
                continue

            # ---- vim COMMAND ----
            if vim_eng.mode == "command":
                act = vim_eng.feed(key)
                if act.name == "submit_command":
                    parsed = vim_eng.parse_command(act.arg)
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    if parsed.name == "quit":
                        return LiveReadResult(kind="quit")
                    if parsed.name == "open_session":
                        return LiveReadResult(
                            kind="line",
                            line=f"/mux attach {parsed.arg}",
                        )
                    if parsed.name == "mux_select":
                        apply_nav("mux_select", arg=parsed.arg)
                        return LiveReadResult(kind="redraw")
                    apply_nav(parsed.name, count=parsed.count, arg=parsed.arg)
                    if a11y:
                        a11y.announce(f"Command {act.arg}", immediate=True)
                    return LiveReadResult(kind="redraw", meta={"cmd": act.arg})
                if act.name == "cancel_command":
                    if a11y:
                        a11y.announce("Normal mode.", immediate=True)
                    _show_prompt()
                    continue
                _show_prompt()
                continue

            # ---- vim INSERT ----
            if key == KEY_ESC:
                vim_eng.feed(KEY_ESC)
                if a11y:
                    a11y.announce("Normal mode.", immediate=True)
                _show_prompt()
                continue
            # Map arrows etc. for line editor
            submitted = editor.handle_key(key)
            _show_prompt()
            if submitted is not None:
                sys.stdout.write("\n")
                sys.stdout.flush()
                return LiveReadResult(kind="line", line=submitted)


def process_cooked_vim_line(line: str, vim_eng, apply_nav) -> Optional[LiveReadResult]:
    """
    Backward-compatible: when cooked input delivers a line in NORMAL mode,
    interpret as key sequence (used if live unavailable mid-session).
    Returns LiveReadResult if fully handled, else None to treat as normal line.
    """
    if not vim_eng or not vim_eng.enabled or vim_eng.mode != "normal":
        return None
    if not line or line.startswith("/"):
        return None
    if line == ":":
        vim_eng.feed(":")
        return LiveReadResult(kind="redraw")
    i = 0
    quit_req = False
    while i < len(line):
        if i + 1 < len(line) and line[i : i + 2] in {"gg", "ZZ", "ZQ"}:
            a1 = vim_eng.feed(line[i])
            a2 = vim_eng.feed(line[i + 1])
            for act in (a1, a2):
                if act.name == "quit":
                    quit_req = True
                elif act.name not in {"none", "passthrough", "unknown", "enter_insert", "enter_command"}:
                    apply_nav(act.name, count=act.count, arg=act.arg)
            i += 2
            continue
        act = vim_eng.feed(line[i])
        if act.name == "quit":
            quit_req = True
        elif act.name == "submit_command":
            parsed = vim_eng.parse_command(act.arg)
            if parsed.name == "quit":
                quit_req = True
            else:
                apply_nav(parsed.name, count=parsed.count, arg=parsed.arg)
        elif act.name not in {"none", "passthrough", "unknown", "enter_insert", "enter_command"}:
            apply_nav(act.name, count=act.count, arg=act.arg)
        i += 1
    if quit_req:
        return LiveReadResult(kind="quit")
    return LiveReadResult(kind="redraw")
