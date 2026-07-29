"""
CLI-level spend ceiling (V1-P1-3 / Phase 2).

``budget_precheck`` existed and was reachable, but ``src/cli/main.py`` never
called it — zero call sites across 8581 lines. Spend was gated only underneath,
inside ``ModelCaller``/``call_lifecycle``, which means a per-command ceiling
(``S132``) could not bind: by the time ``ModelCaller`` runs, the command name
is gone.

This module supplies the missing front door as **one seam**, not 35 hand-edits.
The set of commands to gate is *derived* from ``surface_inventory``'s
classification rather than kept as another hand-maintained list, so a spend
command added tomorrow is gated the day it is written.

Ownership rule, fixed by the plan and enforced here:

    The CLI layer may only PRE-CHECK. It must never RECORD.

``budget_precheck`` asks "could this plausibly exceed the ceiling?" and refuses
early. ``ModelCaller``/``call_lifecycle`` remain the sole owner of
``budget_record``, because only they know actual token usage. Nothing in this
module calls ``budget_record``.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence, Set

#: Set this to skip the CLI gate (the underlying ModelCaller gate still runs).
DISABLE_ENV = "SUPERAI_NO_CLI_BUDGET_GATE"

#: Commands that are spend-classified but must not be gated at the CLI door.
#: Each needs a reason, same rule as docs/SURFACE_EXEMPTIONS.md.
GATE_EXEMPT: Dict[str, str] = {
    # Long-lived interactive sessions: a single up-front estimate is
    # meaningless for a session whose cost accrues per turn, and each turn is
    # already gated at ModelCaller.
    "agent-tui": "interactive session; per-turn spend gated at ModelCaller",
    "split-tui": "interactive session; per-turn spend gated at ModelCaller",
    # Starts a server; requests are gated by web_app's own budget gate.
    "web": "server process; per-request gate lives in web_app",
}


@lru_cache(maxsize=1)
def spend_commands() -> Set[str]:
    """CLI command paths classified as spend, minus the gate exemptions."""
    try:
        from .surface_inventory import CLASS_SPEND, KIND_CLI, enumerate_cli_surfaces

        return {
            r["name"]
            for r in enumerate_cli_surfaces()
            if r["kind"] == KIND_CLI
            and r["classification"] == CLASS_SPEND
            and not r.get("shadowed")
            and r["name"] not in GATE_EXEMPT
        }
    except Exception:
        return set()


def command_path_from_argv(argv: Sequence[str]) -> Optional[str]:
    """
    Resolve ``argv`` to a known spend command path, longest match first.

    Matching on the joined path rather than ``ctx.invoked_subcommand`` is what
    makes nested commands work: ``check upgrades`` is a spend surface, and the
    root callback only ever sees ``check``.
    """
    tokens: List[str] = []
    for arg in argv:
        if arg.startswith("-"):
            continue
        tokens.append(arg)
        if len(tokens) >= 3:
            break
    known = spend_commands()
    # Longest first so "check upgrades" wins over a hypothetical "check".
    for size in range(min(len(tokens), 3), 0, -1):
        candidate = " ".join(tokens[:size])
        if candidate in known:
            return candidate
    return None


def gate_argv(
    argv: Sequence[str],
    *,
    model: Optional[str] = None,
    tokens: int = 500,
) -> Optional[Dict[str, Any]]:
    """
    Pre-check the budget for the command named in ``argv``.

    Returns ``None`` when the command is not a gated spend surface, when the
    gate is disabled, or when the budget allows the call. Returns a blocked
    contract envelope when the ceiling would be exceeded — the caller emits it
    and exits non-zero.

    Never records spend.
    """
    if os.getenv(DISABLE_ENV):
        return None

    command = command_path_from_argv(argv)
    if command is None:
        return None

    # Mock mode cannot spend, and dry-run must not be blocked on cost.
    try:
        from .public_surface import dry_run

        if dry_run():
            return None
    except Exception:
        pass
    try:
        from .config import Config

        if Config().use_mock:
            return None
    except Exception:
        pass

    from .spend_guard import budget_precheck

    block = budget_precheck(command_name=command, model=model, tokens=tokens)
    if block.get("blocked") or block.get("ok") is False:
        block["ok"] = False
        block["blocked"] = True
        block.setdefault("error_code", "budget")
        block["command"] = command
        return block
    return None


def gate_report() -> Dict[str, Any]:
    """Offline inventory of what the CLI gate covers."""
    gated = sorted(spend_commands())
    return {
        "ok": True,
        "product": "spend_gate",
        "gated_commands": gated,
        "gated_count": len(gated),
        "exempt": dict(GATE_EXEMPT),
        "exempt_count": len(GATE_EXEMPT),
        "disable_env": DISABLE_ENV,
        "note": (
            "CLI pre-checks only; budget_record stays owned by "
            "call_lifecycle so spend is never double-counted."
        ),
    }
