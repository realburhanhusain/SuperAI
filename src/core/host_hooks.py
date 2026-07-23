"""
Host IDE / agent capture hooks (Phase 9+).

Maps external lifecycle events (Claude Code / Grok / Cursor style) into
SuperAI SessionCapture (P8) without requiring those hosts to open SuperAI DBs.

Events:
  UserPromptSubmit | user_prompt
  ToolResult | tool_result
  AssistantFinal | assistant_final
  PreCompact | precompact
  SessionEnd | session_end
  SessionStart | start

Honest: this is a **library + MCP/CLI adapter**. Installing into Claude/Grok
settings.json is documented, not automated.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from .memory_otel import memory_span
from .session_capture import (
    SessionCapture,
    get_active_capture,
    process_turn_stream,
    resolve_capture_level,
    set_active_capture,
)

# Host event name → capture hook
_EVENT_MAP = {
    "userpromptsubmit": "user_prompt",
    "user_prompt": "user_prompt",
    "user": "user_prompt",
    "toolresult": "tool_result",
    "tool_result": "tool_result",
    "posttooluse": "tool_result",
    "tool": "tool_result",
    "assistantfinal": "assistant_final",
    "assistant_final": "assistant_final",
    "assistant": "assistant_final",
    "stop": "assistant_final",
    "precompact": "precompact",
    "sessionend": "session_end",
    "session_end": "session_end",
    "sessionstart": "start",
    "session_start": "start",
    "start": "start",
}


def normalize_event(event: str) -> str:
    key = (event or "").strip().lower().replace("-", "").replace(" ", "")
    # also allow underscores already lower
    key2 = (event or "").strip().lower().replace("-", "_")
    return _EVENT_MAP.get(key) or _EVENT_MAP.get(key2) or key2 or "user_prompt"


def emit_host_event(
    event: str,
    *,
    content: Optional[str] = None,
    tool: Optional[str] = None,
    result: Any = None,
    session_id: Optional[str] = None,
    dataset_id: Optional[str] = None,
    level: Optional[str] = None,
    source: str = "host_hook",
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Emit one host lifecycle event into SuperAI session capture.
    """
    hook = normalize_event(event)
    lvl = resolve_capture_level(level or os.getenv("SUPERAI_CAPTURE_LEVEL"))

    with memory_span(
        "host_hook.emit",
        attributes={"hook": hook, "operation": "host_hook", "level": lvl},
    ):
        if hook == "start":
            cap = SessionCapture.start(
                session_id=session_id,
                title=str((meta or {}).get("title") or "host session"),
                dataset_id=dataset_id,
                source=source,
                level=lvl,
            )
            set_active_capture(cap)
            return {
                "ok": True,
                "product": "host_hooks",
                "hook": "start",
                "session_id": cap.session_id,
                "level": cap.level,
                "message": f"Host session started {cap.session_id}",
            }

        cap = get_active_capture()
        if cap is None or (session_id and cap.session_id != session_id):
            cap = SessionCapture.start(
                session_id=session_id,
                dataset_id=dataset_id,
                source=source,
                level=lvl,
            )
            set_active_capture(cap)

        if hook in {"tool_result", "tool"}:
            out = cap.tool_result(
                tool or (meta or {}).get("tool") or "tool",
                result if result is not None else {"ok": True, "summary": content or ""},
                meta=meta,
            )
        else:
            out = cap.capture(hook, content, tool_name=tool, meta=meta)

        out = dict(out)
        out["product"] = "host_hooks"
        out["hook"] = hook
        out["session_id"] = cap.session_id
        out["level"] = cap.level
        out.setdefault("message", f"Host hook {hook} → session {cap.session_id}")
        return out


