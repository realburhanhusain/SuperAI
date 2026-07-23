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

## External smoke (POSTPONED — after all planned implementation)

**Policy:** finish planned product work first; smoke is last. See `docs/UNIVERSAL_MODELS_PLAN.md` Phase 99.

- [!] Live multi-provider keys (all vendors / open-weight / NVIDIA / Ollama)  
- [!] Live Telegram/Slack  
- [!] rclone remote E2E  
- [!] GitHub Pages enable  
- [!] Live Postgres + pgvector server  

## Code gaps closed (no smoke required)

- `[x]` G13 FAISS HNSW depth (`SUPERAI_FAISS_INDEX=hnsw`)  
- `[x]` G14 DuckDuckGo Instant Answer (no HTML scrape)  
- `[x]` G15 GitHub issues/PRs (`superai github`, token or `gh`)  

---

## MoSCoW 100% honesty track

| Bucket | Status |
|--------|--------|
| Must M1–M8 | `[x]` code + `tests/test_moscow_100.py` / related |
| Should S1–S10 | `[x]` |
| Nice N1–N7 | `[x]` |
| Nice N8 live smoke | `[!]` harness only — `superai smoke-harness` |
| Not-important W1–W8 | `[x]` `docs/NOT_IMPORTANT_PLAN.md` |
| SuperAI multi-agent | `[x]` `superai` / `superai agent` · `docs/SUPERAI_AGENT.md` |
| Improvement V4 A–C | `[x]` `docs/IMPROVEMENT_V4_PLAN.md` · `tests/test_improvement_v4.py` |
| Truth file | `docs/MOSCOW_100_PLAN.md` |

## Last session

| Field | Value |
|-------|--------|
| **When** | 2026-07-23 |
| **What** | Resume unfinished foundation depth: **V2-B3** session_compact edge cases (role/content turns, done-checkbox/status filtering, nested message parts); **V5-M4/M002** cost estimate honesty (mock never claims usage, local stays zero_local, is_estimate/estimate_method); WIP SUPERAI_MOCK_MODE mock-path honesty in model_caller |
| **Verify** | \pytest tests/test_session_compact_v2b3.py tests/test_cost_accounting_m002.py tests/test_foundation_lift.py::test_session_compact_preserves_todos -q\ (20 passed) |
| **Still open** | Broader V6 foundation backlog (live streaming providers, learning UX productization, MCP parity matrix, Phase 99 host smoke) — not claimed closed |
| **Prior** | 2026-07-20 M001/M002/M008/M017/M018 foundation close at f874837 |

### Improvement track (strong / efficient / cost / flexible / complete)

**Resume:** `docs/IMPROVEMENT_PLAN.md`  
**Smoke:** postponed (Phase 99).

| Phase | Status | % |
|------:|--------|--:|
| 0 Planning + handoff | `[x]` | 100 |
| 1 Trust & cost foundation | `[x]` | 100 |
| 2 Agent front door + sessions + permissions | `[x]` | 100 |
| 3 Catalog hygiene + profiles + cost report | `[x]` | 100 |
| 4 Routing efficiency + board cache | `[x]` | 100 |
| 5 Tool loop + health UX | `[x]` | 100 |
| 6 NL + Windows PATH + auto Ollama | `[x]` | 100 |
| 7 Docs closeout | `[x]` | 100 |
| 8 Nice-to-have (N1–N8) | `[x]` foundations | 100 |
| 99 Live smoke | postponed | 0 |

**Implementation % (Phases 1–8):** **100%** (smoke still postponed)  
**Phase 8 plan:** `docs/PHASE8_PLAN.md`

---

## Prior session (universal models)

| Field | Value |
|-------|--------|
| **When** | 2026-07-16 |
| **What** | Universal models Phases 0–5 **code complete**; smoke Phase 99 postponed |
| **Plan** | `docs/UNIVERSAL_MODELS_PLAN.md` |
| **Verify** | `pytest tests/test_provider_catalog.py tests/test_model_discovery.py tests/test_member_selection.py tests/test_nl_intent.py -q` |

### Universal models (multi-vendor / open-weight)

**Resume:** `UNIVERSAL_MODELS_PLAN.md` → dashboard → next open task (only Phase 99).

| Phase | Status | % |
|-------|--------|--:|
| 0 Charter | `[x]` | 100 |
| 1 Foundation | `[x]` | 100 |
| 2 Catalog + filters | `[x]` | 100 |
| 3 Doctor/discovery auto | `[x]` | 100 |
| 4 NL + pick filters | `[x]` | 100 |
| 5 Docs closeout | `[x]` | 100 |
| **Code total** | **done** | **100** |
| 99 Live smoke | `[!]` postponed | 0 |

**Deliverables**

- `[x]` provider_catalog + registry-aware ModelCaller  
- `[x]` model_discovery (Ollama sync, register, provider_status)  
- `[x]` models.json multi-vendor (~40) incl. NVIDIA own + hosted OW  
- `[x]` CLI: providers, models-sync-ollama, models-register, members/list-models filters  
- `[x]` doctor llm_providers + ollama_models; discovery expanded keys  
- `[x]` NL vendor hints (deepseek/kimi/glm/nvidia/…)  
- `[!]` Live multi-key smoke → Phase 99 only

---

## Prior last session (multi-CLI board)

| Field | Value |
|-------|--------|
| **When** | 2026-07-16 |
| **What** | Multi-CLI review/advisor board — fill 5 gaps |
| **Verify** | `pytest tests/test_multi_cli_advisory.py -q` |

### Multi-CLI review & advisors

- `[x]` `superai review` / `superai advise` structured board  
- `[x]` Council + pr-review default to available `cli:*`  
- `[x]` `cli_delegate_reviewers` (default false; opt-in) for critic path  
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
