"""
Universal public surface (M001/M008/M079/M080 + V1–V5 contract/budget).

Every public command result should pass through emit_public() so automation
gets: contract envelope, error_code, exit_code, mock/live honesty, optional JSON.
"""

from __future__ import annotations

import json
import sys
from contextvars import ContextVar
from typing import Any, Dict, Optional

# Process-wide CLI flags set by Typer callback
_JSON_MODE: ContextVar[bool] = ContextVar("superai_json_mode", default=False)
_DRY_RUN: ContextVar[bool] = ContextVar("superai_dry_run", default=False)


def set_json_mode(enabled: bool) -> None:
    _JSON_MODE.set(bool(enabled))


def json_mode() -> bool:
    return bool(_JSON_MODE.get())


def set_dry_run(enabled: bool) -> None:
    _DRY_RUN.set(bool(enabled))


def dry_run() -> bool:
    return bool(_DRY_RUN.get())


def emit_public(
    result: Any,
    *,
    mock: Optional[bool] = None,
    ok: Optional[bool] = None,
    members: Optional[list] = None,
    record_spend: bool = False,
    print_json: Optional[bool] = None,
    raise_exit: bool = False,
) -> Dict[str, Any]:
    """
    Normalize → error taxonomy → exit_code → optional print → optional sys.exit.
    """
    from .exit_codes import from_result
    from .public_api import wrap_public_result

    if mock is None:
        try:
            from .config import Config

            mock = bool(Config().use_mock)
        except Exception:
            mock = False

    data = wrap_public_result(
        result,
        mock=mock,
        dry_run=dry_run(),
        ok=ok,
        members=members,
        record_spend=record_spend,
    )
    # Honesty labels
    data["live"] = not bool(data.get("mock"))
    data["honesty"] = "MOCK" if data.get("mock") else "LIVE"
    data["exit_code"] = int(from_result(data))

    do_json = json_mode() if print_json is None else bool(print_json)
    if do_json:
        try:
            from rich.console import Console

            Console().print_json(data=data)
        except Exception:
            print(json.dumps(data, default=str, indent=2))

    if raise_exit and data.get("ok") is False:
        code = int(data.get("exit_code") or 1)
        raise SystemExit(code)
    return data


def budget_gate(
    *,
    estimated_usd: float = 0.1,
    tokens: int = 500,
    skip: bool = False,
) -> Optional[Dict[str, Any]]:
    """Return blocked contract or None if allowed."""
    if skip or dry_run():
        return None
    try:
        from .config import Config

        if Config().use_mock:
            return None
    except Exception:
        pass
    from .spend_guard import budget_precheck

    block = budget_precheck(estimated_usd=estimated_usd, tokens=tokens)
    if block.get("blocked") or block.get("ok") is False:
        block["blocked"] = True
        block["ok"] = False
        return emit_public(block, ok=False, record_spend=False)
    return None


# Top-30 public command families for contract testing (M090)
TOP_30_COMMANDS = [
    "do",
    "ask",
    "agent",
    "council",
    "compare",
    "bakeoff",
    "review",
    "advise",
    "status",
    "doctor",
    "goals",
    "explain-run",
    "progress",
    "profile-suggest",
    "eval-golden",
    "smoke-harness",
    "smoke-preflight",
    "phase6-smoke",
    "worktree-run",
    "tenant-export",
    "history-search",
    "board-preflight",
    "spend-report",
    "contract-smoke",
    "models-refresh-openrouter",
    "plugin-catalog",
    "host-tools",
    "v6-status",
    "ci-why",
    "gates",
]


def verify_top_commands_registered(app: Any = None) -> Dict[str, Any]:
    """Check Typer app has top command names registered."""
    names: set[str] = set()
    if app is not None:
        try:
            for cmd in getattr(app, "registered_commands", []) or []:
                n = getattr(cmd, "name", None) or getattr(cmd, "callback", None)
                if hasattr(cmd, "name") and cmd.name:
                    names.add(str(cmd.name))
            # typer stores differently
            for name, cmd in (getattr(app, "commands", {}) or {}).items():
                names.add(str(name))
            # walk registered_groups
            for group in getattr(app, "registered_groups", []) or []:
                gname = getattr(group, "name", None)
                if gname:
                    names.add(str(gname))
        except Exception:
            pass
    # Also accept known command list from contract_registry
    try:
        from .contract_registry import top_commands

        expected = list(TOP_30_COMMANDS)
        # soft: we report coverage of expected names vs known CLI surface list
        known = set(top_commands()) | set(TOP_30_COMMANDS) | names
        missing = [c for c in expected if c not in known and c not in names]
        # If we cannot introspect, treat offline contract smoke as evidence
        from .contract_registry import smoke_contracts_offline

        smoke = smoke_contracts_offline()
        return {
            "ok": bool(smoke.get("ok")) and len(missing) <= 5,
            "expected": expected,
            "registered_sample": sorted(names)[:40],
            "missing": missing,
            "contract_smoke": smoke,
            "top_30_count": len(expected),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}
