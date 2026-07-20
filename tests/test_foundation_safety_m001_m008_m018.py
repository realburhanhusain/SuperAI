"""Exhaustive offline proof for M001 / M008 / M018 foundation safety."""

from __future__ import annotations

import inspect

import pytest

pytestmark = pytest.mark.unit


def test_m001_spend_registry_and_model_caller_budget():
    from core.foundation_safety import SPEND_PATHS, audit_m001
    from core.model_caller import ModelCaller

    assert len(SPEND_PATHS) >= 12
    assert all(p.get("budget") for p in SPEND_PATHS)
    src = inspect.getsource(ModelCaller.call)
    assert "pre_call" in src
    assert "skip_budget" in src

    out = audit_m001()
    assert out.get("contract")
    assert out.get("ok") is True, out.get("issues")
    assert out.get("spend_path_count", 0) >= 12


def test_m001_pre_call_skip_and_precheck_shape():
    from core.call_lifecycle import pre_call
    from core.spend_guard import budget_precheck

    open_ok = pre_call("gpt-4o-mini", "hello", skip_budget=True)
    assert not open_ok.get("blocked")
    pc = budget_precheck(estimated_usd=0.0, tokens=1, enforce=False)
    assert isinstance(pc, dict)


def test_m001_budget_gate_public_surface():
    from core.public_surface import budget_gate

    # mock / dry paths should not raise
    assert budget_gate(estimated_usd=0.01, tokens=10, skip=True) is None


def test_m008_tui_envelope_helper():
    from core.foundation_safety import tui_envelope

    env = tui_envelope({"msg": "hi"})
    assert env.get("ok") is True
    assert env.get("contract")
    assert env.get("handled") is True
    bad = tui_envelope({"error": "x"}, ok=False)
    assert bad.get("ok") is False
    assert bad.get("contract")


def test_m008_all_tui_slash_handlers_return_contract():
    from core.foundation_safety import TUI_SLASH_HANDLERS, audit_m008
    from core.tui_a11y import handle_a11y_slash
    from core.tui_a11y_native import handle_native_a11y_slash
    from core.tui_mouse import handle_mouse_slash
    from core.tui_mux import handle_mux_slash
    from core.tui_process_mux import handle_pmux_slash
    from core.tui_vim import handle_vim_slash

    handlers = [
        handle_mux_slash,
        handle_pmux_slash,
        handle_vim_slash,
        handle_mouse_slash,
        handle_a11y_slash,
        handle_native_a11y_slash,
    ]
    assert len(TUI_SLASH_HANDLERS) >= 6
    for fn in handlers:
        out = fn("status")
        assert isinstance(out, dict), fn
        assert out.get("contract"), (fn, out.keys())
        assert "ok" in out
        assert out.get("handled") is True

    audit = audit_m008()
    assert audit.get("ok") is True, audit.get("issues")
    assert len(audit.get("checked") or []) >= 5


def test_m008_pmux_and_mux_unknown_still_envelope():
    from core.tui_mux import handle_mux_slash
    from core.tui_process_mux import handle_pmux_slash

    for fn, arg in ((handle_mux_slash, "not-a-real-sub"), (handle_pmux_slash, "not-a-real-sub")):
        out = fn(arg)
        assert out.get("contract")
        assert out.get("ok") is False
        assert out.get("handled") is True


def test_m018_subprocess_safety_run_and_timeouts():
    import sys

    from core.subprocess_safety import resolve_timeout, run, run_result
    from core.tool_timeouts import DEFAULTS

    assert resolve_timeout(kind="git") > 0
    assert "git" in DEFAULTS
    # Finite command with timeout
    r = run([sys.executable, "-c", "print(1)"], kind="default", timeout=30)
    assert r.returncode == 0
    assert "1" in (r.stdout or "")

    env = run_result([sys.executable, "-c", "print(2)"], kind="default", timeout=30)
    assert env.get("contract")
    assert env.get("ok") is True


def test_m018_timeout_fires():
    import sys

    from core.subprocess_safety import run_result

    out = run_result(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        kind="default",
        timeout=0.3,
    )
    assert out.get("ok") is False
    assert out.get("error_code") == "timeout" or "timeout" in str(out.get("error", "")).lower()


def test_m018_inventory_no_missing():
    from core.subprocess_safety import inventory_subprocess_sites

    inv = inventory_subprocess_sites()
    missing = inv.get("missing") or []
    assert inv.get("total", 0) >= 5
    assert missing == [], missing


def test_m018_audit_and_model_timeouts():
    from core.foundation_safety import audit_m018
    from core.model_timeouts import run_with_timeout

    assert run_with_timeout(lambda: 7, seconds=2, kind="model") == 7
    out = audit_m018()
    assert out.get("ok") is True, out.get("issues")


def test_audit_all_foundation_safety():
    from core.foundation_safety import audit_all

    all_out = audit_all()
    assert all_out.get("contract")
    assert all_out.get("ok") is True, {
        "M001": (all_out.get("M001") or {}).get("issues"),
        "M008": (all_out.get("M008") or {}).get("issues"),
        "M018": (all_out.get("M018") or {}).get("issues"),
    }
    assert all_out.get("complete") is True
    assert all_out.get("pct") == 100
