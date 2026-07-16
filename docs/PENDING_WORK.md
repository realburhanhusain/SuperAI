# SuperAI — Pending work

**Updated:** 2026-07-16  

Implementation of planned features, backlog waves, deferred code gaps
(G13–G15), concurrent Memory Palace, review hardening, **pgvector default**,
and **opt-in install wizard** (host tools + Postgres) is **complete in code**.

## Postponed (host / external smoke only)

1. Live multi-provider smoke with real API keys  
2. Live Telegram/Slack E2E  
3. rclone cloud remote E2E  
4. GitHub Pages enablement in repo settings  
5. Live Postgres + `vector` extension smoke on a real server (suite uses SQLite cosine offline)

## Explicitly not planned

- ChromaDB backend or Chroma → SQL migrator (no existing user data; Chroma removed)

## Recently closed (code)

| Item | Notes |
|------|--------|
| G13–G15 | FAISS HNSW, DDG Instant Answer, GitHub issues/PRs |
| Concurrent palace | store_lock, shared palace, sync merge |
| Review hardening | approval/jail/SSRF/redact/MCP/XSS |
| pgvector default | Chroma removed; SQLite cosine offline; FAISS opt-in |
| Install wizard | `superai install`, host tools prompts, Postgres default Yes |
| Semantic tests | Stricter Memory Palace query/delete asserts |
| Unified members | API models + CLIs + inner models on review/advise/council |
| Unified workers | Same catalog for orchestrator worker pool + failover |
| Universal NL agent | `superai ask` / REPL — product routes + agentic fallback for everything |
| Universal models Phase 1 | Multi-vendor + open-weight + NVIDIA + Ollama sync (see UNIVERSAL_MODELS.md) |

## Not pending

- Phases 1–8 modules  
- Feature backlog M1–M13, S1–S22, N1–N30 (in-repo)  

See `TASKBOARD.md` and `docs/FEATURE_BACKLOG.md`.