def emit_host_batch(
    events: List[Dict[str, Any]],
    *,
    session_id: Optional[str] = None,
    dataset_id: Optional[str] = None,
    level: Optional[str] = None,
    source: str = "host_hook_batch",
    auto_end: bool = True,
) -> Dict[str, Any]:
    """Batch host events → process_turn_stream after normalization."""
    turns: List[Dict[str, Any]] = []
    for ev in events or []:
        if not isinstance(ev, dict):
            continue
        hook = normalize_event(str(ev.get("event") or ev.get("hook") or "user_prompt"))
        if hook == "start":
            continue
        turn = {
            "hook": hook,
            "content": ev.get("content") or ev.get("text") or ev.get("message"),
            "tool": ev.get("tool") or ev.get("tool_name"),
            "result": ev.get("result"),
            "pinned": ev.get("pinned"),
            "meta": ev.get("meta"),
        }
        turns.append(turn)
    with memory_span(
        "host_hook.batch",
        attributes={"operation": "host_hook", "count": len(turns)},
    ):
        return process_turn_stream(
            turns,
            session_id=session_id,
            dataset_id=dataset_id,
            level=level,
            source=source,
            auto_end=auto_end,
        )


def install_checklist(host: str = "claude") -> Dict[str, Any]:
    """
    P9-R6: guided checklist for host hook install (still no silent rewrite).
    """
    snip = hook_install_snippet(host)
    host_l = (host or "claude").lower()
    steps = [
        {
            "step": 1,
            "title": "Install SuperAI CLI on PATH",
            "check": "superai --help exits 0",
        },
        {
            "step": 2,
            "title": "Confirm MCP server",
            "check": "superai mcp-serve starts (stdio) or host MCP config points at it",
        },
        {
            "step": 3,
            "title": "Set capture level",
            "check": "SUPERAI_CAPTURE_LEVEL=session (or session+promote)",
        },
        {
            "step": 4,
            "title": "Copy install snippet into host settings",
            "check": f"Manual paste only — never auto-written for {host_l}",
            "snippet_keys": [k for k in snip.keys() if k not in {"ok", "product", "message", "host"}],
        },
        {
            "step": 5,
            "title": "Smoke emit",
            "check": 'superai host-hook emit user_prompt -c "hello" --session smoke1',
        },
        {
            "step": 6,
            "title": "Verify session buffer",
            "check": "superai memory-session list (or MCP superai_host_hook)",
        },
    ]
    return {
        "ok": True,
        "product": "host_hook_checklist",
        "host": host_l,
        "auto_write_host_config": False,
        "steps": steps,
        "snippet": snip,
        "message": (
            f"Host-hook checklist for {host_l}: {len(steps)} steps "
            "(manual install only; no silent settings rewrite)"
        ),
    }


def hook_install_snippet(host: str = "claude") -> Dict[str, Any]:
    """
    Return documented install snippets for hosts (not applied automatically).
    """
    host_l = (host or "claude").lower()
    mcp = {
        "mcpServers": {
            "superai": {
                "command": "superai",
                "args": ["mcp-serve"],
            }
        }
    }
    # Claude-style hooks calling CLI
    claude_hooks = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "type": "command",
                    "command": (
                        "superai host-hook emit user_prompt "
                        "--content \"$PROMPT\" --session \"$SESSION_ID\""
                    ),
                }
            ],
            "SessionEnd": [
                {
                    "type": "command",
                    "command": "superai host-hook emit session_end --session \"$SESSION_ID\"",
                }
            ],
        }
    }
    grok_note = (
        "Call MCP tool superai_host_hook with action=emit, or CLI "
        "`superai host-hook emit ...` from Stop/PreCompact procedures."
    )
    return {
        "ok": True,
        "product": "host_hooks_install",
        "host": host_l,
        "mcp_snippet": mcp,
        "claude_hooks_snippet": claude_hooks if host_l in {"claude", "claude-code"} else None,
        "grok_note": grok_note if host_l in {"grok", "xai"} else None,
        "message": (
            "Install snippets only — SuperAI does not rewrite host settings.json. "
            "Wire MCP + optional hooks manually."
        ),
        "honesty": "manual_install_required",
    }
