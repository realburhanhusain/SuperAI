"""Not-important polish pack W1–W8 unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_w1_export_markdown(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAI_ASK_SESSION_ROOT", str(tmp_path / "sess"))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    from core.ask_session import AskSessionStore

    store = AskSessionStore()
    sid = store.create()
    store.append_turn(sid, "hello", "world", meta={"tokens": 3, "estimated_cost_usd": 0.01})
    dest = tmp_path / "out.md"
    exp = store.export_markdown(sid, dest=dest)
    assert exp["ok"] is True
    assert dest.is_file()
    text = dest.read_text(encoding="utf-8")
    assert "hello" in text and "world" in text


def test_w2_w3_sessions_undo(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAI_ASK_SESSION_ROOT", str(tmp_path / "sess"))
    from core.ask_session import AskSessionStore

    store = AskSessionStore()
    sid = store.create()
    store.append_turn(sid, "a", "b")
    store.append_turn(sid, "c", "d")
    assert len(store.list_sessions()) >= 1
    u = store.undo_turn(sid)
    assert u["ok"] is True
    assert u["turns_left"] == 1
    data = store.get(sid)
    assert len(data["turns"]) == 1


def test_w4_session_totals(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAI_ASK_SESSION_ROOT", str(tmp_path / "sess"))
    from core.ask_session import AskSessionStore

    store = AskSessionStore()
    sid = store.create()
    store.append_turn(sid, "u", "a", meta={"tokens": 10, "estimated_cost_usd": 0.02})
    store.append_turn(sid, "u2", "a2", meta={"tokens": 5, "cost": 0.01})
    tot = store.session_totals(sid)
    assert tot["tokens"] == 15
    assert abs(tot["estimated_cost_usd"] - 0.03) < 1e-9


def test_w5_command_palette():
    from core.tui_commands import command_palette, help_markdown, resolve_alias

    cmds = command_palette()
    assert any(c["cmd"] == "/export" for c in cmds)
    assert resolve_alias("cmds") == "commands"
    assert resolve_alias("quit") == "exit" or resolve_alias("q") == "exit"
    assert "/export" in help_markdown()


def test_w8_smoke_preflight():
    from core.smoke_preflight import smoke_preflight

    p = smoke_preflight(include_readiness=False)
    assert p["ok"] is True
    assert p["live_passed"] is False
    assert p["live_smoke_run"] is False
    assert p["credentialed_count"] >= 0
    assert len(p["providers"]) >= 5
    assert p["checklist"]
