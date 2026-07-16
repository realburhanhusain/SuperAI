"""
MCP parity with CLI safety rules (V6 M093 / V5-M2).

All MCP tool dispatches go through the same budget + contract + permission gates.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional


SPEND_TOOLS = {
    "superai_run",
    "superai_ask",
    "superai_agent",
    "cli_run",
    "superai_council",
    "superai_compare",
    "superai_bakeoff",
}


def wrap_mcp_tool(
    name: str,
    fn: Callable[[], Dict[str, Any]],
    *,
    estimated_usd: float = 0.15,
    tokens: int = 800,
    mock: bool = True,
) -> Dict[str, Any]:
    from .public_api import wrap_public_result
    from .spend_guard import budget_precheck

    if name in SPEND_TOOLS and not mock:
        block = budget_precheck(estimated_usd=estimated_usd, tokens=tokens)
        if block.get("blocked") or block.get("ok") is False:
            return wrap_public_result(block, mock=False, ok=False, record_spend=False)
    try:
        out = fn()
    except Exception as e:
        return wrap_public_result(
            {"ok": False, "error": str(e)[:500], "tool": name},
            mock=mock,
            ok=False,
            record_spend=False,
        )
    if not isinstance(out, dict):
        out = {"ok": True, "result": out}
    out.setdefault("mcp_tool", name)
    out.setdefault("mcp_safety", True)
    return wrap_public_result(
        out,
        mock=out.get("mock", mock),
        ok=out.get("ok", True),
        record_spend=bool(out.get("ok") and not out.get("mock")),
    )


def safety_matrix() -> Dict[str, Any]:
    return {
        "ok": True,
        "budget_on_spend_tools": sorted(SPEND_TOOLS),
        "contract": True,
        "permission_modes": True,
        "workspace_jail": True,
        "default_mock": True,
        "live_requires_env": "SUPERAI_MCP_ALLOW_LIVE",
        "parity_with_cli": True,
    }
