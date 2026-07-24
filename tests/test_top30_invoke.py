"""M090: real offline TOP_30 help + contract invocation harness."""

from __future__ import annotations

import pytest

from core.contract_registry import invoke_top30_offline, offline_library_invokers
from core.foundation_complete import verify_top30_contracts
from core.public_surface import TOP_30_COMMANDS

pytestmark = pytest.mark.unit


def test_top30_offline_invoke_all_commands():
    out = invoke_top30_offline()
    assert out.get("top_30_count") == len(TOP_30_COMMANDS)
    assert out.get("help_pass") == len(TOP_30_COMMANDS), out.get("failures")
    assert out.get("contract_pass") == len(TOP_30_COMMANDS), out.get("failures")
    assert out.get("ok") is True
    assert len(out.get("results") or []) == len(TOP_30_COMMANDS)
    for row in out["results"]:
        assert row.get("help_ok") is True
        assert row.get("contract_ok") is True


def test_top30_library_invokers_return_contracts():
    inv = offline_library_invokers()
    assert "status" in inv
    assert "contract-smoke" in inv
    r = inv["status"]()
    assert isinstance(r, dict)
    assert r.get("ok") is True
    assert r.get("contract") == "superai.result.v1" or "contract" in r


def test_top30_broken_fixture_detected():
    """Intentional broken fixture: missing required contract keys fail ensure_list."""
    from core.contract_registry import ensure_list

    broken = [{"ok": True, "status": "success"}]  # missing many REQUIRED_KEYS
    checked = ensure_list(broken)
    assert checked.get("ok") is False
    assert checked.get("failures")


def test_verify_top30_contracts_uses_invocation():
    v = verify_top30_contracts()
    assert v.get("ok") is True
    assert (v.get("invocation") or {}).get("help_pass") == len(TOP_30_COMMANDS)
    assert v.get("top_30_count") >= 30
