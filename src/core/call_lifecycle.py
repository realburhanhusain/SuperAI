"""
Universal model-call lifecycle (foundation lift → full).

Hooks used by ModelCaller on every spend path:
- cancel check
- budget precheck
- cost accounting attach + record
- bandit outcome update
- preferences observe
- run history append
- secret-safe logging
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional


def pre_call(
    model: str,
    prompt: str = "",
    *,
    registry: Any = None,
    skip_budget: bool = False,
    estimated_usd: Optional[float] = None,
    estimated_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Return {} if ok to proceed, or a blocked contract dict.
    """
    # Cooperative cancel
    try:
        from .cancel_token import current

        tok = current()
        if tok is not None and tok.is_cancelled:
            from .spend_guard import ensure_public_result

            return ensure_public_result(
                {
                    "ok": False,
                    "status": "cancelled",
                    "error": "cancelled",
                    "error_code": "cancelled",
                    "response": "cancelled",
                    "blocked": True,
                },
                ok=False,
            )
    except Exception:
        pass

    if skip_budget:
        return {}

    try:
        from .cost_accounting import estimate_call
        from .spend_guard import budget_precheck

        est = estimate_call(model, prompt, registry=registry)
        usd = float(estimated_usd if estimated_usd is not None else est.get("estimated_cost_usd") or 0.05)
        toks = int(estimated_tokens if estimated_tokens is not None else est.get("tokens") or 200)
        block = budget_precheck(estimated_usd=usd, tokens=toks)
        if block.get("blocked") or block.get("ok") is False:
            block.setdefault("status", "error")
            block.setdefault("error_code", "budget")
            block.setdefault("response", block.get("error") or "budget")
            block["blocked"] = True
            block["ok"] = False
            return block
        return {"_preflight": {"estimated_usd": usd, "tokens": toks}}
    except Exception as e:
        return {"_preflight": {"budget_error": str(e)[:200]}}


def post_call(
    result: Dict[str, Any],
    *,
    model: str,
    prompt: str = "",
    registry: Any = None,
    started: Optional[float] = None,
    record_spend: bool = True,
    update_bandit: bool = True,
) -> Dict[str, Any]:
    """Attach cost fields, record spend, bandit, preferences, history."""
    if not isinstance(result, dict):
        result = {"response": result, "ok": True, "status": "success"}

    latency = (time.time() - started) if started else float(result.get("latency") or 0)
    result.setdefault("latency", round(latency, 4))

    # Cost from usage or estimate
    try:
        from .cost_accounting import estimate_call, from_usage

        usage = result.get("usage") if isinstance(result.get("usage"), dict) else {}
        total = int(
            usage.get("total_tokens")
            or result.get("tokens")
            or 0
        )
        if total <= 0:
            est = estimate_call(model, prompt, registry=registry)
            total = int(est.get("tokens") or 0)
            # Prefer real usage when present; else estimate from prompt + response
            resp_len = len(str(result.get("response") or ""))
            total = max(total, len(prompt or "") // 4 + resp_len // 4 + 20)
        cost = from_usage(
            model,
            total_tokens=total,
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
            registry=registry,
        )
        result["tokens"] = int(cost.get("tokens") or total)
        result["estimated_cost_usd"] = float(cost.get("estimated_cost_usd") or 0)
        result["rate_per_1k"] = cost.get("rate_per_1k")
        result.setdefault("model", model)
    except Exception:
        result.setdefault("tokens", int(result.get("tokens") or 0))
        result.setdefault("estimated_cost_usd", float(result.get("estimated_cost_usd") or 0))

    success = (
        result.get("ok") is not False
        and str(result.get("status") or "") not in {"error", "failed", "cancelled"}
        and not result.get("blocked")
    )
    result.setdefault("ok", success)
    if success and "status" not in result:
        result["status"] = "success"

    if record_spend and success and not result.get("mock"):
        try:
            from .spend_guard import budget_record

            budget_record(
                usd=float(result.get("estimated_cost_usd") or 0),
                tokens=int(result.get("tokens") or 0),
            )
        except Exception:
            pass

    if update_bandit:
        try:
            from .bandit_router import EpsilonGreedyBandit

            b = EpsilonGreedyBandit()
            reward = EpsilonGreedyBandit.reward_from_outcome(
                success=success,
                latency=latency,
                cost=float(result.get("estimated_cost_usd") or 0),
            )
            b.update(str(result.get("model") or model), reward)
            result["bandit_reward"] = reward
        except Exception:
            pass

    try:
        from .preferences import UserPreferenceModel

        UserPreferenceModel().observe_task(
            task_type=str(result.get("task_type") or "model_call"),
            model=str(result.get("model") or model),
            success=success,
            duration=latency,
        )
    except Exception:
        pass

    try:
        from .history import TaskHistory

        TaskHistory().save(
            {
                "task_id": result.get("run_id")
                or TaskHistory.new_task_id(),
                "kind": "model_call",
                "model": str(result.get("model") or model),
                "task": (prompt or "")[:500],
                "success": success,
                "tokens": int(result.get("tokens") or 0),
                "estimated_cost_usd": float(result.get("estimated_cost_usd") or 0),
                "latency": latency,
                "status": result.get("status"),
            }
        )
    except Exception:
        pass

    # Contract + error taxonomy
    try:
        from .spend_guard import ensure_public_result

        result = ensure_public_result(
            result,
            mock=result.get("mock"),
            dry_run=result.get("dry_run"),
            ok=result.get("ok"),
            members=result.get("members"),
        )
    except Exception:
        pass

    return result


def check_cancel() -> Optional[Dict[str, Any]]:
    try:
        from .cancel_token import current

        tok = current()
        if tok is not None and tok.is_cancelled:
            from .spend_guard import ensure_public_result

            return ensure_public_result(
                {
                    "ok": False,
                    "status": "cancelled",
                    "error": "cancelled",
                    "error_code": "cancelled",
                    "blocked": True,
                },
                ok=False,
            )
    except Exception:
        pass
    return None
