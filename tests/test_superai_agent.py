"""SuperAI multi-agent unit tests (product name SuperAI)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_agents_catalog():
    from core.superai_agent.agents import get_agent, list_agents

    agents = list_agents()
    ids = {a["id"] for a in agents}
    assert {"build", "plan", "ask"} <= ids
    assert get_agent("coder").id == "build"


def test_session_store(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAI_SESSIONS_ROOT", str(tmp_path / "sa"))
    from core.superai_agent.session import SuperAISessionStore

    store = SuperAISessionStore()
    st = store.create(agent="plan", model="gpt-4o", permission="plan", title="t")
    assert st.id.startswith("sa-")
    store.append_message(st, "user", "hello")
    store.append_message(st, "assistant", "hi", meta={"tokens": 2})
    loaded = store.load(st.id)
    assert len(loaded.messages) == 2
    path = store.export_markdown(loaded, dest=tmp_path / "x.md")
    assert path.is_file()
    assert "SuperAI agent session" in path.read_text(encoding="utf-8")


def test_runtime_mock_run(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAI_SESSIONS_ROOT", str(tmp_path / "sa"))
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    from core.superai_agent.runtime import AgentRuntime

    rt = AgentRuntime(use_mock=True)
    out = rt.run(
        "Explain SuperAI in one sentence.",
        agent="ask",
        permission="plan",
        max_rounds=1,
    )
    d = out.to_dict()
    assert d.get("contract") == "superai.result.v1"
    assert d.get("ok") is True
    assert d.get("session_id", "").startswith("sa-")


def test_package_exports():
    from core.superai_agent import AgentRuntime, SuperAISessionStore, list_agents

    assert AgentRuntime is not None
    assert SuperAISessionStore is not None
    assert list_agents()
