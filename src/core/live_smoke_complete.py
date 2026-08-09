"""
Phase 6 / M089 live multi-provider smoke — runs live only with credentials;
never claims pass without real results.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .provider_smoke import available_smoke_targets, run_provider_smoke, smoke_harness
from .public_api import wrap_public_result
from .spend_guard import budget_precheck


def _env_keys_present() -> Dict[str, bool]:
    keys = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "CLAUDE_API_KEY",
        "DEEPSEEK_API_KEY",
        "XAI_API_KEY",
        "GOOGLE_API_KEY",
        "GROQ_API_KEY",
    ]
    return {k: bool(os.getenv(k)) for k in keys}


def run_stream_smoke_sample(
    *,
    use_mock: bool = True,
    model: str = "gpt-4o-mini",
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Offline-safe stream aggregation smoke (M027/M089 adjacency).

    Always runs mock path in CI. Live stream sample only when use_mock=False
    and credentials exist for the model path.
    """
    from .model_caller import ModelCaller
    from .model_registry import ModelRegistry

    caller = ModelCaller(use_mock=use_mock, registry=ModelRegistry())
    result = caller.call_stream_complete(
        model=model,
        prompt="Reply with exactly: pong",
        command_name="live-smoke-stream",
        provider=provider,
    )
    return {
        "ok": bool(result.get("ok")),
        "mock": bool(result.get("mock") or use_mock),
        "contract": result.get("contract"),
        "stream_meta": result.get("stream_meta"),
        "has_response": bool(result.get("response")),
        "product": "live_smoke.stream_sample",
        "result": {
            k: result.get(k)
            for k in (
                "ok",
                "status",
                "model",
                "provider",
                "mock",
                "tokens",
                "estimated_cost_usd",
                "cost_source",
                "contract",
            )
        },
    }


def run_phase6_smoke(
    *,
    allow_live: bool = False,
    include_stream: bool = True,
) -> Dict[str, Any]:
    """
    Full Phase 6 / M089 verification path:
    1) harness inventory (never false live pass)
    2) offline stream aggregation sample (always)
    3) optional live smoke if allow_live and credentials exist
    """
    harness = smoke_harness(allow_live=False)
    preflight = None
    try:
        from .smoke_preflight import smoke_preflight

        preflight = smoke_preflight(include_readiness=True)
    except Exception as e:
        preflight = {"ok": False, "error": str(e)[:200]}

    stream_sample = None
    if include_stream:
        try:
            stream_sample = run_stream_smoke_sample(use_mock=True)
        except Exception as e:
            stream_sample = {"ok": False, "error": str(e)[:200], "mock": True}

    live_result = None
    live_attempted = False
    live_stream = None
    if allow_live:
        targets = available_smoke_targets()
        if not targets:
            live_result = {
                "ok": True,
                "live_attempted": False,
                "live_passed": False,
                "message": "allow_live set but no credentials/Ollama — not claiming pass",
                "env_keys": _env_keys_present(),
            }
        else:
            block = budget_precheck(
                estimated_usd=0.5,
                tokens=2000,
                command_name="live-smoke",
            )
            if block.get("blocked"):
                return wrap_public_result(block, ok=False, record_spend=False)
            live_attempted = True
            live_result = run_provider_smoke(use_mock=False)
            live_result["live_attempted"] = True
            live_result["live_passed"] = (
                int(live_result.get("passed") or 0) > 0
                and int(live_result.get("failed") or 0) == 0
            )
            # Optional one-provider stream live sample (honest fail does not skip call smoke)
            try:
                t0 = targets[0]
                live_stream = run_stream_smoke_sample(
                    use_mock=False, model=str(t0.get("model") or "gpt-4o-mini"), provider=t0.get("provider")
                )
                live_stream["provider"] = t0.get("provider")
            except Exception as e:
                live_stream = {"ok": False, "error": str(e)[:200], "mock": False}

    host_complete = bool((live_result or {}).get("live_passed"))
    out = {
        "ok": True,
        "phase": 6,
        "product": "live_smoke_complete.m089",
        "harness": harness,
        "preflight": preflight,
        "stream_sample_offline": stream_sample,
        "live": live_result,
        "live_stream": live_stream,
        "live_attempted": live_attempted,
        "live_passed": host_complete,
        "phase6_complete_code": True,
        "phase6_complete_host": host_complete,
        "env_keys_present": _env_keys_present(),
        "budget_command": "live-smoke",
        "message": (
            "M089 code path complete (harness + offline stream aggregate). "
            "Host complete only if live_passed=true with real provider results."
            if not host_complete
            else "M089 host live matrix passed with real provider results."
        ),
    }
    return wrap_public_result(
        out, mock=not live_attempted, ok=True, record_spend=False
    )
