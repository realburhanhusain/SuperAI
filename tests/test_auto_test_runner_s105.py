"""
Unit tests for Auto Test Discovery & Impacted Test Runner (S105).
"""

from __future__ import annotations

from pathlib import Path
import pytest
from core.auto_test_runner import find_impacted_tests, run_impacted_tests


def test_find_impacted_tests_empty():
    assert find_impacted_tests([]) == []


def test_find_impacted_tests_direct_test_file():
    mod_files = ["tests/test_exit_codes_m080.py"]
    res = find_impacted_tests(mod_files)
    assert len(res) == 1
    assert "test_exit_codes_m080.py" in res[0]


def test_find_impacted_tests_source_file():
    mod_files = ["src/core/exit_codes.py"]
    res = find_impacted_tests(mod_files)
    assert len(res) >= 1
    assert any("test_exit_codes" in r for r in res)


def test_run_impacted_tests_execution():
    res = run_impacted_tests(["src/core/exit_codes.py"])
    assert res["ok"] is True
    assert res["count"] >= 1
    assert res["status"] == "success"
