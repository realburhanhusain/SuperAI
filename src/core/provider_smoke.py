"""
Live multi-provider smoke tests (Phase 2 Track F2.1).

Runs only against providers that have credentials / local services available.
Never fails the suite solely because keys are missing — reports skipped.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

from .load_balancer import LoadBalancer
from .model_caller import ModelCaller
from .model_registry import ModelRegistry
from .provider_health import ProviderHealthStore

# Default model name per provider for smoke (must exist in registry or still callable)
SMOKE_TARGETS = [
    {"provider": "openai", "model": "gpt-4o", "env": "OPENAI_API_KEY"},
    {"provider": "anthropic", "model": "claude-4-sonnet", "env": "ANTHROPIC_API_KEY"},
    {"provider": "xai", "model": "grok-3", "env": "XAI_API_KEY"},
    {"provider": "google", "model": "gemini-2.0-flash", "env": "GOOGLE_API_KEY"},
    {"provider": "deepseek", "model": "deepseek-coder", "env": "DEEPSEEK_API_KEY"},
    {"provider": "groq", "model": "llama-3.3-70b", "env": "GROQ_API_KEY"},
    {"provider": "ollama", "model": "llama3.2", "env": None},  # local probe
]


def _ollama_available() -> bool:
    try:
        import urllib.request

        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def available_smoke_targets() -> List[Dict[str, Any]]:
    out = []
    for t in SMOKE_TARGETS:
        if t["provider"] == "ollama":
            if _ollama_available():
                out.append(t)
            continue
        env = t.get("env")
        if env and os.getenv(env):
            out.append(t)
    return out


def smoke_harness(
    *,
    allow_live: bool = False,
    prompt: str = "Reply with exactly: pong",
) -> Dict[str, Any]:
    """
    N8 harness only — never claims live multi-vendor pass without keys.

    Default: inventory targets + mock dry path; live only if allow_live and
    credentials exist. Does not set ok=True for live success unless real calls ran.
    """
    targets = available_smoke_targets()
    inventory = [
        {
            "provider": t["provider"],
            "model": t["model"],
            "credentialed": t in targets if t.get("env") else t["provider"] == "ollama",
            "env": t.get("env"),
        }
        for t in SMOKE_TARGETS
    ]
    if not allow_live:
        return {
            "ok": True,
            "live": False,
            "harness": True,
            "message": (
                "Smoke harness only — live multi-vendor smoke postponed by policy. "
                "Pass allow_live=True when credentials are ready."
            ),
            "targets_known": len(SMOKE_TARGETS),
            "targets_credentialed": len(targets),
            "inventory": inventory,
            "live_passed": False,
            "live_claimed": False,
            "contract": "superai.smoke.harness.v1",
        }
    if not targets:
        return {
            "ok": True,
            "live": False,
            "harness": True,
            "message": "allow_live set but no credentials/Ollama; not claiming pass",
            "targets_credentialed": 0,
            "inventory": inventory,
            "live_passed": False,
            "live_claimed": False,
            "contract": "superai.smoke.harness.v1",
        }
    live = run_provider_smoke(prompt=prompt, use_mock=False)
    return {
        "ok": bool(live.get("ok")),
        "live": True,
        "harness": True,
        "live_passed": int(live.get("passed") or 0) > 0 and int(live.get("failed") or 0) == 0,
        "live_claimed": True,
        "result": live,
        "contract": "superai.smoke.harness.v1",
    }


def run_provider_smoke(
    prompt: str = "Reply with exactly: pong",
    use_mock: bool = False,
    health: Optional[ProviderHealthStore] = None,
) -> Dict[str, Any]:
    """
    Call each available provider once.

    Returns summary with per-provider results.
    """
    health = health or ProviderHealthStore()
    registry = ModelRegistry()
    lb = LoadBalancer()
    health.apply_to_circuit_breakers(lb)
    caller = ModelCaller(use_mock=use_mock, registry=registry, load_balancer=lb)
    # Attach health store for recording if caller supports it
    if hasattr(caller, "health_store"):
        caller.health_store = health

    targets = available_smoke_targets() if not use_mock else SMOKE_TARGETS[:3]
    results: List[Dict[str, Any]] = []
    passed = 0
    failed = 0
    skipped = 0

    if not targets and not use_mock:
        return {
            "ok": True,
            "passed": 0,
            "failed": 0,
            "skipped": len(SMOKE_TARGETS),
            "message": "No provider credentials or Ollama detected; all skipped.",
            "results": [],
            "targets_available": 0,
        }

    for t in targets:
        provider = t["provider"]
        model = t["model"]
        start = time.time()
        entry: Dict[str, Any] = {
            "provider": provider,
            "model": model,
            "status": "failed",
        }
        try:
            if not use_mock and not health.can_call(provider):
                entry["status"] = "skipped"
                entry["error"] = "provider throttled or circuit open"
                skipped += 1
                results.append(entry)
                continue

            resp = caller.call(
                provider=provider,
                model=model,
                prompt=prompt,
                use_fallback=False,
            )
            latency = time.time() - start
            entry["latency"] = round(latency, 3)
            entry["mock"] = bool(resp.get("mock"))
            entry["response_preview"] = str(resp.get("response", ""))[:120]
            if resp.get("status") == "success":
                entry["status"] = "passed"
                passed += 1
                tokens = int((resp.get("usage") or {}).get("total_tokens") or 0)
                health.record_success(provider, latency=latency, tokens=tokens)
            else:
                entry["status"] = "failed"
                entry["error"] = resp.get("response")
                failed += 1
                health.record_failure(provider, error=str(resp.get("response")), latency=latency)
        except Exception as e:  # noqa: BLE001
            latency = time.time() - start
            entry["status"] = "failed"
            entry["error"] = str(e)
            entry["latency"] = round(latency, 3)
            failed += 1
            health.record_failure(provider, error=str(e), latency=latency)
        results.append(entry)

    return {
        "ok": failed == 0,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "targets_available": len(targets),
        "results": results,
        "health_snapshot": health.snapshot(),
        "message": f"Smoke complete: {passed} passed, {failed} failed, {skipped} skipped.",
    }
