"""
Aggregate routing / model performance stats from task history (Phase 2).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from .history import TaskHistory


def compute_model_stats(history: Optional[TaskHistory] = None, limit: int = 200) -> Dict[str, Dict[str, Any]]:
    """
    Per-model aggregates from recent history records.

    Returns map: model_name -> {successes, failures, total, success_rate, avg_duration, last_task_type}
    """
    store = history or TaskHistory()
    records = store.list(limit=limit)
    stats: Dict[str, Dict[str, Any]] = {}

    for rec in records:
        models_seen: List[str] = []
        model = rec.get("model_used")
        if model:
            models_seen.append(str(model))
        for step in rec.get("steps") or []:
            sm = step.get("model")
            if sm:
                models_seen.append(str(sm))

        success = bool(rec.get("success"))
        duration = float(rec.get("duration") or 0.0)
        task_type = (rec.get("metadata") or {}).get("task_type") or "general"

        for m in set(models_seen):
            bucket = stats.setdefault(
                m,
                {
                    "successes": 0,
                    "failures": 0,
                    "total": 0,
                    "duration_sum": 0.0,
                    "last_task_type": task_type,
                },
            )
            bucket["total"] += 1
            if success:
                bucket["successes"] += 1
            else:
                bucket["failures"] += 1
            bucket["duration_sum"] += duration
            bucket["last_task_type"] = task_type

    for m, bucket in stats.items():
        total = max(bucket["total"], 1)
        bucket["success_rate"] = round(bucket["successes"] / total, 3)
        bucket["avg_duration"] = round(bucket["duration_sum"] / total, 3)
        del bucket["duration_sum"]

    return stats


def compute_provider_health(
    load_balancer_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, float]:
    """Map provider -> health score 0..1 from circuit breaker state if provided."""
    if not load_balancer_state:
        return {}
    health: Dict[str, float] = {}
    for provider, cb in load_balancer_state.items():
        if getattr(cb, "is_open", False):
            health[provider] = 0.1
        else:
            failures = getattr(cb, "failures", 0)
            health[provider] = max(0.2, 1.0 - 0.2 * failures)
    return health


def summarize_routing(history: Optional[TaskHistory] = None, limit: int = 50) -> Dict[str, Any]:
    """High-level summary for CLI routing-stats."""
    model_stats = compute_model_stats(history=history, limit=limit)
    if not model_stats:
        return {
            "total_models_seen": 0,
            "total_runs_sampled": 0,
            "top_models": [],
            "message": "No history yet. Run tasks with `superai run` first.",
        }

    store = history or TaskHistory()
    runs = store.list(limit=limit)
    ranked = sorted(
        model_stats.items(),
        key=lambda kv: (kv[1]["success_rate"], kv[1]["total"]),
        reverse=True,
    )
    top = [
        {
            "model": name,
            "success_rate": data["success_rate"],
            "total": data["total"],
            "avg_duration": data["avg_duration"],
        }
        for name, data in ranked[:8]
    ]
    return {
        "total_models_seen": len(model_stats),
        "total_runs_sampled": len(runs),
        "top_models": top,
        "by_model": model_stats,
        "message": f"Aggregated {len(runs)} recent run(s) across {len(model_stats)} model(s).",
    }
