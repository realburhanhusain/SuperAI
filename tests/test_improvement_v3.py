"""Improvement V3 A–D unit tests."""

import pytest

from core.tool_protocol import agent_with_tools, extract_tool_calls, run_tool_calls
from core.side_effect_audit import record_side_effect, recent
from core.cost_router import should_skip_or_shrink
from pathlib import Path

pytestmark = pytest.mark.unit


def test_extract_tool_call_json():
    calls = extract_tool_calls(
        '{"tool_call": {"name": "glob", "arguments": {"pattern": "*.py"}}}'
    )
    assert calls[0]["name"] == "glob"


def test_run_tool_calls(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAI_WORKSPACE", str(tmp_path))
    (tmp_path / "z.txt").write_text("hi", encoding="utf-8")
    res = run_tool_calls(
        [{"name": "read", "arguments": {"path": "z.txt"}}],
        permission_mode="plan",
    )
    assert res[0]["result"]["ok"] is True


def test_agent_with_tools_mock():
    out = agent_with_tools(
        "Just say hello without tools",
        model="gpt-4o",
        use_mock=True,
        max_rounds=1,
    )
    assert out.get("contract") == "superai.result.v1"
    assert "response" in out or out.get("ok") is not None


def test_side_effect_audit(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    record_side_effect("tool", name="read", ok=True, dry_run=True, detail="x")
    rows = recent(5)
    assert rows
    assert rows[-1]["name"] == "read"


def test_cost_shrink():
    d = should_skip_or_shrink(
        ["a", "b", "c"],
        "task " * 200,
        run_usd_limit=0.0,
        prefer_cheap=True,
    )
    assert d["action"] in {"shrunk", "block", "proceed"}
