"""N209 — Split-pane TUI: thorough offline tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text

pytestmark = pytest.mark.unit


@pytest.fixture()
def tui_home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai" / "tui").mkdir(parents=True)
    import importlib

    import core.split_pane_tui as spt

    importlib.reload(spt)
    yield tmp_path, spt


# ---------------------------------------------------------------------------
# Config / persistence
# ---------------------------------------------------------------------------


def test_default_config(tui_home):
    tmp_path, spt = tui_home
    cfg = spt.SplitPaneConfig()
    assert cfg.layout in spt.PRESETS
    assert cfg.focus == "messages"
    assert cfg.hidden == []


def test_save_load_config(tui_home):
    tmp_path, spt = tui_home
    cfg = spt.SplitPaneConfig(layout="triple", focus="tools", hidden=["cost"])
    path = spt.save_config(cfg)
    assert path.is_file()
    loaded = spt.load_config()
    assert loaded.layout == "triple"
    assert loaded.focus == "tools"
    assert "cost" in loaded.hidden


def test_from_dict_invalid_layout_falls_back(tui_home):
    tmp_path, spt = tui_home
    cfg = spt.SplitPaneConfig.from_dict({"layout": "nope", "focus": "zzz"})
    assert cfg.layout == spt.DEFAULT_LAYOUT
    assert cfg.focus == "messages"


# ---------------------------------------------------------------------------
# Presets & tree ops
# ---------------------------------------------------------------------------


def test_list_layouts(tui_home):
    tmp_path, spt = tui_home
    layouts = spt.list_layouts()
    names = {L["name"] for L in layouts}
    assert {"classic", "h-split", "v-split", "triple", "quad", "focus", "agent", "ide"} <= names
    for L in layouts:
        assert L["panes"]
        assert L["description"]


def test_panes_in_tree_agent(tui_home):
    tmp_path, spt = tui_home
    panes = spt.panes_in_tree(spt.PRESETS["agent"]["tree"])
    assert "header" in panes
    assert "messages" in panes
    assert "tools" in panes
    assert "status" in panes


def test_filter_tree_hides_leaf(tui_home):
    tmp_path, spt = tui_home
    tree = spt.PRESETS["triple"]["tree"]
    filtered = spt.filter_tree(tree, ["tools"])
    panes = spt.panes_in_tree(filtered)
    assert "tools" not in panes
    assert "messages" in panes
    assert "events" in panes


def test_filter_tree_all_hidden_returns_none(tui_home):
    tmp_path, spt = tui_home
    tree = {"kind": "leaf", "pane": "messages"}
    assert spt.filter_tree(tree, ["messages"]) is None


def test_filter_collapses_single_child(tui_home):
    tmp_path, spt = tui_home
    tree = {
        "kind": "row",
        "ratio": [1, 1],
        "children": [
            {"kind": "leaf", "pane": "messages"},
            {"kind": "leaf", "pane": "tools"},
        ],
    }
    filtered = spt.filter_tree(tree, ["tools"])
    assert filtered["kind"] == "leaf"
    assert filtered["pane"] == "messages"


# ---------------------------------------------------------------------------
# Layout build
# ---------------------------------------------------------------------------


def test_build_layout_classic(tui_home):
    tmp_path, spt = tui_home
    cfg = spt.SplitPaneConfig(layout="classic", focus="messages")
    lay = spt.build_layout(
        {"messages": Text("hello"), "tools": Text("tools")},
        cfg=cfg,
    )
    assert isinstance(lay, Layout)


def test_build_layout_each_preset(tui_home):
    tmp_path, spt = tui_home
    contents = {p: Text(p) for p in spt.PANE_IDS}
    for name in spt.PRESETS:
        cfg = spt.SplitPaneConfig(layout=name, focus="messages")
        lay = spt.build_layout(contents, cfg=cfg)
        assert isinstance(lay, Layout), name


def test_build_layout_with_hidden(tui_home):
    tmp_path, spt = tui_home
    cfg = spt.SplitPaneConfig(layout="triple", hidden=["events"], focus="messages")
    lay = spt.build_layout(
        {"messages": Text("m"), "tools": Text("t"), "events": Text("e")},
        cfg=cfg,
    )
    assert isinstance(lay, Layout)
    summary = spt.layout_summary(cfg)
    assert "events" not in summary["visible_panes"]


def test_wrap_pane_focus_highlight(tui_home):
    tmp_path, spt = tui_home
    cfg = spt.SplitPaneConfig(focus="tools", border_focused="bright_cyan")
    p = spt.wrap_pane("tools", Text("x"), cfg)
    assert isinstance(p, Panel)
    assert "▸" in str(p.title)
    p2 = spt.wrap_pane("messages", Text("y"), cfg)
    assert "▸" not in str(p2.title)


def test_demo_frame(tui_home):
    tmp_path, spt = tui_home
    lay = spt.demo_frame(layout="quad")
    assert isinstance(lay, Layout)


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


def test_set_layout(tui_home):
    tmp_path, spt = tui_home
    out = spt.set_layout("quad", persist=True)
    assert out["ok"] is True
    assert out["layout"] == "quad"
    assert spt.load_config().layout == "quad"


def test_set_layout_alias(tui_home):
    tmp_path, spt = tui_home
    assert spt.set_layout("h", persist=False)["layout"] == "h-split"
    assert spt.set_layout("3", persist=False)["layout"] == "triple"
    assert spt.set_layout("2x2", persist=False)["layout"] == "quad"


def test_set_layout_unknown(tui_home):
    tmp_path, spt = tui_home
    out = spt.set_layout("no-such", persist=False)
    assert out["ok"] is False
    assert out["error"] == "unknown_layout"


def test_set_focus_and_cycle(tui_home):
    tmp_path, spt = tui_home
    spt.set_layout("triple", persist=True)
    spt.set_focus("messages", persist=True)
    c1 = spt.cycle_focus(persist=True)
    assert c1["ok"] is True
    assert c1["focus"] in spt.layout_summary()["visible_panes"]
    c2 = spt.cycle_focus(persist=True)
    assert c2["focus"] != c1["focus"] or len(spt.layout_summary()["visible_panes"]) == 1


def test_hide_show_pane(tui_home):
    tmp_path, spt = tui_home
    spt.set_layout("triple", persist=True)
    h = spt.hide_pane("tools", persist=True)
    assert h["ok"] is True
    assert "tools" in h["hidden"]
    assert "tools" not in spt.layout_summary()["visible_panes"]
    s = spt.show_pane("tools", persist=True)
    assert s["ok"] is True
    assert "tools" not in s["hidden"]


def test_hide_moves_focus(tui_home):
    tmp_path, spt = tui_home
    spt.set_layout("classic", persist=True)
    spt.set_focus("tools", persist=True)
    spt.hide_pane("tools", persist=True)
    assert spt.load_config().focus != "tools"


def test_set_ratio_simple(tui_home):
    tmp_path, spt = tui_home
    out = spt.set_ratio("3:1", persist=True)
    assert out["ok"] is True
    assert out["ratio"] == [3.0, 1.0]
    assert "messages:tools" in out["overrides"]


def test_set_ratio_named(tui_home):
    tmp_path, spt = tui_home
    out = spt.set_ratio("messages:tools=2:1", persist=True)
    assert out["ok"] is True
    assert out["key"] == "messages:tools"
    assert out["ratio"] == [2.0, 1.0]


def test_set_ratio_triple(tui_home):
    tmp_path, spt = tui_home
    out = spt.set_ratio("3:1:1", persist=True)
    assert out["ok"] is True
    assert len(out["ratio"]) == 3


def test_set_ratio_bad(tui_home):
    tmp_path, spt = tui_home
    assert spt.set_ratio("", persist=False)["ok"] is False
    assert spt.set_ratio("a:b", persist=False)["ok"] is False


def test_reset_config(tui_home):
    tmp_path, spt = tui_home
    spt.set_layout("quad", persist=True)
    spt.hide_pane("cost", persist=True)
    out = spt.reset_config(persist=True)
    assert out["ok"] is True
    cfg = spt.load_config()
    assert cfg.layout == spt.DEFAULT_LAYOUT
    assert cfg.hidden == []


# ---------------------------------------------------------------------------
# Slash handler
# ---------------------------------------------------------------------------


def test_handle_split_slash_not_handled(tui_home):
    tmp_path, spt = tui_home
    out = spt.handle_split_slash("cost", "", persist=False)
    assert out.get("handled") is False


def test_handle_split_slash_layout(tui_home):
    tmp_path, spt = tui_home
    out = spt.handle_split_slash("split", "ide", persist=True)
    assert out.get("handled") is True
    assert out.get("ok") is True
    assert out.get("layout") == "ide"


def test_handle_split_slash_panes_layouts(tui_home):
    tmp_path, spt = tui_home
    p = spt.handle_split_slash("panes", "", persist=False)
    assert p["handled"] is True
    assert "visible" in p
    L = spt.handle_split_slash("layouts", "", persist=False)
    assert L["handled"] is True
    assert L["layouts"]


def test_handle_split_slash_help(tui_home):
    tmp_path, spt = tui_home
    out = spt.handle_split_slash("split-help", "", persist=False)
    assert out["handled"] is True
    assert "Split-pane" in (out.get("help") or "")


def test_handle_split_slash_focus_cycle_ratio(tui_home):
    tmp_path, spt = tui_home
    spt.handle_split_slash("layout", "agent", persist=True)
    f = spt.handle_split_slash("focus", "tools", persist=True)
    assert f["focus"] == "tools"
    c = spt.handle_split_slash("cycle", "", persist=True)
    assert c["ok"] is True
    r = spt.handle_split_slash("ratio", "2:1", persist=True)
    assert r["ok"] is True


# ---------------------------------------------------------------------------
# Agent state content
# ---------------------------------------------------------------------------


def test_content_from_agent_state(tui_home):
    tmp_path, spt = tui_home

    class S:
        id = "s1"
        agent = "build"
        model = "m"
        permission = "ask"
        messages = [
            {"role": "user", "content": "hi"},
            {
                "role": "assistant",
                "content": "hello",
                "parts": [
                    {"type": "tool_call", "name": "read", "arguments": {"path": "a"}},
                    {"type": "tool_result", "ok": True},
                ],
            },
        ]
        estimated_cost_usd = 0.01
        tokens = 42

    contents = spt.content_from_agent_state(
        state=S(),
        events=[{"kind": "tool", "name": "read"}],
        tools_info=[{"name": "read", "desc": "read file"}],
        stream_on=True,
        status="ok",
        changeset_summary={"staged": 1},
        sessions=[{"id": "s1", "agent": "build", "messages": 2}],
    )
    for key in ("header", "messages", "tools", "events", "cost", "status", "changeset", "sessions"):
        assert key in contents


def test_render_split_frame(tui_home):
    tmp_path, spt = tui_home

    class S:
        id = "x"
        agent = "plan"
        model = None
        permission = "plan"
        messages = []
        estimated_cost_usd = 0
        tokens = 0

    lay = spt.render_split_frame(state=S(), events=[], tools_info=[], cfg=spt.SplitPaneConfig(layout="agent"))
    assert isinstance(lay, Layout)


def test_status_public(tui_home):
    tmp_path, spt = tui_home
    st = spt.status_public()
    assert st.get("ok") is True
    assert "layout" in st
    assert "presets" in st


# ---------------------------------------------------------------------------
# Integration with superai_agent.tui.render_frame
# ---------------------------------------------------------------------------


def test_agent_tui_render_frame_uses_split(tui_home, monkeypatch):
    tmp_path, spt = tui_home
    # ensure tools catalog does not require network
    import core.superai_agent.tui as atui

    class S:
        id = "a"
        agent = "build"
        model = "auto"
        permission = "plan"
        messages = [{"role": "user", "content": "test"}]
        estimated_cost_usd = 0.0
        tokens = 0

    monkeypatch.setattr(atui, "catalog", lambda: [{"name": "read", "desc": "r"}])
    lay = atui.render_frame(S(), [{"kind": "x"}], stream_on=True, use_split=True)
    assert isinstance(lay, Layout)
    lay2 = atui.render_frame(S(), [], use_split=False)
    assert isinstance(lay2, Layout)


def test_ratio_override_applied_in_tree(tui_home):
    tmp_path, spt = tui_home
    tree = spt.PRESETS["classic"]["tree"]
    overridden = spt.apply_ratio_overrides(tree, {"messages:tools": [5.0, 1.0]})
    assert overridden["ratio"] == [5.0, 1.0]


def test_config_path_under_home(tui_home):
    tmp_path, spt = tui_home
    p = spt.config_path()
    assert str(tmp_path) in str(p)
    assert p.name == "split_pane.json"
