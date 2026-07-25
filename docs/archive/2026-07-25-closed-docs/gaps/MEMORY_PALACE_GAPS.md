# Memory Palace gaps — closed (Wings/Rooms + clustering)

**Updated:** 2026-07-16

## Vector backend (default: pgvector)

| Backend | When |
|---------|------|
| **pgvector** (default) | Postgres DSN (`SUPERAI_MEMORY_DSN=postgresql+psycopg://…`) with `vector` extension; multi-session R/W safe |
| **SQL cosine (SQLite)** | Default offline path: `~/.superai/memory/palace.sqlite` when no Postgres DSN — same API, brute-force cosine |
| **FAISS** | Opt-in only: `SUPERAI_MEMORY_BACKEND=faiss` |
| **memory** | Opt-in only: `SUPERAI_MEMORY_BACKEND=memory` (RAM, tests) |
| ~~ChromaDB~~ | **Removed** (unsafe concurrent multi-session local store) |
| ~~Qdrant~~ | Not supported |

Env: `SUPERAI_MEMORY_BACKEND`, `SUPERAI_MEMORY_DSN`, `SUPERAI_EMBEDDING_HASH=1` for offline hash embeddings.

### Opt-in Postgres install (not automatic)

Postgres is **never** installed silently (live still requires confirm). During guided
install the Memory Palace Postgres question defaults to **Yes** (user can decline).

```text
superai install                          # interactive: host tools + optional Postgres
superai install --with-postgres --live --yes
superai install-postgres --setup-only --live
```

Flow when opted in: detect Postgres → optional winget/brew/apt install → create DB/user → `CREATE EXTENSION vector` → write `memory_dsn` + `memory_backend=pgvector` into `~/.superai/config.json`.

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

## P3 — cluster → rooms + palace browser

| Feature | API / CLI |
|---------|-----------|
| Suggest rooms from clusters | `suggest_rooms_from_clusters` · `memory-palace suggest` |
| Auto-promote rooms into catalog | `auto_promote_rooms(apply=…)` · `memory-palace promote [--apply] [--reassign]` |
| Browser snapshot | `browser_snapshot` · `memory-palace snapshot` · dashboard Memory panel · web `/palace` |
| Web API | `GET /api/palace` · `GET /api/palace/suggest` · `POST /api/palace/promote` |
| MCP | `superai_memory_palace` actions: `suggest` · `promote` · `snapshot` |

Promote is **dry-run by default** (`--apply` to write). `--reassign` also updates memory metadata wing/room for cluster members.

## Phase 3 — concurrent-safe multi-CLI / multi-process writes

| Layer | Mechanism |
|-------|-----------|
| Cross-process + thread lock | `src/core/store_lock.py` — `FileLock` (msvcrt/fcntl) + per-path RLock via `store_lock()` |
| Atomic file writes | `atomic_write_json` / `atomic_write_text` / `atomic_write_bytes` (unique tmp + `os.replace` + Windows retry) |
| Shared palace | `get_shared_palace(persist_directory)` singleton — prefer over many `MemoryPalace()` instances |
| Store path | `MemoryPalace.store` / `update_metadata` under `palace.lock` |
| Optional write queue | `store_queued` → process-wide `WriteQueue` for multi-CLI fan-out |
| FAISS sidecar | `faiss.lock` + atomic meta/index save on `add`/`save` |
| Wings assignments | `wings.lock` + re-read/merge on `save` |
| Learning history | `learning_history.lock` + atomic JSON append |
| Encrypted sync | `export_encrypted_memory` under lock; `import_encrypted_memory(merge=skip\|overwrite\|always, use_queue=…)` |
| Call sites | `central_memory`, `mcp_context` use `get_shared_palace()` |
| CLI | `memory-sync --merge skip\|overwrite\|always` · `--queue` |

**Tests:** `tests/test_memory_concurrency.py` (thread stores, queue, singleton, wings, merge-skip).
