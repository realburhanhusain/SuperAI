"""
Hierarchical delegation (Hermes-inspired).

Supervisor decomposes a goal into subtasks and runs them via SuperAIOrchestrator
with depth limits from config.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .config import Config
from .orchestrator import SuperAIOrchestrator


class HierarchicalDelegator:
    def __init__(
        self,
        orchestrator: Optional[SuperAIOrchestrator] = None,
        config: Optional[Config] = None,
    ):
        self.config = config or Config()
        self.orchestrator = orchestrator or SuperAIOrchestrator(config=self.config)
        self.max_depth = int(self.config.get("max_delegation_depth") or 3)

    def run(
        self,
        goal: str,
        depth: int = 0,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        if depth >= self.max_depth:
            result = self.orchestrator.run_task(goal, verbose=verbose)
            return {
                "goal": goal,
                "depth": depth,
                "leaf": True,
                "result": result,
            }

        # Simple split heuristic for hierarchy demo
        subtasks = self._decompose(goal)
        if len(subtasks) <= 1 or depth + 1 >= self.max_depth:
            result = self.orchestrator.run_task(goal, verbose=verbose)
            return {
                "goal": goal,
                "depth": depth,
                "leaf": True,
                "result": result,
            }

        children = []
        for sub in subtasks:
            children.append(self.run(sub, depth=depth + 1, verbose=verbose))

        return {
            "goal": goal,
            "depth": depth,
            "leaf": False,
            "subtasks": subtasks,
            "children": children,
            "message": f"Delegated into {len(children)} subtasks at depth {depth}",
        }

    def _decompose(self, goal: str) -> List[str]:
        g = goal.lower()
        if any(k in g for k in ("build", "create", "implement", "system")):
            return [
                f"Design approach for: {goal}",
                f"Implement core of: {goal}",
                f"Validate and document: {goal}",
            ]
        return [goal]
