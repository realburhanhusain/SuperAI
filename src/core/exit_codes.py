"""
Trustworthy Process Exit Codes (V6 M080).

Standardized exit codes for SuperAI CLI, background daemons, and subprocesses.
"""

from __future__ import annotations

import sys
from typing import Any, Dict, Optional, Union

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


# (code, constant_name, description) for CLI `exit-codes`
_EXIT_NAME_BY_CODE = {
    OK: "OK",
    GENERAL: "GENERAL",
    USAGE: "USAGE",
    BUDGET: "BUDGET",
    PERMISSION: "PERMISSION",
    READINESS: "READINESS",
    TIMEOUT: "TIMEOUT",
    PROVIDER: "PROVIDER",
    CANCELLED: "CANCELLED",
    JAIL: "JAIL",
    INTERNAL: "INTERNAL",
}
EXIT_CODES_TABLE = [
    (code, _EXIT_NAME_BY_CODE.get(code, f"CODE_{code}"), desc)
    for code, desc in sorted(EXIT_CODE_DESCRIPTIONS.items())
]


def from_exception(exc: Exception) -> int:
    """Map Exception instance to standardized SuperAI exit code integer."""
    if exc is None:
        return OK
    if hasattr(exc, "exit_code") and isinstance(getattr(exc, "exit_code"), int):
        return int(getattr(exc, "exit_code"))
    if isinstance(exc, FileNotFoundError):
        return USAGE
    if isinstance(exc, PermissionError):
        return PERMISSION
    if isinstance(exc, TimeoutError):
        return TIMEOUT
    if isinstance(exc, KeyboardInterrupt):
        return CANCELLED
    if isinstance(exc, ValueError):
        return USAGE

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

    # Prefer explicit integer exit_code on payloads
    if isinstance(result.get("exit_code"), int):
        return int(result["exit_code"])

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
        "not_found": USAGE,
        "io": GENERAL,
        "db": INTERNAL,
    }.get(code, GENERAL)


def raise_typer_exit(exc_or_result: Any = None, *, code: Optional[int] = None) -> None:  # noqa: ANN401
    """
    Raise typer.Exit with mapped SuperAI exit code (M080 product boundary).

    Usage:
      raise_typer_exit(exc)
      raise_typer_exit({"ok": False, "error_code": "budget"})
      raise_typer_exit(code=BUDGET)
    """
    import typer

    if code is not None:
        raise typer.Exit(int(code))
    if isinstance(exc_or_result, BaseException):
        raise typer.Exit(from_exception(exc_or_result))
    if isinstance(exc_or_result, dict):
        raise typer.Exit(from_result(exc_or_result))
    raise typer.Exit(GENERAL)
