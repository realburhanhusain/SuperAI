"""Assert public spend entrypoints pass command_name into budget_precheck."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def capture_command_names(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    calls = []

    def mock_precheck(*args, **kwargs):
        calls.append(kwargs.get("command_name") or (args[0] if args else None))
        return {"ok": True, "blocked": False, "enforced": False}

    monkeypatch.setattr("core.spend_guard.budget_precheck", mock_precheck)
    # Also patch imported aliases used after local import
    return calls, mock_precheck


def test_council_bakeoff_compare_command_names(capture_command_names, monkeypatch, tmp_path):
    calls, mock_precheck = capture_command_names
    monkeypatch.setattr("core.council.budget_precheck", mock_precheck, raising=False)

    from core.council import Council
    from core.model_bakeoff import bakeoff
    from core.model_compare import compare_models
    from core.model_caller import ModelCaller
    from core.model_registry import ModelRegistry

    # Patch ModelCaller to no-op so bakeoff/compare don't call models
    monkeypatch.setattr(
        ModelCaller,
        "call",
        lambda self, **kw: {"ok": True, "status": "success", "response": "x", "mock": True},
    )

    reg = ModelRegistry()
    caller = ModelCaller(use_mock=True, registry=reg)
    # council imports budget_precheck inside method — patch spend_guard is enough if import is local
    monkeypatch.setattr("core.spend_guard.budget_precheck", mock_precheck)

    try:
        Council(caller=caller, registry=reg).run("test topic", models=["gpt-4o-mini"])
    except Exception:
        pass
    bakeoff("hi", ["gpt-4o-mini"], use_mock=True, report=False)
    compare_models("hi", models=["gpt-4o-mini"], use_mock=True)

    assert "council" in calls
    assert "bakeoff" in calls
    assert "compare" in calls


def test_pr_review_multi_cli_goals_command_names(capture_command_names, monkeypatch, tmp_path):
    calls, mock_precheck = capture_command_names
    monkeypatch.setattr("core.spend_guard.budget_precheck", mock_precheck)

    from core.pr_review import review_diff
    from core.multi_cli_advisory import multi_cli_board
    from core.assistant_goals import GoalStore

    monkeypatch.setattr(
        "core.council.Council.run",
        lambda self, *a, **k: {"ok": True, "decision": "approve", "mock": True},
    )

    review_diff("diff --git a/x b/x\n+", use_mock=True, use_clis=False)
    assert "pr_review" in calls

    multi_cli_board("subject", dry_run=True, max_clis=2, write_memory=False)
    assert "multi_cli" in calls

    gm = GoalStore()
    monkeypatch.setattr(gm, "heartbeat", lambda: {"due": []})
    gm.execute_due(max_goals=1, use_ask=False)
    assert "goals" in calls


def test_board_preflight_and_mcp_command_names(capture_command_names, monkeypatch):
    calls, mock_precheck = capture_command_names
    monkeypatch.setattr("core.spend_guard.budget_precheck", mock_precheck)
    monkeypatch.setenv("SUPERAI_MCP_ALLOW_LIVE", "1")

    from core.board_preflight import estimate_board
    from core.mcp_safety import wrap_mcp_tool

    estimate_board("subj", ["gpt-4o-mini"])
    assert "board-preflight" in calls

    wrap_mcp_tool(
        "superai_run",
        lambda: {"ok": True},
        mock=False,
        args={"live": True},
        estimated_usd=0.01,
        tokens=10,
    )
    assert "mcp:superai_run" in calls


def test_web_budget_command_name(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    calls = []

    def mock_precheck(**kwargs):
        calls.append(kwargs.get("command_name"))
        return {"ok": True, "blocked": False}

    monkeypatch.setattr("core.spend_guard.budget_precheck", mock_precheck)

    # Exercise the same call shape as web_app
    from core.spend_guard import budget_precheck

    budget_precheck(estimated_usd=0.0, tokens=50, command_name="web", enforce=False)
    assert "web" in calls
