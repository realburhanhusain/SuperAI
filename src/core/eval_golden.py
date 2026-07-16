"""
Offline golden eval set (V5 M8) — mock-friendly quality ceilings.
"""

from __future__ import annotations

from typing import Any, Dict, List


GOLDEN_TASKS: List[Dict[str, Any]] = [
    {
        "id": "g1",
        "task": "What is SuperAI in one sentence?",
        "path": "agent",
        "agent_role": "ask",
        "max_cost_usd": 0.05,
        "require_ok": True,
    },
    {
        "id": "g2",
        "task": "summarize the idea of a budget guard",
        "path": "agent",
        "agent_role": "ask",
        "max_cost_usd": 0.05,
        "require_ok": True,
    },
    {
        "id": "g3",
        "task": "plan a small FastAPI hello endpoint",
        "path": "agent",
        "agent_role": "plan",
        "max_cost_usd": 0.1,
        "require_ok": True,
    },
]


def run_golden(*, use_mock: bool = True, limit: int = 10) -> Dict[str, Any]:
    from .front_door import choose_path
    from .public_api import wrap_public_result
    from .superai_agent.runtime import AgentRuntime

    rt = AgentRuntime(use_mock=use_mock)
    results = []
    passed = 0
    for g in GOLDEN_TASKS[:limit]:
        route = choose_path(g["task"])
        out = rt.run(
            g["task"],
            agent=str(g.get("agent_role") or "ask"),
            permission="plan",
            max_rounds=1,
        )
        data = wrap_public_result(
            out.to_dict(),
            mock=use_mock,
            ok=bool(out.ok),
            record_spend=False,
        )
        cost = float(data.get("estimated_cost_usd") or 0)
        ok = True
        reasons = []
        if g.get("require_ok") and not data.get("ok"):
            ok = False
            reasons.append("not_ok")
        if cost > float(g.get("max_cost_usd") or 1):
            ok = False
            reasons.append("over_cost")
        if not (data.get("response") or data.get("message") or out.response):
            # mock may still set response
            if not str(out.response or "").strip():
                ok = False
                reasons.append("empty")
        if ok:
            passed += 1
        results.append(
            {
                "id": g["id"],
                "ok": ok,
                "reasons": reasons,
                "route": route.get("path"),
                "cost": cost,
                "contract": data.get("contract"),
            }
        )
    return {
        "ok": passed == len(results),
        "passed": passed,
        "total": len(results),
        "results": results,
        "mock": use_mock,
        "contract": "superai.result.v1",
    }
