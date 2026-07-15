# Checkpoint: pgvector-default-chroma-removed

- **When:** 2026-07-16 01:29:27 +03:00
- **Host:** IT-DV-110-L
- **Repo:** C:\Users\burhan.husain\Documents\Personal\github\SuperAI
- **Git HEAD:** a2d4048
- **Git status:** ## master...origin/master
- **Pytest:** skipped

## Recovery

1. Open this repo path.
2. Read `TASKBOARD.md` Last session + first `[ ]` / `[~]` item.
3. If tree is corrupted, restore from last git commit: `git status` / `git log -5 --oneline` / `git stash list`.
4. Runtime data (not always in git): `~/.superai/` â€” use `superai backup-verify` / `superai restore`.

## TASKBOARD snapshot (truncated)

```markdown
# TASKBOARD â€” SuperAI

**Backlog:** `docs/FEATURE_BACKLOG.md`  
**Security:** `docs/SECURITY_REVIEW.md`  
**Progress:** `docs/PROGRESS.md`  
**Layout:** `src/cli` (`scli`) Â· `src/core` (`core`) Â· entry `superai = scli.main:app`

**Legend:** `[x]` done Â· `[!]` external host only

---

## Prior tracks

| Track | Status |
|-------|--------|
| Aâ€“J foundations | `[x]` |
| Future Plan G1â€“G12 | `[x]` |
| Depth finish + security harden | `[x]` |
| M1â€“M8 / S1â€“S12 / N1â€“N15 | `[x]` |
| **Wave 2 M9â€“M13 / S13â€“S22 / N16â€“N30** | `[x]` |

---

## Wave 2 commands (highlights)

| Command | ID |
|---------|-----|
| `secrets` / `update` / `diagnose` / `rate-queue` | M10â€“M13 |
| `diff-edit` / `tdd` / `workspace-index` / `profile-bundle` | S13â€“S21 |
| `forecast` / `ab-route` / `compliance` / `onboard` | N20â€“N28 |
| `browse` / `speak` / `listen` / `pr-review` / `notebook` | N17â€“N26 |
| `memory-forget` / `memory-ttl` / `memory-sync` | N19/N27 |
| `langgraph-export` / `plugin-catalog` / `skill-perms` / `telemetry` / `lang` | N16+ |
| `merge-results` / `validate-json` | S16/S18 |

---

## External smoke (POSTPONED â€” not code)

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
| **What** | Memory Palace default backend â†’ pgvector; remove ChromaDB |
| **Verify** | `pytest tests/test_pgvector_store.py -q` Â· full suite **207 passed** |

### pgvector default (Chroma removed)

- `[x]` `src/core/pgvector_store.py` â€” Postgres+pgvector or SQLite JSON cosine  
- `[x]` `MemoryPalace` default `SUPERAI_MEMORY_BACKEND=pgvector`  
- `[x]` ChromaDB dependency and code paths removed  
- `[x]` FAISS remains opt-in (`SUPERAI_MEMORY_BACKEND=faiss`)  
- `[x]` Tests: `tests/test_pgvector_store.py`

### Review hardening (from full master audit)

- `[x]` Approval denial â†’ `status=error` (not success dry-run)
- `[x]` WriteQueue timeout raises `TimeoutError`
- `[x]` Terminal/external CLI workspace jail fail-closed
- `[x]` CLI/terminal job registry multiproc `store_lock` + merge
- `[x]` Palace: embed outside lock; no unlocked query mutations; FAISS incremental add
- `[x]` SSRF guard (`net_safety`) for browser/webhooks/ecosystem
- `[x]` Central memory redact; MCP `superai_run` mock-default; proposal force gated
- `[x]` Web XSS escape; step_cache atomic; keyring/backup key improvements
- `[x]` Tests: `tests/test_review_hardening.py`

### Concurrent Memory Palace (Phase 3 parallel-safe)

- `[x]` `src/core/store_lock.py` â€” FileLock + thread RLock + atomic_write_* + WriteQueue  
- `[x]` `MemoryPalace` store/update under `palace.lock`; `get_shared_palace`; `store_queued`  
- `[x]` FAISS / wings / learning history atomic + locked saves  
- `[x]` `memory_sync` merge skip|overwrite|always + optional queue; CLI flags  
- `[x]` central_memory / mcp_context â†’ shared palace  
- `[x]` Tests: `tests/test_memory_concurrency.py`

### Multi-CLI parallel (new)

- `[x]` `ParallelCLIManager` â€” concurrent external CLIs + job registry  
- `[x]` `cli-parallel` / `cli-jobs` commands  
- `[x]` Terminal dashboard panel for all CLI workers  
- `[x]` Web `/cli-pool` + `/api/cli-pool`  
- `[x]` Agentic fan-out + supervisor synthesis  
- `[x]` Windows-safe concurrent `cli_jobs.json` save (lock + unique tmp + retry)  
- `[x]` Tests: `tests/test_cli_pool.py`

### Multi-terminal parallel (new)

- `[x]` `ParallelTerminalManager` â€” concurrent shell sessions + registry  
- `[x]` `term-parallel` / `term-jobs` commands  
- `[x]` Dashboard panel (side-by-side with CLI pool)  
- `[x]` Web `/terminals` + `/api/terminals`  
- `[x]` Agentic role terminals + supervisor synthesis  
- `[x]` Safety: dry-run defa
...[truncated]...
```
