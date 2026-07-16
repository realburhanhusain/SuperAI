# SuperAI — Pending work

**Updated:** 2026-07-16  

Implementation of planned features, backlog waves, deferred code gaps
(G13–G15), concurrent Memory Palace, review hardening, **pgvector default**,
and **opt-in install wizard** (host tools + Postgres) is **complete in code**.

## Postponed (host / external smoke — only after all planned code is done)

**Policy:** do not run live smoke mid-development. Complete planned features first; smoke is the final host gate.

1. Live multi-provider smoke with real API keys (Phase 99 / UNIVERSAL_MODELS_PLAN)  
2. Live Telegram/Slack E2E  
3. rclone cloud remote E2E  
4. GitHub Pages enablement in repo settings  
5. Live Postgres + `vector` extension smoke on a real server (suite uses SQLite cosine offline)

## Explicitly not planned

- ChromaDB backend or Chroma → SQL migrator (no existing user data; Chroma removed)

## Improvement track status

| Item | Notes |
|------|--------|
| Improvement Phases 1–7 | **100%** — `docs/IMPROVEMENT_PLAN.md` |
| Phase 8 N1–N8 | **100% foundations** — `docs/PHASE8_PLAN.md` |
| Improvement V2 Sprints A–D | **100%** — `docs/IMPROVEMENT_V2_PLAN.md` |
| Improvement V3 Sprints A–D | **100%** — tool protocol, failover, cost on run, tenant write, goals safety — `docs/IMPROVEMENT_V3_PLAN.md` |
| Phase 99 live smoke | **Postponed** |

## Recently closed (code)

| Item | Notes |
| G13–G15 | FAISS HNSW, DDG Instant Answer, GitHub issues/PRs |
| Concurrent palace | store_lock, shared palace, sync merge |
| Review hardening | approval/jail/SSRF/redact/MCP/XSS |
| pgvector default | Chroma removed; SQLite cosine offline; FAISS opt-in |
| Install wizard | `superai install`, host tools prompts, Postgres default Yes |
| Semantic tests | Stricter Memory Palace query/delete asserts |
| Unified members | API models + CLIs + inner models on review/advise/council |
| Unified workers | Same catalog for orchestrator worker pool + failover |
| Universal NL agent | `superai ask` / REPL — product routes + agentic fallback for everything |
| Universal models Phases 0–5 | Code complete — plan in UNIVERSAL_MODELS_PLAN.md |
| Phase 99 multi-provider live smoke | **Postponed** until after complete development |

## Not pending

- Phases 1–8 modules  
- Feature backlog M1–M13, S1–S22, N1–N30 (in-repo)  

See `TASKBOARD.md` and `docs/FEATURE_BACKLOG.md`.
