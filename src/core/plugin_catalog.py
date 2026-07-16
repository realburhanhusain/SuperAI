"""
Plugin marketplace browse + install (Phase 8 N8 / V1-N8).

Production browse UX:
- Offline bundled catalog (src/core/data/plugin_marketplace_catalog.json)
- Optional remote catalog URL (JSON object with plugins[])
- Search by query / tag / category
- Sort by name|id|category|version
- Overlay installed state from PluginRegistry
- Get-by-id, list categories, marketplace status
- Install with sha256 verify (M097 / MOS-N5)

Contract-shaped returns for CLI/automation.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


CATALOG_SCHEMA = "superai.plugin_catalog.v1"


def _contract(data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from .spend_guard import ensure_public_result

        data.setdefault("ok", bool(data.get("ok", True)))
        return ensure_public_result(data, mock=data.get("mock"), ok=data.get("ok"))
    except Exception:
        data.setdefault("ok", True)
        data.setdefault("contract", "superai.result.v1")
        return data


def bundled_catalog_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "plugin_marketplace_catalog.json"


def default_sha_store() -> Path:
    """N5: default path for expected plugin SHAs."""
    d = Path.home() / ".superai" / "plugin_sha"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_bundled_catalog() -> Dict[str, Any]:
    """Load offline marketplace catalog shipped with SuperAI."""
    path = bundled_catalog_path()
    if not path.is_file():
        return {
            "schema": CATALOG_SCHEMA,
            "name": "fallback-empty",
            "version": "0.0.0",
            "plugins": [],
            "error": f"bundled catalog missing: {path}",
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("bundled catalog must be a JSON object")
    data.setdefault("schema", CATALOG_SCHEMA)
    if not isinstance(data.get("plugins"), list):
        data["plugins"] = []
    return data


def fetch_catalog(url: str, timeout: float = 15.0) -> Dict[str, Any]:
    """Fetch remote catalog JSON (public URL; caller may pre-check SSRF)."""
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("catalog must be a JSON object")
    if not isinstance(data.get("plugins"), list) and not isinstance(
        data.get("entries"), list
    ):
        # allow either plugins or entries
        pass
    return data


def verify_sha256(path: Path, expected: str) -> bool:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().lower() == expected.lower()


def _normalize_plugin(raw: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    pid = str(raw.get("id") or raw.get("name") or "").strip()
    if not pid:
        return None
    tags = raw.get("tags") or []
    if not isinstance(tags, list):
        tags = [str(tags)]
    return {
        "id": pid,
        "name": str(raw.get("name") or pid),
        "version": str(raw.get("version") or "0.0.0"),
        "category": str(raw.get("category") or "uncategorized"),
        "description": str(raw.get("description") or ""),
        "tags": [str(t) for t in tags],
        "author": str(raw.get("author") or ""),
        "license": str(raw.get("license") or ""),
        "homepage": raw.get("homepage"),
        "source": str(raw.get("source") or "catalog"),
        "entry": raw.get("entry"),
        "sha256": raw.get("sha256"),
        "url": raw.get("url"),
        "install_hint": raw.get("install_hint"),
    }


def _extract_plugins(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_list = data.get("plugins")
    if not isinstance(raw_list, list):
        raw_list = data.get("entries")
    if not isinstance(raw_list, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in raw_list:
        norm = _normalize_plugin(item)
        if norm:
            out.append(norm)
    return out


def _installed_ids(registry_root: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Map plugin id -> registry info for install overlay."""
    try:
        from .plugin_registry import PluginRegistry

        reg = PluginRegistry(root=registry_root)
        by_id: Dict[str, Dict[str, Any]] = {}
        for p in reg.list_plugins():
            if isinstance(p, dict) and p.get("id"):
                by_id[str(p["id"])] = p
        return by_id
    except Exception:
        return {}


