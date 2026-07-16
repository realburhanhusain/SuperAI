"""
SuperAI multi-agent coding runtime (product name: SuperAI — not a third-party fork).

Architecture:
  - multi-agent roles: build | plan | ask
  - full message session (parts: text, tool_call, tool_result)
  - permission-aware tool loop
  - multi-panel Rich TUI + optional HTTP API
  - model-agnostic via SuperAI ModelCaller / member catalog
"""

from .agents import AGENT_ROLES, get_agent, list_agents
from .runtime import AgentRuntime, RunResult
from .session import SuperAISessionStore, SessionState

# Back-compat aliases
OpenCodeSessionStore = SuperAISessionStore
AgentSessionStore = SuperAISessionStore

__all__ = [
    "AGENT_ROLES",
    "get_agent",
    "list_agents",
    "AgentRuntime",
    "RunResult",
    "SuperAISessionStore",
    "AgentSessionStore",
    "OpenCodeSessionStore",
    "SessionState",
]
