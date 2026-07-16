"""Ask multi-turn session store."""

from pathlib import Path

from core.ask_session import AskSessionStore


def test_ask_session_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    store = AskSessionStore()
    sid = store.create()
    store.append_turn(sid, "hello", "hi there")
    store.append_turn(sid, "next", "ok")
    pref = store.context_preface(sid, max_turns=2)
    assert "hello" in pref
    assert "next" in pref
    rows = store.list_sessions()
    assert any(r.get("id") == sid for r in rows)
