"""
Standard error codes for SuperAI public results (V5 M5).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# Canonical codes
BUDGET = "budget"
READINESS = "readiness"
PERMISSION = "permission"
TIMEOUT = "timeout"
TOOL = "tool"
PROVIDER = "provider"
CANCELLED = "cancelled"
VALIDATION = "validation"
UNKNOWN = "unknown"

VALID = {
    BUDGET,
    READINESS,
    PERMISSION,
    TIMEOUT,
    TOOL,
    PROVIDER,
    CANCELLED,
    VALIDATION,
    UNKNOWN,
}


def set_error_code(result: Dict[str, Any], code: str, *, message: Optional[str] = None) -> Dict[str, Any]:
    c = (code or UNKNOWN).strip().lower()
    if c not in VALID:
        c = UNKNOWN
    result["error_code"] = c
    if message:
        result.setdefault("error", message)
    if result.get("ok") is None:
        result["ok"] = False
    if not result.get("status") or result.get("status") == "success":
        result["status"] = "error" if c != TIMEOUT else "partial"
        if c == TIMEOUT:
            result["status"] = "partial"
        if c == CANCELLED:
            result["status"] = "cancelled"
    return result


def infer_error_code(result: Dict[str, Any]) -> str:
    if result.get("error_code") in VALID:
        return str(result["error_code"])
    err = str(result.get("error") or result.get("response") or "").lower()
    if result.get("blocked") or "budget" in err:
        return BUDGET
    if "readiness" in err or "not_ready" in err or "model_not_ready" in err:
        return READINESS
    if "permission" in err or "denied" in err or "plan mode" in err:
        return PERMISSION
    if "timeout" in err or result.get("status") == "partial":
        return TIMEOUT
    if "tool" in err or result.get("tool_error"):
        return TOOL
    if "provider" in err or result.get("status") == "error":
        return PROVIDER if "provider" in err or "api" in err else UNKNOWN
    if result.get("status") == "cancelled":
        return CANCELLED
    return UNKNOWN


def apply_error_taxonomy(result: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return result
    if result.get("ok") is False or result.get("status") in {
        "error",
        "failed",
        "partial",
        "cancelled",
    }:
        if "error_code" not in result:
            set_error_code(result, infer_error_code(result))
    return result
