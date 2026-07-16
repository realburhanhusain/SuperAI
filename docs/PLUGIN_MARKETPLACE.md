# SuperAI Plugin Marketplace Browse (Phase 8 N8 / V1-N8)

**Status:** Production-ready offline marketplace **browse**  
**Module:** `src/core/plugin_catalog.py`  
**Bundled catalog:** `src/core/data/plugin_marketplace_catalog.json`  
**CLI:** `superai plugin-catalog`  
**Tests:** `tests/test_plugin_marketplace_n8.py`  
**Related:** M097 (sha256 install), MOS-N5 (plugin sha store), `plugin_registry.py`

---

## Purpose

V1-N8 delivers a **real plugin marketplace browse experience**:

- Offline-first catalog shipped with SuperAI (no network required)
- Search, category/tag filters, sort, pagination limit
- Installed vs available overlay from local `PluginRegistry`
- Get plugin by id, list categories, marketplace status
- Optional remote catalog URL (JSON) with offline fallback
- Optional install from remote entry with **sha256 verification**

This is **browse + safe install hooks**, not a payment marketplace or community app store.

---

## Architecture

```text
superai plugin-catalog
        │
        ▼
 plugin_catalog.browse_catalog()
        │
        ├─ load_bundled_catalog()  ← data/plugin_marketplace_catalog.json
        ├─ OR fetch_catalog(url)   ← optional remote JSON
        ├─ _overlay_installed()    ← PluginRegistry.list_plugins()
        ├─ filter (query/tag/category)
        └─ sort + limit
```

### Catalog schema (`superai.plugin_catalog.v1`)

```json
{
  "schema": "superai.plugin_catalog.v1",
  "name": "…",
  "version": "1.0.0",
  "updated": "YYYY-MM-DD",
  "plugins": [
    {
      "id": "core.memory",
      "name": "Memory Palace",
      "version": "0.1.0",
      "category": "memory",
      "description": "…",
      "tags": ["memory", "palace"],
      "author": "SuperAI",
      "license": "Apache-2.0",
      "source": "builtin|catalog",
      "entry": "core.memory_palace",
      "url": null,
      "sha256": null
    }
  ]
}
```

### Install safety

- Remote install requires `id` + `url` pointing at a **JSON manifest** (not zip).
- Default `require_sha=True`: sha256 from entry or `~/.superai/plugin_sha/<id>.sha256`.
- Verified hashes are persisted under `~/.superai/plugin_sha/`.

---

## CLI usage

```powershell
# Marketplace status (counts, paths)
superai plugin-catalog --status

# Browse bundled catalog (offline)
superai plugin-catalog

# Search
superai plugin-catalog -q memory
superai plugin-catalog --tag builtin
superai plugin-catalog --category messaging

# Sort / limit
superai plugin-catalog --sort installed -n 20

# Categories
superai plugin-catalog --categories

# Show one plugin
superai plugin-catalog --show core.memory

# Remote catalog (optional)
superai plugin-catalog https://example.com/catalog.json -q security

# Install from remote entry (sha required by default)
superai plugin-catalog https://example.com/catalog.json --install sample.hello
```

### Programmatic API

```python
from core.plugin_catalog import (
    browse_catalog,
    get_plugin,
    list_categories,
    marketplace_status,
    install_from_catalog_entry,
)

status = marketplace_status()
browse = browse_catalog(query="memory", category="memory", sort="name", limit=20)
one = get_plugin("core.memory")
cats = list_categories()
```

---

## Result contract

Browse/status/get responses include stable fields:

| Field | Meaning |
|-------|---------|
| `ok` | Success |
| `contract` | `superai.result.v1` |
| `plugins` / `plugin` | Entries |
| `count` / `total_matched` / `total_catalog` | Sizing |
| `source` | `bundled`, remote URL, or `bundled_fallback` |
| `installed` | Overlay boolean per plugin |

---

## Testing

```powershell
$env:PYTHONPATH="src"
pytest tests/test_plugin_marketplace_n8.py -q
pytest tests/test_phase8.py::test_tenant_and_plugins -q
```

Coverage includes:

- Bundled catalog load and schema
- Search / tag / category filters
- Sort and limit
- Installed overlay
- Get by id (found / not found)
- Categories aggregation
- Status summary
- Contract shape
- Remote failure → bundled fallback
- SHA verify helper
- Install rejects missing sha/url

---

## Definition of done (V1-N8)

| Criterion | Status |
|-----------|--------|
| Production-ready browse code | Yes — `plugin_catalog.py` + bundled JSON |
| Thorough documentation | Yes — this file + PHASE8 N8 |
| Fully tested | Yes — `test_plugin_marketplace_n8.py` |

**Out of scope for N8:** payments, ratings, community publishing UI, binary zip installs.

---

## Files

| Path | Role |
|------|------|
| `src/core/plugin_catalog.py` | Browse/install API |
| `src/core/data/plugin_marketplace_catalog.json` | Bundled catalog |
| `src/core/plugin_registry.py` | Local install state overlay |
| `src/cli/main.py` | `plugin-catalog` command |
| `docs/PLUGIN_MARKETPLACE.md` | This document |
| `tests/test_plugin_marketplace_n8.py` | Thorough unit tests |
