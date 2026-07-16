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
    Includes confidence 0..1 (V5 S6) for optional user confirm when low.
    """
    if force in {"agent", "board", "run", "ask"}:
        return {
            "path": force,
            "reason": "forced",
            "complexity": classify_task(text),
            "confidence": 1.0,
            "needs_confirm": False,
        }

    low = (text or "").lower()
    cx = classify_task(text)

    def _out(path: str, reason: str, conf: float, **extra: Any) -> Dict[str, Any]:
        return {
            "path": path,
            "reason": reason,
            "complexity": cx,
            "confidence": round(conf, 2),
            "needs_confirm": conf < 0.55,
            **extra,
        }

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
        return _out("board", "review_or_council_language", 0.9)

    if cx["step_kind"] == "code" or any(
        k in low for k in ("implement", "refactor", "fix bug", "edit file", "write tests")
    ):
        return _out("agent", "coding_task", 0.88, agent_role="build")

    if cx["step_kind"] == "plan":
        return _out("agent", "planning", 0.8, agent_role="plan")

    if cx["tier"] in {"trivial", "simple"} and cx["step_kind"] in {
        "summarize",
        "general",
    }:
        return _out("ask", "simple_nl", 0.75)

    if any(k in low for k in ("orchestrate", "multi-step", "pipeline", "workflow")):
        return _out("run", "orchestrator_language", 0.85)

    # default: lower confidence when ambiguous
    if cx["words"] < 30:
        return _out("agent", "default_short", 0.5, agent_role="ask")
    return _out("agent", "default", 0.45, agent_role="build")
