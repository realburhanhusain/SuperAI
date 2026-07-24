"""CLI middleware / thin-wrapper spend gates (V5-M1 adjacency)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_thin_wrappers_call_budget_precheck(tmp_path: Path, monkeypatch):
    """pr_review, multi_cli board, goals execute_due must hit budget_precheck."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    seen = []

    def mock_precheck(**kwargs):
        seen.append(kwargs.get("command_name"))
        return {"ok": True, "blocked": False}

    monkeypatch.setattr("core.spend_guard.budget_precheck", mock_precheck)

    from core.pr_review import review_diff
    from core.multi_cli_advisory import multi_cli_board
    from core.assistant_goals import GoalStore

    monkeypatch.setattr(
        "core.council.Council.run",
        lambda self, *a, **k: {"ok": True, "decision": "approve", "mock": True},
    )

    review_diff("+a\n", use_mock=True, use_clis=False)
    multi_cli_board("advise me", dry_run=True, max_clis=1, write_memory=False)
    gm = GoalStore()
    monkeypatch.setattr(gm, "heartbeat", lambda: {"due": []})
    gm.execute_due(max_goals=1, use_ask=False)

    assert "pr_review" in seen
    assert "multi_cli" in seen
    assert "goals" in seen


def test_budget_gate_forwards_command_name(monkeypatch):
    seen = []

    def mock_precheck(**kwargs):
        seen.append(kwargs.get("command_name"))
        return {"ok": True, "blocked": False}

    monkeypatch.setattr("core.spend_guard.budget_precheck", mock_precheck)
    monkeypatch.setattr("core.public_surface.dry_run", lambda: False)

    class Cfg:
        use_mock = False

    monkeypatch.setattr("core.config.Config", lambda: Cfg())

    from core.public_surface import budget_gate

    budget_gate(estimated_usd=0.05, command_name="pr_review")
    assert seen == ["pr_review"]
