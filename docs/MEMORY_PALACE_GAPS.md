# Memory Palace gaps — closed (Wings/Rooms + clustering)

**Updated:** 2026-07-15

## Observations → status

| Observation | Status |
|-------------|--------|
| Wings & Rooms only partial / try-except sidecar | **Closed** — wing/room on every `store`, query filters, layout/browse APIs |
| Clustering basic (no ML) | **Improved** — numpy k-means on embeddings (`method=embedding\|auto`) + wing/tag fallbacks |

## Now first-class

- `MemoryPalace.store(..., wing=, room=, auto_wings=True)` writes `metadata.wing` / `metadata.room`
- Sidecar `WingsManager.assign` still updated for assignment index
- `query_semantic(..., wing=, room=)`
- `query_by_location(wing, room)`
- `palace_layout()` counts by wing→room
- `cluster_memories(method=auto|embedding|wing|tag)`
- Richer `WingsManager.classify_task_type` / `classify_from_metadata`
- CLI: `memory-palace`, `memory-clusters --method`, `wings stats|browse|sync`
- MCP: wing/room on `superai_memory_search`; tool `superai_memory_palace`

## Defaults wings

technical · operations · product · learning · agentic
