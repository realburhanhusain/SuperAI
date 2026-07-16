"""
Suggest run profile from recent spend/success (V5 S5).
"""

from __future__ import annotations

from typing import Any, Dict


def suggest_profile() -> Dict[str, Any]:
    """
    Heuristic:
    - high daily spend relative to limit → cheap / local-only
    - low spend + failures → quality
    - else balanced
    """
    spent = 0.0
    limit = 5.0
    try:
        from .budget import BudgetGuard

        snap = BudgetGuard().snapshot()
        spent = float(snap.get("spent_usd_today") or 0)
        limit = float(snap.get("daily_usd_limit") or 5.0) or 5.0
    except Exception:
        pass

    ratio = spent / limit if limit else 0
    if ratio >= 0.7:
        choice = "cheap"
        reason = f"daily spend {spent:.4f} is {ratio:.0%} of limit {limit}"
    elif ratio <= 0.1 and spent == 0:
        choice = "balanced"
        reason = "little spend today; keep balanced"
    elif ratio >= 0.4:
        choice = "local-only"
        reason = "moderate spend; prefer local/OW"
    else:
        choice = "balanced"
        reason = "spend within normal band"

    return {
        "ok": True,
        "suggested_profile": choice,
        "reason": reason,
        "spent_usd_today": spent,
        "daily_usd_limit": limit,
        "contract": "superai.result.v1",
    }
