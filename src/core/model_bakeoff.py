"""
Lightweight model bake-off / eval (Phase 8 N6).
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Sequence  # noqa: F401


def bakeoff(
    prompt: str,
    models: Sequence[str],
    *,
    use_mock: bool = True,
) -> Dict[str, Any]:
    """Run same prompt on multiple models; rank by success then latency."""
    from .model_caller import ModelCaller
    from .model_registry import ModelRegistry

    reg = ModelRegistry()
    caller = ModelCaller(use_mock=use_mock, registry=reg)
    rows: List[Dict[str, Any]] = []
    for m in models:
        t0 = time.time()
        try:
            out = caller.call(model=m, prompt=prompt)
            latency = time.time() - t0
            ok = str(out.get("status") or "") != "error"
            rows.append(
                {
                    "model": m,
                    "ok": ok,
                    "latency_sec": round(latency, 3),
                    "mock": bool(out.get("mock")),
                    "tokens": int((out.get("usage") or {}).get("total_tokens") or out.get("tokens") or 0),
                    "cost": float(out.get("estimated_cost_usd") or 0),
                    "preview": str(out.get("response") or out.get("error") or "")[:240],
                }
            )
        except Exception as e:
            rows.append(
                {
                    "model": m,
                    "ok": False,
                    "latency_sec": round(time.time() - t0, 3),
                    "error": str(e)[:200],
                }
            )
    rows.sort(key=lambda r: (not r.get("ok"), r.get("latency_sec") or 999))
    winner = rows[0]["model"] if rows else None
    out = {
        "ok": True,
        "status": "success",
        "prompt": prompt[:500],
        "results": rows,
        "winner": winner,
        "mock": use_mock,
        "dry_run": False,
        "model_chain": [r.get("model") for r in rows if r.get("model")],
        "tokens": sum(int(r.get("tokens") or 0) for r in rows),
        "estimated_cost_usd": round(sum(float(r.get("cost") or 0) for r in rows), 6),
        "members": [r.get("model") for r in rows if r.get("model")],
        "memory_ids": [],
        "contract": "superai.result.v1",
    }
    return out


def pin_winner(model: Optional[str], *, persist: bool = True) -> Dict[str, Any]:
    """Persist bakeoff winner as preferred default model + bandit boost."""
    if not model:
        return {"ok": False, "error": "no_winner"}
    try:
        from .config import Config

        cfg = Config()
        cfg.set("preferred_model", model, persist=persist)
        cfg.set("default_model", model, persist=persist)
        bandit_ok = False
        try:
            from .model_registry import ModelRegistry
            from .model_router import ModelRouter

            router = ModelRouter(ModelRegistry())
            if hasattr(router, "update_bandit"):
                router.update_bandit(model, success=True, latency=0.5, cost=0.0)
                bandit_ok = True
        except Exception:
            pass
        return {
            "ok": True,
            "preferred_model": model,
            "persisted": persist,
            "bandit_updated": bandit_ok,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}
