"""
SuperAI OpenCode-style agent (inspired by OpenCode patterns, not a fork).

Architecture:
  - multi-agent roles: build | plan | ask
  - full message session (parts: text, tool_call, tool_result)
  - permission-aware tool loop
  - multi-panel Rich TUI + optional HTTP API
  - model-agnostic via SuperAI ModelCaller / member catalog
"""

from .agents import AGENT_ROLES, get_agent, list_agents
from .runtime import AgentRuntime, RunResult
from .session import OpenCodeSessionStore, SessionState

__all__ = [
    "AGENT_ROLES",
    "get_agent",
    "list_agents",
    "AgentRuntime",
    "RunResult",
    "OpenCodeSessionStore",
    "SessionState",
]
