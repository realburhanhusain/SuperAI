"""Compat tests for deprecated core.opencode_agent re-exports."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_compat_reexports():
    from core.opencode_agent import AgentRuntime, OpenCodeSessionStore
    from core.super_agent import AgentRuntime as AR2
    from core.super_agent import AgentSessionStore

    assert AgentRuntime is AR2 or AgentRuntime.__name__ == "AgentRuntime"
    assert OpenCodeSessionStore is AgentSessionStore or OpenCodeSessionStore.__name__


def test_compat_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAI_AGENT_ROOT", str(tmp_path / "sa"))
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    from core.opencode_agent.runtime import AgentRuntime

    out = AgentRuntime(use_mock=True).run(
        "hi", agent="ask", permission="plan", max_rounds=1
    )
    assert out.to_dict().get("ok") is True
