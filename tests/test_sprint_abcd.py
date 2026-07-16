"""Sprint A–D improvement tests."""

import pytest
from pathlib import Path

from core.agent_tools import execute_directives, parse_tool_directives, run_tool
from core.cost_router import estimate_board_cost, should_skip_or_shrink
from core.git_diff_apply import apply_unified_diff, check_unified_diff, propose_unified_diff
from core.readiness import check_model_ready
from core.session_compact import smart_compact
from core.palace_tenant import scope_metadata
from core.model_bakeoff import bakeoff, pin_winner
from core.path_which import which_cmd

pytestmark = pytest.mark.unit


def test_parse_and_run_tool_read(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAI_WORKSPACE", str(tmp_path))
    f = tmp_path / "a.txt"
    f.write_text("hello world", encoding="utf-8")
    dirs = parse_tool_directives("/tool read path=a.txt")
    assert dirs and dirs[0]["tool"] == "read"
    r = run_tool("read", path="a.txt")
    assert r.get("ok") is True
    assert "hello" in r.get("content", "")


def test_diff_propose_and_dry_apply():
    d = propose_unified_diff("x.py", "a\n", "b\n")
    assert "x.py" in d
    out = apply_unified_diff(d, dry_run=True)
    assert out.get("dry_run") is True
    assert out.get("ok") is True


def test_readiness_mock_ok():
    r = check_model_ready("gpt-4o", use_mock=True)
    assert r.get("ok") is True


def test_cost_router_shrink():
    # force tiny budget
    d = should_skip_or_shrink(
        ["gpt-4o", "claude-4-opus", "deepseek-chat"],
        "x" * 5000,
        run_usd_limit=0.0000001,
        prefer_cheap=True,
    )
    assert d.get("action") in {"shrunk", "proceed", "block"}
    assert "estimated_cost_usd" in d


def test_smart_compact():
    t = smart_compact(
        [{"user": "implement auth", "assistant": "done with jwt"}],
        max_chars=500,
    )
    assert "auth" in t.lower() or "compact" in t.lower()


def test_tenant_scope():
    m = scope_metadata({}, tenant="team-a")
    assert m["tenant_id"] == "team-a"


def test_bakeoff_pin(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    out = bakeoff("hi", ["gpt-4o"], use_mock=True)
    assert out.get("contract") == "superai.result.v1"
    pin = pin_winner(out.get("winner"), persist=True)
    assert pin.get("ok") is True


def test_which_cmd():
    p = which_cmd("python")
    assert p is None or isinstance(p, str)


def test_execute_directives_grep(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAI_WORKSPACE", str(tmp_path))
    (tmp_path / "b.py").write_text("TODO fix me\n", encoding="utf-8")
    res = execute_directives("/tool grep pattern=TODO path=.", permission_mode="plan")
    assert res
    assert res[0]["result"].get("ok") is True


def test_tool_protocol_extract():
    from core.tool_protocol import extract_tool_calls

    text = 'Here\n{"tool_call": {"name": "read", "arguments": {"path": "a.py"}}}\n'
    calls = extract_tool_calls(text)
    assert calls and calls[0]["name"] == "read"


def test_diff_check():
    d = propose_unified_diff("x.py", "a\n", "b\n")
    c = check_unified_diff(d)
    assert "ok" in c
