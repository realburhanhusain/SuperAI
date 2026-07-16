"""
Cost-aware routing helpers (Sprint B M3).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence


def estimate_board_cost(members: Sequence[str], subject: str = "") -> float:
    """Rough USD estimate before running a multi-member board."""
    try:
        from .model_registry import ModelRegistry

        reg = ModelRegistry()
    except Exception:
        reg = None
    tokens = max(200, len(subject or "") // 3)
    total = 0.0
    for m in members:
        rate = 0.002
        if reg:
            info = reg.get_model(str(m).split("@")[0] if not str(m).startswith("cli:") else m)
            # cli cheap
            if str(m).startswith("cli:") or (info and info.provider == "external_cli"):
                rate = 0.0
            elif info:
                rate = float(info.cost_per_1k_tokens or 0.002)
        total += (tokens / 1000.0) * rate
    return round(total, 6)


def should_skip_or_shrink(
    members: Sequence[str],
    subject: str,
    *,
    run_usd_limit: float = 1.0,
    prefer_cheap: bool = False,
) -> Dict[str, Any]:
    """
    If estimate exceeds run budget, shrink board or recommend cache-only.
    """
    mems = list(members)
    est = estimate_board_cost(mems, subject)
    if est <= run_usd_limit:
        return {
            "ok": True,
            "members": mems,
            "estimated_cost_usd": est,
            "action": "proceed",
        }
    # shrink to 1 cheapest
    if prefer_cheap or est > run_usd_limit:
        # prefer local/cli/open-weight names
        ranked = sorted(
            mems,
            key=lambda m: (
                0
                if str(m).startswith("cli:") or "ollama" in str(m) or "local" in str(m)
                else 1,
                str(m),
            ),
        )
        small = ranked[:1] if ranked else mems[:1]
        est2 = estimate_board_cost(small, subject)
        return {
            "ok": True,
            "members": small,
            "estimated_cost_usd": est2,
            "original_estimate": est,
            "action": "shrunk",
            "reason": "budget",
        }
    return {
        "ok": False,
        "members": mems,
        "estimated_cost_usd": est,
        "action": "block",
        "reason": "over_budget",
    }
