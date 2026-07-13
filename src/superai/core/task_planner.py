from __future__ import annotations

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


class TaskPlanner:
    """Generates execution plans for complex tasks."""

    def __init__(self, model_router: Any):
        self.model_router = model_router

    def create_plan(self, task: str) -> List[ExecutionStep]:
        """Create a structured execution plan for a task."""
        low = (task or "").lower()

        # Multi-concern tasks: independent research/doc arms can parallelize
        if any(k in low for k in ("build", "create", "implement", "develop")):
            return [
                ExecutionStep(
                    step_id=1,
                    description="Analyze requirements and design high-level architecture",
                    depends_on=[],
                    recommended_model="auto",
                    estimated_complexity="High",
                    can_run_parallel=False,
                ),
                ExecutionStep(
                    step_id=2,
                    description="Design data models and database schema",
                    depends_on=[1],
                    recommended_model="auto",
                    estimated_complexity="Medium",
                    can_run_parallel=False,
                ),
                ExecutionStep(
                    step_id=3,
                    description="Implement core business logic",
                    depends_on=[2],
                    recommended_model="auto",
                    estimated_complexity="High",
                    can_run_parallel=False,
                ),
                # After core impl, tests + docs are independent → parallel
                ExecutionStep(
                    step_id=4,
                    description="Write unit tests for core logic",
                    depends_on=[3],
                    recommended_model="auto",
                    estimated_complexity="Medium",
                    can_run_parallel=True,
                ),
                ExecutionStep(
                    step_id=5,
                    description="Write documentation and usage examples",
                    depends_on=[3],
                    recommended_model="auto",
                    estimated_complexity="Medium",
                    can_run_parallel=True,
                ),
                ExecutionStep(
                    step_id=6,
                    description="Add error handling, validation, and security review",
                    depends_on=[4, 5],
                    recommended_model="auto",
                    estimated_complexity="Medium",
                    can_run_parallel=False,
                ),
            ]

        if any(k in low for k in ("research", "compare", "analyze and", "survey")):
            return [
                ExecutionStep(
                    step_id=1,
                    description=f"Gather background for: {task}",
                    depends_on=[],
                    recommended_model="auto",
                    estimated_complexity="Medium",
                    can_run_parallel=True,
                ),
                ExecutionStep(
                    step_id=2,
                    description=f"Collect counterpoints / alternatives for: {task}",
                    depends_on=[],
                    recommended_model="auto",
                    estimated_complexity="Medium",
                    can_run_parallel=True,
                ),
                ExecutionStep(
                    step_id=3,
                    description="Synthesize findings into a recommendation",
                    depends_on=[1, 2],
                    recommended_model="auto",
                    estimated_complexity="High",
                    can_run_parallel=False,
                ),
            ]

        return [
            ExecutionStep(
                step_id=1,
                description=task,
                depends_on=[],
                recommended_model="auto",
                estimated_complexity="Medium",
                can_run_parallel=False,
            )
        ]

    def print_plan(self, steps: List[ExecutionStep]):
        """Pretty print the execution plan."""
        print("\n" + "=" * 60)
        print("EXECUTION PLAN")
        print("=" * 60)

        for step in steps:
            deps = f" (depends on: {step.depends_on})" if step.depends_on else ""
            parallel = " [PARALLEL]" if step.can_run_parallel else ""

            print(f"\nStep {step.step_id}: {step.description}")
            print(f"  → Recommended Model: {step.recommended_model}")
            print(f"  → Complexity: {step.estimated_complexity}{parallel}{deps}")

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
                }
                for s in steps
            ],
        }

    def export_plan_markdown(
        self, task: str, steps: Optional[List[ExecutionStep]] = None
    ) -> str:
        data = self.export_plan(task, steps)
        lines = [f"# Execution plan", f"", f"**Task:** {task}", ""]
        for s in data["steps"]:
            deps = (
                f" (depends on {', '.join(map(str, s['depends_on']))})"
                if s["depends_on"]
                else ""
            )
            par = " `[parallel]`" if s["can_run_parallel"] else ""
            lines.append(
                f"## Step {s['step_id']}{par}{deps}\n\n"
                f"{s['description']}\n\n"
                f"- Model: `{s['recommended_model']}`\n"
                f"- Complexity: {s['estimated_complexity']}\n"
            )
        return "\n".join(lines)
