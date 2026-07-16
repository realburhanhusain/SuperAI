# SuperAI improvement plan — strengthen, efficiency, cost, flexibility, completeness

**Created:** 2026-07-16  
**Status:** Planning complete · implementation **not started**  
**Track:** `TASKBOARD.md` · **Resume:** this file + TASKBOARD only  
**Smoke:** Phase 99 / host live smoke remains **POSTPONED** until all planned code work is done  

## Goals

| Goal | Meaning |
|------|---------|
| Strong | Trustworthy results, safe side effects, resilient failover |
| Efficient | Less latency, less wasted work, better caching |
| Cost optimized | Prefer cheap/local when OK; visible spend; budgets that bite |
| Flexible | Profiles, multi-vendor, local OW, CLI workers |
| Complete | Default agent entry, sessions, clear contracts, NL coverage |

## Standing rules

1. Phase tasks in order; thin vertical slice; improve interactively.  
2. Commit + push after each phase.  
3. Update this dashboard + TASKBOARD after each phase.  
4. Unit/offline tests only until global smoke gate.  
5. No live multi-provider smoke mid-stream.  

## Progress dashboard (pre-implementation)

| Phase | Name | Priority | Tasks | Done | Status | % |
|------:|------|----------|------:|-----:|--------|--:|
| 0 | Charter + taskboard + session handoff | Plan | 3 | 3 | complete | 100% |
| 1 | Trust, cost defaults, run contract (Sprint A core) | Must | 6 | 0 | pending | 0% |
| 2 | Agent front door + sessions + permissions | Must | 5 | 0 | pending | 0% |
| 3 | Catalog hygiene + profiles + cost report | Must/Should | 5 | 0 | pending | 0% |
| 4 | Routing efficiency (OW/local prefer, smart boards, cache) | Should | 5 | 0 | pending | 0% |
| 5 | Tool loop + streaming + provider health UX | Should | 5 | 0 | pending | 0% |
| 6 | NL surface expansion + Windows hardening | Should | 4 | 0 | pending | 0% |
| 7 | Docs closeout for improvement track | Docs | 3 | 0 | pending | 0% |
| 8 | Nice-to-have backlog (optional, not blocking) | Nice | — | 0 | backlog | — |
| 99 | Live host smoke (global) | Host | — | 0 | **POSTPONED** | 0% |

**Implementation track (Phases 1–7):** 0 / 33 tasks = **0%** (planning 100%).  
**After Phase 0 only:** planning complete; ready for Phase 1 implementation in a **new compacted session**.

---

## Phase 0 — Planning `[x]`

- [x] P0.1 MoSCoW improvement list agreed in session  
- [x] P0.2 Write this plan file with phases/tasks/%  
- [x] P0.3 TASKBOARD + PENDING_WORK + session summary handoff  

---

## Phase 1 — Trust & cost foundation (Must) `[ ]`

**Maps to:** M2, M4, M5 + cost visibility seed  

- [ ] P1.1 Stable **run/board result contract** (`status`, `mock`, `dry_run`, `model_chain`, `tokens`, `estimated_cost_usd`, `members`, `memory_ids`)  
- [ ] P1.2 Enforce mock/dry_run flags on multi_cli_board, worker pool, ask outputs (never ambiguous success)  
- [ ] P1.3 **Budget hard-stop** mid-orchestrator (already partial — make default-on path clear + tests)  
- [ ] P1.4 Cost fields always populated (mock estimates OK offline)  
- [ ] P1.5 Unit tests for contract + mock labeling  
- [ ] P1.6 Docs snippet + commit/push  

**Exit:** Every major path returns the same contract shape; mock vs live unambiguous.

---

## Phase 2 — Agent front door & safety (Must) `[ ]`

**Maps to:** M1, M6, M7  

- [ ] P2.1 Default CLI entry: no-args / `superai` → NL agent REPL (or explicit `superai ask` as default callback)  
- [ ] P2.2 Permission modes: `plan` | `ask` | `auto` | `yolo` on run/cli-run/ask (config + flag)  
- [ ] P2.3 Wire modes to ExternalCLITool + file-modifying paths  
- [ ] P2.4 **Ask session continuity**: session id, resume, last-N turns inject into orchestrator/context  
- [ ] P2.5 Tests + commit/push  

**Exit:** User can open SuperAI, talk multi-turn, with controlled side effects.

---

## Phase 3 — Catalog hygiene & cost UX (Must/Should) `[ ]`

**Maps to:** M8, S7, S8  

