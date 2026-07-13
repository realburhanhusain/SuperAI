"""
Model comparison and lightweight benchmarking (Future Plan G1).
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .model_caller import ModelCaller
from .model_registry import ModelRegistry
from .model_router import ModelRouter


def compare_models(
    prompt: str,
    models: Optional[List[str]] = None,
    use_mock: bool = True,
    top_n: int = 4,
) -> Dict[str, Any]:
    """
    Run the same prompt against several models and rank by latency + success.
    """
    registry = ModelRegistry()
    router = ModelRouter(registry)
    if not models:
        ranked = router.explain_selection(prompt, top_k=top_n)
        models = [r["model"] for r in ranked]
    if not models:
        models = list(registry.list_all_models())[:top_n]

    caller = ModelCaller(use_mock=use_mock, registry=registry)
    results: List[Dict[str, Any]] = []
    for name in models:
        t0 = time.time()
        try:
            out = caller.call(model=name, prompt=prompt)
            latency = time.time() - t0
            ok = not (
                isinstance(out, dict) and out.get("status") == "error"
            )
            text = ""
            if isinstance(out, dict):
                text = str(out.get("response") or "")[:500]
            else:
                text = str(out)[:500]
            results.append(
                {
                    "model": name,
                    "ok": ok,
                    "latency_sec": round(latency, 4),
                    "preview": text,
                    "usage": (out.get("usage") if isinstance(out, dict) else None),
                    "cost_usd": (
                        out.get("estimated_cost_usd") if isinstance(out, dict) else None
                    ),
                }
            )
        except Exception as e:  # noqa: BLE001
            results.append(
                {
                    "model": name,
                    "ok": False,
                    "latency_sec": round(time.time() - t0, 4),
                    "error": str(e),
                    "preview": "",
                }
            )

    # Rank: success first, then lower latency
    results.sort(key=lambda r: (not r.get("ok"), r.get("latency_sec") or 999.0))
    return {
        "prompt": prompt,
        "mock": use_mock,
        "count": len(results),
        "winner": results[0]["model"] if results else None,
        "results": results,
    }


def benchmark_models(
    prompts: Optional[List[str]] = None,
    models: Optional[List[str]] = None,
    use_mock: bool = True,
) -> Dict[str, Any]:
    """Run a small suite of prompts and aggregate per-model stats."""
    prompts = prompts or [
        "Write a one-line Python hello world.",
        "Explain recursion in two sentences.",
        "List three HTTP status codes and meanings.",
    ]
    aggregates: Dict[str, Dict[str, Any]] = {}
    rounds = []
    for p in prompts:
        round_r = compare_models(p, models=models, use_mock=use_mock)
        rounds.append(round_r)
        for row in round_r["results"]:
            m = row["model"]
            agg = aggregates.setdefault(
                m, {"ok": 0, "fail": 0, "latency_sum": 0.0, "n": 0}
            )
            agg["n"] += 1
            if row.get("ok"):
                agg["ok"] += 1
            else:
                agg["fail"] += 1
            agg["latency_sum"] += float(row.get("latency_sec") or 0)

    summary = []
    for m, a in aggregates.items():
        n = max(1, a["n"])
        summary.append(
            {
                "model": m,
                "success_rate": round(a["ok"] / n, 3),
                "avg_latency_sec": round(a["latency_sum"] / n, 4),
                "runs": a["n"],
            }
        )
    summary.sort(key=lambda x: (-x["success_rate"], x["avg_latency_sec"]))
    return {"prompts": prompts, "summary": summary, "rounds": rounds}


def benchmark_report_markdown(data: Optional[Dict[str, Any]] = None, **kwargs: Any) -> str:
    """N8: Markdown report for stakeholders."""
    data = data or benchmark_models(**kwargs)
    lines = [
        "# SuperAI Model Benchmark Report",
        "",
        f"Prompts: {len(data.get('prompts') or [])}",
        "",
        "| Model | Success rate | Avg latency (s) | Runs |",
        "|-------|-------------:|----------------:|-----:|",
    ]
    for row in data.get("summary") or []:
        lines.append(
            f"| {row.get('model')} | {row.get('success_rate')} | "
            f"{row.get('avg_latency_sec')} | {row.get('runs')} |"
        )
    if data.get("summary"):
        lines.extend(
            [
                "",
                f"**Winner (by success then latency):** `{data['summary'][0].get('model')}`",
            ]
        )
    lines.append("")
    return "\n".join(lines)
