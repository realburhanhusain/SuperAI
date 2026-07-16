"""
Deprecated alias package — use ``core.superai_agent`` (product name: SuperAI).
"""

from core.superai_agent import *  # noqa: F403
from core.superai_agent import SuperAISessionStore as OpenCodeSessionStore
from core.superai_agent.tui import run_superai_agent_tui as run_opencode_tui

__all__ = [
    "AGENT_ROLES",
    "get_agent",
    "list_agents",
    "AgentRuntime",
    "RunResult",
    "SuperAISessionStore",
    "OpenCodeSessionStore",
    "SessionState",
    "run_opencode_tui",
]
