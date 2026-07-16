"""Architecture mode vs implementation mode (V6 S103)."""

from __future__ import annotations

from typing import Any, Dict, Literal

Mode = Literal["architecture", "implementation", "plan", "build", "ask"]


def resolve_mode(mode: str) -> Dict[str, Any]:
    m = str(mode or "build").lower().strip()
    if m in {"architecture", "arch", "design"}:
        return {
            "mode": "architecture",
            "agent_role": "plan",
            "allow_writes": False,
            "permission": "plan",
            "system_extra": (
                "You are in ARCHITECTURE mode. Produce designs, ADRs, component "
                "boundaries, and trade-offs. Do not implement code changes."
            ),
        }
    if m in {"implementation", "build", "code"}:
        return {
            "mode": "implementation",
            "agent_role": "build",
            "allow_writes": True,
            "permission": "ask",
            "system_extra": (
                "You are in IMPLEMENTATION mode. Make concrete code changes, "
                "follow existing patterns, and keep diffs minimal."
            ),
        }
    if m == "plan":
        return {
            "mode": "plan",
            "agent_role": "plan",
            "allow_writes": False,
            "permission": "plan",
            "system_extra": "Plan only; no writes.",
        }
    if m == "ask":
        return {
            "mode": "ask",
            "agent_role": "ask",
            "allow_writes": False,
            "permission": "plan",
            "system_extra": "Answer questions only.",
        }
    return {
        "mode": "implementation",
        "agent_role": "build",
        "allow_writes": True,
        "permission": "ask",
        "system_extra": "",
    }
