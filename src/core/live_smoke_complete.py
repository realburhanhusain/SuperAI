"""
Phase 6 completion for smoke (M089) — runs live only with credentials;
never claims pass without real results.
"""

from __future__ import annotations

from typing import Any, Dict

from .provider_smoke import available_smoke_targets, run_provider_smoke, smoke_harness
from .public_api import wrap_public_result
from .spend_guard import budget_precheck


def run_phase6_smoke(*, allow_live: bool = False) -> Dict[str, Any]:
    """
    Full Phase 6 verification path:
    1) harness inventory
    2) optional live smoke if allow_live and credentials exist
    """
    harness = smoke_harness(allow_live=False)
    preflight = None
    try:
        from .smoke_preflight import smoke_preflight

        preflight = smoke_preflight(include_readiness=True)
    except Exception as e:
        preflight = {"ok": False, "error": str(e)[:200]}

    live_result = None
    live_attempted = False
    if allow_live:
        targets = available_smoke_targets()
        if not targets:
            live_result = {
                "ok": True,
                "live_attempted": False,
                "live_passed": False,
                "message": "allow_live set but no credentials/Ollama — not claiming pass",
            }
        else:
            block = budget_precheck(estimated_usd=0.5, tokens=2000)
            if block.get("blocked"):
                return wrap_public_result(block, ok=False, record_spend=False)
            live_attempted = True
            live_result = run_provider_smoke(use_mock=False)
            live_result["live_attempted"] = True
            live_result["live_passed"] = (
                int(live_result.get("passed") or 0) > 0
                and int(live_result.get("failed") or 0) == 0
            )

    out = {
        "ok": True,
        "phase": 6,
        "harness": harness,
        "preflight": preflight,
        "live": live_result,
        "live_attempted": live_attempted,
        "live_passed": bool((live_result or {}).get("live_passed")),
        "phase6_complete_code": True,
        "phase6_complete_host": bool((live_result or {}).get("live_passed")),
        "message": (
            "Phase 6 code path complete. Host complete only if live_passed=true "
            "with real provider results."
        ),
    }
    return wrap_public_result(out, mock=not live_attempted, ok=True, record_spend=False)
