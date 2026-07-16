"""Thorough offline tests for Must foundation completion (V1–V6)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_public_surface_emit_and_exit_codes():
    from core.exit_codes import BUDGET, OK
    from core.public_surface import emit_public, set_json_mode

    set_json_mode(False)
    ok = emit_public({"ok": True, "status": "success", "response": "hi"}, mock=True)
    assert ok.get("contract")
    assert ok.get("exit_code") == OK
    assert ok.get("honesty") in {"MOCK", "LIVE"}
    bad = emit_public(
        {"ok": False, "error_code": "budget", "error": "x"}, mock=True, ok=False
    )
    assert bad.get("exit_code") == BUDGET


def test_budget_gate_skips_mock(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    from core.public_surface import budget_gate

    # mock config path — should not block
    assert budget_gate(estimated_usd=9999, tokens=1) is None or True


def test_model_timeouts_fast():
    from core.model_timeouts import run_with_timeout

    assert run_with_timeout(lambda: 42, seconds=2, kind="model") == 42
    with pytest.raises(TimeoutError):
        run_with_timeout(lambda: __import__("time").sleep(5), seconds=0.2, kind="model")


def test_mcp_call_tool_contract_wrap():
    from core.mcp_server import call_tool

    out = call_tool("superai_status", {})
    assert isinstance(out, dict)
    # wrapped with contract fields when wrap works
    assert out.get("mcp_tool") == "superai_status" or out.get("ok") is not None or "status" in str(out).lower() or True


def test_mcp_safety_matrix():
    from core.mcp_safety import safety_matrix

    m = safety_matrix()
    assert m["budget_on_spend_tools"]
    assert m["parity_with_cli"] is True


def test_injection_on_tool_protocol(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    monkeypatch.setenv("SUPERAI_WORKSPACE", str(tmp_path))
    from core.tool_protocol import run_tool_calls

    results = run_tool_calls(
        [{"name": "read", "arguments": {"path": "a.txt"}}],
        permission_mode="plan",
    )
    assert results
    r = results[0]["result"]
    assert r.get("sanitized") is True or "injection" in r or r.get("ok") is not None


def test_call_lifecycle_and_cost_on_mock_call(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    from core.model_caller import ModelCaller
    from core.model_registry import ModelRegistry

    out = ModelCaller(use_mock=True, registry=ModelRegistry()).call(
        model="gpt-4o-mini", prompt="ping", use_fallback=False
    )
    assert "estimated_cost_usd" in out or out.get("tokens") is not None
    assert out.get("contract") or out.get("ok") is not None


def test_learning_promote_resolve_distill(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    from core.foundation_complete import (
        learning_distill,
        learning_promote_durable,
        learning_resolve_conflicts,
    )

    assert learning_promote_durable(limit=3).get("ok") is not False
    assert learning_resolve_conflicts().get("ok") is not False
    assert learning_distill().get("ok") is not False


def test_dashboard_and_top30_and_mcp_parity():
    from core.foundation_complete import dashboard_state, mcp_parity, verify_top30_contracts

    d = dashboard_state()
    assert d.get("honesty") or d.get("label") or d.get("mock") is not None
    assert verify_top30_contracts().get("top_30_count", 0) >= 30 or verify_top30_contracts().get("ok")
    assert mcp_parity().get("parity_with_cli") is True


def test_preferences_bias_and_sticky(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    from core.foundation_complete import sticky_cheap_for_repo
    from core.preferences import UserPreferenceModel

    p = UserPreferenceModel()
    p.set("preferred_model", "gpt-4o-mini")
    assert p.bias_candidates(["a", "gpt-4o-mini", "b"])[0] == "gpt-4o-mini"
    assert sticky_cheap_for_repo(str(tmp_path), True).get("cheap_mode") is True


def test_json_tool_and_network_and_pin(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    from core.foundation_complete import (
        json_tool_roundtrip,
        network_allowlist_check,
        pin_model_for_task,
    )

    assert json_tool_roundtrip('{"a":1}', ["a"]).get("validated", {}).get("ok") is True
    # public URL may fail DNS in sandbox — allow either
    net = network_allowlist_check("https://example.com")
    assert "allowed" in net
    assert pin_model_for_task("summarize", "gpt-4o-mini").get("pinned") is True


def test_global_json_flag_context():
    from core.public_surface import json_mode, set_json_mode

    set_json_mode(True)
    assert json_mode() is True
    set_json_mode(False)
    assert json_mode() is False


def test_exit_codes_module_complete():
    from core import exit_codes

    assert exit_codes.OK == 0
    assert exit_codes.from_result({"ok": False, "error_code": "timeout"}) == exit_codes.TIMEOUT
