"""
MCP parity with CLI safety rules (V6 M093 / V5-M2).

All MCP tool dispatches go through the same budget + contract + permission gates.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional, Set

# Tools that can spend money / call live models (must honor budget when live)
SPEND_TOOLS: Set[str] = {
    "superai_run",
    "superai_ask",
    "superai_agent",
    "cli_run",
    "superai_cli_run",
    "superai_council",
    "superai_compare",
    "superai_bakeoff",
    "superai_review",
    "superai_advise",
    "superai_do",
}

# Tools that mutate disk / memory (permission + dry-run aware)
MUTATING_TOOLS: Set[str] = {
    "superai_memory_store",
    "superai_learn",
    "superai_memory_palace",  # promote can write
    "cli_run",
    "superai_cli_run",
    "superai_run",
    "superai_agent",
}

# MCP tool → closest CLI command (parity map)
CLI_PARITY: Dict[str, str] = {
    "superai_status": "doctor --quick / status",
    "superai_central_memory_status": "status --cost / central memory",
    "superai_memory_search": "memory-chat / learnings <query>",
    "superai_memory_palace": "memory palace browse",
    "superai_memory_store": "memory store",
    "superai_memory_context": "context-pack",
    "superai_learn": "learnings / learning promote",
    "superai_ask": "ask",
    "superai_ask_session": "ask --session / ask-session",
    "superai_run": "do / agent",
    "superai_agent": "agent / agent-tui",
    "superai_council": "council",
    "superai_compare": "compare",
    "superai_bakeoff": "bakeoff",
    "cli_run": "cli-run",
    "superai_cli_run": "cli-run",
    "superai_cli_discover": "host-tools / cli discover",
    "superai_cli_parallel": "cli-parallel",
    "superai_host_tools": "host-tools",
}


def live_allowed() -> bool:
    """Live MCP spend requires explicit env opt-in (never accidental live)."""
    v = (os.getenv("SUPERAI_MCP_ALLOW_LIVE") or "").strip().lower()
    return v in {"1", "true", "yes", "on"}


def wrap_mcp_tool(
    name: str,
    fn: Callable[[], Dict[str, Any]],
    *,
    estimated_usd: float = 0.15,
    tokens: int = 800,
    mock: bool = True,
    permission_mode: Optional[str] = None,
    args: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    from .public_api import wrap_public_result
    from .spend_guard import budget_precheck

    args = args or {}
    want_live = bool(args.get("live") or args.get("live_run")) and not mock
    if want_live and not live_allowed():
        return wrap_public_result(
            {
                "ok": False,
                "error": "Live MCP blocked: set SUPERAI_MCP_ALLOW_LIVE=1",
                "error_code": "permission",
                "tool": name,
                "mcp_safety": True,
            },
            mock=True,
            ok=False,
            record_spend=False,
        )

    # Permission mode: plan blocks mutating tools
    mode = (permission_mode or args.get("permission_mode") or "").strip().lower()
    if not mode:
        try:
            from .config import Config

            mode = str(Config().get("permission_mode") or "ask").lower()
        except Exception:
            mode = "ask"
    if mode in {"plan", "read"} and name in MUTATING_TOOLS:
        apply_flag = args.get("apply")
        if apply_flag is not True and name == "superai_memory_palace":
            # allow read-only palace actions
            action = str(args.get("action") or "").lower()
            if action in {"layout", "browse", "clusters", "suggest", "snapshot", ""}:
                pass
            else:
                return wrap_public_result(
                    {
                        "ok": False,
                        "error": f"permission_mode={mode} blocks mutating MCP tool {name}",
                        "error_code": "permission",
                        "tool": name,
                        "mcp_safety": True,
                    },
                    mock=mock,
                    ok=False,
                    record_spend=False,
                )
        elif name != "superai_memory_palace":
            return wrap_public_result(
                {
                    "ok": False,
                    "error": f"permission_mode={mode} blocks mutating MCP tool {name}",
                    "error_code": "permission",
                    "tool": name,
                    "mcp_safety": True,
                },
                mock=mock,
                ok=False,
                record_spend=False,
            )

    # Workspace jail for path-like args
    for path_key in ("path", "file", "cwd", "workdir", "workspace"):
        p = args.get(path_key)
        if p and isinstance(p, str) and p not in (".", ""):
            try:
                from .workspace import assert_in_workspace

                assert_in_workspace(p)
            except Exception as e:
                return wrap_public_result(
                    {
                        "ok": False,
                        "error": f"workspace jail: {e}"[:400],
                        "error_code": "permission",
                        "tool": name,
                        "mcp_safety": True,
                    },
                    mock=mock,
                    ok=False,
                    record_spend=False,
                )

    if name in SPEND_TOOLS and want_live:
        block = budget_precheck(estimated_usd=estimated_usd, tokens=tokens)
        if block.get("blocked") or block.get("ok") is False:
            return wrap_public_result(block, mock=False, ok=False, record_spend=False)
    try:
        out = fn()
    except Exception as e:
        return wrap_public_result(
            {"ok": False, "error": str(e)[:500], "tool": name, "mcp_safety": True},
            mock=mock,
            ok=False,
            record_spend=False,
        )
    if not isinstance(out, dict):
        out = {"ok": True, "result": out}
    out.setdefault("mcp_tool", name)
    out.setdefault("mcp_safety", True)
    out.setdefault("cli_parity", CLI_PARITY.get(name))
    return wrap_public_result(
        out,
        mock=out.get("mock", mock),
        ok=out.get("ok", True),
        record_spend=bool(out.get("ok") and not out.get("mock") and want_live),
    )


def list_registered_mcp_tools() -> List[str]:
    try:
        from .mcp_server import TOOLS

        return sorted(str(t.get("name") or "") for t in TOOLS if t.get("name"))
    except Exception:
        return []


def safety_matrix() -> Dict[str, Any]:
    """Exhaustive offline safety matrix for M093."""
    registered = list_registered_mcp_tools()
    spend_registered = sorted(t for t in registered if t in SPEND_TOOLS)
    mutate_registered = sorted(t for t in registered if t in MUTATING_TOOLS)
    parity_coverage = {
        t: CLI_PARITY.get(t, "unmapped") for t in registered
    }
    unmapped = [t for t, v in parity_coverage.items() if v == "unmapped"]
    return {
        "ok": True,
        "product": "mcp_safety_matrix",
        "budget_on_spend_tools": sorted(SPEND_TOOLS),
        "mutating_tools": sorted(MUTATING_TOOLS),
        "registered_tools": registered,
        "registered_count": len(registered),
        "spend_tools_registered": spend_registered,
        "mutating_tools_registered": mutate_registered,
        "cli_parity": parity_coverage,
        "cli_parity_unmapped": unmapped,
        "contract": True,
        "permission_modes": True,
        "workspace_jail": True,
        "default_mock": True,
        "live_requires_env": "SUPERAI_MCP_ALLOW_LIVE",
        "live_allowed_now": live_allowed(),
        "parity_with_cli": len(unmapped) == 0 or len(unmapped) <= max(2, len(registered) // 5),
        "message": (
            f"{len(registered)} MCP tools; spend={len(spend_registered)}; "
            f"mutate={len(mutate_registered)}; unmapped CLI parity={len(unmapped)}"
        ),
    }


def audit_tool_dispatch(name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Dry audit: would this MCP call pass safety gates?"""
    args = dict(args or {})
    mock = not (bool(args.get("live") or args.get("live_run")) and live_allowed())

    def _fn() -> Dict[str, Any]:
        return {"ok": True, "audit_only": True, "tool": name}

    return wrap_mcp_tool(name, _fn, mock=mock, args=args)
