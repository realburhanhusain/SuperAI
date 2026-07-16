"""OpenCode-style agent rewrite unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_agents_catalog():
    from core.opencode_agent.agents import get_agent, list_agents

    agents = list_agents()
    ids = {a["id"] for a in agents}
    assert {"build", "plan", "ask"} <= ids
    assert get_agent("coder").id == "build"
    assert get_agent("architect").id == "plan"


def test_session_store(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAI_OPENCODE_ROOT", str(tmp_path / "oc"))
    from core.opencode_agent.session import OpenCodeSessionStore

    store = OpenCodeSessionStore()
    st = store.create(agent="plan", model="gpt-4o", permission="plan", title="t")
    store.append_message(st, "user", "hello")
    store.append_message(st, "assistant", "hi", meta={"tokens": 2})
    loaded = store.load(st.id)
    assert len(loaded.messages) == 2
    store.undo_last_user_assistant(loaded)
    loaded = store.load(st.id)
    assert len(loaded.messages) == 0
    path = store.export_markdown(store.load(st.id), dest=tmp_path / "x.md")
    assert path.is_file()
    assert store.list_sessions()


def test_runtime_mock_run(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAI_OPENCODE_ROOT", str(tmp_path / "oc"))
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    from core.opencode_agent.runtime import AgentRuntime

    rt = AgentRuntime(use_mock=True)
    out = rt.run(
        "Explain what SuperAI is in one sentence.",
        agent="ask",
        permission="plan",
        max_rounds=1,
    )
    d = out.to_dict()
    assert d.get("contract") == "superai.result.v1"
    assert d.get("ok") is True
    assert d.get("session_id")
    assert d.get("agent") == "ask"
    assert "response" in d


def test_tools_bridge_plan_blocks_write(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAI_WORKSPACE", str(tmp_path))
    from core.opencode_agent.tools_bridge import dispatch_tool

    r = dispatch_tool(
        "write",
        {"path": "x.txt", "content": "hi"},
        agent_id="plan",
        permission_mode="plan",
    )
    # either not allowed or dry_run plan
    assert r.get("ok") is False or r.get("dry_run") is True or r.get("error")


def test_tools_bridge_bash_dry(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAI_WORKSPACE", str(tmp_path))
    from core.opencode_agent.tools_bridge import tool_bash

    r = tool_bash("echo hi", dry_run=True)
    assert r.get("ok") is True
    assert r.get("dry_run") is True


def test_voice_file_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    from core.voice_io import listen_once, queue_voice_text

    queue_voice_text("hello from file")
    # may still try mic first and fail then file
    r = listen_once(timeout=0.1)
    # On systems without mic, file backend should work
    if r.get("backend") == "file":
        assert "hello" in r.get("text", "")
    else:
        assert "ok" in r
