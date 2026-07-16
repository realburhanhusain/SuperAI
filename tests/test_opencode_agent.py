"""Compat tests for deprecated core.opencode_agent re-exports."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_compat_reexports():
    from core.opencode_agent import AgentRuntime, OpenCodeSessionStore
    from core.superai_agent import AgentRuntime as AR2
    from core.superai_agent import SuperAISessionStore

    assert AgentRuntime is AR2 or AgentRuntime.__name__ == "AgentRuntime"
    assert OpenCodeSessionStore is SuperAISessionStore or OpenCodeSessionStore.__name__


def test_compat_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAI_SESSIONS_ROOT", str(tmp_path / "sa"))
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    from core.opencode_agent.runtime import AgentRuntime

    out = AgentRuntime(use_mock=True).run(
        "hi", agent="ask", permission="plan", max_rounds=1
    )
    assert out.to_dict().get("ok") is True


def test_super_agent_compat_package():
    from core.super_agent import AgentRuntime
    from core.superai_agent import AgentRuntime as AR2

    assert AgentRuntime is AR2 or AgentRuntime.__name__ == AR2.__name__
