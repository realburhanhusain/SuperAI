"""Multi-agent role debate foundation (V6 N261)."""

from __future__ import annotations

from typing import Any, Dict, List

from .public_api import wrap_public_result
from .superai_agent.runtime import AgentRuntime


def debate(topic: str, *, use_mock: bool = True) -> Dict[str, Any]:
    rt = AgentRuntime(use_mock=use_mock)
    roles = [
        ("plan", "Architect: outline approach and risks."),
        ("ask", "Critic: attack weaknesses of the plan."),
        ("build", "Builder: propose concrete implementation steps."),
    ]
    turns: List[Dict[str, Any]] = []
    prior = ""
    for role, intro in roles:
        prompt = f"{intro}\n\nTopic: {topic}\n\nPrior turns:\n{prior[-3000:]}"
        out = rt.run(prompt, agent=role, permission="plan", max_rounds=1)
        turns.append(
            {
                "role": role,
                "response": (out.response or "")[:1500],
                "ok": out.ok,
            }
        )
        prior += f"\n[{role}] {out.response or ''}\n"
    return wrap_public_result(
        {
            "ok": True,
            "topic": topic[:500],
            "turns": turns,
            "mock": use_mock,
        },
        mock=use_mock,
        ok=True,
        record_spend=False,
    )
