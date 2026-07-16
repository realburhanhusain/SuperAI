"""Phase 6 smoke path + Phase 16 parked features tests."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_phase6_smoke_harness_no_false_pass():
    from core.live_smoke_complete import run_phase6_smoke

    r = run_phase6_smoke(allow_live=False)
    assert r.get("ok") is True
    assert r.get("phase6_complete_code") is True
    assert r.get("live_passed") is False


def test_parked_refuse_closed():
    from core.parked_features import invoke, list_refused, refuse

    assert refuse("P391")["ok"] is False
    assert invoke("P396")["ok"] is False
    assert list_refused()["count"] >= 10


def test_parked_optional_flags(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    from core.parked_features import (
        agent_only_enabled,
        catalog,
        load_flags,
        set_agent_only,
        set_display_name,
        splash_banner,
    )

    set_display_name("SuperAI Labs")
    assert "SuperAI" in splash_banner() or "Labs" in load_flags().get(
        "product_display_name", ""
    )
    set_agent_only(True)
    assert agent_only_enabled() is True
    set_agent_only(False)
    assert catalog()["count"] == 100


def test_enterprise_stubs():
    from core.enterprise_stubs import rbac_roles, sso_status

    assert len(rbac_roles()["roles"]) == 4
    assert sso_status()["sso_configured"] is False


def test_v6_all_phases_done_except_na():
    from core.v6_phase_status import phase_report

    r = phase_report()
    by = {p["phase"]: p["status"] for p in r["phases"]}
    for ph in range(0, 17):
        if ph in (17, 18, 19, 20):
            continue
        assert by[ph] == "done", f"phase {ph} not done: {by[ph]}"
    assert by[17] == "n/a"
