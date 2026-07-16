"""
Deprecated alias package — use ``core.super_agent`` (product name: SuperAI).

Kept so older imports/docs keep working.
"""

from core.super_agent import *  # noqa: F403
from core.super_agent import AgentSessionStore as OpenCodeSessionStore
from core.super_agent.tui import run_super_agent_tui as run_opencode_tui

__all__ = [
    "AGENT_ROLES",
    "get_agent",
    "list_agents",
    "AgentRuntime",
    "RunResult",
    "AgentSessionStore",
    "OpenCodeSessionStore",
    "SessionState",
    "run_opencode_tui",
]