def _overlay_installed(
    plugins: List[Dict[str, Any]],
    *,
    registry_root: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    installed = _installed_ids(registry_root)
    out = []
    for p in plugins:
        row = dict(p)
        info = installed.get(row["id"])
        if info:
            row["installed"] = True
            row["install_status"] = str(info.get("status") or "installed")
            row["installed_source"] = info.get("source")
        else:
            # builtin entries without registry row still count as available
            if row.get("source") == "builtin" and row.get("entry"):
                row["installed"] = True
                row["install_status"] = "builtin"
            else:
                row["installed"] = False
                row["install_status"] = "available"
        out.append(row)
    return out


def _filter_plugins(
    plugins: Sequence[Dict[str, Any]],
    *,
    query: str = "",
    category: str = "",
    tag: str = "",
    installed_only: bool = False,
    available_only: bool = False,
) -> List[Dict[str, Any]]:
    q = (query or "").lower().strip()
    cat = (category or "").lower().strip()
    tg = (tag or "").lower().strip()
    out: List[Dict[str, Any]] = []
    for p in plugins:
        if cat and cat not in str(p.get("category") or "").lower():
            continue
        if tg and not any(tg in str(t).lower() for t in (p.get("tags") or [])):
            continue
        if installed_only and not p.get("installed"):
            continue
        if available_only and p.get("installed"):
            continue
        if q:
            blob = " ".join(
                [
                    str(p.get("id") or ""),
                    str(p.get("name") or ""),
                    str(p.get("description") or ""),
                    str(p.get("category") or ""),
                    " ".join(str(t) for t in (p.get("tags") or [])),
                    str(p.get("author") or ""),
                ]
            ).lower()
            if q not in blob:
                continue
        out.append(p)
    return out


def _sort_plugins(
    plugins: List[Dict[str, Any]], sort: str = "name"
) -> List[Dict[str, Any]]:
    key = (sort or "name").lower().strip()
    if key in {"id", "name", "category", "version", "author"}:
        return sorted(plugins, key=lambda p: str(p.get(key) or "").lower())
    if key == "installed":
        return sorted(
            plugins,
            key=lambda p: (0 if p.get("installed") else 1, str(p.get("name") or "").lower()),
        )
    return sorted(plugins, key=lambda p: str(p.get("name") or "").lower())


def browse_catalog(
    url: Optional[str] = None,
    *,
    query: str = "",
    category: str = "",
    tag: str = "",
    sort: str = "name",
    limit: int = 50,
    installed_only: bool = False,
    available_only: bool = False,
    registry_root: Optional[Path] = None,
    include_meta: bool = True,
) -> Dict[str, Any]:
    """
    Browse offline bundled marketplace or remote catalog.

    Phase 8 N8 production browse surface.
    """
    limit = max(1, min(int(limit or 50), 500))
    source = "bundled"
    remote_error = None
    meta: Dict[str, Any] = {}

    if url:
        try:
            data = fetch_catalog(url)
            source = url
            meta = {
                "name": data.get("name"),
                "version": data.get("version"),
                "schema": data.get("schema"),
            }
        except Exception as e:
            remote_error = str(e)[:300]
            data = load_bundled_catalog()
            source = "bundled_fallback"
    else:
        data = load_bundled_catalog()
        meta = {
            "name": data.get("name"),
            "version": data.get("version"),
            "schema": data.get("schema"),
            "updated": data.get("updated"),
        }

    plugins = _extract_plugins(data)
    plugins = _overlay_installed(plugins, registry_root=registry_root)
    filtered = _filter_plugins(
        plugins,
        query=query,
        category=category,
        tag=tag,
        installed_only=installed_only,
        available_only=available_only,
    )
    filtered = _sort_plugins(filtered, sort=sort)
    page = filtered[:limit]

    out: Dict[str, Any] = {
        "ok": remote_error is None or source.startswith("bundled"),
        "count": len(page),
        "total_matched": len(filtered),
        "total_catalog": len(plugins),
        "plugins": page,
        "source": source,
        "query": query or None,
        "category": category or None,
        "tag": tag or None,
        "sort": sort,
        "limit": limit,
    }
    if include_meta:
        out["catalog"] = meta
        out["bundled_path"] = str(bundled_catalog_path())
    if remote_error:
        out["remote_error"] = remote_error
        out["ok"] = True  # still ok with fallback
        out["fallback"] = True
    return _contract(out)


def get_plugin(
    plugin_id: str,
    *,
    url: Optional[str] = None,
    registry_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Get a single marketplace plugin by id."""
    cat = browse_catalog(url=url, limit=500, registry_root=registry_root)
    pid = str(plugin_id or "").strip()
    for p in cat.get("plugins") or []:
        if str(p.get("id")) == pid:
            return _contract({"ok": True, "plugin": p, "source": cat.get("source")})
    # search full catalog without filters
    data = load_bundled_catalog() if not url else None
    if url:
        try:
            data = fetch_catalog(url)
        except Exception as e:
            return _contract({"ok": False, "error": str(e)[:300], "plugin_id": pid})
    for p in _overlay_installed(_extract_plugins(data or {}), registry_root=registry_root):
        if p.get("id") == pid:
            return _contract({"ok": True, "plugin": p, "source": url or "bundled"})
    return _contract({"ok": False, "error": "not_found", "plugin_id": pid})


def list_categories(
    url: Optional[str] = None,
    *,
    registry_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """List categories with plugin counts."""
    cat = browse_catalog(url=url, limit=500, registry_root=registry_root, sort="category")
    counts: Dict[str, int] = {}
    for p in cat.get("plugins") or []:
        c = str(p.get("category") or "uncategorized")
        counts[c] = counts.get(c, 0) + 1
    rows = [
        {"category": k, "count": v}
        for k, v in sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    ]
    return _contract(
        {
            "ok": True,
            "categories": rows,
            "count": len(rows),
            "source": cat.get("source"),
        }
    )


def marketplace_status(registry_root: Optional[Path] = None) -> Dict[str, Any]:
    """High-level marketplace health for doctor / docs."""
    bundled = load_bundled_catalog()
    plugins = _extract_plugins(bundled)
    over = _overlay_installed(plugins, registry_root=registry_root)
    installed = sum(1 for p in over if p.get("installed"))
    return _contract(
        {
            "ok": True,
            "bundled_path": str(bundled_catalog_path()),
            "bundled_exists": bundled_catalog_path().is_file(),
            "catalog_name": bundled.get("name"),
            "catalog_version": bundled.get("version"),
            "schema": bundled.get("schema") or CATALOG_SCHEMA,
            "plugin_count": len(plugins),
            "installed_count": installed,
            "available_count": len(plugins) - installed,
            "sha_store": str(default_sha_store()),
            "commands": [
                "superai plugin-catalog",
                "superai plugin-catalog -q memory",
                "superai plugin-catalog --category memory",
                "superai plugin-catalog --show core.memory",
                "superai plugin-catalog --categories",
            ],
        }
    )


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
    Downloads plugin.json (zip not supported — json only for safety).
    When require_sha=True (default), sha256 must come from entry or
    ~/.superai/plugin_sha/<id>.sha256.
    """
    from .plugin_registry import PluginRegistry

    pid = entry.get("id") or entry.get("name")
    url = entry.get("url")
    if not pid or not url:
        return _contract(
            {
                "ok": False,
                "error": "entry needs id and url",
                "plugin_id": pid,
            }
        )
    expected = entry.get("sha256") or load_expected_sha(str(pid), sha_store=sha_store)
    if require_sha and not expected:
        return _contract(
            {
                "ok": False,
                "error": (
                    f"sha256 required for plugin {pid}; place it in entry or "
                    f"{default_sha_store() / (str(pid) + '.sha256')}"
                ),
                "plugin_id": pid,
            }
        )
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
    except Exception as e:
        return _contract({"ok": False, "error": f"download_failed:{e}"[:300], "plugin_id": pid})
    got = hashlib.sha256(raw).hexdigest()
    if expected and got.lower() != str(expected).lower():
        return _contract(
            {
                "ok": False,
                "error": f"sha256 mismatch: {got} != {expected}",
                "plugin_id": pid,
            }
        )
    try:
        store = Path(sha_store or default_sha_store())
        store.mkdir(parents=True, exist_ok=True)
        (store / f"{pid}.sha256").write_text(got + "\n", encoding="utf-8")
    except Exception:
        pass
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except Exception as e:
        return _contract({"ok": False, "error": f"invalid_json:{e}"[:200], "plugin_id": pid})
    if not isinstance(manifest, dict):
        return _contract({"ok": False, "error": "plugin manifest must be object", "plugin_id": pid})
    manifest.setdefault("id", pid)
    reg = PluginRegistry(root=dest_root)
    installed = reg.install_manifest(manifest)
    return _contract(
        {
            "ok": True,
            "installed": installed,
            "sha256": got,
            "sha_verified": bool(expected),
            "sha_store": str(default_sha_store()),
            "plugin_id": pid,
        }
    )
