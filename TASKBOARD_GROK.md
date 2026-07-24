# TASKBOARD — Grok (Memory / Learning / Routing Honesty)

**Owner:** Grok  
**Peer board:** [`TASKBOARD_AGY.md`](TASKBOARD_AGY.md)  
**Index:** [`TASKBOARD.md`](TASKBOARD.md)  
**Scorecard:** [`docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md`](docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md)  
**Strict bar:** production code + thorough docs + full tests. Promote scorecard rows only with evidence.  
**Created:** 2026-07-24 · **Detail expansion:** 2026-07-24 · **G1–G4 implementation:** 2026-07-24  

**Legend:** `[ ]` open · `[~]` in progress · `[x]` done · `[!]` host-gated  

---

## Mission

Close the **9 near-complete Musts** (80–90%) that need product depth, routing proof, streaming honesty, dashboard completeness, or host smoke — **without** re-opening archived memory/hardening handoffs.

| Wave | IDs | Theme | Target | Status |
|------|-----|--------|--------|--------|
| G1 | M061–M063 | Learning lifecycle product | 85% → 100% | **[x] DONE** |
| G2 | M068, M050 | Preferences + bandit continuous product | 80–85% → 100% | **[x] DONE** |
| G3 | M027, V4-M4 | Real streaming provider coverage | 85% → 100% offline DoD | **[x] DONE** offline |
| G4 | M100 | Honest mock vs live dashboard | 80% → 100% | **[x] DONE** |
| G5 | M089 | Live multi-provider smoke | host when keys | **[!]** open |

---

## Prior wave (archived — do not re-open)

| Track | Status | Location |
|-------|--------|----------|
| Memory P1–P9 offline + integrity handoff | **DONE** | `docs/archive/2026-07-24-wave-handoffs/GROK_HANDOFF_PENDING_AND_INCOMPLETE.md` |
| AGY hardening reassignment residuals | **DONE** | same archive |

---

## Wave G1 — Learning lifecycle product (M061–M063) — **DONE**

**Docs:** [`docs/LEARNING_LIFECYCLE.md`](docs/LEARNING_LIFECYCLE.md)  
**Tests:** `tests/test_learning_lifecycle_m061_m063.py` (22 passed)

### G1.1 M061 promote durable — [x]

- [x] Operator UX preview (candidates eligible/skipped with reasons)
- [x] `learning promote --dry-run` no mutate
- [x] In-place promote (no re-store duplicates); write-back loop documented
- [x] Session vs durable promote distinction documented
- [x] Tests: dry-run, below-threshold, id-not-found, product loop
- [x] Scorecard → 100%

### G1.2 M062 conflict UI — [x]

- [x] Rich conflict samples + score factors + suggested_keep_id
- [x] `--keep <id>` keeper override
- [x] Explainability in resolve details (`kept_score_factors`)
- [x] Post-resolve `list --kind deprecated`; never deletes rows
- [x] Tests + docs Conflict UI section
- [x] Scorecard → 100%

### G1.3 M063 distill product — [x]

- [x] Full operator loop docs + test
- [x] `distill --dry-run` preview_groups
- [x] `--similarity-threshold` CLI
- [x] Embedding honesty on distill output
- [x] `learning undeprecate` soft undo
- [x] Tests noop / jaccard / summary / no delete
- [x] Scorecard → 100%

**CLI:** `superai learning status|list|promote|conflicts|distill|deprecate|undeprecate`

---

## Wave G2 — Routing preferences & bandit — **DONE**

**Docs:** [`docs/ROUTING_PREFS_BANDIT.md`](docs/ROUTING_PREFS_BANDIT.md)  
**Tests:** `tests/test_routing_prefs_bandit_g2.py`

### G2.1 M068 preferences bias — [x]

- [x] `bias_candidates` wired in `ModelCaller.call` and `ModelRouter.get_best_model`
- [x] Pipeline: **preferences first → bandit second** (`route_candidates`)
- [x] CLI: `pref show|sticky|cheap|clear|set|get|delete`
- [x] Persistence `~/.superai/preferences.json`
- [x] Tests: preferred first, cheap_mode, empty, integration
- [x] Scorecard → 100%

### G2.2 M050 bandit continuous — [x]

