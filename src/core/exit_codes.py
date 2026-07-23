"""
Trustworthy Process Exit Codes (V6 M080).

Standardized exit codes for SuperAI CLI, background daemons, and subprocesses.
"""

from __future__ import annotations

import sys
from typing import Any, Dict, Optional

# Standard Exit Codes
OK = 0
GENERAL = 1
USAGE = 2
BUDGET = 3
PERMISSION = 4
READINESS = 5
TIMEOUT = 6
PROVIDER = 7
CANCELLED = 8
JAIL = 9
INTERNAL = 99

EXIT_CODE_DESCRIPTIONS: Dict[int, str] = {
    OK: "Success (clean execution)",
    GENERAL: "General execution failure or unmapped error",
    USAGE: "Invalid CLI usage, bad options, or schema validation error",
    BUDGET: "Spend budget ceiling exceeded",
    PERMISSION: "Permission model block (ask/plan required)",
    READINESS: "Provider API key missing or provider check failed",
    TIMEOUT: "Subprocess or network execution timed out",
    PROVIDER: "LLM Provider API error (5xx / network fail)",
    CANCELLED: "Operation cancelled by user or token",
    JAIL: "Workspace jail sandbox path violation",
    INTERNAL: "Internal error or unexpected crash",
}


def get_exit_code_description(code: int) -> str:
    """Return human-readable description for an exit code integer."""
    return EXIT_CODE_DESCRIPTIONS.get(code, f"Unknown exit code ({code})")


def list_exit_codes() -> Dict[int, str]:
    """Return dictionary of all registered exit codes and their descriptions."""
    return dict(EXIT_CODE_DESCRIPTIONS)


def from_result(result: Dict[str, Any]) -> int:
    """Map result payload dictionary to exit code."""
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

    code = str(result.get("error_code") or result.get("code") or "").lower()
    return {
        "budget": BUDGET,
        "permission": PERMISSION,
        "readiness": READINESS,
        "timeout": TIMEOUT,
        "provider": PROVIDER,
        "cancelled": CANCELLED,
        "jail": JAIL,
        "validation": USAGE,
        "usage": USAGE,
    }.get(code, GENERAL)


def from_exception(exc: Exception) -> int:
    """Map python exception type or message to exit code integer."""
    if exc is None:
        return OK
    
    # Check if exception has explicit exit_code attribute
    if hasattr(exc, "exit_code") and isinstance(exc.exit_code, int):
        return exc.exit_code

    msg = str(exc).lower()
    exc_type = type(exc).__name__.lower()

    if "budget" in msg or "budget" in exc_type:
        return BUDGET
    if "jail" in msg or "workspace" in msg:
        return JAIL
    if "permission" in msg or "denied" in msg:
        return PERMISSION
    if "readiness" in msg or "api key" in msg:
        return READINESS
    if "timeout" in msg or "timed out" in msg:
        return TIMEOUT
    if "provider" in msg or "rate limit" in msg:
        return PROVIDER
    if "cancel" in msg or "keyboardinterrupt" in exc_type:
        return CANCELLED
    if "usage" in msg or "invalid" in msg or "valueerror" in exc_type:
        return USAGE

    return GENERAL
