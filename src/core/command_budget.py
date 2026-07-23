"""
Per-Command Budget Overrides (V6 S132).

Provides fine-grained spend budget limits per CLI command / tool execution path.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

COMMAND_BUDGETS_FILE = Path.home() / ".superai" / "command_budgets.json"
_DEFAULT_COMMAND_BUDGETS: Dict[str, float] = {}


@dataclass
class CommandBudgetGuardResult:
    allowed: bool
    command_name: str
    effective_limit_usd: float
    current_spend_usd: float
    message: str


def set_command_budget(command_name: str, max_usd: float) -> Dict[str, Any]:
    """Set a specific spend budget limit in USD for a given CLI command or tool path."""
    if not command_name or not isinstance(command_name, str):
        return {"ok": False, "error": "Invalid command name"}

    budgets = _load_command_budgets()
    budgets[command_name.strip().lower()] = float(max(0.0, max_usd))
    _save_command_budgets(budgets)

    return {
        "ok": True,
        "command": command_name,
        "max_usd": float(max_usd),
        "status": "updated",
    }


def get_command_budget(command_name: str) -> Optional[float]:
    """Retrieve explicit spend budget limit for command, or None if unconstrained."""
    budgets = _load_command_budgets()
    return budgets.get(command_name.strip().lower())


def check_command_budget_guard(
    command_name: str, current_spend_usd: float
) -> CommandBudgetGuardResult:
    """Check if current spend exceeds command-specific budget limit."""
    limit = get_command_budget(command_name)
    if limit is None:
        return CommandBudgetGuardResult(
            allowed=True,
            command_name=command_name,
            effective_limit_usd=0.0,
            current_spend_usd=current_spend_usd,
            message="No per-command budget restriction.",
        )

    allowed = current_spend_usd <= limit
    msg = (
        f"Spend (${current_spend_usd:.4f}) within limit (${limit:.4f})"
        if allowed
        else f"Per-command budget exceeded for '{command_name}': ${current_spend_usd:.4f} > ${limit:.4f}"
    )

    return CommandBudgetGuardResult(
        allowed=allowed,
        command_name=command_name,
        effective_limit_usd=limit,
        current_spend_usd=current_spend_usd,
        message=msg,
    )


def _load_command_budgets() -> Dict[str, float]:
    """Internal helper to load command budget configuration."""
    if not COMMAND_BUDGETS_FILE.exists():
        return dict(_DEFAULT_COMMAND_BUDGETS)
    try:
        data = json.loads(COMMAND_BUDGETS_FILE.read_text(encoding="utf-8"))
        return {k: float(v) for k, v in data.items()}
    except Exception:
        return dict(_DEFAULT_COMMAND_BUDGETS)


def _save_command_budgets(budgets: Dict[str, float]) -> None:
    """Internal helper to save command budget configuration."""
    try:
        COMMAND_BUDGETS_FILE.parent.mkdir(parents=True, exist_ok=True)
        COMMAND_BUDGETS_FILE.write_text(json.dumps(budgets, indent=2), encoding="utf-8")
    except Exception:
        pass
