# Memory Datasets / Namespaces — Memory Roadmap P7

**Status:** Implemented  
**Date:** 2026-07-23  
**Module:** `src/core/memory_dataset.py`  
**CLI:** `superai dataset list|create|use|status|export|import|forget`  
**MCP:** `superai_dataset`  
**Aligns with:** `palace_tenant` (tenant = multi-user; dataset = multi-topic)  
**Coordination:** Memory track only — does not modify AGY scorecard modules.

## Model

| Layer | Scope |
|-------|--------|
| **Tenant** (`palace_tenant`) | Multi-user / org isolation |
| **Dataset** (this module) | Multi-topic namespaces under a tenant |

### Built-in datasets

| Id | Purpose |
|----|---------|
| `default` | Legacy / unspecified (backward compatible) |
| `personal` | Personal notes |
| `d360` | D360 work knowledge |
| `superai` | SuperAI product memory |
| `scratch` | Ephemeral experiments (safe to forget) |
| `shared` | Cross-dataset readable facts |

## Active dataset resolution

1. Explicit CLI/API `--dataset` / `dataset_id`  
2. Env `SUPERAI_DATASET_ID`  
3. Config `active_dataset` / registry `active`  
4. Fallback `default`

Registry file: `~/.superai/memory/datasets_registry.json`  
(override with `SUPERAI_DATASETS_PATH`)

Disable default query scoping: `SUPERAI_DATASET_SCOPE=off` (or `all`).

## Isolation (default query mode)

- Palace `query_semantic` and recall **filter to active dataset** (+ **`shared`**).  
- Graph queries/path already accept `dataset_id`; recall passes active id.  
- Store auto-stamps `metadata.dataset_id` + tag `dataset:<id>` when missing.

**DoD:** no cross-dataset leakage in default query mode (covered by tests).

## CLI

```powershell
superai dataset list
superai dataset create work-uat -D "UAT work"
superai dataset use d360
superai dataset status
superai dataset status scratch

superai dataset export d360 -o d360-mem.zip
superai dataset import d360-mem.zip --dataset d360_copy
superai dataset import d360-mem.zip --dry-run

superai dataset forget scratch --yes
```

## Export / import

Zip contains:

- `manifest.json`
- `memories.json` — palace rows for that dataset
- `kg_nodes.json` / `kg_edges.json`

Import re-stores memories and upserts nodes (edges re-linked when `from_name`/`to_name` present).

## Forget

Requires `--yes`. Deletes palace memories + KG nodes/edges for the id. Removes non-builtin registry entries.

## MCP

Tool **`superai_dataset`**: `action=list|create|use|status|export|import|forget` with `dataset_id`, `path`, `yes`, `dry_run`.

## Library

```python
from core.memory_dataset import get_registry, resolve_dataset_id, export_dataset

reg = get_registry()
reg.use("d360")
assert resolve_dataset_id(None) == "d360"
export_dataset("d360", dest=Path("d360.zip"))
```

## Tests

`tests/test_memory_dataset_p7.py` — builtins, create/use, store stamp, isolation, shared visibility, KG delete, export/import, forget gate, recall scope.

## Honest limits

- Edge re-import needs names on edges; id-only neighbor dumps may skip some edges.  
- Session buffer has its own `dataset_id` column (P3) but dataset forget does not wipe sessions (promote first if needed).  
- Tenant and dataset filters compose; empty results may mean either isolation layer.
