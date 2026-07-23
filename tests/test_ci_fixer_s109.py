"""
Unit tests for Fix CI Failure from Log Paste (S109).
"""

from __future__ import annotations

import tempfile
import pytest

from core.ci_fixer import analyze_ci_log_file, analyze_ci_log_paste


def test_analyze_clean_ci_log():
    log_text = "================ 10 passed in 1.2s ================"
    res = analyze_ci_log_paste(log_text)
    assert res.has_failures is False
    assert res.total_failures == 0


def test_analyze_failed_test_ci_log():
    log_text = "FAILED tests/test_exit_codes.py::test_from_result - AssertionError: assert False"
    res = analyze_ci_log_paste(log_text)
    assert res.has_failures is True
    assert res.total_failures == 1
    assert res.findings[0].failure_type == "TEST_FAILURE"
    assert "test_exit_codes.py" in res.findings[0].failing_file


def test_analyze_module_not_found_ci_log():
    log_text = "ModuleNotFoundError: No module named 'pytest_mock'"
    res = analyze_ci_log_paste(log_text)
    assert res.has_failures is True
    assert any(f.failure_type == "IMPORT_ERROR" for f in res.findings)
    assert "pytest_mock" in res.findings[0].suggested_patch
