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
    if enabled:
        _force_utf8_stdout()


def _force_utf8_stdout() -> None:
    """
    JSON is UTF-8 by definition, so ``--json`` output must be.

    Without this, a payload containing a non-ASCII character silently produced
    malformed JSON on Windows. ``superai --json bandit`` reports a pipeline of
    ``preferences.bias_candidates → bandit.select → call``; that arrow is not
    encodable in cp1252, and on a stock console the write failed part-way and
    the envelope was re-emitted, so stdout held a truncated object followed by
    a second copy — 878 bytes instead of 652, and **exit code 0**. Any
    automation parsing that got a corrupt document with no error to catch.

    It never reproduced under investigation because every manual run set
    PYTHONIOENCODING=utf-8; only the sweep, which does not, saw real behaviour.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            if getattr(stream, "encoding", "").lower().replace("-", "") != "utf8":
                stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except Exception:
            # Not all streams are reconfigurable (pytest capture, pipes on some
            # platforms). Failing to upgrade the encoding must not break the CLI.
            pass


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


def contract_payload(
    data: Any,
    *,
    mock: Optional[bool] = None,
    ok: Optional[bool] = None,
) -> Any:
    """
    Apply the public contract to a payload **without** printing or exiting.

    ``emit_public`` both normalizes and emits. This is the normalize half, for
    callers that already own their own printing — chiefly
    :func:`contract_console`.

    Non-dict payloads pass through untouched: a list or a string printed as
    JSON is not a result envelope and wrapping it would change its type. The
    input dict is copied first, because ``apply_contract`` mutates in place and
    a display helper must not rewrite the caller's object.
    """
    if not isinstance(data, dict):
        return data
    from .error_codes import apply_error_taxonomy
    from .exit_codes import from_result
    from .result_contract import apply_contract

    if mock is None:
        try:
            from .config import Config

            mock = bool(Config().use_mock)
        except Exception:
            mock = None

    out = apply_contract(dict(data), mock=mock, dry_run=dry_run(), ok=ok)
    out = apply_error_taxonomy(out)
    out["live"] = not bool(out.get("mock"))
    out["honesty"] = "MOCK" if out.get("mock") else "LIVE"
    out.setdefault("exit_code", int(from_result(out)))
    return out


def contract_console(*args: Any, **kwargs: Any) -> Any:
    """
    A Rich ``Console`` whose ``print_json`` always emits a contracted envelope.

    ``src/cli/main.py`` prints results through ``console.print_json(data=...)``
    at 264 call sites. Rewriting each one would be 264 chances to change
    behaviour by hand; routing them through one console subclass is a single
    seam that cannot be partially applied, and a newly added
    ``console.print_json`` is contracted the day it is written rather than the
    day someone notices it was missed.

    Only ``data=`` payloads are contracted. A pre-serialized ``json=`` string is
    passed through, because re-parsing it to inject fields would silently
    reformat output the caller deliberately built.
    """
    from rich.console import Console

    class _ContractConsole(Console):
        def print_json(  # type: ignore[override]
            self,
            json: Optional[str] = None,
            *,
            data: Any = None,
            **kw: Any,
        ) -> None:
            if json is None and isinstance(data, dict):
                data = contract_payload(data)
            return super().print_json(json, data=data, **kw)

    return _ContractConsole(*args, **kwargs)


def render_public(
    result: Any,
    *,
    human_fn: Any = None,
    mock: Optional[bool] = None,
    ok: Optional[bool] = None,
    record_spend: bool = False,
    force_json: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    M079 helper: when global ``--json`` is on, always emit contract JSON;
    otherwise call ``human_fn(data)`` for Rich/text UX (or print JSON if no human_fn).
    """
    data = emit_public(
        result,
        mock=mock,
        ok=ok,
        record_spend=record_spend,
        print_json=False,  # decide below
    )
    use_json = json_mode() if force_json is None else bool(force_json)
    if use_json:
        try:
            from rich.console import Console

            Console().print_json(data=data)
        except Exception:
            print(json.dumps(data, default=str, indent=2))
        return data
    if callable(human_fn):
        try:
            human_fn(data)
        except Exception:
            print(json.dumps(data, default=str, indent=2))
        return data
    # No human renderer — still machine-friendly
    try:
        from rich.console import Console

        Console().print_json(data=data)
    except Exception:
        print(json.dumps(data, default=str, indent=2))
    return data


