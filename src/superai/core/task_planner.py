from typing import List, Dict, Any
from dataclasses import dataclass

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

    def __init__(self, model_router):
        self.model_router = model_router

    def create_plan(self, task: str) -> List[ExecutionStep]:
        """Create a structured execution plan for a task."""
        # This is a simplified version. In a full implementation,
        # this would use an LLM to break down the task intelligently.
        
        steps = []
        
        # Simple heuristic-based planning for now
        if any(keyword in task.lower() for keyword in ["build", "create", "implement", "develop"]):
            steps = [
                ExecutionStep(
                    step_id=1,
                    description="Analyze requirements and design high-level architecture",
                    depends_on=[],
                    recommended_model="claude-fable-5",
                    estimated_complexity="High",
                    can_run_parallel=False
                ),
                ExecutionStep(
                    step_id=2,
                    description="Design data models and database schema",
                    depends_on=[1],
                    recommended_model="deepseek-v4-pro",
                    estimated_complexity="Medium",
                    can_run_parallel=False
                ),
                ExecutionStep(
                    step_id=3,
                    description="Implement core business logic",
                    depends_on=[2],
                    recommended_model="deepseek-v4-pro",
                    estimated_complexity="High",
                    can_run_parallel=False
                ),
                ExecutionStep(
                    step_id=4,
                    description="Add error handling, validation, and security",
                    depends_on=[3],
                    recommended_model="claude-fable-5",
                    estimated_complexity="Medium",
                    can_run_parallel=False
                ),
                ExecutionStep(
                    step_id=5,
                    description="Write tests and documentation",
                    depends_on=[3, 4],
                    recommended_model="grok-4.5",
                    estimated_complexity="Medium",
                    can_run_parallel=True
                )
            ]
        else:
            # Simple single-step plan
            steps = [
                ExecutionStep(
                    step_id=1,
                    description=task,
                    depends_on=[],
                    recommended_model="auto",
                    estimated_complexity="Medium",
                    can_run_parallel=False
                )
            ]
        
        return steps

    def print_plan(self, steps: List[ExecutionStep]):
        """Pretty print the execution plan."""
        print("\n" + "="*60)
        print("EXECUTION PLAN")
        print("="*60)
        
        for step in steps:
            deps = f" (depends on: {step.depends_on})" if step.depends_on else ""
            parallel = " [PARALLEL]" if step.can_run_parallel else ""
            
            print(f"\nStep {step.step_id}: {step.description}")
            print(f"  → Recommended Model: {step.recommended_model}")
            print(f"  → Complexity: {step.estimated_complexity}{parallel}{deps}")
        
        print("\n" + "="*60 + "\n")
