"""
Contract coverage for top public commands (V6 M008/M090).
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

# Top public command families that must return result contracts
TOP_COMMANDS: List[str] = [
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
    "tenant-import",
    "models-refresh-openrouter",
    "plugin-catalog",
    "host-tools",
    "v6-status",
    "ci-why",
    "gates",
    "todos",
    "recipes",
    "macros",
]


def top_commands() -> List[str]:
    return list(TOP_COMMANDS)


def ensure_list(results: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate a list of public results for contract keys."""
    from .result_contract import REQUIRED_KEYS

    bad = []
    for i, r in enumerate(results):
        if not isinstance(r, dict):
            bad.append({"index": i, "error": "not_dict"})
            continue
        missing = [k for k in REQUIRED_KEYS if k not in r]
        if missing:
            bad.append({"index": i, "missing": missing, "keys": list(r.keys())[:20]})
    return {
        "ok": len(bad) == 0,
        "checked": len(results),
        "failures": bad,
        "required": list(REQUIRED_KEYS),
        "top_commands": top_commands(),
    }


def smoke_contracts_offline() -> Dict[str, Any]:
    """Offline contract checks for major APIs (no live providers)."""
    from .public_api import wrap_public_result
    from .spend_guard import ensure_public_result

    samples = [
        ensure_public_result({"ok": True, "response": "x"}, mock=True, ok=True),
        wrap_public_result({"ok": True, "status": "success"}, mock=True, record_spend=False),
        ensure_public_result(
            {"ok": False, "error": "budget", "error_code": "budget"}, ok=False
        ),
    ]
    # simulate board/council envelopes
    samples.append(
        ensure_public_result(
            {
                "ok": True,
                "opinions": [{"cli": "a", "verdict": "approve"}],
                "members": ["a"],
            },
            mock=True,
            members=["a"],
        )
    )
    return ensure_list(samples)
