"""Result contract + profiles + permission modes."""

from core.result_contract import apply_contract, assert_contract, empty_contract
from core.permission_mode import (
    apply_to_cli_tool_kwargs,
    force_dry_run,
    normalize_mode,
    should_auto_approve,
)
from core.run_profiles import apply_profile_to_config, get_profile, list_profiles
from core.registry_validate import validate_registry
from core.config import Config
from core.multi_cli_advisory import multi_cli_board
from pathlib import Path


def test_apply_contract_fills_required():
    r = apply_contract({"ok": True, "model": "gpt-4o"}, mock=True, dry_run=True)
    issues = assert_contract(r)
    assert issues == []
    assert r["mock"] is True
    assert r["dry_run"] is True
    assert r["contract"] == "superai.result.v1"
    assert "gpt-4o" in r["model_chain"]


def test_empty_contract_keys():
    e = empty_contract(status="error")
    assert e["ok"] is False
    assert assert_contract(e) == []


def test_permission_modes():
    assert normalize_mode("YOLO") == "yolo"
    assert force_dry_run("plan") is True
    assert should_auto_approve("yolo") is True
    kw = apply_to_cli_tool_kwargs("plan")
    assert kw["dry_run"] is True


def test_profiles():
    assert "cheap" in list_profiles()
    p = get_profile("local-only")
    assert p.get("prefer_local") or p.get("local_only")
    cfg = Config()
    applied = apply_profile_to_config(cfg, "cheap")
    assert applied.get("run_profile") == "cheap"


def test_validate_registry():
    v = validate_registry()
    assert "total" in v
    assert v["total"] >= 1


def test_board_has_contract(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    out = multi_cli_board(
        "quick check",
        mode="review",
        members=["gpt-4o"],
        dry_run=True,
        approve=True,
    )
    assert out.get("contract") == "superai.result.v1"
    assert out.get("dry_run") is True
    assert out.get("mock") is True
    assert "tokens" in out
    assert "estimated_cost_usd" in out