def budget_gate(
    *,
    estimated_usd: float = 0.1,
    tokens: int = 500,
    skip: bool = False,
    command_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """If live, check budget. If blocked, emit public error and exit."""
    if skip or dry_run():
        return None
    try:
        from .config import Config

        if Config().use_mock:
            return None
    except Exception:
        pass
    from .spend_guard import budget_precheck

    block = budget_precheck(estimated_usd=estimated_usd, tokens=tokens, command_name=command_name)
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

# Commands known to honor global --json via emit_public / render_public / print_json contract
JSON_CAPABLE_COMMANDS = sorted(
    set(TOP_30_COMMANDS)
    | {
        "status",
        "doctor",
        "dashboard",
        "learning",
        "learnings",
        "conflicts",
        "reflect",
        "spend-report",
        "smoke-preflight",
        "v6-status",
        "gates",
        "config",
        "history",
        "telemetry",
        "lang",
        "onboard",
        "recipes",
        "parked",
        "phase6-smoke",
        "project-budget",
        "contract-smoke",
        "context-pack",
        "json-surface",
    }
)


def json_surface_report() -> Dict[str, Any]:
    """Offline inventory for M079 automation coverage."""
    return {
        "ok": True,
        "product": "json_surface",
        "json_mode": json_mode(),
        "dry_run": dry_run(),
        "capable_commands": list(JSON_CAPABLE_COMMANDS),
        "count": len(JSON_CAPABLE_COMMANDS),
        "global_flag": "--json",
        "helper": "public_surface.render_public / emit_public",
        "message": (
            f"{len(JSON_CAPABLE_COMMANDS)} command families honor global --json "
            "via contract envelope (emit_public/render_public)."
        ),
    }


def registered_command_names(app: Any = None) -> set:
    """
    Names actually registered on the Typer app, including nested sub-apps.

    Derived from the live app via ``surface_inventory``; falls back to a shallow
    walk if that import is unavailable. Never seeded with the expected list —
    see the note in :func:`verify_top_commands_registered`.
    """
    if app is None:
        try:
            from scli.main import app as cli_app

            app = cli_app
        except Exception:
            return set()
    try:
        from .surface_inventory import enumerate_cli_surfaces

        return {r["name"] for r in enumerate_cli_surfaces(app=app)}
    except Exception:
        pass
    names: set = set()
    try:
        for cmd in getattr(app, "registered_commands", []) or []:
            if getattr(cmd, "name", None):
                names.add(str(cmd.name))
        for name, _cmd in (getattr(app, "commands", {}) or {}).items():
            names.add(str(name))
        for group in getattr(app, "registered_groups", []) or []:
            if getattr(group, "name", None):
                names.add(str(group.name))
    except Exception:
        pass
    return names


def verify_top_commands_registered(app: Any = None) -> Dict[str, Any]:
    """
    Check every TOP_30 command is really registered on the Typer app.

    Two defects were fixed here, and both are worth remembering because the
    same shapes recur elsewhere in this codebase:

    1. The pass condition was ``len(missing) <= 5`` — a completeness check with
       five slots of built-in slack. Anything layered on top inherited it.
    2. More seriously, ``missing`` was computed against
       ``known = top_commands() | TOP_30_COMMANDS | names``. Since ``expected``
       *is* ``TOP_30_COMMANDS``, every expected name was in ``known`` by
       construction and ``missing`` was unconditionally empty. The check could
       not fail — not for five missing commands, not for thirty.

    ``missing`` is now computed against registered names only.
    """
    try:
        from .contract_registry import smoke_contracts_offline

        names = registered_command_names(app)
        expected = list(TOP_30_COMMANDS)
        missing = sorted(c for c in expected if c not in names)
        smoke = smoke_contracts_offline()
        return {
            "ok": bool(smoke.get("ok")) and not missing,
            "expected": expected,
            "registered_count": len(names),
            "registered_sample": sorted(names)[:40],
            "missing": missing,
            "contract_smoke": smoke,
            "top_30_count": len(expected),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}
