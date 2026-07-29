"""
Shared spend + contract helpers (DoD-strict V4 sweep).

Use on every public spend path: agent, board, council, bakeoff, compare, HTTP.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

#: Flat estimate used when the model is unknown. Preserved so callers that
#: pass no model and no estimate behave exactly as they did before.
DEFAULT_ESTIMATE_USD = 0.1


def estimate_for_model(
    model: Optional[str],
    *,
    tokens: int = 500,
    registry: Any = None,
) -> Dict[str, Any]:
    """
    Pre-flight cost estimate for ``model``, priced from the registry when known.

    ``budget_precheck`` used a flat ``0.1 USD / 500 tokens`` regardless of
    model, so a ceiling check on a local CLI model and one on Opus saw the same
    number. Where the model is known the registry rate is used instead, and the
    result carries ``estimate_source`` so a caller can tell a registry-priced
    estimate from a heuristic one rather than inheriting false precision.
    """
    from .cost_accounting import from_usage

    if not model:
        return {
            "estimated_usd": DEFAULT_ESTIMATE_USD,
            "tokens": int(tokens),
            "model": None,
            "estimate_source": "fallback",
            "rate_per_1k": None,
        }

    priced = from_usage(
        str(model), total_tokens=int(tokens), registry=registry, cost_source="estimate"
    )
    return {
        "estimated_usd": float(priced.get("estimated_cost_usd") or 0.0),
        "tokens": int(tokens),
        "model": str(model),
        "estimate_source": priced.get("estimate_source", "fallback"),
        "rate_per_1k": priced.get("rate_per_1k"),
    }


def budget_precheck(
    *,
    estimated_usd: Optional[float] = None,
    tokens: int = 500,
    enforce: Optional[bool] = None,
    command_name: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return {ok:True} or blocked contract envelope.

    ``estimated_usd`` now defaults to None rather than a flat 0.1. When the
    caller names a ``model``, the estimate comes from registry rates; otherwise
    it falls back to the old constant, which is preserved so existing callers
    that pass nothing behave exactly as before.
    """
    estimate_source = "caller"
    if estimated_usd is None:
        derived = estimate_for_model(model, tokens=tokens)
        estimated_usd = derived["estimated_usd"]
        estimate_source = derived["estimate_source"]
    try:
        from .budget import BudgetGuard
        from .config import Config
        from .command_budget import check_command_budget_guard

        if command_name:
            c_guard = check_command_budget_guard(command_name, estimated_usd)
            if not c_guard.allowed:
                return {
                    "ok": False,
                    "error": c_guard.message,
                    "blocked": True,
                    "command_budget_exceeded": True,
                    "estimate_source": estimate_source,
                    "estimated_usd": float(estimated_usd),
                }

        if enforce is None:
            enforce = bool(Config().get("enforce_budget", True))
        return BudgetGuard().enforce_or_block(
            float(estimated_usd),
            tokens=int(tokens),
            enforce=bool(enforce),
        )
    except Exception as e:
        if enforce is not False:
            return {
                "ok": False,
                "error": f"Budget precheck internal failure: {e}",
                "error_code": "budget_internal",
                "blocked": True,
                "budget_error": str(e)[:200],
            }
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
    """Normalize any public API dict with result_contract + error taxonomy."""
    from .error_codes import apply_error_taxonomy
    from .result_contract import apply_contract

    if not isinstance(result, dict):
        result = {"payload": result, "ok": True}
    out = apply_contract(
        result,
        mock=mock,
        dry_run=dry_run,
        ok=ok,
        members=members,
    )
    return apply_error_taxonomy(out)
