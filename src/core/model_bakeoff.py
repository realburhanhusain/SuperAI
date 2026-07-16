"""
Lightweight model bake-off / eval (Phase 8 N6 / MoSCoW N4).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence  # noqa: F401


def default_eval_hook(row: Dict[str, Any], prompt: str) -> Dict[str, Any]:
    """
    N4 eval hook: score row with simple heuristics (length, ok, latency).
    Returns score 0..1 and notes.
    """
    if not row.get("ok"):
        return {"score": 0.0, "notes": ["failed"]}
    preview = str(row.get("preview") or "")
    lat = float(row.get("latency_sec") or 99)
    length_score = min(1.0, len(preview) / 120.0)
    latency_score = max(0.0, 1.0 - min(lat, 30.0) / 30.0)
    score = 0.5 * length_score + 0.3 * latency_score + 0.2
    return {
        "score": round(score, 4),
        "notes": [f"len={len(preview)}", f"lat={lat}"],
    }


def write_bakeoff_report(
    result: Dict[str, Any],
    dest: Optional[Path] = None,
) -> Path:
    """Persist bakeoff JSON report under ~/.superai/bakeoff/."""
    root = Path.home() / ".superai" / "bakeoff"
    root.mkdir(parents=True, exist_ok=True)
    path = Path(dest or (root / f"bakeoff_{int(time.time())}.json"))
    path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return path


def bakeoff(
    prompt: str,
    models: Sequence[str],
    *,
    use_mock: bool = True,
    report: bool = True,
    report_path: Optional[Path] = None,
    eval_hook: Optional[Callable[[Dict[str, Any], str], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Run same prompt on multiple models; rank by success then latency (+ eval)."""
    from .model_caller import ModelCaller
    from .model_registry import ModelRegistry

    reg = ModelRegistry()
    caller = ModelCaller(use_mock=use_mock, registry=reg)
    hook = eval_hook or default_eval_hook
    rows: List[Dict[str, Any]] = []
    for m in models:
        t0 = time.time()
        try:
            out = caller.call(model=m, prompt=prompt)
            latency = time.time() - t0
            ok = str(out.get("status") or "") != "error"
            row = {
                "model": m,
                "ok": ok,
                "latency_sec": round(latency, 3),
                "mock": bool(out.get("mock")),
                "tokens": int(
                    (out.get("usage") or {}).get("total_tokens") or out.get("tokens") or 0
                ),
                "cost": float(out.get("estimated_cost_usd") or 0),
                "preview": str(out.get("response") or out.get("error") or "")[:240],
            }
            try:
                row["eval"] = hook(row, prompt)
            except Exception as e:
                row["eval"] = {"score": 0.0, "notes": [f"eval_error:{e}"]}
            rows.append(row)
        except Exception as e:
            rows.append(
                {
                    "model": m,
                    "ok": False,
                    "latency_sec": round(time.time() - t0, 3),
                    "error": str(e)[:200],
                    "eval": {"score": 0.0, "notes": ["exception"]},
                }
            )
    # Prefer higher eval score, then success, then lower latency
    rows.sort(
        key=lambda r: (
            not r.get("ok"),
            -(float((r.get("eval") or {}).get("score") or 0)),
            r.get("latency_sec") or 999,
        )
    )
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
    if report:
        try:
            path = write_bakeoff_report(out, report_path)
            out["report_path"] = str(path)
        except Exception as e:
            out["report_error"] = str(e)[:200]
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
