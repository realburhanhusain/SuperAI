"""
Public API wrapper (V5 M1) — budget precheck + contract + error taxonomy.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional


def wrap_public_result(
    result: Any,
    *,
    mock: Optional[bool] = None,
    dry_run: Optional[bool] = None,
    ok: Optional[bool] = None,
    members: Optional[list] = None,
    estimated_usd: float = 0.0,
    tokens: int = 0,
    record_spend: bool = True,
) -> Dict[str, Any]:
    from .error_codes import apply_error_taxonomy
    from .spend_guard import budget_record, ensure_public_result

    data = ensure_public_result(
        result, mock=mock, dry_run=dry_run, ok=ok, members=members
    )
    apply_error_taxonomy(data)
    if record_spend and data.get("ok") and not data.get("blocked"):
        usd = float(data.get("estimated_cost_usd") or estimated_usd or 0)
        tok = int(data.get("tokens") or tokens or 0)
        if usd or tok:
            budget_record(usd=usd, tokens=tok)
    return data


def guarded_call(
    fn: Callable[[], Dict[str, Any]],
    *,
    estimated_usd: float = 0.1,
    tokens: int = 500,
    mock: bool = False,
) -> Dict[str, Any]:
    """Precheck budget, run fn, wrap result."""
    from .error_codes import set_error_code
    from .spend_guard import budget_precheck

    block = budget_precheck(estimated_usd=estimated_usd, tokens=tokens)
    if block.get("blocked"):
        set_error_code(block, "budget", message=str(block.get("error") or "budget"))
        return block
    try:
        out = fn()
    except Exception as e:
        from .spend_guard import ensure_public_result

        err = ensure_public_result(
            {"ok": False, "error": str(e)[:500]}, mock=mock, ok=False
        )
        set_error_code(err, "unknown", message=str(e)[:300])
        return err
    return wrap_public_result(out, mock=mock)
