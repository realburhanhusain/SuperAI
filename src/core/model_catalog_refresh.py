"""
Refresh gateway model lists (Phase 8 N5) — OpenRouter public models API.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any, Dict, List, Optional

from .model_discovery import register_openai_compatible_model
from .model_refresh import merge_catalogs, user_models_path, load_json_array, _project_models_path


def fetch_openrouter_models(limit: int = 40, timeout: float = 20.0) -> List[Dict[str, Any]]:
    url = "https://openrouter.ai/api/v1/models"
    req = urllib.request.Request(url, headers={"User-Agent": "SuperAI/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    models = data.get("data") if isinstance(data, dict) else data
    if not isinstance(models, list):
        return []
    out = []
    for m in models[:limit]:
        if not isinstance(m, dict):
            continue
        mid = m.get("id") or m.get("name")
        if not mid:
            continue
        safe = str(mid).replace("/", "-").replace(":", "-")
        out.append(
            {
                "name": f"openrouter/{safe}",
                "provider": "openrouter",
                "model_id": mid,
                "base_url": "https://openrouter.ai/api/v1",
                "api_key_env": "OPENROUTER_API_KEY",
                "context_window": int(
                    (m.get("context_length") or m.get("top_provider", {}).get("context_length") or 128000)
                    if isinstance(m.get("top_provider"), dict)
                    else (m.get("context_length") or 128000)
                ),
                "cost_per_1k_tokens": 0.002,
                "latency_tier": 2,
                "strengths": str(m.get("name") or mid)[:200],
                "open_weight": True,
                "gateway": "openrouter",
            }
        )
    return out


def refresh_openrouter_into_user_registry(
    *, write: bool = True, limit: int = 40
) -> Dict[str, Any]:
    try:
        discovered = fetch_openrouter_models(limit=limit)
    except Exception as e:
        return {"ok": False, "error": str(e)[:400], "hint": "Network required for OpenRouter list"}
    catalogs: List[List[Dict[str, Any]]] = []
    proj = _project_models_path()
    if proj and proj.is_file():
        try:
            catalogs.append(load_json_array(proj))
        except Exception:
            pass
    user = user_models_path()
    if user.is_file():
        try:
            catalogs.append(load_json_array(user))
        except Exception:
            pass
    catalogs.append(discovered)
    merged = merge_catalogs(*catalogs)
    meta = {
        "ok": True,
        "discovered": len(discovered),
        "merged_total": len(merged),
        "written_to": None,
        "sample": [d["name"] for d in discovered[:8]],
    }
    if write and discovered:
        user.parent.mkdir(parents=True, exist_ok=True)
        user.write_text(json.dumps(merged, indent=2), encoding="utf-8")
        meta["written_to"] = str(user)
    return meta
