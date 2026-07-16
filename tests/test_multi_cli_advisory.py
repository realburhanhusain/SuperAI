"""Multi-CLI review/advisor board + structured protocol."""

from pathlib import Path

import pytest

from core.multi_cli_advisory import (
    default_council_members,
    merge_board,
    parse_structured_opinion,
    pick_advisory_clis,
    multi_cli_board,
)
from core.external_cli import ExternalCLIRegistry, CLI_ROLES


def test_advisor_and_reviewer_roles_exist():
    assert "advisor" in CLI_ROLES
    assert "reviewer" in CLI_ROLES
    reg = ExternalCLIRegistry()
    # gemini defaults to advisor, grok to reviewer
    assert reg.get("gemini").default_role == "advisor"
    assert reg.get("grok").default_role == "reviewer"
    assert reg.pick_for_role("advisor") is None or isinstance(
        reg.pick_for_role("advisor"), str
    )


def test_parse_structured_opinion_json():
    raw = """
    {"verdict": "request_changes", "confidence": 0.8,
     "findings": [{"severity": "high", "title": "auth gap", "detail": "no auth"}],
     "summary": "Needs auth before merge"}
    """
    o = parse_structured_opinion(raw, cli="grok", role="reviewer")
    assert o["verdict"] == "request_changes"
    assert o["confidence"] == 0.8
    assert o["findings"][0]["title"] == "auth gap"
    assert o["structured"] is True


def test_parse_structured_opinion_prose_fallback():
    o = parse_structured_opinion(
        "This looks good LGTM approve the change",
        cli="gemini",
        role="advisor",
    )
    assert o["verdict"] == "approve"
    assert "looks good" in o["summary"].lower() or "LGTM" in o["summary"]


def test_merge_board_majority_and_reject_escalation():
    opinions = [
        {"ok": True, "cli": "a", "verdict": "approve", "confidence": 0.7, "summary": "ok", "findings": []},
        {"ok": True, "cli": "b", "verdict": "reject", "confidence": 0.9, "summary": "bad", "findings": [{"severity": "high", "title": "x", "detail": "y"}]},
        {"ok": True, "cli": "c", "verdict": "reject", "confidence": 0.6, "summary": "no", "findings": []},
    ]
    board = merge_board(opinions)
    assert board["verdict"] == "reject"
    assert board["findings"]
    assert "a" in board["members"]


def test_multi_cli_board_dry_run(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    out = multi_cli_board(
        "Should we add rate limiting to the API?",
        mode="advise",
        clis=["grok", "gemini"],
        dry_run=True,
        approve=True,
    )
    assert out.get("ok") is True
    assert out.get("role") == "advisor"
    assert out.get("protocol") in {
        "superai.multi_cli_review.v1",
        "superai.multi_member_review.v2",
    }
    assert out.get("board", {}).get("verdict")
    assert len(out.get("opinions") or []) >= 1
    assert out.get("members")


def test_default_council_members_prefer_cli_prefix():
    members = default_council_members(3, prefer_clis=True)
    assert members
    # When any CLI is available they should be cli:*; otherwise API models
    assert all(isinstance(m, str) for m in members)


def test_probe_and_install_hint():
    reg = ExternalCLIRegistry()
    p = reg.probe("codex")
    assert "available" in p
    assert "install_hint" in p
    assert "codex" in reg.install_hint("codex").lower() or "PATH" in reg.install_hint("codex")


def test_multi_member_board_mixed_api_cli(tmp_path: Path, monkeypatch):
    """Configured API models + CLIs can sit on the same board."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    out = multi_cli_board(
        "Is rate limiting enough for this public API?",
        mode="review",
        members=["gpt-4o", "cli:gemini@flash"],
        dry_run=True,
        approve=True,
    )
    assert out.get("ok") is True
    assert "gpt-4o" in (out.get("members") or [])
    kinds = {o.get("kind") for o in (out.get("opinions") or [])}
    assert "api" in kinds
    assert "cli" in kinds


def test_pr_review_uses_cli_board(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    from core.pr_review import review_diff

    out = review_diff(
        "diff --git a/x b/x\n+print('hi')\n",
        use_mock=True,
        use_clis=True,
        dry_run=True,
    )
    assert out.get("ok") is True
    assert out.get("protocol") == "superai.pr_review.v2"
    assert "cli_board" in out
