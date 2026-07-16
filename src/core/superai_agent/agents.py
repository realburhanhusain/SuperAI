"""
Multi-agent roles for SuperAI: build / plan / ask.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class AgentRole:
    id: str
    title: str
    description: str
    system_prompt: str
    default_tools: bool = True
    max_tool_rounds: int = 4


AGENT_ROLES: Dict[str, AgentRole] = {
    "build": AgentRole(
        id="build",
        title="Build",
        description="Implement features, edit files, run tools aggressively",
        system_prompt=(
            "You are SuperAI Build agent (coding implementer). "
            "Prefer concrete code changes. When you need tools, emit JSON:\n"
            '{"tool_call":{"name":"read|write|grep|glob|diff_apply|bash","arguments":{...}}}\n'
            "You may emit multiple tool_call blocks. After tools, continue until done. "
            "Be concise; show final summary of files changed."
        ),
        default_tools=True,
        max_tool_rounds=5,
    ),
    "plan": AgentRole(
        id="plan",
        title="Plan",
        description="Architecture and step plans without side effects",
        system_prompt=(
            "You are SuperAI Plan agent (architect). "
            "Produce clear step-by-step plans, risks, and file touch list. "
            "Do NOT modify files. You may use read/grep/glob tools only. "
            "Respond with a structured plan (goals, steps, tests)."
        ),
        default_tools=True,
        max_tool_rounds=2,
    ),
    "ask": AgentRole(
        id="ask",
        title="Ask",
        description="Q&A about the codebase; read-only",
        system_prompt=(
            "You are SuperAI Ask agent. Answer questions about the codebase. "
            "Use read/grep/glob tools when needed. Never write or apply diffs."
        ),
        default_tools=True,
        max_tool_rounds=3,
    ),
}


def list_agents() -> List[Dict[str, str]]:
    return [
        {
            "id": a.id,
            "title": a.title,
            "description": a.description,
            "max_tool_rounds": str(a.max_tool_rounds),
        }
        for a in AGENT_ROLES.values()
    ]


def get_agent(agent_id: str) -> AgentRole:
    key = (agent_id or "build").strip().lower()
    if key in {"coder", "code", "implement", "agent"}:
        key = "build"
    if key in {"architect", "design"}:
        key = "plan"
    if key in {"chat", "qa", "question"}:
        key = "ask"
    return AGENT_ROLES.get(key) or AGENT_ROLES["build"]
