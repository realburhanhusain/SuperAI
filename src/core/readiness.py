"""
Fail-closed readiness checks before live model/CLI calls (Sprint A M4).
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional


def check_model_ready(
    model: str,
    *,
    use_mock: bool = False,
    registry=None,
) -> Dict[str, Any]:
    """Return {ok, reason, provider, ...}. ok=True if safe to call live or mock."""
    if use_mock:
        return {"ok": True, "reason": "mock", "model": model}
    try:
        from .model_registry import ModelRegistry

        reg = registry or ModelRegistry()
        info = reg.get_model(model)
        if not info:
            # cli:name
            if str(model).startswith("cli:") or "@" in str(model):
                return check_cli_ready(model, use_mock=False)
            return {"ok": False, "reason": "unknown_model", "model": model}
        if info.provider == "external_cli":
            return check_cli_ready(f"cli:{info.model_id}", use_mock=False)
        # local often no key
        local_provs = {"ollama", "ollama_openai", "lmstudio", "vllm"}
        if (info.provider or "").lower() in local_provs:
            return {"ok": True, "reason": "local", "provider": info.provider, "model": model}
        env = info.api_key_env
        if env and not (os.getenv(env) or "").strip():
            # allow empty for allow_empty_key providers
            try:
                from .provider_catalog import get_openai_compat_config

                cat = get_openai_compat_config(info.provider or "")
                if cat and cat.get("allow_empty_key"):
                    return {"ok": True, "reason": "local_compat", "provider": info.provider}
            except Exception:
                pass
            return {
                "ok": False,
                "reason": "missing_key",
                "model": model,
                "provider": info.provider,
                "api_key_env": env,
            }
        # circuit
        try:
            from .provider_health import ProviderHealthStore

            h = ProviderHealthStore().data.get("providers", {}).get(info.provider or "", {})
            if h.get("circuit_open"):
                return {
                    "ok": False,
                    "reason": "circuit_open",
                    "provider": info.provider,
                    "model": model,
                }
        except Exception:
            pass
        return {"ok": True, "reason": "ready", "provider": info.provider, "model": model}
    except Exception as e:
        return {"ok": False, "reason": "check_error", "error": str(e)[:200]}


def check_cli_ready(selector: str, *, use_mock: bool = False) -> Dict[str, Any]:
    if use_mock:
        return {"ok": True, "reason": "mock", "cli": selector}
    try:
        from .external_cli import ExternalCLIRegistry, split_cli_selector

        name, _ = split_cli_selector(selector)
        if not name:
            name = str(selector).replace("cli:", "").split("@")[0]
        reg = ExternalCLIRegistry()
        if name not in reg.available():
            return {
                "ok": False,
                "reason": "cli_not_on_path",
                "cli": name,
                "hint": reg.install_hint(name),
            }
        return {"ok": True, "reason": "ready", "cli": name}
    except Exception as e:
        return {"ok": False, "reason": "check_error", "error": str(e)[:200]}


def assert_ready_or_error(model: str, *, use_mock: bool = False) -> Optional[Dict[str, Any]]:
    """Return error payload if not ready; else None."""
    r = check_model_ready(model, use_mock=use_mock)
    if r.get("ok"):
        return None
    return {
        "ok": False,
        "status": "error",
        "error": f"not_ready:{r.get('reason')}",
        "readiness": r,
        "mock": False,
        "dry_run": False,
        "model_chain": [model],
        "tokens": 0,
        "estimated_cost_usd": 0.0,
        "members": [model],
        "memory_ids": [],
        "contract": "superai.result.v1",
    }
