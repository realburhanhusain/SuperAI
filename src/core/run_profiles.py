"""
Run profiles for cost/quality tradeoffs (Improvement Phase 3).

cheap | balanced | quality | local-only
"""

from __future__ import annotations

from typing import Any, Dict


PROFILES: Dict[str, Dict[str, Any]] = {
    "cheap": {
        "worker_prefer": "api",  # will prefer OW/local via prefer_open_weight
        "prefer_open_weight": True,
        "prefer_local": True,
        "worker_max": 2,
        "critic_mode": "off",
        "cli_delegate_reviewers": False,
        "budget_run_usd": 0.25,
        "permission_mode": "ask",
        "description": "Minimize cost: local/OW first, small pool, no critic board",
    },
    "balanced": {
        "worker_prefer": "mixed",
        "prefer_open_weight": False,
        "prefer_local": False,
        "worker_max": 5,
        "critic_mode": "light",
        "cli_delegate_reviewers": False,
        "budget_run_usd": 1.0,
        "permission_mode": "ask",
        "description": "Default mix of quality and cost",
    },
    "quality": {
        "worker_prefer": "mixed",
        "prefer_open_weight": False,
        "prefer_local": False,
        "worker_max": 5,
        "critic_mode": "council",
        "cli_delegate_reviewers": True,
        "budget_run_usd": 5.0,
        "permission_mode": "ask",
        "description": "Higher spend, council critic, multi-member boards",
    },
    "local-only": {
        "worker_prefer": "api",
        "prefer_open_weight": True,
        "prefer_local": True,
        "local_only": True,
        "worker_max": 3,
        "critic_mode": "off",
        "cli_delegate_reviewers": False,
        "budget_run_usd": 0.05,
        "permission_mode": "ask",
        "description": "Ollama/LM Studio/vLLM only when available",
    },
}


def list_profiles() -> Dict[str, Dict[str, Any]]:
    return {k: dict(v) for k, v in PROFILES.items()}


def get_profile(name: str) -> Dict[str, Any]:
    key = (name or "balanced").strip().lower()
    if key not in PROFILES:
        key = "balanced"
    return dict(PROFILES[key])


def apply_profile_to_config(config: Any, profile_name: str) -> Dict[str, Any]:
    """Apply profile keys onto Config (in-memory; optional persist)."""
    prof = get_profile(profile_name)
    applied = {}
    for k, v in prof.items():
        if k == "description":
            continue
        try:
            config.set(k, v, persist=False) if hasattr(config, "set") else None
            if hasattr(config, "config") and isinstance(config.config, dict):
                config.config[k] = v
            applied[k] = v
        except Exception:
            try:
                config.config[k] = v
                applied[k] = v
            except Exception:
                pass
    if hasattr(config, "config"):
        config.config["run_profile"] = (profile_name or "balanced").strip().lower()
    applied["run_profile"] = (profile_name or "balanced").strip().lower()
    return applied
