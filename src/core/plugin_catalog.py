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


def browse_catalog(
    url: Optional[str] = None,
    *,
    query: str = "",
    limit: int = 30,
) -> Dict[str, Any]:
    """
    Browse remote or bundled sample catalog (Phase 8 N8 marketplace UX).
    """
    sample = {
        "plugins": [
            {
                "id": "sample-hello",
                "name": "Hello Skill",
                "description": "Sample plugin manifest entry",
                "tags": ["sample", "demo"],
                "url": None,
            },
            {
                "id": "memory-extra",
                "name": "Memory extras",
                "description": "Placeholder for memory-related plugin",
                "tags": ["memory"],
                "url": None,
            },
        ]
    }
    data = sample
    if url:
        try:
            data = fetch_catalog(url)
        except Exception as e:
            return {"ok": False, "error": str(e)[:300], "plugins": sample["plugins"]}
    plugins = data.get("plugins") if isinstance(data, dict) else None
    if not isinstance(plugins, list):
        plugins = sample["plugins"]
    q = (query or "").lower().strip()
    if q:
        plugins = [
            p
            for p in plugins
            if isinstance(p, dict)
            and (
                q in str(p.get("id") or "").lower()
                or q in str(p.get("name") or "").lower()
                or q in str(p.get("description") or "").lower()
                or any(q in str(t).lower() for t in (p.get("tags") or []))
            )
        ]
    return {
        "ok": True,
        "count": len(plugins[:limit]),
        "plugins": plugins[:limit],
        "source": url or "bundled_sample",
    }


def default_sha_store() -> Path:
    """N5: default path for expected plugin SHAs."""
    d = Path.home() / ".superai" / "plugin_sha"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_expected_sha(plugin_id: str, sha_store: Optional[Path] = None) -> Optional[str]:
    """Load sha256 from ~/.superai/plugin_sha/<id>.sha256 if present."""
    root = Path(sha_store or default_sha_store())
    for name in (f"{plugin_id}.sha256", f"{plugin_id}.sha", "checksums.json"):
        p = root / name
        if not p.is_file():
            continue
        try:
            if p.suffix == ".json" or p.name == "checksums.json":
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    v = data.get(plugin_id) or (data.get("plugins") or {}).get(plugin_id)
                    if isinstance(v, dict):
                        return str(v.get("sha256") or v.get("sha") or "") or None
                    if v:
                        return str(v)
            else:
                line = p.read_text(encoding="utf-8").strip().split()[0]
                return line or None
        except Exception:
            continue
    return None


def install_from_catalog_entry(
    entry: Dict[str, Any],
    dest_root: Optional[Path] = None,
    *,
    require_sha: bool = True,
    sha_store: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    entry: {id, url, sha256?, name?}
    Downloads plugin.json (or zip not supported — json only for safety).
    N5: when require_sha=True (default), sha256 must come from entry or
    ~/.superai/plugin_sha/<id>.sha256.
    """
    from .plugin_registry import PluginRegistry

    pid = entry.get("id") or entry.get("name")
    url = entry.get("url")
    if not pid or not url:
        raise ValueError("entry needs id and url")
    expected = entry.get("sha256") or load_expected_sha(str(pid), sha_store=sha_store)
    if require_sha and not expected:
        raise ValueError(
            f"sha256 required for plugin {pid}; place it in entry or "
            f"{default_sha_store() / (str(pid) + '.sha256')}"
        )
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    got = hashlib.sha256(raw).hexdigest()
    if expected and got.lower() != str(expected).lower():
        raise ValueError(f"sha256 mismatch: {got} != {expected}")
    # Persist verified sha for next time
    try:
        store = Path(sha_store or default_sha_store())
        store.mkdir(parents=True, exist_ok=True)
        (store / f"{pid}.sha256").write_text(got + "\n", encoding="utf-8")
    except Exception:
        pass
    manifest = json.loads(raw.decode("utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("plugin manifest must be object")
    manifest.setdefault("id", pid)
    reg = PluginRegistry(root=dest_root)
    installed = reg.install_manifest(manifest)
    return {
        "ok": True,
        "installed": installed,
        "sha256": got,
        "sha_verified": bool(expected),
        "sha_store": str(default_sha_store()),
    }
