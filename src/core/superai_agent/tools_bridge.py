"""
Tool bridge for SuperAI agent runtime (workspace-jailed + permission).
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Set

from ..agent_tools import list_tools as base_list_tools
from ..agent_tools import run_tool
from ..permission_mode import force_dry_run, normalize_mode, should_auto_approve


# plan agent: read-only tools
READ_ONLY = {"read", "grep", "glob"}
# build agent: all + bash
ALL_TOOLS = set(base_list_tools()) | {"bash", "shell"}

# Tools that mutate host state and therefore require approval.
SIDE_EFFECT_TOOLS = {"write", "diff_apply", "bash", "shell"}


def allowed_tools_for_agent(agent_id: str) -> Set[str]:
    a = (agent_id or "build").lower()
    if a in {"plan", "ask"}:
        return set(READ_ONLY)
    return set(ALL_TOOLS)


def _unattended_side_effects_allowed() -> bool:
    """Explicit opt-out for headless callers that cannot supply an approver."""
    return (os.getenv("SUPERAI_ALLOW_UNATTENDED_SIDE_EFFECTS") or "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def tool_bash(
    command: str,
    *,
    dry_run: bool = False,
    timeout: float = 60.0,
    permission_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """Run a shell command through the hardened os_shell policy engine.

    Delegates to core.os_shell.run_shell rather than calling subprocess
    directly, so the agent shell tool inherits the full policy:
      - regex deny-list for catastrophic commands (rm -rf /, mkfs, dd if=,
        fork bombs, curl|sh, Invoke-Expression(...Download), shutdown, ...)
      - workspace cwd jail (override: SUPERAI_SHELL_ALLOW_ANY_CWD=1)
      - permission-mode aware dry-run
      - timeout enforcement
      - side-effect audit trail via record_side_effect

    Previously this function ran subprocess.run(cmd, shell=True) behind a
    naive substring blocklist, which was bypassable by trivial whitespace
    or flag reordering (e.g. "rm  -rf /", "rm -fr /") and emitted no audit
    record. Its docstring also incorrectly claimed it avoided shell=True.
    """
    from ..os_shell import run_shell

    cmd = (command or "").strip()
    if not cmd:
        return {"ok": False, "error": "empty_command"}

    # An explicit dry_run forces dry; otherwise let run_shell derive it from
    # the permission mode so "plan" mode still cannot execute.
    return run_shell(
        cmd,
        timeout=timeout,
        dry_run=True if dry_run else None,
        permission_mode=permission_mode,
    )


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
    approve_callback(name, args) -> bool gates side effects.

    Fails closed: if a side-effecting tool is requested and no approver is
    available, the call is denied unless the permission mode auto-approves
    (auto/yolo) or SUPERAI_ALLOW_UNATTENDED_SIDE_EFFECTS=1 is set.
    """
    n = (name or "").lower().strip()
    args = dict(arguments or {})
    allowed = allowed_tools_for_agent(agent_id)

    # ALL_TOOLS already contains bash/shell and READ_ONLY intentionally does
    # not, so a single membership test is sufficient and unambiguous.
    if n not in allowed:
        return {
            "ok": False,
            "error": "tool_not_allowed_for_agent",
            "tool": n,
            "agent": agent_id,
        }

    mode = normalize_mode(permission_mode)
    dry = force_dry_run(mode)
    side_effect = n in SIDE_EFFECT_TOOLS

    # Gate every non-dry side effect the mode does not auto-approve, not just
    # mode == "ask".
    if side_effect and not dry and not should_auto_approve(mode):
        if approve_callback is not None:
            try:
                ok = bool(approve_callback(n, args))
            except Exception:
                ok = False
            denial = "user_denied"
        else:
            ok = _unattended_side_effects_allowed()
            denial = "no_approver_available"
        if not ok:
            return {
                "ok": False,
                "error": denial,
                "tool": n,
                "dry_run": True,
                "permission_mode": mode,
            }

    # V6 N227 hooks
    try:
        from ..hooks import run_pre

        blocked = run_pre(n, args)
        if isinstance(blocked, dict):
            return blocked
    except Exception:
        pass

    if n in {"bash", "shell"}:
        res = tool_bash(
            str(args.get("command") or args.get("cmd") or ""),
            dry_run=dry,
            permission_mode=mode,
        )
    else:
        res = run_tool(n, permission_mode=mode, dry_run=dry, **args)

    try:
        from ..hooks import run_post as _post

        _post(n, args, res)
    except Exception:
        pass
    return res


def catalog() -> List[Dict[str, str]]:
    return [
        {"name": "read", "desc": "Read a file in workspace"},
        {"name": "write", "desc": "Write a file (permission-aware)"},
        {"name": "grep", "desc": "Search file contents"},
        {"name": "glob", "desc": "Glob paths"},
        {"name": "diff_apply", "desc": "Apply unified diff"},
        {"name": "bash", "desc": "Run shell in workspace (build agent)"},
    ]
