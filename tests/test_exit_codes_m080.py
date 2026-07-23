"""
Unit tests for Trustworthy Process Exit Codes (M080).
"""

from __future__ import annotations

import pytest
from core.exit_codes import (
    OK,
    GENERAL,
    USAGE,
    BUDGET,
    PERMISSION,
    READINESS,
    TIMEOUT,
    PROVIDER,
    CANCELLED,
    JAIL,
    INTERNAL,
    from_exception,
    from_result,
    get_exit_code_description,
    list_exit_codes,
)


def test_exit_code_constants():
    assert OK == 0
    assert GENERAL == 1
    assert USAGE == 2
    assert BUDGET == 3
    assert PERMISSION == 4
    assert READINESS == 5
    assert TIMEOUT == 6
    assert PROVIDER == 7
    assert CANCELLED == 8
    assert JAIL == 9
    assert INTERNAL == 99


def test_get_exit_code_description():
    desc = get_exit_code_description(OK)
    assert "Success" in desc
    desc_budget = get_exit_code_description(BUDGET)
    assert "budget" in desc_budget.lower()
    desc_unknown = get_exit_code_description(999)
    assert "Unknown" in desc_unknown


def test_list_exit_codes():
    codes = list_exit_codes()
    assert isinstance(codes, dict)
    assert OK in codes
    assert BUDGET in codes
    assert JAIL in codes


def test_from_result_mappings():
    assert from_result({"ok": True, "status": "success"}) == OK
    assert from_result({"ok": True, "status": "partial"}) == TIMEOUT
    assert from_result({"ok": False, "error_code": "budget"}) == BUDGET
    assert from_result({"ok": False, "error_code": "permission"}) == PERMISSION
    assert from_result({"ok": False, "error_code": "readiness"}) == READINESS
    assert from_result({"ok": False, "error_code": "timeout"}) == TIMEOUT
    assert from_result({"ok": False, "error_code": "provider"}) == PROVIDER
    assert from_result({"ok": False, "error_code": "cancelled"}) == CANCELLED
    assert from_result({"ok": False, "error_code": "jail"}) == JAIL
    assert from_result({"ok": False, "error_code": "validation"}) == USAGE
    assert from_result({"ok": False, "error_code": "unknown_code"}) == GENERAL
    assert from_result(None) == GENERAL


def test_from_exception_mappings():
    assert from_exception(None) == OK
    assert from_exception(ValueError("Invalid usage param")) == USAGE
    assert from_exception(RuntimeError("Spend budget ceiling hit")) == BUDGET
    assert from_exception(PermissionError("Permission denied by policy")) == PERMISSION
    assert from_exception(TimeoutError("Execution timed out")) == TIMEOUT
    assert from_exception(KeyboardInterrupt()) == CANCELLED
    assert from_exception(Exception("Workspace jail path blocked")) == JAIL
    assert from_exception(Exception("Provider readiness check failed")) == READINESS

    class CustomExc(Exception):
        exit_code = 42

    assert from_exception(CustomExc()) == 42
