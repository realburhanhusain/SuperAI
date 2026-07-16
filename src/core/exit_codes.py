"""Trustworthy process exit codes (V6 M080)."""

from __future__ import annotations

from typing import Any, Dict

OK = 0
GENERAL = 1
USAGE = 2
BUDGET = 3
PERMISSION = 4
READINESS = 5
TIMEOUT = 6
PROVIDER = 7
CANCELLED = 8


def from_result(result: Dict[str, Any]) -> int:
    if not isinstance(result, dict):
        return GENERAL
    if result.get("ok") is True and result.get("status") in {
        None,
        "success",
        "partial",
    }:
        if result.get("status") == "partial":
            return TIMEOUT
        return OK
    code = str(result.get("error_code") or "").lower()
    return {
        "budget": BUDGET,
        "permission": PERMISSION,
        "readiness": READINESS,
        "timeout": TIMEOUT,
        "provider": PROVIDER,
        "cancelled": CANCELLED,
        "validation": USAGE,
    }.get(code, GENERAL)
