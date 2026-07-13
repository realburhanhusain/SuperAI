"""
Model catalog refresh (Phase 2 Track F2.2).

Refresh order:
1. SUPERAI_MODELS_URL (HTTP JSON array) if set
2. Project config/models.json
3. User override ~/.superai/config/models.json
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _project_models_path() -> Optional[Path]:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[3] / "config" / "models.json",
        Path.cwd() / "config" / "models.json",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def user_models_path() -> Path:
    return Path.home() / ".superai" / "config" / "models.json"


def load_json_array(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path} must be a JSON array of models")
    return data


def fetch_remote_models(url: str, timeout: float = 20.0) -> List[Dict[str, Any]]:
    req = urllib.request.Request(url, headers={"User-Agent": "SuperAI/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    data = json.loads(raw)
    if isinstance(data, dict) and "models" in data:
        data = data["models"]
    if not isinstance(data, list):
        raise ValueError("Remote catalog must be a JSON array or {models: [...]}")
    return data


def merge_catalogs(*catalogs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Later catalogs override earlier ones by model name."""
    by_name: Dict[str, Dict[str, Any]] = {}
    for catalog in catalogs:
        for entry in catalog:
            if isinstance(entry, dict) and entry.get("name"):
                by_name[entry["name"]] = entry
    return list(by_name.values())


def refresh_models(
    write_user_copy: bool = True,
    remote_url: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Refresh model list and optionally write to ~/.superai/config/models.json.

    Returns (models, meta).
    """
    meta: Dict[str, Any] = {"sources": [], "errors": []}
    catalogs: List[List[Dict[str, Any]]] = []

    project = _project_models_path()
    if project:
        try:
            catalogs.append(load_json_array(project))
            meta["sources"].append(str(project))
        except Exception as e:  # noqa: BLE001
            meta["errors"].append(f"project: {e}")

    url = remote_url or os.getenv("SUPERAI_MODELS_URL")
    if url:
        try:
            catalogs.append(fetch_remote_models(url))
            meta["sources"].append(url)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError) as e:
            meta["errors"].append(f"remote: {e}")

    user_path = user_models_path()
    if user_path.is_file() and not write_user_copy:
        try:
            catalogs.append(load_json_array(user_path))
            meta["sources"].append(str(user_path))
        except Exception as e:  # noqa: BLE001
            meta["errors"].append(f"user: {e}")

    if not catalogs:
        raise RuntimeError("No model catalogs available to refresh")

    merged = merge_catalogs(*catalogs)
    meta["count"] = len(merged)

    if write_user_copy:
        user_path.parent.mkdir(parents=True, exist_ok=True)
        with open(user_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2)
        meta["written_to"] = str(user_path)

    return merged, meta
