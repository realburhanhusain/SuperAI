"""
Pre-run cost forecasting (N20).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .model_registry import ModelRegistry
from .task_planner import TaskPlanner


def forecast_task_cost(
    task: str,
    model: Optional[str] = None,
    tokens_per_step: int = 1500,
) -> Dict[str, Any]:
    reg = ModelRegistry()
    planner = TaskPlanner(None)
    steps = planner.create_plan(task, use_llm=False)
    models = []
    total = 0.0
    for s in steps:
        name = model or s.recommended_model
        if name == "auto":
            name = reg.list_all_models()[0] if reg.list_all_models() else "gpt-4o"
        info = reg.get_model(name)
        rate = float(info.cost_per_1k_tokens) if info else 0.005
        step_cost = rate * (tokens_per_step / 1000.0)
        total += step_cost
        models.append({"step": s.step_id, "model": name, "est_usd": round(step_cost, 6)})
    return {
        "task": task,
        "steps": len(steps),
        "estimated_usd": round(total, 6),
        "breakdown": models,
        "tokens_per_step_assumed": tokens_per_step,
    }
