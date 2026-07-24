"""
Verification test suite for AGY Stage I1 residuals (P0-P2 spend, budget, MCP, contracts).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_spend_guard_fail_closed_on_exception(monkeypatch):
    from core.spend_guard import budget_precheck

    def _broken_guard(*args, **kwargs):
        raise RuntimeError("simulated budget guard failure")

    monkeypatch.setattr("core.budget.BudgetGuard.enforce_or_block", _broken_guard)

    res = budget_precheck(estimated_usd=0.1, tokens=50, enforce=True)
    assert res["ok"] is False
    assert res["blocked"] is True
    assert res["error_code"] == "budget_internal"
    assert "simulated budget guard failure" in res["error"]


def test_call_stream_live_budget_gate(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    from core.model_caller import ModelCaller
    from core.token_stream import get_stream_meta

    # Mock pre_call to return blocked
    def _blocked_pre_call(*args, **kwargs):
        return {"ok": False, "blocked": True, "error": "stream_budget_exceeded"}

    monkeypatch.setattr("core.call_lifecycle.pre_call", _blocked_pre_call)

    caller = ModelCaller(use_mock=False)
    chunks = list(caller.call_stream("claude-3-5-sonnet-20241022", "hello"))
    assert len(chunks) == 0
    meta = get_stream_meta()
    assert meta["mode"] == "budget_blocked"
    assert meta["fallback_reason"] == "stream_budget_exceeded"


def test_mcp_safety_matrix_exhaustive():
    from core.mcp_safety import safety_matrix

    m = safety_matrix()
    assert m["ok"] is True
    assert m["parity_with_cli"] is True
    assert len(m["cli_parity_unmapped"]) == 0
    assert "superai_ask_session" in m["spend_tools_registered"]
    assert "superai_cli_parallel" in m["spend_tools_registered"]


def test_top30_commands_contract_depth():
    from core.public_surface import TOP_30_COMMANDS, json_surface_report, verify_top_commands_registered

    assert len(TOP_30_COMMANDS) >= 30
    rep = json_surface_report()
    assert rep["ok"] is True
    assert rep["count"] >= 20
    ver = verify_top_commands_registered()
    assert ver["ok"] is True
    assert ver["top_30_count"] >= 30