- [ ] P3.1 Registry validation (required fields, warn deprecated/stale ids)  
- [ ] P3.2 `list-models` / `providers` warn when selected model has no key (non-mock)  
- [ ] P3.3 Config **profiles**: `cheap` | `balanced` | `quality` | `local-only` (worker_prefer, critic, budget defaults)  
- [ ] P3.4 Per-task **cost report footer** on run/ask (chain + $ estimate)  
- [ ] P3.5 Tests + commit/push  

**Exit:** Profiles + validation + spend feedback without live APIs.

---

## Phase 4 — Routing efficiency (Should) `[ ]`

**Maps to:** M3, S3, S4  

- [ ] P4.1 Failover/worker pool: prefer local/open-weight when profile=`cheap`|`local-only` or keys missing for premium  
- [ ] P4.2 Smart board sizing (max members by task complexity / config)  
- [ ] P4.3 Extend step/prompt cache to review-board identical subjects (short TTL)  
- [ ] P4.4 Diversity cap (don’t call 5 expensive models by default)  
- [ ] P4.5 Tests + commit/push  

**Exit:** Default paths use fewer/cheaper calls with same feature surface.

---

## Phase 5 — Tool loop & observability (Should) `[ ]`

**Maps to:** S1, S2, S5  

- [ ] P5.1 Minimal in-process tools: Read, Grep/Glob, Write/Edit (workspace-jailed) behind permission mode  
- [ ] P5.2 Orchestrator/ask optional use of in-process tools before CLI delegate  
- [ ] P5.3 Streaming/progress events for run steps (model start/end, board member)  
- [ ] P5.4 Provider health surfaced in `providers --ready` + doctor (circuit open)  
- [ ] P5.5 Tests + commit/push  

**Exit:** Basic agent tool loop exists; progress visible offline/mock.

---

## Phase 6 — Completeness polish (Should) `[ ]`

**Maps to:** S6, S9, S10  

- [ ] P6.1 Opt-in auto Ollama soft-sync on doctor/members (`config`)  
- [ ] P6.2 Expand NL intent map for high-traffic commands still missing  
- [ ] P6.3 Windows PATH/CLI probe hardening (document + targeted fixes)  
- [ ] P6.4 Tests + commit/push  

**Exit:** NL + local discovery + Windows reliability improved.

---

## Phase 7 — Docs closeout (this track) `[ ]`

- [ ] P7.1 Update this dashboard to 100% for Phases 1–7  
- [ ] P7.2 QUICK_REFERENCE + FEATURES/README pointers  
- [ ] P7.3 Checkpoint + final commit/push for improvement track  

---

## Phase 8 — Nice-to-have backlog (not blocking) `[backlog]`

Do **not** start until Phases 1–7 done (unless user re-prioritizes).

| ID | Item |
|----|------|
| N1 | Full Claude-style TUI (diffs, tool traces, compact) |
| N2 | Personal assistant layer (scheduler, Telegram E2E, multi-day goals) |
| N3 | Multimodal images in chat |
| N4 | Subagent graph UI on web dashboard |
| N5 | Auto-refresh remote vendor model lists |
| N6 | Eval harness / model bake-off |
| N7 | Team multi-user palace defaults |
| N8 | Plugin marketplace UX |

---

## Phase 99 — Live smoke `[POSTPONED]`

After **all** planned product work (this track + any concurrent tracks) is code-complete:

- [ ] Multi-provider live keys matrix  
- [ ] Messengers / rclone / Pages / live Postgres as listed in PENDING_WORK  

---

## Mapping: MoSCoW → phases

| Priority | IDs | Phases |
|----------|-----|--------|
| Must | M1–M8 | 1–3 (M1/M6/M7 in 2; M2/M4/M5 in 1; M3/M8 split 3–4) |
| Should | S1–S10 | 3–6 |
| Nice | N1–N8 | 8 backlog |
| Smoke | — | 99 |

---

## Definition of done (improvement track, pre-smoke)

- [ ] Default NL agent entry + multi-turn session  
- [ ] Permission modes enforced on side effects  
- [ ] Stable result contract + mock labeling  
- [ ] Profiles cheap/balanced/quality/local-only  
- [ ] Cost report on runs  
- [ ] Prefer OW/local when configured  
- [ ] Minimal in-process tools + streaming progress  
- [ ] Plan dashboard 100% for Phases 1–7  
- [ ] Smoke still postponed  

---

## Resume (new session — minimal tokens)

```text
1. Read docs/IMPROVEMENT_PLAN.md (dashboard + current phase tasks)
2. Read TASKBOARD.md → Improvement track
3. Implement ONLY next unchecked phase tasks (start Phase 1)
4. pytest for touched modules; commit; push; update dashboard %
5. Do NOT start Phase 99 smoke
6. Do NOT expand Phase 8 nice-to-haves unless plan says so
```
