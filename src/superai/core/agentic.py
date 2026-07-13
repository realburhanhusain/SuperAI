"""
Advanced agentic patterns (Phase 8 / Track I) — foundational implementations.

- Debate / critique / extend between roles
- Dynamic role labels for models
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

    def _default_models(self, n: int) -> List[str]:
        names = self.registry.list_all_models()
        if not names:
            return ["gpt-4o"] * n
        return names[:n]
