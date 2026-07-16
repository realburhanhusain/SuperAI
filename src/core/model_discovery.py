"""
Discover local / gateway models and merge into SuperAI registry files.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from .model_refresh import merge_catalogs, user_models_path
from .provider_catalog import OPENAI_COMPAT_PROVIDERS, list_providers


def _http_json(url: str, timeout: float = 8.0) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "SuperAI/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def list_ollama_tags(
    base: str = "http://localhost:11434",
    timeout: float = 5.0,
) -> List[Dict[str, Any]]:
    """Return Ollama /api/tags models (empty if daemon down)."""
    base = (os.getenv("OLLAMA_HOST") or base).rstrip("/")
    try:
        data = _http_json(f"{base}/api/tags", timeout=timeout)
    except Exception:
        return []
    models = data.get("models") if isinstance(data, dict) else None
    if not isinstance(models, list):
        return []
    return models


def ollama_tags_to_catalog(
    tags: Optional[List[Dict[str, Any]]] = None,
    *,
    use_openai_compat: bool = True,
) -> List[Dict[str, Any]]:
    """
    Convert Ollama tags into SuperAI models.json entries.

    use_openai_compat=True → provider ollama_openai (chat via /v1)
    else provider ollama (native generate API)
    """
    tags = tags if tags is not None else list_ollama_tags()
    out: List[Dict[str, Any]] = []
    provider = "ollama_openai" if use_openai_compat else "ollama"
    base_url = (
        "http://localhost:11434/v1"
        if use_openai_compat
        else "http://localhost:11434"
    )
    for m in tags:
        name_raw = str(m.get("name") or m.get("model") or "").strip()
        if not name_raw:
            continue
        # SuperAI name: ollama/<tag> for uniqueness
        safe = name_raw.replace(":", "-")
        entry_name = f"ollama/{safe}"
        out.append(
            {
                "name": entry_name,
                "provider": provider,
                "model_id": name_raw,
                "base_url": base_url,
                "api_key_env": "OLLAMA_API_KEY" if use_openai_compat else None,
                "context_window": 128000,
                "cost_per_1k_tokens": 0.0,
                "latency_tier": 2,
                "strengths": f"Local open-weight via Ollama ({name_raw})",
                "is_latest": False,
                "supports_tools": True,
                "open_weight": True,
                "local": True,
            }
        )
    return out


def sync_ollama_to_user_registry(
    *,
    write: bool = True,
    use_openai_compat: bool = True,
) -> Dict[str, Any]:
    """Merge Ollama models into ~/.superai/config/models.json."""
    from .model_refresh import _project_models_path, load_json_array

    tags = list_ollama_tags()
    discovered = ollama_tags_to_catalog(tags, use_openai_compat=use_openai_compat)
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
        "ollama_tags": len(tags),
        "discovered": len(discovered),
        "merged_total": len(merged),
        "written_to": None,
        "names": [d["name"] for d in discovered],
    }
    if write and discovered:
        user.parent.mkdir(parents=True, exist_ok=True)
        user.write_text(json.dumps(merged, indent=2), encoding="utf-8")
        meta["written_to"] = str(user)
    elif not tags:
        meta["ok"] = False
        meta["error"] = "ollama_unreachable_or_empty"
        meta["hint"] = "Start Ollama and pull a model: ollama pull llama3.2"
    return meta


def register_openai_compatible_model(
    name: str,
    model_id: str,
    *,
    provider: str = "custom",
    base_url: str,
    api_key_env: Optional[str] = None,
    write: bool = True,
    strengths: str = "User-registered OpenAI-compatible model",
) -> Dict[str, Any]:
    """Append/override a model in user models.json."""
    from .model_refresh import _project_models_path, load_json_array

    entry = {
        "name": name,
        "provider": provider,
        "model_id": model_id,
        "base_url": base_url.rstrip("/"),
        "api_key_env": api_key_env,
        "context_window": 128000,
        "cost_per_1k_tokens": 0.0,
        "latency_tier": 2,
        "strengths": strengths,
        "is_latest": True,
        "supports_tools": True,
        "open_weight": True,
        "user_registered": True,
    }
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
    catalogs.append([entry])
    merged = merge_catalogs(*catalogs)
    if write:
        user.parent.mkdir(parents=True, exist_ok=True)
        user.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    return {"ok": True, "entry": entry, "written_to": str(user) if write else None}


def provider_status() -> Dict[str, Any]:
    rows = list_providers(include_native=True)
    return {
        "ok": True,
        "providers": rows,
        "counts": {
            "total": len(rows),
            "key_configured": sum(1 for r in rows if r.get("key_configured")),
            "local": sum(1 for r in rows if r.get("kind") == "local"),
            "cloud": sum(1 for r in rows if r.get("kind") == "cloud"),
            "gateway": sum(1 for r in rows if r.get("kind") == "gateway"),
            "cli": sum(1 for r in rows if r.get("kind") == "cli"),
        },
        "openai_compat_ids": list(OPENAI_COMPAT_PROVIDERS.keys()),
    }
