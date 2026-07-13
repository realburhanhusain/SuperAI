"""
Hierarchical delegation — full decompose → run → synthesize path.
"""

from __future__ import annotations

import json
import re
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
        roles: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Decompose goal into subtasks, run each (optionally with role models),
        synthesize a parent summary.
        """
        roles = roles or {}
        if depth >= self.max_depth:
            result = self.orchestrator.run_task(goal, verbose=verbose)
            return {
                "goal": goal,
                "depth": depth,
                "leaf": True,
                "role": roles.get("worker", "worker"),
                "result": result,
            }

        subtasks = self._decompose(goal)
        if len(subtasks) <= 1 or depth + 1 >= self.max_depth:
            forced = roles.get("worker") or roles.get("supervisor")
            result = self.orchestrator.run_task(
                goal, forced_model=forced, verbose=verbose
            )
            return {
                "goal": goal,
                "depth": depth,
                "leaf": True,
                "result": result,
            }

        children = []
        for i, sub in enumerate(subtasks):
            # Dynamic role: first child design, last validate, middle implement
            child_roles = dict(roles)
            if i == 0:
                child_roles.setdefault("worker", roles.get("supervisor"))
            elif i == len(subtasks) - 1:
                child_roles.setdefault("worker", roles.get("critic"))
            children.append(
                self.run(sub, depth=depth + 1, verbose=verbose, roles=child_roles)
            )

        synthesis = self._synthesize(goal, children)
        return {
            "goal": goal,
            "depth": depth,
            "leaf": False,
            "subtasks": subtasks,
            "children": children,
            "synthesis": synthesis,
            "message": f"Delegated into {len(children)} subtasks at depth {depth}",
            "success": all(
                (c.get("result") or {}).get("success")
                or (c.get("synthesis") and c.get("success"))
                for c in children
            ),
        }

    def _decompose(self, goal: str) -> List[str]:
        # Prefer model-assisted decomposition
        try:
            caller = self.orchestrator.model_caller
            model = (
                self.config.default_supervisor
                or self.orchestrator.model_router.select_model(goal)
            )
            prompt = (
                "Decompose this goal into 2-5 concrete subtasks. "
                "Return ONLY a JSON string array.\n"
                f"Goal: {goal}"
            )
            raw = caller.call(model=model, prompt=prompt)
            text = str(raw.get("response") or "")
            arr = self._parse_string_array(text)
            if len(arr) >= 2:
                return arr[:5]
        except Exception:
            pass
        return self._heuristic_decompose(goal)

    def _heuristic_decompose(self, goal: str) -> List[str]:
        g = goal.lower()
        if any(k in g for k in ("build", "create", "implement", "system", "app")):
            return [
                f"Design approach for: {goal}",
                f"Implement core of: {goal}",
                f"Validate and document: {goal}",
            ]
        if any(k in g for k in ("research", "compare", "analyze")):
            return [
                f"Gather sources for: {goal}",
                f"Compare options for: {goal}",
                f"Recommend decision for: {goal}",
            ]
        if any(k in g for k in ("fix", "bug", "debug")):
            return [
                f"Reproduce: {goal}",
                f"Root-cause: {goal}",
                f"Fix and verify: {goal}",
            ]
        # Multi-clause goals
        parts = re.split(r"\band\b|;|\n", goal)
        parts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 8]
        if len(parts) >= 2:
            return parts[:5]
        return [goal]

    @staticmethod
    def _parse_string_array(text: str) -> List[str]:
        text = (text or "").strip()
        if "```" in text:
            m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.S)
            if m:
                text = m.group(1)
        try:
            start = text.find("[")
            end = text.rfind("]")
            if start >= 0 and end > start:
                data = json.loads(text[start : end + 1])
                if isinstance(data, list):
                    return [str(x).strip() for x in data if str(x).strip()]
        except json.JSONDecodeError:
            pass
        return []

    def _synthesize(self, goal: str, children: List[Dict[str, Any]]) -> str:
        parts = []
        for c in children:
            r = c.get("result") or {}
            leaf = r.get("result") if isinstance(r, dict) else None
            syn = c.get("synthesis")
            text = leaf or syn or c.get("message") or ""
            parts.append(f"### {c.get('goal')}\n{str(text)[:800]}")
        blob = "\n\n".join(parts)
        try:
            model = (
                self.config.default_supervisor
                or self.orchestrator.model_router.select_model(goal)
            )
            raw = self.orchestrator.model_caller.call(
                model=model,
                prompt=(
                    f"Parent goal: {goal}\n\nSubtask results:\n{blob}\n\n"
                    "Write a concise synthesis of the overall outcome."
                ),
            )
            return str(raw.get("response") or blob)
        except Exception:
            return blob
