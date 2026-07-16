"""Daily/weekly spend reports + cache stats (V6 S134/S135)."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Dict, List


def spend_report(*, days: int = 7) -> Dict[str, Any]:
    from .budget import BudgetGuard
    from .history import TaskHistory

    snap = BudgetGuard().snapshot()
    hist = TaskHistory().list(limit=500)
    by_day: Dict[str, float] = defaultdict(float)
    by_model: Dict[str, float] = defaultdict(float)
    total = 0.0
    for rec in hist:
        usd = float(rec.get("estimated_cost_usd") or rec.get("cost") or 0)
        total += usd
        tid = str(rec.get("task_id") or "")
        day = tid[:8] if len(tid) >= 8 and tid[:8].isdigit() else "unknown"
        by_day[day] += usd
        by_model[str(rec.get("model") or "unknown")] += usd

    # cache hit rate if available
    cache_hits = cache_miss = 0
    try:
        from .result_cache import stats as cache_stats

        st = cache_stats() if callable(cache_stats) else {}
        cache_hits = int(st.get("hits") or 0)
        cache_miss = int(st.get("misses") or 0)
    except Exception:
        try:
            from .board_cache import BoardCache

            # best-effort
            cache_hits = 0
        except Exception:
            pass

    denom = cache_hits + cache_miss
    hit_rate = (cache_hits / denom) if denom else None

    return {
        "ok": True,
        "budget_snapshot": snap,
        "history_records": len(hist),
        "total_estimated_usd": round(total, 6),
        "by_day": dict(sorted(by_day.items(), reverse=True)[: max(1, days)]),
        "by_model": dict(sorted(by_model.items(), key=lambda x: -x[1])[:20]),
        "cache_hits": cache_hits,
        "cache_misses": cache_miss,
        "cache_hit_rate": hit_rate,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
