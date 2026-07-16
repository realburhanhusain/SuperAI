"""
Pre-flight cost estimate before multi-member boards (V6 M003).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence


def estimate_board(
    subject: str,
    members: Sequence[str],
    *,
    registry: Any = None,
    tokens_per_member: int = 400,
) -> Dict[str, Any]:
    from .cost_accounting import from_usage
    from .spend_guard import budget_precheck

    members = [str(m) for m in members if str(m).strip()]
    per: List[Dict[str, Any]] = []
    total_usd = 0.0
    total_tok = 0
    # subject tokens once + per member response estimate
    subj_tok = max(50, len(subject or "") // 4)
    for m in members:
        est = from_usage(m, total_tokens=subj_tok + int(tokens_per_member), registry=registry)
        per.append(est)
        total_usd += float(est.get("estimated_cost_usd") or 0)
        total_tok += int(est.get("tokens") or 0)

    block = budget_precheck(estimated_usd=total_usd, tokens=total_tok)
    return {
        "ok": not block.get("blocked"),
        "blocked": bool(block.get("blocked")),
        "member_count": len(members),
        "members": list(members),
        "estimated_cost_usd": round(total_usd, 6),
        "estimated_tokens": total_tok,
        "per_member": per,
        "budget": block,
        "subject_preview": (subject or "")[:200],
        "preflight": True,
    }


def enforce_or_allow(
    subject: str,
    members: Sequence[str],
    *,
    registry: Any = None,
    force: bool = False,
) -> Dict[str, Any]:
    """Return estimate; if budget blocked and not force, mark blocked."""
    est = estimate_board(subject, members, registry=registry)
    if est.get("blocked") and not force:
        est["ok"] = False
        est["error"] = (est.get("budget") or {}).get("error") or "budget_preflight_blocked"
        est["error_code"] = "budget"
    return est
