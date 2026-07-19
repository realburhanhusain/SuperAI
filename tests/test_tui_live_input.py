"""Live TTY input — raw CSI, line editor, capabilities (closes N210/N211 boundaries)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture()
def tui_home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai" / "tui").mkdir(parents=True)
    import importlib

    import core.tui_a11y as a11y
    import core.tui_live_session as live
    import core.tui_raw_input as raw

    importlib.reload(raw)
    importlib.reload(live)
    importlib.reload(a11y)
    yield tmp_path, raw, live, a11y


# ---------------------------------------------------------------------------
# CSI / key parsing (pure)
# ---------------------------------------------------------------------------


def test_decode_byte_keys(tui_home):
    tmp, raw, *_ = tui_home
    assert raw.decode_byte_key("a").key == "a"
    assert raw.decode_byte_key("\r").key == raw.KEY_ENTER
    assert raw.decode_byte_key("\x7f").key == raw.KEY_BACKSPACE
    assert raw.decode_byte_key("\x03").key == raw.KEY_CTRL_C
    assert raw.decode_byte_key("\x17").key == raw.KEY_CTRL_W
    assert raw.decode_byte_key("\x04").key == raw.KEY_CTRL_D


def test_feed_plain_and_arrows(tui_home):
    tmp, raw, *_ = tui_home
    events, pending = raw.feed_chars_to_events("ab")
    assert [e.key for e in events] == ["a", "b"]
    assert pending == ""

    events, pending = raw.feed_chars_to_events("\x1b[A")
    assert len(events) == 1
    assert events[0].key == raw.KEY_UP
    assert pending == ""


def test_feed_incomplete_esc_then_complete(tui_home):
    tmp, raw, *_ = tui_home
    events, pending = raw.feed_chars_to_events("\x1b")
    assert events == []
    assert pending == "\x1b"
    events, pending = raw.feed_chars_to_events("[B", pending=pending)
    assert events[0].key == raw.KEY_DOWN
    assert pending == ""


def test_finalize_pending_esc(tui_home):
    tmp, raw, *_ = tui_home
    events, pending = raw.finalize_pending_esc("\x1b")
    assert events[0].key == raw.KEY_ESC
    assert pending == ""


def test_feed_mouse_sgr(tui_home):
    tmp, raw, *_ = tui_home
    seq = "\x1b[<0;10;5M"
    events, pending = raw.feed_chars_to_events(seq)
    assert len(events) == 1
    assert events[0].kind == "mouse"
    assert events[0].mouse_seq == seq
    assert pending == ""


def test_feed_mouse_sgr_incomplete(tui_home):
    tmp, raw, *_ = tui_home
    events, pending = raw.feed_chars_to_events("\x1b[<0;10")
    assert events == []
    assert pending.startswith("\x1b")


def test_page_keys(tui_home):
    tmp, raw, *_ = tui_home
    events, _ = raw.feed_chars_to_events("\x1b[5~")
    assert events[0].key == raw.KEY_PAGE_UP
    events, _ = raw.feed_chars_to_events("\x1b[6~")
    assert events[0].key == raw.KEY_PAGE_DOWN


# ---------------------------------------------------------------------------
# Line editor
# ---------------------------------------------------------------------------


def test_line_editor_insert_backspace_enter(tui_home):
    tmp, raw, *_ = tui_home
    ed = raw.LineEditor()
    assert ed.handle_key("h") is None
    assert ed.handle_key("i") is None
    assert ed.display() == "hi"
    assert ed.handle_key(raw.KEY_BACKSPACE) is None
    assert ed.display() == "h"
    assert ed.handle_key(raw.KEY_ENTER) == "h"
    assert ed.display() == ""


def test_line_editor_arrows_and_ctrl_w(tui_home):
    tmp, raw, *_ = tui_home
    ed = raw.LineEditor()
    for ch in "hello world":
        ed.handle_key(ch)
    ed.handle_key(raw.KEY_CTRL_W)
    assert ed.display() == "hello "
    ed.handle_key(raw.KEY_HOME)
    assert ed.cursor == 0
    ed.handle_key(raw.KEY_END)
    assert ed.cursor == len(ed.buf)


# ---------------------------------------------------------------------------
# Live capabilities / flags
# ---------------------------------------------------------------------------


def test_live_capabilities_shape(tui_home):
    tmp, raw, live, _ = tui_home
    caps = raw.live_capabilities()
    assert caps["ok"] is True
    assert "tty" in caps
    assert "platform" in caps
    assert caps["modules"]["raw"]


def test_live_enabled_env(tui_home, monkeypatch):
    tmp, raw, live, _ = tui_home
    monkeypatch.setenv("SUPERAI_TUI_LIVE", "0")
    assert live.live_enabled() is False
    monkeypatch.setenv("SUPERAI_TUI_LIVE", "1")
    # may be True or False depending on whether test runner is a TTY
    assert live.live_enabled() in {True, False}
    assert live.live_enabled() == raw.is_tty()


def test_process_cooked_vim_line(tui_home):
    tmp, raw, live, _ = tui_home
    from core.tui_vim import VimEngine

    eng = VimEngine(mode="normal", enabled=True)
    actions = []

    def apply_nav(name, count=1, arg=""):
        actions.append(name)
        return True

    r = live.process_cooked_vim_line("jk", eng, apply_nav)
    assert r is not None
    assert r.kind == "redraw"
    assert "scroll_down" in actions
    assert "scroll_up" in actions


def test_process_cooked_vim_quit(tui_home):
    tmp, raw, live, _ = tui_home
    from core.tui_vim import VimEngine

    eng = VimEngine(mode="normal", enabled=True)
    r = live.process_cooked_vim_line("q", eng, lambda *a, **k: True)
    assert r is not None and r.kind == "quit"


def test_process_cooked_skips_slash(tui_home):
    tmp, raw, live, _ = tui_home
    from core.tui_vim import VimEngine

    eng = VimEngine(mode="normal", enabled=True)
    assert live.process_cooked_vim_line("/help", eng, lambda *a, **k: True) is None


# ---------------------------------------------------------------------------
# A11y live file
# ---------------------------------------------------------------------------


def test_a11y_live_file_announce(tui_home):
    tmp, raw, live, a11y = tui_home
    ctl = a11y.A11yController(a11y.A11yConfig(enabled=True, announce_live=True))
    ctl.live_bell = False  # quieter tests
    ctl.announce("Focus messages.", immediate=True)
    path = a11y.live_announce_path()
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "Focus messages." in text
    st = ctl.status()
    assert "live_file" in st
    assert st["live_file"].endswith("a11y_live.txt")


def test_raw_tty_status_when_inactive(tui_home):
    tmp, raw, *_ = tui_home
    tty = raw.RawTTY(mouse=False)
    st = tty.status()
    assert st["active"] is False
    assert "platform" in st


def test_mouse_live_pipeline(tui_home):
    """Raw parse → mouse controller → focus action (live path without TTY)."""
    tmp, raw, live, _ = tui_home
    from core.tui_mouse import MouseController, MouseConfig

    events, _ = raw.feed_chars_to_events("\x1b[<0;5;10M")
    assert events[0].kind == "mouse"
    ctl = MouseController(MouseConfig(enabled=True))
    ctl.set_layout("classic", 80, 24)
    act = ctl.handle_sequence(events[0].mouse_seq)
    assert act.name == "focus_pane"
    assert act.pane == "messages"
