"""
Task planner — heuristic + optional LLM JSON plans (complete, not stub).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ExecutionStep:
    step_id: int
    description: str
    depends_on: List[int]
    recommended_model: str
    estimated_complexity: str
    can_run_parallel: bool = False
    role: str = "worker"  # worker | supervisor | critic


class TaskPlanner:
    """Generates execution plans for complex tasks."""

    def __init__(self, model_router: Any, model_caller: Any = None):
        self.model_router = model_router
        self.model_caller = model_caller

    def create_plan(
        self,
        task: str,
        use_llm: Optional[bool] = None,
    ) -> List[ExecutionStep]:
        task = (task or "").strip()
        if not task:
            return []

        # Try LLM plan when caller available and not forced mock-only
        if use_llm is None:
            use_llm = self.model_caller is not None
        if use_llm and self.model_caller is not None:
            try:
                llm_steps = self._llm_plan(task)
                if llm_steps and len(llm_steps) >= 1:
                    return llm_steps
            except Exception:
                pass

        return self._heuristic_plan(task)

    def _llm_plan(self, task: str) -> List[ExecutionStep]:
        model = "auto"
        try:
            if self.model_router:
                model = self.model_router.select_model(task) or "gpt-4o"
        except Exception:
            model = "gpt-4o"

        prompt = (
            "Break the user task into an execution plan. "
            "Reply ONLY with valid JSON array of objects:\n"
            '[{"step_id":1,"description":"...","depends_on":[],'
            '"estimated_complexity":"Low|Medium|High",'
            '"can_run_parallel":false,"role":"worker"}]\n'
            "Rules: step_id starts at 1; depends_on lists prior step_ids; "
            "independent steps after a shared parent may set can_run_parallel true.\n"
            f"Task: {task}"
        )
        raw = self.model_caller.call(model=model, prompt=prompt)
        text = str(raw.get("response") or "")
        data = self._extract_json_array(text)
        if not data:
            return []
        steps: List[ExecutionStep] = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                continue
            sid = int(item.get("step_id") or (i + 1))
            desc = str(item.get("description") or "").strip()
            if not desc:
                continue
            deps = item.get("depends_on") or []
            if not isinstance(deps, list):
                deps = []
            deps = [int(d) for d in deps if str(d).isdigit() or isinstance(d, int)]
            steps.append(
                ExecutionStep(
                    step_id=sid,
                    description=desc,
                    depends_on=deps,
                    recommended_model=str(item.get("recommended_model") or "auto"),
                    estimated_complexity=str(
                        item.get("estimated_complexity") or "Medium"
                    ),
                    can_run_parallel=bool(item.get("can_run_parallel")),
                    role=str(item.get("role") or "worker"),
                )
            )
        return steps

    @staticmethod
    def _extract_json_array(text: str) -> List[Any]:
        text = (text or "").strip()
        # strip markdown fences
        if "```" in text:
            m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.S)
            if m:
                text = m.group(1)
        try:
            start = text.find("[")
            end = text.rfind("]")
            if start >= 0 and end > start:
                return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
        return []

    def _heuristic_plan(self, task: str) -> List[ExecutionStep]:
        low = task.lower()

        if any(
            k in low
            for k in ("build", "create", "implement", "develop", "scaffold")
        ):
            return [
                ExecutionStep(
                    1,
                    "Analyze requirements and design high-level architecture",
                    [],
                    "auto",
                    "High",
                    role="supervisor",
                ),
                ExecutionStep(
                    2,
                    "Design data models / interfaces / API surface",
                    [1],
                    "auto",
                    "Medium",
                ),
                ExecutionStep(
                    3,
                    "Implement core business logic",
                    [2],
                    "auto",
                    "High",
                ),
                ExecutionStep(
                    4,
                    "Write unit tests for core logic",
                    [3],
                    "auto",
                    "Medium",
                    can_run_parallel=True,
                ),
                ExecutionStep(
                    5,
                    "Write documentation and usage examples",
                    [3],
                    "auto",
                    "Medium",
                    can_run_parallel=True,
                ),
                ExecutionStep(
                    6,
                    "Security, validation, error handling review",
                    [4, 5],
                    "auto",
                    "Medium",
                    role="critic",
                ),
            ]

        if any(
            k in low
            for k in ("research", "compare", "analyze", "survey", "evaluate")
        ):
            return [
                ExecutionStep(
                    1,
                    f"Gather background and sources for: {task}",
                    [],
                    "auto",
                    "Medium",
                    can_run_parallel=True,
                ),
                ExecutionStep(
                    2,
                    f"Collect alternatives and counterpoints for: {task}",
                    [],
                    "auto",
                    "Medium",
                    can_run_parallel=True,
                ),
                ExecutionStep(
                    3,
                    "Synthesize findings into a recommendation with trade-offs",
                    [1, 2],
                    "auto",
                    "High",
                    role="supervisor",
                ),
            ]

        if any(k in low for k in ("fix", "debug", "fix", "bug")):
            return [
                ExecutionStep(
                    1,
                    f"Reproduce and classify issue: {task}",
                    [],
                    "auto",
                    "Medium",
                ),
                ExecutionStep(
                    2,
                    "Propose root cause and fix plan",
                    [1],
                    "auto",
                    "High",
                ),
                ExecutionStep(
                    3,
                    "Apply fix and verify with checks",
                    [2],
                    "auto",
                    "Medium",
                ),
            ]

        if any(k in low for k in ("refactor", "optimize", "performance")):
            return [
                ExecutionStep(
                    1,
                    f"Baseline current behavior/metrics: {task}",
                    [],
                    "auto",
                    "Medium",
                ),
                ExecutionStep(
                    2,
                    "Apply improvements with safety checks",
                    [1],
                    "auto",
                    "High",
                ),
                ExecutionStep(
                    3,
                    "Validate outcomes and document changes",
                    [2],
                    "auto",
                    "Medium",
                ),
            ]

        return [
            ExecutionStep(
                1,
                task,
                [],
                "auto",
                "Medium",
                role="worker",
            )
        ]

    def print_plan(self, steps: List[ExecutionStep]) -> None:
        print("\n" + "=" * 60)
        print("EXECUTION PLAN")
        print("=" * 60)
        for step in steps:
            deps = f" (depends on: {step.depends_on})" if step.depends_on else ""
            parallel = " [PARALLEL]" if step.can_run_parallel else ""
            role = f" [{step.role}]" if step.role != "worker" else ""
            print(f"\nStep {step.step_id}: {step.description}")
            print(f"  → Model: {step.recommended_model}")
            print(
                f"  → Complexity: {step.estimated_complexity}{parallel}{role}{deps}"
            )
        print("\n" + "=" * 60 + "\n")

    def export_plan(
        self, task: str, steps: Optional[List[ExecutionStep]] = None
    ) -> Dict[str, Any]:
        steps = steps or self.create_plan(task)
        return {
            "task": task,
            "steps": [
                {
                    "step_id": s.step_id,
                    "description": s.description,
                    "depends_on": list(s.depends_on or []),
                    "recommended_model": s.recommended_model,
                    "estimated_complexity": s.estimated_complexity,
                    "can_run_parallel": s.can_run_parallel,
                    "role": getattr(s, "role", "worker"),
                }
                for s in steps
            ],
        }

    def export_plan_markdown(
        self, task: str, steps: Optional[List[ExecutionStep]] = None
    ) -> str:
        data = self.export_plan(task, steps)
        lines = ["# Execution plan", "", f"**Task:** {task}", ""]
        for s in data["steps"]:
            deps = (
                f" (depends on {', '.join(map(str, s['depends_on']))})"
                if s["depends_on"]
                else ""
            )
            par = " `[parallel]`" if s["can_run_parallel"] else ""
            role = f" `{s.get('role', 'worker')}`"
            lines.append(
                f"## Step {s['step_id']}{par}{deps}\n\n"
                f"{s['description']}\n\n"
                f"- Model: `{s['recommended_model']}`\n"
                f"- Complexity: {s['estimated_complexity']}\n"
                f"- Role: {role}\n"
            )
        return "\n".join(lines)
