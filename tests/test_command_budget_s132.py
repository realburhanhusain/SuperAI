"""
Unit tests for Per-Command Budget Overrides (S132).
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

import core.command_budget as cb
from core.command_budget import (
    check_command_budget_guard,
    get_command_budget,
    set_command_budget,
)


@pytest.fixture(autouse=True)
def temp_budgets_file(tmp_path, monkeypatch):
    test_file = tmp_path / "command_budgets.json"
    monkeypatch.setattr(cb, "COMMAND_BUDGETS_FILE", test_file)
    return test_file


def test_set_and_get_command_budget():
    res = set_command_budget("council", 0.50)
    assert res["ok"] is True
    assert get_command_budget("council") == 0.50


def test_command_budget_guard_allowed():
    set_command_budget("run", 1.00)
    guard = check_command_budget_guard("run", current_spend_usd=0.45)
    assert guard.allowed is True
    assert guard.effective_limit_usd == 1.00


def test_command_budget_guard_exceeded():
    set_command_budget("bakeoff", 0.20)
    guard = check_command_budget_guard("bakeoff", current_spend_usd=0.35)
    assert guard.allowed is False
    assert "exceeded" in guard.message
