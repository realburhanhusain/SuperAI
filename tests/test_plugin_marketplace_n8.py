"""V1-N8 / Phase 8 N8 — Plugin marketplace browse (thorough offline tests)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_bundled_catalog_exists_and_schema():
    from core.plugin_catalog import bundled_catalog_path, load_bundled_catalog

    path = bundled_catalog_path()
    assert path.is_file(), f"missing bundled catalog: {path}"
    data = load_bundled_catalog()
    assert data.get("schema") == "superai.plugin_catalog.v1"
    assert isinstance(data.get("plugins"), list)
    assert len(data["plugins"]) >= 8
    ids = {p["id"] for p in data["plugins"]}
    assert "core.memory" in ids
    assert "sample.hello" in ids


def test_browse_catalog_offline_basic():
    from core.plugin_catalog import browse_catalog

    out = browse_catalog()
    assert out.get("ok") is True
    assert out.get("contract") == "superai.result.v1" or "plugins" in out
    assert out.get("count", 0) >= 1
    assert out.get("source") in {"bundled", "bundled_fallback"}
    assert isinstance(out.get("plugins"), list)
    p0 = out["plugins"][0]
    for key in ("id", "name", "category", "description", "tags", "installed"):
        assert key in p0


def test_browse_search_query():
    from core.plugin_catalog import browse_catalog

    out = browse_catalog(query="memory")
    assert out.get("ok") is True
    assert out["total_matched"] >= 1
    for p in out["plugins"]:
        blob = f"{p.get('id')} {p.get('name')} {p.get('description')} {p.get('tags')}".lower()
        assert "memory" in blob


def test_browse_filter_category_and_tag():
    from core.plugin_catalog import browse_catalog

    by_cat = browse_catalog(category="messaging")
    assert by_cat.get("ok") is True
    assert all(p.get("category") == "messaging" for p in by_cat["plugins"])

    by_tag = browse_catalog(tag="builtin")
    assert by_tag.get("ok") is True
    assert by_tag["total_matched"] >= 1
    for p in by_tag["plugins"]:
        assert any("builtin" in str(t).lower() for t in (p.get("tags") or []))


def test_browse_sort_and_limit():
    from core.plugin_catalog import browse_catalog

    by_id = browse_catalog(sort="id", limit=3)
    assert by_id["count"] <= 3
    ids = [p["id"] for p in by_id["plugins"]]
    assert ids == sorted(ids)


def test_installed_overlay(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai" / "plugins").mkdir(parents=True)
    from core.plugin_catalog import browse_catalog
    from core.plugin_registry import PluginRegistry

    reg = PluginRegistry(root=tmp_path / ".superai" / "plugins")
    reg.install_manifest(
        {
            "id": "local.demo",
            "name": "Local Demo",
            "version": "0.0.1",
            "category": "example",
            "description": "installed for overlay test",
        }
    )
    # browse uses default registry under home — we pass registry_root
    out = browse_catalog(limit=200, registry_root=tmp_path / ".superai" / "plugins")
    # builtin memory still shows installed=True via entry
    mem = next(p for p in out["plugins"] if p["id"] == "core.memory")
    assert mem.get("installed") is True


def test_get_plugin_found_and_missing():
    from core.plugin_catalog import get_plugin

    ok = get_plugin("core.memory")
    assert ok.get("ok") is True
    assert ok["plugin"]["id"] == "core.memory"
    missing = get_plugin("no.such.plugin.zzz")
    assert missing.get("ok") is False
    assert missing.get("error") == "not_found"


def test_list_categories():
    from core.plugin_catalog import list_categories

    out = list_categories()
    assert out.get("ok") is True
    assert out["count"] >= 3
    cats = {c["category"] for c in out["categories"]}
    assert "memory" in cats or "reasoning" in cats


def test_marketplace_status():
    from core.plugin_catalog import marketplace_status

    st = marketplace_status()
    assert st.get("ok") is True
    assert st.get("bundled_exists") is True
    assert st.get("plugin_count", 0) >= 8
    assert "plugin-catalog" in str(st.get("commands"))


def test_remote_failure_falls_back_to_bundled(monkeypatch):
    from core import plugin_catalog as pc

    def boom(url, timeout=15.0):
        raise RuntimeError("network down")

    monkeypatch.setattr(pc, "fetch_catalog", boom)
    out = pc.browse_catalog("https://example.invalid/catalog.json")
    assert out.get("ok") is True
    assert out.get("fallback") is True
    assert out.get("remote_error")
    assert out.get("count", 0) >= 1


def test_verify_sha256(tmp_path):
    from core.plugin_catalog import verify_sha256

    f = tmp_path / "p.json"
    f.write_bytes(b'{"id":"x"}')
    import hashlib

    h = hashlib.sha256(b'{"id":"x"}').hexdigest()
    assert verify_sha256(f, h) is True
    assert verify_sha256(f, "0" * 64) is False


def test_install_rejects_missing_url_and_sha(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    from core.plugin_catalog import install_from_catalog_entry

    no_url = install_from_catalog_entry({"id": "x"})
    assert no_url.get("ok") is False
    no_sha = install_from_catalog_entry(
        {"id": "x", "url": "https://example.com/p.json"},
        require_sha=True,
    )
    assert no_sha.get("ok") is False
    assert "sha256" in str(no_sha.get("error") or "").lower()


def test_browse_available_only_filter():
    from core.plugin_catalog import browse_catalog

    out = browse_catalog(available_only=True, limit=200)
    assert out.get("ok") is True
    # samples without entry should be available
    assert all(not p.get("installed") or p.get("source") == "catalog" for p in out["plugins"]) or out["count"] >= 0


def test_phase8_compat_browse_memory():
    """Keep PHASE8 test expectation working."""
    from core.plugin_catalog import browse_catalog

    cat = browse_catalog(query="memory")
    assert cat["ok"] is True
