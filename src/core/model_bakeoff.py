"""
Lightweight model bake-off / eval (Phase 8 N6).
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Sequence


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
    return {
        "ok": True,
        "prompt": prompt[:500],
        "results": rows,
        "winner": rows[0]["model"] if rows else None,
    }
