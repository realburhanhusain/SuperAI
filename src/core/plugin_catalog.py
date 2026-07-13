"""
Remote plugin catalog (N23) — fetch + hash verify.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


def fetch_catalog(url: str, timeout: float = 15.0) -> Dict[str, Any]:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("catalog must be a JSON object")
    return data


def verify_sha256(path: Path, expected: str) -> bool:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().lower() == expected.lower()


def install_from_catalog_entry(
    entry: Dict[str, Any],
    dest_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    entry: {id, url, sha256?, name?}
    Downloads plugin.json (or zip not supported — json only for safety).
    """
    from .plugin_registry import PluginRegistry

    pid = entry.get("id") or entry.get("name")
    url = entry.get("url")
    if not pid or not url:
        raise ValueError("entry needs id and url")
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    expected = entry.get("sha256")
    if expected:
        got = hashlib.sha256(raw).hexdigest()
        if got.lower() != str(expected).lower():
            raise ValueError(f"sha256 mismatch: {got} != {expected}")
    manifest = json.loads(raw.decode("utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("plugin manifest must be object")
    manifest.setdefault("id", pid)
    reg = PluginRegistry(root=dest_root)
    installed = reg.install_manifest(manifest)
    return {"ok": True, "installed": installed}
