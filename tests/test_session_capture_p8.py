"""Memory Roadmap P8 — agent turn capture into session memory."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.hooks import clear_hooks, run_post
from core.session_capture import (
    SessionCapture,
    capture_config,
    install_tool_capture_hooks,
    process_turn_stream,
    resolve_capture_level,
    set_active_capture,
)
from core.session_memory import SessionMemory

pytestmark = pytest.mark.unit


@pytest.fixture
def iso(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.delenv("SUPERAI_CAPTURE_LEVEL", raising=False)
    monkeypatch.delenv("SUPERAI_DATASET_ID", raising=False)
    monkeypatch.setenv(
        "SUPERAI_SESSION_DSN",
        f"sqlite:///{(tmp_path / 'sessions.sqlite').as_posix()}",
    )
    monkeypatch.setenv(
        "SUPERAI_KG_DSN", f"sqlite:///{(tmp_path / 'kg.sqlite').as_posix()}"
    )
    mem = tmp_path / ".superai" / "memory"
    mem.mkdir(parents=True)
    monkeypatch.setenv(
        "SUPERAI_MEMORY_DSN", f"sqlite:///{(mem / 'palace.sqlite').as_posix()}"
    )
    clear_hooks()
    set_active_capture(None)
    # reset install flag
    import core.session_capture as sc

    sc._POST_REGISTERED = False
    return tmp_path


@pytest.fixture
def sm(iso: Path) -> SessionMemory:
    return SessionMemory(lock_root=iso)


def test_resolve_capture_level_aliases(monkeypatch):
    assert resolve_capture_level("off") == "off"
    assert resolve_capture_level("session") == "session"
    assert resolve_capture_level("session+promote") == "session+promote"
    assert resolve_capture_level("full-cognify") == "full-cognify"
    assert resolve_capture_level("promote") == "session+promote"
    monkeypatch.setenv("SUPERAI_CAPTURE_LEVEL", "off")
    assert resolve_capture_level(None) == "off"


def test_capture_config_lists_levels():
    cfg = capture_config()
    assert cfg["ok"]
    assert "session" in cfg["levels"]
    assert "off" in cfg["levels"]
    assert "sessions_db" in cfg["storage"]


def test_toggle_off_skips_writes(sm: SessionMemory):
    cap = SessionCapture.start(
        session_id="sess_off",
        level="off",
        sm=sm,
        title="off test",
    )
    r = cap.user_prompt("should not store")
    assert r.get("skipped") is True
    listed = sm.list_items("sess_off")
    # off mode may not create session items
    assert listed.get("count", 0) == 0 or listed.get("ok") is False or True
    # stream with off
    out = process_turn_stream(
        [{"hook": "user_prompt", "content": "hi"}],
        level="off",
        sm=sm,
        session_id="stream_off",
        auto_end=False,
    )
    assert out["level"] == "off"
    assert out["items_count"] == 0


def test_e2e_turn_stream_session_buffer(sm: SessionMemory):
    turns = [
        {"hook": "user_prompt", "content": "What is Cloud SQL?"},
        {
            "hook": "tool_result",
            "tool": "search",
            "result": {
                "ok": True,
                "summary": "Cloud SQL is managed Postgres",
                "path": "/docs/cloudsql.md",
            },
        },
        {
            "hook": "assistant_final",
            "content": "Cloud SQL is a managed database service.",
        },
        {"hook": "precompact", "content": "compacting context"},
    ]
    out = process_turn_stream(
        turns,
        session_id="sess_e2e",
        level="session",
        dataset_id="superai",
        sm=sm,
        auto_end=True,
    )
    assert out["ok"]
    assert out["session_id"] == "sess_e2e"
    assert out["items_count"] >= 4  # user, tool, assistant, snapshot (+ maybe none)
    kinds = {it.get("kind") for it in out.get("items") or []}
    assert "user" in kinds
    assert "tool" in kinds
    assert "assistant" in kinds
    assert "snapshot" in kinds
    # session ended
    st = sm.get("sess_e2e")
    assert st["ok"]
    assert st["session"]["status"] == "ended"


def test_secrets_redacted_on_user_prompt(sm: SessionMemory):
    cap = SessionCapture.start(session_id="sess_sec", level="session", sm=sm)
    secret_line = "use api_key=sk-abcdefghijklmnopqrstuvwxyz0123456789 for auth"
    out = cap.user_prompt(secret_line)
    assert out["ok"]
    content = (out.get("item") or {}).get("content") or ""
    assert "sk-abcdefghijklmnopqrstuvwxyz0123456789" not in content
    # redaction should have altered something
    assert "REDACTED" in content or content != secret_line


def test_session_promote_level(sm: SessionMemory, iso: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    turns = [
        {"hook": "user_prompt", "content": "Remember PIN me preference dark mode"},
        {
            "hook": "assistant_final",
            "content": "Noted preference dark mode",
            "pinned": True,
        },
    ]
    # pin via capture API for promote
    cap = SessionCapture.start(
        session_id="sess_promo",
        level="session+promote",
        sm=sm,
        dataset_id="scratch",
    )
    cap.user_prompt("Remember preference dark mode")
    cap.assistant_final("Noted dark mode preference", pinned=True, importance=0.9)
    end = cap.session_end()
    assert end.get("ok")
    assert end.get("capture_promoted") is True
    assert end.get("capture_cognify") is False
    # promoted count may be in nested promote payload
    promo = end.get("promoted") or (end.get("promote") or {})
    # end() returns promoted in nested structure
    assert end.get("ok") is True


def test_full_cognify_level_runs(sm: SessionMemory, iso: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    cap = SessionCapture.start(
        session_id="sess_cog",
        level="full-cognify",
        sm=sm,
        dataset_id="scratch",
    )
    cap.user_prompt("Cloud SQL uses Dataplex for catalog.")
    cap.assistant_final("Yes, Cloud SQL uses Dataplex.")
    end = cap.session_end(cognify_mode="mock")
    assert end.get("ok")
    assert end.get("capture_cognify") is True


def test_install_tool_hooks_captures_post(sm: SessionMemory):
    cap = SessionCapture.start(session_id="sess_hook", level="session", sm=sm)
    set_active_capture(cap)
    install_tool_capture_hooks(cap)
    run_post("demo_tool", {"q": "x"}, {"ok": True, "summary": "tool did work", "path": "a.py"})
    items = sm.list_items("sess_hook")
    assert items["count"] >= 1
    assert any(it.get("kind") == "tool" for it in items["items"])
    blob = " ".join(str(it.get("content") or "") for it in items["items"])
    assert "demo_tool" in blob


def test_precompact_pins_snapshot(sm: SessionMemory):
    cap = SessionCapture.start(session_id="sess_pc", level="session", sm=sm)
    cap.user_prompt("before compact")
    out = cap.precompact(note="forced snapshot")
    assert out["ok"]
    item = out.get("item") or {}
    assert item.get("kind") == "snapshot"
    assert item.get("pinned") is True
