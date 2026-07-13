"""
Export SuperAI plans as LangGraph-style graphs (N16).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .task_planner import ExecutionStep, TaskPlanner


def plan_to_langgraph(task: str, steps: Optional[List[ExecutionStep]] = None) -> Dict[str, Any]:
    planner = TaskPlanner(None)
    steps = steps or planner.create_plan(task, use_llm=False)
    nodes = []
    edges = []
    for s in steps:
        nodes.append(
            {
                "id": f"step_{s.step_id}",
                "type": s.role or "worker",
                "data": {
                    "label": s.description,
                    "complexity": s.estimated_complexity,
                    "parallel": s.can_run_parallel,
                },
            }
        )
        if not s.depends_on:
            edges.append({"source": "START", "target": f"step_{s.step_id}"})
        for d in s.depends_on or []:
            edges.append({"source": f"step_{d}", "target": f"step_{s.step_id}"})
    # terminal edges
    terminals = {s.step_id for s in steps}
    for s in steps:
        for d in s.depends_on or []:
            pass
    dependents = set()
    for s in steps:
        for d in s.depends_on or []:
            dependents.add(d)
    for s in steps:
        if s.step_id not in {e for e in dependents}:
            # if no one depends on s, edge to END — approximate leaves
            pass
    leaves = []
    pointed = set()
    for s in steps:
        for d in s.depends_on or []:
            pointed.add(s.step_id)
    for s in steps:
        # leaf if no step depends on this step_id
        if not any(s.step_id in (o.depends_on or []) for o in steps):
            leaves.append(s.step_id)
    for lid in leaves:
        edges.append({"source": f"step_{lid}", "target": "END"})
    return {
        "format": "superai.langgraph.v1",
        "task": task,
        "nodes": [{"id": "START", "type": "start"}, *nodes, {"id": "END", "type": "end"}],
        "edges": edges,
    }
