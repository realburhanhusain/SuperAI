"""
Smoke preflight (Not-important W8) — prepare for Phase 99 live smoke.

Does NOT run live provider calls by default. Reports credential inventory,
readiness probes (optional), and a checklist. Never claims live smoke passed.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional


# Align with provider_smoke targets + common open-weight endpoints
PREFLIGHT_CHECKS = [
    {"id": "openai", "env": "OPENAI_API_KEY", "model": "gpt-4o"},
    {"id": "anthropic", "env": "ANTHROPIC_API_KEY", "model": "claude-4-sonnet"},
    {"id": "xai", "env": "XAI_API_KEY", "model": "grok-3"},
    {"id": "google", "env": "GOOGLE_API_KEY", "model": "gemini-2.0-flash"},
    {"id": "deepseek", "env": "DEEPSEEK_API_KEY", "model": "deepseek-chat"},
    {"id": "groq", "env": "GROQ_API_KEY", "model": "llama-3.3-70b"},
    {"id": "openrouter", "env": "OPENROUTER_API_KEY", "model": "openrouter-auto"},
    {"id": "nvidia", "env": "NVIDIA_API_KEY", "model": "nvidia-llama-3.1-70b-instruct"},
    {"id": "ollama", "env": None, "model": "llama3.2", "local": True},
    {"id": "lmstudio", "env": None, "model": "lmstudio-local", "local": True},
]


def _env_set(name: Optional[str]) -> bool:
    if not name:
        return False
    return bool((os.getenv(name) or "").strip())


def _local_up(kind: str) -> bool:
    try:
        import urllib.request

        urls = {
            "ollama": "http://localhost:11434/api/tags",
            "lmstudio": "http://localhost:1234/v1/models",
        }
        url = urls.get(kind)
        if not url:
            return False
        with urllib.request.urlopen(url, timeout=1.5) as r:
            return int(getattr(r, "status", 200) or 200) < 500
    except Exception:
        return False


def smoke_preflight(
    *,
    include_readiness: bool = False,
    use_mock_readiness: bool = True,
) -> Dict[str, Any]:
    """
    Build pre-live-smoke inventory + checklist.

    include_readiness: call check_model_ready for credentialed models (still not live chat).
    """
    rows: List[Dict[str, Any]] = []
    ready_n = 0
    for item in PREFLIGHT_CHECKS:
        row: Dict[str, Any] = {
            "provider": item["id"],
            "model": item.get("model"),
            "env": item.get("env"),
            "credentialed": False,
            "local_up": False,
            "ready_for_live_smoke": False,
        }
        if item.get("local"):
            row["local_up"] = _local_up(item["id"])
            row["credentialed"] = row["local_up"]
        else:
            row["credentialed"] = _env_set(item.get("env"))
        if include_readiness and row["credentialed"] and item.get("model"):
            try:
                from .readiness import check_model_ready

                r = check_model_ready(
                    str(item["model"]),
                    use_mock=use_mock_readiness,
                )
                row["readiness"] = {
                    "ok": bool(r.get("ok")),
                    "detail": str(r.get("error") or r.get("reason") or "")[:120],
                }
            except Exception as e:
                row["readiness"] = {"ok": False, "detail": str(e)[:120]}
        row["ready_for_live_smoke"] = bool(row["credentialed"])
        if row["ready_for_live_smoke"]:
            ready_n += 1
        rows.append(row)

    checklist = [
        "Set API keys for providers you want to smoke (OPENAI_API_KEY, …)",
        "Start Ollama/LM Studio if testing local open-weight",
        "Run: superai smoke-harness  (inventory, no false pass)",
        "Run: superai smoke-preflight --readiness",
        "When ready: superai smoke-harness --allow-live  (only claims pass on real results)",
        "Optional: SUPERAI_MOCK_MODE=0 for non-mock paths",
    ]

    return {
        "ok": True,
        "harness": True,
        "live_smoke_run": False,
        "live_passed": False,
        "providers": rows,
        "credentialed_count": ready_n,
        "total_checks": len(rows),
        "checklist": checklist,
        "message": (
            "Preflight only — does not run live multi-vendor smoke. "
            f"{ready_n}/{len(rows)} targets look credentialed/local-up."
        ),
        "contract": "superai.smoke.preflight.v1",
    }
