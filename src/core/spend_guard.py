"""
Shared spend + contract helpers (DoD-strict V4 sweep).

Use on every public spend path: agent, board, council, bakeoff, compare, HTTP.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def budget_precheck(
    *,
    estimated_usd: float = 0.1,
    tokens: int = 500,
    enforce: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Return {ok:True} or blocked contract envelope.
    """
    try:
        from .budget import BudgetGuard
        from .config import Config

        if enforce is None:
            enforce = bool(Config().get("enforce_budget", True))
        return BudgetGuard().enforce_or_block(
            float(estimated_usd),
            tokens=int(tokens),
            enforce=bool(enforce),
        )
    except Exception as e:
        return {"ok": True, "budget_error": str(e)[:200], "blocked": False}


def budget_record(usd: float = 0.0, tokens: int = 0) -> None:
    try:
        from .budget import BudgetGuard

        BudgetGuard().record(usd=float(usd or 0), tokens=int(tokens or 0))
    except Exception:
        pass


def ensure_public_result(
    result: Any,
    *,
    mock: Optional[bool] = None,
    dry_run: Optional[bool] = None,
    ok: Optional[bool] = None,
    members: Optional[list] = None,
) -> Dict[str, Any]:
    """Normalize any public API dict with result_contract."""
    from .result_contract import apply_contract

    if not isinstance(result, dict):
        result = {"payload": result, "ok": True}
    return apply_contract(
        result,
        mock=mock,
        dry_run=dry_run,
        ok=ok,
        members=members,
    )