- [x] `post_call` auto `bandit.update` (existing) + select on front door
- [x] Operator UI: `bandit status` table + `bandit reset` + JSON
- [x] `EpsilonGreedyBandit.status()` / `route_candidates`
- [x] Bakeoff sticky bridge documented
- [x] Tests persist/select/reward; avoid double-count via single post_call path
- [x] Scorecard → 100%

---

## Wave G3 — Streaming honesty — **DONE offline**

**Docs:** [`docs/STREAMING.md`](docs/STREAMING.md)  
**Tests:** `tests/test_stream_dashboard_g3_g4.py`, `tests/test_m079_m027_m093.py`

### G3.1 M027 + G3.2 V4-M4 — [x] offline

- [x] Provider matrix (Anthropic / OpenAI-compat / Ollama / mock / fallback)
- [x] `supports_stream` + `stream_capabilities.provider_matrix`
- [x] Meta honesty: mode, provider, model, cancelled, **fallback_reason**
- [x] Cancel between chunks (existing path retained)
- [x] Offline tests: mock_chunked, chunked_fallback reason, matrix
- [x] Scorecard → 100% offline (live SSE optional note)

---

## Wave G4 — M100 Honest dashboard — **DONE**

- [x] `build_dashboard_snapshot` always includes `mock_mode`, `honesty` MOCK|LIVE, spend, provider_health
- [x] Terminal dashboard title banner `[MOCK]` / `[LIVE]`
- [x] CLI `status` honesty banner always
- [x] `dashboard_state` / `dashboard_honesty` enriched
- [x] Tests mock → MOCK; forced live flag → LIVE
- [x] Scorecard → 100%

---

## Wave G5 — M089 Live multi-provider smoke — offline code done · host `[!]`

| Field | Value |
|-------|--------|
| **Scorecard** | HOST-GATED · live keys required for 100% host |
| **Deps** | M088 smoke harness never false-passes; M041 registration |
| **Modules** | `core.live_smoke_complete`, `provider_smoke`, Phase 99 plan |
| **AGY residual pickup** | [`docs/grok_work_review_result_I1_v1.md`](docs/grok_work_review_result_I1_v1.md) |

**Offline code (I1 residual close-out):**

- [x] Harness never claims live pass without keys / real results
- [x] `budget_precheck(..., command_name="live-smoke")` on live branch
- [x] Offline stream aggregate sample always (`stream_sample_offline`)
- [x] Env key inventory in result (`env_keys_present`)
- [x] Tests: `tests/test_grok_i1_residuals.py`

**When host keys available:**

- [ ] Run `run_phase6_smoke(allow_live=True)` / `superai phase6-smoke` across credentialed providers
- [ ] Record results; never mark CI green on missing keys
- [ ] Update scorecard M089 only after real matrix evidence

**Also closed from AGY Grok review residual list:**

- [x] Atomic prefs + bandit state (`store_lock` + `atomic_write_json`)
- [x] Stream completion → contracted `aggregated` result (`call_stream_complete`)

---

## Explicitly not on this board

| Item | Owner |
|------|--------|
| Spend_guard / public contracts / MCP spend / TOP_30 / JSON-all-commands / cost fallbacks | **AGY** → `TASKBOARD_AGY.md` |
| M091 cold-start perf (50%) | Unassigned |
| Archived handoff checklist items | `docs/archive/2026-07-24-wave-handoffs/` |

---

## Full verify pack (Grok)

```text
pytest tests/test_learning_lifecycle_m061_m063.py tests/test_learning_engine_gaps.py -q
pytest tests/test_routing_prefs_bandit_g2.py tests/test_msg_vega_plugin_bandit.py -q
pytest tests/test_stream_dashboard_g3_g4.py tests/test_m079_m027_m093.py tests/test_improvement_v4.py -q
pytest tests/test_grok_i1_residuals.py -q
```

---

## Last session

| Field | Value |
|-------|--------|
| **When** | 2026-07-24 |
| **What** | Closed AGY `grok_work_review_result_I1_v1` residuals: atomic prefs/bandit, stream aggregate contract, M089 offline harness honesty. Host live matrix still `[!]`. |
| **Still open** | G5 M089 **host** live multi-provider run only (keys) |
| **Evidence** | `tests/test_grok_i1_residuals.py` + prior G1–G4 suites |
| **Pickup closed** | [`docs/grok_work_review_result_I1_v1.md`](docs/grok_work_review_result_I1_v1.md) |
| **Archive** | `docs/archive/2026-07-24-wave-handoffs/` |
