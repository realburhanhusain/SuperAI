"""
Front-door policy map (V4 S5) — choose agent vs board vs orchestrator run.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .task_complexity import classify_task


def choose_path(
    text: str,
    *,
    force: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Returns path: agent | board | run | ask
    """
    if force in {"agent", "board", "run", "ask"}:
        return {"path": force, "reason": "forced", "complexity": classify_task(text)}

    low = (text or "").lower()
    cx = classify_task(text)

    if any(
        k in low
        for k in (
            "code review",
            "review this",
            "multi-cli",
            "advise",
            "council",
            "vote on",
        )
    ):
        return {"path": "board", "reason": "review_or_council_language", "complexity": cx}

    if cx["step_kind"] == "code" or any(
        k in low for k in ("implement", "refactor", "fix bug", "edit file", "write tests")
    ):
        return {
            "path": "agent",
            "reason": "coding_task",
            "complexity": cx,
            "agent_role": "build",
        }

    if cx["step_kind"] == "plan":
        return {
            "path": "agent",
            "reason": "planning",
            "complexity": cx,
            "agent_role": "plan",
        }

    if cx["tier"] in {"trivial", "simple"} and cx["step_kind"] in {
        "summarize",
        "general",
    }:
        return {"path": "ask", "reason": "simple_nl", "complexity": cx}

    if any(k in low for k in ("orchestrate", "multi-step", "pipeline", "workflow")):
        return {"path": "run", "reason": "orchestrator_language", "complexity": cx}

    # default: agent ask role for Q&A, build for longer
    if cx["words"] < 30:
        return {
            "path": "agent",
            "reason": "default_short",
            "complexity": cx,
            "agent_role": "ask",
        }
    return {
        "path": "agent",
        "reason": "default",
        "complexity": cx,
        "agent_role": "build",
    }
