"""
Advanced agentic patterns (Phase 8 / Track I).

- Debate / critique / extend between roles
- Dynamic role switching (supervisor → workers → critic → final)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .model_caller import ModelCaller
from .model_registry import ModelRegistry


class AgenticWorkflows:
    def __init__(
        self,
        caller: Optional[ModelCaller] = None,
        registry: Optional[ModelRegistry] = None,
    ):
        self.registry = registry or ModelRegistry()
        self.caller = caller or ModelCaller(
            use_mock=True, registry=self.registry
        )

    def debate(
        self,
        topic: str,
        models: Optional[List[str]] = None,
        rounds: int = 1,
    ) -> Dict[str, Any]:
        """
        Each model proposes a stance; optional second round of critique.
        """
        models = models or self._default_models(2)
        proposals = []
        for m in models:
            prompt = (
                f"You are debating the topic: {topic}\n"
                f"Give a concise position with 3 bullet reasons."
            )
            resp = self.caller.call(model=m, prompt=prompt)
            proposals.append(
                {
                    "model": m,
                    "role": "debater",
                    "text": resp.get("response"),
                    "mock": resp.get("mock"),
                }
            )

        critiques = []
        if rounds >= 2 and len(proposals) >= 2:
            for i, p in enumerate(proposals):
                other = proposals[(i + 1) % len(proposals)]
                prompt = (
                    f"Topic: {topic}\n"
                    f"Opponent said:\n{other['text']}\n"
                    f"Critique constructively and refine your stance."
                )
                resp = self.caller.call(model=p["model"], prompt=prompt)
                critiques.append(
                    {
                        "model": p["model"],
                        "role": "critique",
                        "text": resp.get("response"),
                    }
                )

        return {
            "topic": topic,
            "proposals": proposals,
            "critiques": critiques,
            "message": f"Debate completed with {len(models)} model(s).",
        }

    def critique_and_extend(
        self,
        draft: str,
        critic_model: Optional[str] = None,
        extender_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        models = self._default_models(2)
        critic = critic_model or models[0]
        extender = extender_model or (models[1] if len(models) > 1 else models[0])

        critique = self.caller.call(
            model=critic,
            prompt=f"Critique this draft and list issues:\n\n{draft}",
        )
        extended = self.caller.call(
            model=extender,
            prompt=(
                f"Original draft:\n{draft}\n\n"
                f"Critique:\n{critique.get('response')}\n\n"
                f"Produce an improved extended version."
            ),
        )
        return {
            "critic_model": critic,
            "extender_model": extender,
            "critique": critique.get("response"),
            "extended": extended.get("response"),
        }

    def parallel_cli_workflow(
        self,
        task: str,
        clis: Optional[List[str]] = None,
        max_workers: int = 4,
        dry_run: bool = True,
        auto_approve: bool = False,
    ) -> Dict[str, Any]:
        """
        Fan-out the same task to multiple external CLIs in parallel.
        Live status is visible on `superai dashboard` and web `/api/cli-pool`.
        """
        from .cli_pool import ParallelCLIManager

        return ParallelCLIManager().run_agentic_parallel(
            task,
            clis=clis,
            max_workers=max_workers,
            dry_run=dry_run,
            auto_approve=auto_approve,
        )

    def dynamic_roles(
        self,
        task: str,
        supervisor: Optional[str] = None,
        workers: Optional[List[str]] = None,
        critic: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Dynamic role switching: assign supervisor / workers / critic, run a mini cycle.
        Any model may play any role.
        """
        pool = self._default_models(4)
        sup = supervisor or pool[0]
        worker_list = workers or pool[1:3] or [pool[0]]
        crit = critic or pool[-1]

        plan = self.caller.call(
            model=sup,
            prompt=f"You are supervisor. Outline 3 steps for: {task}",
        )
        worker_outputs = []
        for w in worker_list:
            out = self.caller.call(
                model=w,
                prompt=(
                    f"Supervisor plan:\n{plan.get('response')}\n\n"
                    f"As worker, execute your part for: {task}"
                ),
            )
            worker_outputs.append({"model": w, "role": "worker", "text": out.get("response")})

        critique = self.caller.call(
            model=crit,
            prompt=(
                f"Task: {task}\nPlan: {plan.get('response')}\n"
                f"Worker outputs: {worker_outputs}\n"
                "Critique and list risks."
            ),
        )
        # Role switch: critic becomes temporary supervisor for final call
        final = self.caller.call(
            model=crit,
            prompt=(
                f"Now act as supervisor. Integrate critique and produce final answer.\n"
                f"Task: {task}\nCritique: {critique.get('response')}\n"
                f"Workers: {worker_outputs}"
            ),
        )
        return {
            "task": task,
            "roles": {
                "supervisor": sup,
                "workers": worker_list,
                "critic": crit,
                "final_supervisor": crit,
            },
            "plan": plan.get("response"),
            "worker_outputs": worker_outputs,
            "critique": critique.get("response"),
            "final": final.get("response"),
            "message": "Dynamic role cycle complete (supervisor→workers→critic→final).",
        }

    def _default_models(self, n: int) -> List[str]:
        names = [
            n
            for n in self.registry.list_all_models()
            if not str(n).startswith("cli:")
        ]
        if not names:
            return ["gpt-4o"] * n
        return names[:n]
