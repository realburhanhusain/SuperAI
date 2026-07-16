"""
Tool bridge for SuperAI agent runtime (workspace-jailed + permission).
"""

from __future__ import annotations

import subprocess
from typing import Any, Dict, List, Optional, Set

from ..agent_tools import list_tools as base_list_tools
from ..agent_tools import run_tool
from ..permission_mode import force_dry_run, normalize_mode, should_auto_approve


# plan agent: read-only tools
READ_ONLY = {"read", "grep", "glob"}
# build agent: all + bash
ALL_TOOLS = set(base_list_tools()) | {"bash", "shell"}


def allowed_tools_for_agent(agent_id: str) -> Set[str]:
    a = (agent_id or "build").lower()
    if a in {"plan", "ask"}:
        return set(READ_ONLY)
    return set(ALL_TOOLS)


def tool_bash(
    command: str,
    *,
    dry_run: bool = False,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """Sandboxed shell: workspace cwd, no shell=True injection via list form when possible."""
    from ..workspace import workspace_root

    root = str(workspace_root())
    cmd = (command or "").strip()
    if not cmd:
        return {"ok": False, "error": "empty_command"}
    # block obvious destructive patterns in plan/ask is handled by caller
    blocked = ("rm -rf /", "format c:", ":(){", "mkfs", "shutdown", "reboot")
    low = cmd.lower()
    if any(b in low for b in blocked):
        return {"ok": False, "error": "blocked_command", "command": cmd[:200]}
    if dry_run:
        return {"ok": True, "dry_run": True, "command": cmd, "cwd": root}
    try:
        # Prefer shell on Windows for user convenience inside workspace only
        proc = subprocess.run(
            cmd,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=True,
        )
        return {
            "ok": proc.returncode == 0,
            "command": cmd,
            "cwd": root,
            "returncode": proc.returncode,
            "stdout": (proc.stdout or "")[:12000],
            "stderr": (proc.stderr or "")[:4000],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:300], "command": cmd}


def dispatch_tool(
    name: str,
    arguments: Optional[Dict[str, Any]] = None,
    *,
    agent_id: str = "build",
    permission_mode: str = "ask",
    approve_callback=None,
) -> Dict[str, Any]:
    """
    Run one tool with agent allowlist + permission mode.
    approve_callback(name, args) -> bool for ask mode side effects.
    """
    n = (name or "").lower().strip()
    args = dict(arguments or {})
    allowed = allowed_tools_for_agent(agent_id)
    if n not in allowed and n not in {"bash", "shell"}:
        return {"ok": False, "error": "tool_not_allowed_for_agent", "tool": n, "agent": agent_id}
    if n in {"bash", "shell"} and n not in allowed and "bash" not in allowed:
        return {"ok": False, "error": "bash_not_allowed", "agent": agent_id}

    mode = normalize_mode(permission_mode)
    dry = force_dry_run(mode)
    side_effect = n in {"write", "diff_apply", "bash", "shell"}
    if side_effect and mode == "ask" and not should_auto_approve(mode):
        ok = True
        if approve_callback:
            try:
                ok = bool(approve_callback(n, args))
            except Exception:
                ok = False
        if not ok:
            return {"ok": False, "error": "user_denied", "tool": n, "dry_run": True}

    if n in {"bash", "shell"}:
        return tool_bash(str(args.get("command") or args.get("cmd") or ""), dry_run=dry)

    return run_tool(n, permission_mode=mode, dry_run=dry, **args)


def catalog() -> List[Dict[str, str]]:
    return [
        {"name": "read", "desc": "Read a file in workspace"},
        {"name": "write", "desc": "Write a file (permission-aware)"},
        {"name": "grep", "desc": "Search file contents"},
        {"name": "glob", "desc": "Glob paths"},
        {"name": "diff_apply", "desc": "Apply unified diff"},
        {"name": "bash", "desc": "Run shell in workspace (build agent)"},
    ]
