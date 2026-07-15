# TASKBOARD — SuperAI

**Backlog:** `docs/FEATURE_BACKLOG.md`  
**Security:** `docs/SECURITY_REVIEW.md`  
**Progress:** `docs/PROGRESS.md`  
**Layout:** `src/cli` (`scli`) · `src/core` (`core`) · entry `superai = scli.main:app`

**Legend:** `[x]` done · `[!]` external host only

---

## Prior tracks

| Track | Status |
|-------|--------|
| A–J foundations | `[x]` |
| Future Plan G1–G12 | `[x]` |
| Depth finish + security harden | `[x]` |
| M1–M8 / S1–S12 / N1–N15 | `[x]` |
| **Wave 2 M9–M13 / S13–S22 / N16–N30** | `[x]` |

---

## Wave 2 commands (highlights)

| Command | ID |
|---------|-----|
| `secrets` / `update` / `diagnose` / `rate-queue` | M10–M13 |
| `diff-edit` / `tdd` / `workspace-index` / `profile-bundle` | S13–S21 |
| `forecast` / `ab-route` / `compliance` / `onboard` | N20–N28 |
| `browse` / `speak` / `listen` / `pr-review` / `notebook` | N17–N26 |
| `memory-forget` / `memory-ttl` / `memory-sync` | N19/N27 |
| `langgraph-export` / `plugin-catalog` / `skill-perms` / `telemetry` / `lang` | N16+ |
| `merge-results` / `validate-json` | S16/S18 |

---

## External smoke (POSTPONED — not code)

- [!] Live multi-provider keys  
- [!] Live Telegram/Slack  
- [!] rclone remote E2E  
- [!] GitHub Pages enable  

## Code gaps closed (no smoke required)

- `[x]` G13 FAISS HNSW depth (`SUPERAI_FAISS_INDEX=hnsw`)  
- `[x]` G14 DuckDuckGo Instant Answer (no HTML scrape)  
- `[x]` G15 GitHub issues/PRs (`superai github`, token or `gh`)  

---

## Last session

| Field | Value |
|-------|--------|
| **When** | 2026-07-16 |
| **What** | Multi-CLI review/advisor board — fill 5 gaps (council CLIs, delegate reviewers, advisor role, templates, structured protocol) |
| **Verify** | `pytest tests/test_multi_cli_advisory.py -q` |

### Multi-CLI review & advisors

- `[x]` `superai review` / `superai advise` structured board  
- `[x]` Council + pr-review default to available `cli:*`  
- `[x]` `cli_delegate_reviewers` (default true) for critic path  
- `[x]` `advisor` role + gemini/grok defaults  
- `[x]` Alt args templates, probe, install_hint  
- `[x]` Protocol v1: verdict / findings / confidence / merge

### Install wizard (opt-in Postgres + host tools)

- `[x]` `superai install` / `install-postgres`  
- `[x]` `postgres_setup.py` detect/install/DB/vector/DSN→config  
- `[x]` Host tools profile prompts; live only with consent  
- `[x]` Bootstrap `-Interactive` / `--with-postgres` |

### pgvector default (Chroma removed)

- `[x]` `src/core/pgvector_store.py` — Postgres+pgvector or SQLite JSON cosine  
- `[x]` `MemoryPalace` default `SUPERAI_MEMORY_BACKEND=pgvector`  
- `[x]` ChromaDB dependency and code paths removed  
- `[x]` FAISS remains opt-in (`SUPERAI_MEMORY_BACKEND=faiss`)  
- `[x]` Tests: `tests/test_pgvector_store.py`

### Review hardening (from full master audit)

- `[x]` Approval denial → `status=error` (not success dry-run)
- `[x]` WriteQueue timeout raises `TimeoutError`
- `[x]` Terminal/external CLI workspace jail fail-closed
- `[x]` CLI/terminal job registry multiproc `store_lock` + merge
- `[x]` Palace: embed outside lock; no unlocked query mutations; FAISS incremental add
- `[x]` SSRF guard (`net_safety`) for browser/webhooks/ecosystem
- `[x]` Central memory redact; MCP `superai_run` mock-default; proposal force gated
- `[x]` Web XSS escape; step_cache atomic; keyring/backup key improvements
- `[x]` Tests: `tests/test_review_hardening.py`

### Concurrent Memory Palace (Phase 3 parallel-safe)

- `[x]` `src/core/store_lock.py` — FileLock + thread RLock + atomic_write_* + WriteQueue  
- `[x]` `MemoryPalace` store/update under `palace.lock`; `get_shared_palace`; `store_queued`  
- `[x]` FAISS / wings / learning history atomic + locked saves  
- `[x]` `memory_sync` merge skip|overwrite|always + optional queue; CLI flags  
- `[x]` central_memory / mcp_context → shared palace  
- `[x]` Tests: `tests/test_memory_concurrency.py`

### Multi-CLI parallel (new)

- `[x]` `ParallelCLIManager` — concurrent external CLIs + job registry  
- `[x]` `cli-parallel` / `cli-jobs` commands  
- `[x]` Terminal dashboard panel for all CLI workers  
- `[x]` Web `/cli-pool` + `/api/cli-pool`  
- `[x]` Agentic fan-out + supervisor synthesis  
- `[x]` Windows-safe concurrent `cli_jobs.json` save (lock + unique tmp + retry)  
- `[x]` Tests: `tests/test_cli_pool.py`

### Multi-terminal parallel (new)

- `[x]` `ParallelTerminalManager` — concurrent shell sessions + registry  
- `[x]` `term-parallel` / `term-jobs` commands  
- `[x]` Dashboard panel (side-by-side with CLI pool)  
- `[x]` Web `/terminals` + `/api/terminals`  
- `[x]` Agentic role terminals + supervisor synthesis  
- `[x]` Safety: dry-run default, argv-only, workspace jail, meta-shell block  
- `[x]` Tests: `tests/test_terminal_pool.py`
