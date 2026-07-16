"""N208 mux · N210 vim · N211 mouse · N215 a11y — thorough offline tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture()
def tui_home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai" / "tui").mkdir(parents=True)
    # sessions root too
    monkeypatch.setenv("SUPERAI_SESSIONS_ROOT", str(tmp_path / "sessions"))
    import importlib

    import core.tui_a11y as a11y
    import core.tui_mouse as mouse
    import core.tui_mux as mux
    import core.tui_vim as vim

    importlib.reload(mux)
    importlib.reload(vim)
    importlib.reload(mouse)
    importlib.reload(a11y)
    yield tmp_path, mux, vim, mouse, a11y


# =============================================================================
# N208 SessionMux
# =============================================================================


def test_mux_new_select_next_prev(tui_home):
    tmp, mux_mod, *_ = tui_home
    m = mux_mod.SessionMux(persist=True)
    a = m.new_window(session_id="sa-aaa", title="A", create_session=False)
    assert a["ok"] is True
    b = m.new_window(session_id="sa-bbb", title="B", create_session=False)
    assert b["ok"] is True
    assert m.state.active_index == 1
    m.prev_window()
    assert m.active_window().session_id == "sa-aaa"
    m.next_window()
    assert m.active_window().session_id == "sa-bbb"
    m.select(0)
    assert m.active_window().title == "A"


def test_mux_kill_and_bar(tui_home):
    tmp, mux_mod, *_ = tui_home
    m = mux_mod.SessionMux(persist=True)
    m.new_window(session_id="s1", title="one", create_session=False)
    m.new_window(session_id="s2", title="two", create_session=False)
    bar = m.status_bar()
    assert "one" in bar or "s1" in bar
    assert "*" in bar
    out = m.kill_window()
    assert out["ok"] is True
    assert out["window_count"] == 1


def test_mux_attach_existing(tui_home):
    tmp, mux_mod, *_ = tui_home
    m = mux_mod.SessionMux(persist=True)
    m.new_window(session_id="sa-x", title="X", create_session=False)
    again = m.attach("sa-x")
    assert again["ok"] is True
    assert again.get("already") is True
    m.attach("sa-y", title="Y")
    assert len(m.state.windows) == 2


def test_mux_rename_and_persist(tui_home):
    tmp, mux_mod, *_ = tui_home
    m = mux_mod.SessionMux(persist=True)
    m.new_window(session_id="s1", title="old", create_session=False)
    m.rename("new-title")
    m.rename_mux("work")
    loaded = mux_mod.load_mux()
    assert loaded.name == "work"
    assert loaded.windows[0].title == "new-title"


def test_mux_select_out_of_range(tui_home):
    tmp, mux_mod, *_ = tui_home
    m = mux_mod.SessionMux(persist=True)
    assert m.select(0)["ok"] is False
    m.new_window(session_id="s1", create_session=False)
    assert m.select(9)["ok"] is False


def test_mux_slash_handler(tui_home):
    tmp, mux_mod, *_ = tui_home
    m = mux_mod.SessionMux(persist=True)
    assert mux_mod.handle_mux_slash("new hello", mux=m)["ok"] is True
    assert mux_mod.handle_mux_slash("list", mux=m)["ok"] is True
    assert mux_mod.handle_mux_slash("next", mux=m)["ok"] is True
    h = mux_mod.handle_mux_slash("help", mux=m)
    assert "Multiplexed" in (h.get("help") or "")


def test_mux_new_creates_session(tui_home):
    tmp, mux_mod, *_ = tui_home
    m = mux_mod.SessionMux(persist=True)
    out = m.new_window(title="auto", agent="plan", create_session=True)
    assert out["ok"] is True
    sid = out["created"]["session_id"]
    assert sid.startswith("sa-")


# =============================================================================
# N210 Vim
# =============================================================================


def test_vim_insert_passthrough(tui_home):
    tmp, _, vim_mod, *_ = tui_home
    eng = vim_mod.VimEngine(mode="insert", enabled=True)
    a = eng.feed("x")
    assert a.name == vim_mod.ACTION_PASSTHROUGH
    assert a.arg == "x"


def test_vim_esc_to_normal_and_jk(tui_home):
    tmp, _, vim_mod, *_ = tui_home
    eng = vim_mod.VimEngine(mode="insert", enabled=True)
    eng.feed("Esc")
    assert eng.mode == "normal"
    assert eng.feed("j").name == vim_mod.ACTION_SCROLL_DOWN
    assert eng.feed("k").name == vim_mod.ACTION_SCROLL_UP


def test_vim_gg_and_G(tui_home):
    tmp, _, vim_mod, *_ = tui_home
    eng = vim_mod.VimEngine(mode="normal", enabled=True)
    assert eng.feed("g").name == vim_mod.ACTION_NONE
    assert eng.feed("g").name == vim_mod.ACTION_SCROLL_TOP
    assert eng.feed("G").name == vim_mod.ACTION_SCROLL_BOTTOM


def test_vim_count_prefix(tui_home):
    tmp, _, vim_mod, *_ = tui_home
    eng = vim_mod.VimEngine(mode="normal", enabled=True)
    eng.feed("3")
    a = eng.feed("j")
    assert a.name == vim_mod.ACTION_SCROLL_DOWN
    assert a.count == 3


def test_vim_ctrl_w_pane(tui_home):
    tmp, _, vim_mod, *_ = tui_home
    eng = vim_mod.VimEngine(mode="normal", enabled=True)
    eng.feed("Ctrl-w")
    a = eng.feed("w")
    assert a.name == vim_mod.ACTION_FOCUS_NEXT
    eng.feed("Ctrl-w")
    assert eng.feed("t").name == vim_mod.ACTION_MUX_NEXT


def test_vim_command_mode(tui_home):
    tmp, _, vim_mod, *_ = tui_home
    eng = vim_mod.VimEngine(mode="normal", enabled=True)
    eng.feed(":")
    assert eng.mode == "command"
    for ch in "q":
        eng.feed(ch)
    a = eng.feed("Enter")
    assert a.name == vim_mod.ACTION_SUBMIT_COMMAND
    assert a.arg == "q"
    parsed = eng.parse_command("q")
    assert parsed.name == vim_mod.ACTION_QUIT
    assert eng.parse_command("tabnew").name == vim_mod.ACTION_MUX_NEW
    assert eng.parse_command("bn").name == vim_mod.ACTION_MUX_NEXT


def test_vim_disabled_passthrough(tui_home):
    tmp, _, vim_mod, *_ = tui_home
    eng = vim_mod.VimEngine(mode="normal", enabled=False)
    a = eng.feed("j")
    assert a.name == vim_mod.ACTION_PASSTHROUGH


def test_vim_config_persist(tui_home):
    tmp, _, vim_mod, *_ = tui_home
    cfg = vim_mod.VimConfig(enabled=False, default_mode="normal")
    vim_mod.save_vim_config(cfg)
    loaded = vim_mod.load_vim_config()
    assert loaded.enabled is False
    assert loaded.default_mode == "normal"


def test_vim_slash(tui_home):
    tmp, _, vim_mod, *_ = tui_home
    eng = vim_mod.create_engine()
    assert vim_mod.handle_vim_slash("status", engine=eng)["ok"] is True
    assert vim_mod.handle_vim_slash("off", engine=eng)["enabled"] is False
    assert "Vim" in (vim_mod.handle_vim_slash("help", engine=eng).get("help") or "")


def test_vim_feed_sequence(tui_home):
    tmp, _, vim_mod, *_ = tui_home
    eng = vim_mod.VimEngine(mode="normal", enabled=True)
    acts = eng.feed_sequence("jk")
    assert [a.name for a in acts] == [
        vim_mod.ACTION_SCROLL_DOWN,
        vim_mod.ACTION_SCROLL_UP,
    ]


# =============================================================================
# N211 Mouse
# =============================================================================


def test_mouse_parse_sgr_click(tui_home):
    tmp, _mux, _vim, mouse_mod, _a11y = tui_home
    seq = "\x1b[<0;10;5M"
    ev = mouse_mod.parse_mouse_sgr(seq)
    assert ev is not None
    assert ev.x == 10 and ev.y == 5
    assert ev.pressed is True


def test_mouse_parse_sgr_wheel(tui_home):
    tmp, _mux, _vim, mouse_mod, _a11y = tui_home
    up = mouse_mod.parse_mouse_sgr("\x1b[<64;10;5M")
    assert up is not None and up.wheel == "up"
    down = mouse_mod.parse_mouse_sgr("\x1b[<65;10;5M")
    assert down is not None and down.wheel == "down"


def test_mouse_parse_x10(tui_home):
    tmp, _mux, _vim, mouse_mod, _a11y = tui_home
    # button 0, x=5, y=5 → bytes 32+0, 32+5, 32+5
    seq = "\x1b[M" + chr(32) + chr(37) + chr(37)
    ev = mouse_mod.parse_mouse_x10(seq)
    assert ev is not None
    assert ev.x == 5 and ev.y == 5


def test_mouse_hit_test_regions(tui_home):
    tmp, _mux, _vim, mouse_mod, _a11y = tui_home
    regions = mouse_mod.default_regions(80, 24, "classic")
    # left side messages
    assert mouse_mod.hit_test(5, 10, regions) == "messages"
    # right side tools
    assert mouse_mod.hit_test(75, 10, regions) == "tools"


def test_mouse_controller_click_focus(tui_home):
    tmp, _mux, _vim, mouse_mod, _a11y = tui_home
    ctl = mouse_mod.MouseController(
        mouse_mod.MouseConfig(enabled=True, click_focus=True)
    )
    ctl.set_layout("classic", 80, 24)
    act = ctl.handle_event(mouse_mod.MouseEvent(button=0, x=5, y=10, pressed=True))
    assert act.name == "focus_pane"
    assert act.pane == "messages"


def test_mouse_controller_wheel(tui_home):
    tmp, _mux, _vim, mouse_mod, _a11y = tui_home
    ctl = mouse_mod.MouseController(
        mouse_mod.MouseConfig(enabled=True, wheel_scroll=True, scroll_lines=3)
    )
    act = ctl.handle_event(
        mouse_mod.MouseEvent(button=64, x=1, y=1, pressed=True, wheel="up")
    )
    assert act.name == "scroll_up"
    assert act.lines == 3


def test_mouse_disabled_noop(tui_home):
    tmp, _mux, _vim, mouse_mod, _a11y = tui_home
    ctl = mouse_mod.MouseController(mouse_mod.MouseConfig(enabled=False))
    act = ctl.handle_sequence("\x1b[<0;1;1M")
    assert act.name == "none"


def test_mouse_enable_ansi(tui_home):
    tmp, _mux, _vim, mouse_mod, _a11y = tui_home
    assert "1000" in mouse_mod.enable_mouse_ansi()
    assert "1006" in mouse_mod.enable_mouse_ansi()
    assert "l" in mouse_mod.disable_mouse_ansi()


def test_mouse_config_persist(tui_home):
    tmp, _mux, _vim, mouse_mod, _a11y = tui_home
    cfg = mouse_mod.MouseConfig(enabled=True, scroll_lines=5)
    mouse_mod.save_mouse_config(cfg)
    assert mouse_mod.load_mouse_config().scroll_lines == 5


def test_mouse_slash_hit(tui_home):
    tmp, _mux, _vim, mouse_mod, _a11y = tui_home
    ctl = mouse_mod.MouseController(mouse_mod.MouseConfig(enabled=True))
    out = mouse_mod.handle_mouse_slash("hit 5 10 classic", ctl=ctl)
    assert out["ok"] is True
    assert out.get("pane") == "messages"


def test_mouse_slash_parse_sgr_builder(tui_home):
    tmp, _mux, _vim, mouse_mod, _a11y = tui_home
    out = mouse_mod.handle_mouse_slash("parse sgr:0;12;8")
    assert out["ok"] is True
    assert out["event"]["x"] == 12


# =============================================================================
# N215 A11y
# =============================================================================


def test_a11y_linearize_landmarks(tui_home):
    tmp, *_, a11y_mod = tui_home

    class S:
        id = "sa-1"
        agent = "build"
        model = "m"
        permission = "plan"
        messages = [
            {"role": "user", "content": "hi"},
            {
                "role": "assistant",
                "content": "hello",
                "parts": [
                    {"type": "tool_call", "name": "read", "arguments": {}},
                    {"type": "tool_result", "ok": True},
                ],
            },
        ]
        estimated_cost_usd = 0.01
        tokens = 10

    cfg = a11y_mod.A11yConfig(enabled=True, verbosity="normal", include_landmarks=True)
    text = a11y_mod.linearize_frame(
        state=S(),
        events=[{"kind": "tool", "name": "read"}],
        tools_info=[{"name": "read", "desc": "read file"}],
        cfg=cfg,
        mux_bar="[default] *0:sa-1",
        vim_mode="NORMAL",
        mouse_on=True,
    )
    assert "[banner: session]" in text
    assert "[main: messages]" in text
    assert "[/main: messages]" in text
    assert "user: hi" in text
    assert "tool-call" in text
    assert "Windows:" in text or "mux" in text.lower() or "default" in text


def test_a11y_brief_omits_tools(tui_home):
    tmp, *_, a11y_mod = tui_home

    class S:
        id = "x"
        agent = "a"
        model = None
        permission = "ask"
        messages = [{"role": "user", "content": "z" * 500}]
        estimated_cost_usd = 0
        tokens = 0

    cfg = a11y_mod.A11yConfig(verbosity="brief", include_landmarks=True)
    text = a11y_mod.linearize_frame(state=S(), cfg=cfg)
    assert "[complementary: tools]" not in text
    assert "[main: messages]" in text


def test_a11y_announce_queue(tui_home):
    tmp, *_, a11y_mod = tui_home
    ctl = a11y_mod.A11yController(a11y_mod.A11yConfig(announce_live=True))
    ctl.announce("Hello")
    ctl.announce("World")
    notes = ctl.pop_announcements()
    assert notes == ["Hello", "World"]
    assert ctl.pop_announcements() == []


def test_a11y_controller_render_with_announce(tui_home):
    tmp, *_, a11y_mod = tui_home
    ctl = a11y_mod.A11yController(
        a11y_mod.A11yConfig(enabled=True, verbosity="normal")
    )
    ctl.announce("Ready")

    class S:
        id = "s"
        agent = "build"
        model = "m"
        permission = "plan"
        messages = []
        estimated_cost_usd = 0
        tokens = 0

    text = ctl.render(state=S())
    assert text.startswith("ANNOUNCE: Ready")


def test_a11y_enable_persist(tui_home):
    tmp, *_, a11y_mod = tui_home
    ctl = a11y_mod.A11yController()
    ctl.enable(True, persist=True)
    loaded = a11y_mod.load_a11y_config()
    assert loaded.enabled is True
    ctl.set_verbosity("verbose", persist=True)
    assert a11y_mod.load_a11y_config().verbosity == "verbose"


def test_a11y_slash(tui_home):
    tmp, *_, a11y_mod = tui_home
    ctl = a11y_mod.A11yController()
    assert a11y_mod.handle_a11y_slash("on", ctl=ctl)["enabled"] is True
    assert a11y_mod.handle_a11y_slash("brief", ctl=ctl)["ok"] is True
    h = a11y_mod.handle_a11y_slash("help", ctl=ctl)
    assert "Screen-reader" in (h.get("help") or "")


def test_landmark_disabled(tui_home):
    tmp, *_, a11y_mod = tui_home
    body = a11y_mod.landmark("main", "messages", "hi", enabled=False)
    assert body == "hi"
    body2 = a11y_mod.landmark("main", "messages", "hi", enabled=True)
    assert body2.startswith("[main: messages]")


# =============================================================================
# Cross-cutting
# =============================================================================


def test_all_help_strings_nonempty(tui_home):
    tmp, mux_mod, vim_mod, mouse_mod, a11y_mod = tui_home
    for h in (
        mux_mod.MUX_HELP,
        vim_mod.VIM_HELP,
        mouse_mod.MOUSE_HELP,
        a11y_mod.A11Y_HELP,
    ):
        assert len(h) > 50
