# TASKBOARD — Grok (Memory / Learning / Routing Honesty)

**Owner:** Grok  
**Peer board:** [`TASKBOARD_AGY.md`](TASKBOARD_AGY.md)  
**Index:** [`TASKBOARD.md`](TASKBOARD.md)  
**Scorecard:** [`docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md`](docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md)  
**Strict bar:** production code + thorough docs + full tests. Promote scorecard rows only with evidence.  
**Created:** 2026-07-24 · **Detail expansion:** 2026-07-24  

**Legend:** `[ ]` open · `[~]` in progress · `[x]` done · `[!]` host-gated  

---

## Mission

Close the **9 near-complete Musts** (80–90%) that need product depth, routing proof, streaming honesty, dashboard completeness, or host smoke — **without** re-opening archived memory/hardening handoffs.

| Wave | IDs | Theme | Target |
|------|-----|--------|--------|
| G1 | M061–M063 | Learning lifecycle product | 85% → 100% |
| G2 | M068, M050 | Preferences + bandit continuous product | 80–85% → 100% |
| G3 | M027, V4-M4 | Real streaming provider coverage | 85% → 100% offline DoD |
| G4 | M100 | Honest mock vs live dashboard | 80% → 100% |
| G5 | M089 | Live multi-provider smoke | host when keys |

**Suggested order:** G1 → G2 → G3 → G4 → G5 (host last).

---

## Prior wave (archived — do not re-open)

| Track | Status | Location |
|-------|--------|----------|
| Memory P1–P9 offline + integrity handoff | **DONE** | `docs/archive/2026-07-24-wave-handoffs/GROK_HANDOFF_PENDING_AND_INCOMPLETE.md` |
| AGY hardening reassignment residuals | **DONE** | same archive |

---

## Global DoD (every Grok item)

Before marking `[x]` and promoting scorecard:

1. **Code:** Intent of backlog title is production-usable (not library-only if title implies product).
2. **Docs:** Dedicated or plan section updated (`LEARNING_LIFECYCLE.md`, V6 backlog notes, etc.).
3. **Tests:** Offline unit/integration covering the new behavior; no false live pass.
4. **Honesty:** Hash embeddings, mock streaming, and host gates labeled — never claim full semantic/live when not.
5. **Scorecard:** Update improved scorecard row only if all three pillars pass; else keep honest %.
6. **Board:** Update this file’s checkbox + Last session.

---

## Wave G1 — Learning lifecycle product (M061–M063 @ 85%)

**Why incomplete:** Core `LearningEngine` APIs are strong; scorecard residual is **product UX completeness** and continuous operator surface (not missing algorithms).

**Shared modules**

| Path | Role |
|------|------|
| `src/core/learning_engine.py` | `promote_durable`, `resolve_conflicts`, `distill_knowledge`, `deprecate_memory`, `lifecycle_status`, `list_lifecycle`, `embedding_backend_info` |
| `src/core/foundation_complete.py` | Thin public wrappers: `learning_*` |
| `src/cli/main.py` | `learning` Typer group (`status`, `list`, `promote`, `conflicts`, `distill`, `deprecate`) |
| `docs/LEARNING_LIFECYCLE.md` | Product docs + honesty table |
| `tests/test_learning_lifecycle_m061_m063.py` | Primary suite |
| `tests/test_learning_engine_gaps.py` | Embedding honesty, conflict/distill edge cases |
| `tests/test_learning.py` | Broader learning |

**Shared product facts (do not regress)**

- Conflict resolve and distill **deprecate** losers — **never delete rows** (`deletes_rows: false`).
- Default offline embeddings may be **hash** (`SUPERAI_EMBEDDING_HASH` / missing sentence-transformers) — weaker semantic distill; must surface in `embedding` / `honesty` fields.
- Conflict **detect** uses success-rate **binary entropy** per `(task_type, model)` — not vector similarity.
- Distill uses embedding cosine when real ST loaded, else **Jaccard**; may **noop** with clear message when insufficient memories.
- CLI: `superai learning status|list|promote|conflicts|distill|deprecate` (+ global `--json`).

**Legacy aliases (keep working):** `superai learnings`, `superai conflicts`, `superai reflect --distill`.

---

### G1.1 — M061 Learning: promote durable patterns only

| Field | Value |
|-------|--------|
| **Scorecard** | 85% · incomplete · Product UX incomplete |
| **Implemented** | `LearningEngine.promote_durable()` — tags `durable`, boosts importance, `promoted_at` |
| **CLI today** | `superai learning promote [--min-importance] [--limit] [--id]` |

**Backlog intent (V6):** Only promote high-value durable patterns (from successful outcomes), not everything.

**What works**

- Filters by `min_importance` (default 0.75) and success when auto-scanning.
- Single-id promote path; batch from `retrieve_by_tags(["learning"])`.
- Returns contract-like dict: `ok`, `promoted`, `count`, `product`.

**Gaps to close (implementation checklist)**

- [ ] **Operator UX polish:** Human-readable table of candidates *before* promote (dry preview): id, task_type, importance, success, why eligible/skipped.
- [ ] **Dry-run flag:** `learning promote --dry-run` lists would-be promotions without mutating.
- [ ] **Wire to outcomes:** Ensure successful agent/board runs can opt-in write learnings that become promotable (M057 write-back path) — document the full loop in `LEARNING_LIFECYCLE.md`.
- [ ] **TUI / status integration:** `learning status` already shows durable counts; ensure promote results update status fields used by dashboard if any.
- [ ] **Session bridge:** Document/link `memory-session promote --learning` vs `learning promote` (session buffer ≠ durable pattern).
- [ ] **Tests:** dry-run; below-threshold skip; id-not-found honesty; JSON mode shape stable under `emit_public` / `_print_learning_result`.
- [ ] **Scorecard promote only when:** preview + dry-run + docs + tests prove product UX, not only API.

**Verify**

```text
superai learning status
superai learning promote --dry-run
superai --json learning promote --limit 3
pytest tests/test_learning_lifecycle_m061_m063.py -q -k promote
```

---

### G1.2 — M062 Conflict resolution for contradictory memories

| Field | Value |
|-------|--------|
| **Scorecard** | 85% · incomplete · Conflict UI incomplete |
| **Implemented** | `detect_conflicts()` + `resolve_conflicts(auto_resolve=True/False)` |
| **CLI today** | `superai learning conflicts` · `superai learning conflicts --resolve` |

**Backlog intent:** Detect and resolve contradictory learnings safely (no silent data loss).

**What works**

- Entropy severity ranking (high/medium/low).
- Multi-factor score keeper; soft-demote diverse successes; deprecate failures/low scores.
- List-only mode when `auto_resolve=False`.

**Gaps to close**

- [ ] **Conflict UI:** Rich table: task_type, model, entropy, severity, success/fail counts, sample content snippets, keeper vs candidates.
- [ ] **Interactive/select mode (optional but strong):** `--keep <id>` or approve per group before deprecate.
- [ ] **Explainability:** Each resolve detail already has `kept_memory_id`, `deprecated_count`; surface `score` factors in CLI (importance, success, recency).
- [ ] **Post-resolve list:** Show deprecated bucket counts (`learning list --kind deprecated`).
- [ ] **Tests:** auto_resolve off lists only; resolve never deletes; soft-demote path; JSON honesty fields include `deletes_rows: false`.
- [ ] **Docs:** Expand “Conflict UI” section in `LEARNING_LIFECYCLE.md` with example output.

**Verify**

```text
superai learning conflicts
superai learning conflicts --resolve
superai learning list --kind deprecated -n 10
pytest tests/test_learning_lifecycle_m061_m063.py -q -k conflict
pytest tests/test_learning_engine_gaps.py -q
```

---

### G1.3 — M063 Distill / deprecate redundant memories

| Field | Value |
|-------|--------|
| **Scorecard** | 85% · incomplete · Lifecycle product incomplete |
| **Implemented** | `distill_knowledge()` + `deprecate_memory()` |
| **CLI today** | `superai learning distill [--type] [--min-memories]` · `learning deprecate <id> --reason` |

**Backlog intent:** Consolidate redundant learnings; deprecate dups; keep rows; write summary memories.

**What works**

- Group by `(task_type, model)`; near-dup clustering; summary memory with `distilled` tag.
- Honest noop when `insufficient_memories`.
- Manual deprecate with reason + tags.

**Gaps to close**

- [ ] **Lifecycle product loop:** Document and test full path: learn → promote → conflict → distill → list buckets as one operator story.
- [ ] **Distill preview:** `--dry-run` showing groups, similarity method (cosine vs jaccard), would-deprecate ids.
- [ ] **Threshold controls:** Expose similarity threshold on CLI if only code defaults today; document defaults.
- [ ] **Embedding honesty in CLI output:** Always print `embedding.backend` / honesty from `embedding_backend_info()` on distill result.
- [ ] **Deprecate undo story:** Document that rows remain; how to re-list / re-activate if needed (or add soft “undeprecate” if missing — only if product needs it).
- [ ] **Tests:** noop path; jaccard path under hash; distill creates summary; dups deprecated not deleted.
- [ ] **Scorecard:** Promote when product loop is one coherent UX, not three disconnected commands.

**Verify**

```text
superai learning distill --dry-run
superai learning distill --type coding --min-memories 5
superai learning list --kind distilled
pytest tests/test_learning_lifecycle_m061_m063.py -q -k distill
```

---

## Wave G2 — Routing preferences & bandit (M068 @ 85%, M050 @ 80%)

### G2.1 — M068 Preferences that bias routing

| Field | Value |
|-------|--------|
| **Scorecard** | 85% · Deep routing bias not fully proven |
| **Implemented** | `Preferences.bias_candidates()` sticky preferred + cheap_mode reorder |
| **Module** | `src/core/preferences.py` |

**Backlog intent:** User preferences (sticky model, cheap mode, success signals) actually reorder routing candidates on real front-door paths.

**What works**

- Preferred model pin; cheap keyword heuristic (`mini`, `flash`, `haiku`, `local`, `ollama`).
- Success-rate signal helpers (`preferred_model_for`, `profile_summary`).

**Gaps to close**

- [ ] **End-to-end proof:** Call `bias_candidates` from actual routers: model pick for `ask` / agent / board member selection / cost router — grep for call sites; wire if missing.
- [ ] **CLI product:** Commands to set/show sticky model, cheap mode, clear preference; JSON status.
- [ ] **Persistence:** Confirm prefs path under `~/.superai/`; document location.
- [ ] **Interaction with bandit (M050):** Document order of application: preferences first then bandit (or vice versa) — implement one consistent pipeline and test it.
- [ ] **Tests:** bias puts preferred first; cheap_mode reorders; empty candidates; integration test on one public route.
- [ ] **Docs:** Short section in V6 backlog or `docs/UNIVERSAL_MODELS.md` / routing docs.

**Verify**

```text
# after wiring: show prefs → run route → assert order
pytest tests/ -q -k prefer
rg "bias_candidates" src
```

---

### G2.2 — M050 Bandit / learned routing from outcomes

| Field | Value |
|-------|--------|
| **Scorecard** | 80% · Not continuous-product UI |
| **Implemented** | `EpsilonGreedyBandit` select/update/reward_from_outcome; CLI `bandit` |
| **Modules** | `src/core/bandit_router.py`, `src/cli/main.py` `bandit_cmd`, web `bandit_state` |

**Backlog intent:** Continuous learned routing from outcomes (not a one-shot library).

**What works**

- Epsilon-greedy over models; state in `~/.superai/bandit_state.json`.
- Reward from success, latency, cost, satisfaction.
- Some CLI/web exposure already.

**Gaps to close**

- [ ] **Continuous product loop:** On successful/failed model calls, automatically `update()` bandit (call_lifecycle or ModelCaller post-path) with measured cost/latency.
- [ ] **Select integration:** Front-door / router uses `select(candidates)` after preference bias.
- [ ] **Operator UI:** `superai bandit status` table (arms, n, mean reward); `bandit reset`; pin/exclude arms if product needs.
- [ ] **Bakeoff bridge:** Pin winner from bakeoff updates bandit or preferences (document which).
- [ ] **Tests:** update persists; select respects high reward; epsilon explores; offline mock deterministic where required.
- [ ] **Avoid double-count:** Coordinate with AGY spend recording so rewards use real cost when available.

**Verify**

```text
superai bandit --help
pytest tests/test_msg_vega_plugin_bandit.py -q
rg "EpsilonGreedyBandit|bandit" src/core src/cli
```

---

## Wave G3 — Streaming honesty (M027 @ 85%, V4-M4 @ 85%)

**Shared modules:** `src/core/model_caller.py` (`call_stream`), `src/core/token_stream.py` (`set_stream_meta`, modes: `mock_chunked`, `sse`, `chunked_fallback`).

**Coordinate with AGY:** Stream paths must still hit spend_guard / result contract (V4-M1/M2). Grok owns **stream completeness + honesty labels**; AGY owns **budget/contract wrappers**.

### G3.1 — M027 Real token streaming where supported

| Field | Value |
|-------|--------|
| **Scorecard** | 85% · Not all providers proven live |
| **Implemented** | SSE for Anthropic/Claude path; mock chunking; cancel between chunks; fallback to full `call()` chunked |

**Gaps to close**

- [ ] **Provider matrix (offline-first):** Document which providers have real SSE vs fallback: Anthropic, OpenAI-compatible, Ollama, others.
- [ ] **Ollama / local OpenAI-compatible stream:** Implement or explicitly document `chunked_fallback` only; add offline unit tests with mocked HTTP SSE fixtures (no live keys).
- [ ] **Meta honesty:** Always set `token_stream` meta: `mode`, `provider`, `model`, `cancelled`; surface in TUI/agent-tui if used.
- [ ] **Agent-tui / MOS-S1 adjacency:** If agent-tui uses streaming, ensure it consumes `call_stream` not fake sleep loops.
- [ ] **Cancel:** Partial stream cancel (S148 adjacency) honors CancelToken — keep tests green.
- [ ] **Tests:** mock mode yields chunks; meta mode mock_chunked; anthropic path unit-mocked; fallback path; cancel mid-stream.
- [ ] **Scorecard honesty:** Can reach 100% offline if matrix + fixtures prove supported providers; live remains optional note, not blocker for offline complete.

**Verify**

```text
pytest tests/test_improvement_v4.py -q -k stream
pytest tests/test_m079_m027_m093.py -q -k stream
```

---

### G3.2 — V4-M4 Provider stream API path

| Field | Value |
|-------|--------|
| **Scorecard** | 85% · Provider coverage incomplete |
| **Plan** | `docs/IMPROVEMENT_V4_PLAN.md` M4 |

**Gaps to close**

- [ ] Treat as **API completeness twin of M027**: public callable `ModelCaller.call_stream` stable for all registered provider kinds that claim stream support.
- [ ] Registry flag or capability: `supports_stream: true/false` per model/provider; routers prefer stream only when true.
- [ ] Error path: stream failure falls back once and sets meta `chunked_fallback` + reason (not silent).
- [ ] Shared tests with M027; one scorecard note can cross-link both IDs.

---

## Wave G4 — M100 Honest dashboard: mock vs live (@ 80%)

| Field | Value |
|-------|--------|
| **Scorecard** | 80% · Full dashboard product incomplete |
| **Modules** | `src/cli/dashboard.py`, `core.observability.build_dashboard_snapshot` |
| **Related** | `public_surface.emit_public` honesty fields `mock` / `live` / `honesty` |

**Backlog intent:** Operators always know MOCK vs LIVE spend/risk on dashboard and status surfaces.

**Gaps to close**

- [ ] **Snapshot fields:** Ensure `build_dashboard_snapshot()` always includes `mock_mode`, `honesty` (MOCK|LIVE), spend so far, provider health.
- [ ] **Terminal dashboard:** Visible banner MOCK/LIVE; never look “production green” while mock.
- [ ] **Web dashboard (if any):** Same labels; no mixed messaging.
- [ ] **CLI `status` / `doctor`:** Align honesty labels with dashboard.
- [ ] **Tests:** mock config → snapshot honesty MOCK; forced live flag labeled LIVE offline-safe.
- [ ] **Docs:** Short “honesty” paragraph in README or dashboard help.

**Verify**

```text
superai status
# dashboard once if available
pytest tests/ -q -k dashboard
```

---

## Wave G5 — M089 Live multi-provider smoke matrix (@ 90% host) `[!]`

| Field | Value |
|-------|--------|
| **Scorecard** | HOST-GATED · live keys required |
| **Deps** | M088 smoke harness never false-passes; M041 registration |
| **Related IDs** | V1-P99, MOS-N8 (shared index board) |
| **Modules** | `core.live_smoke_complete`, Phase 99 plan in `docs/UNIVERSAL_MODELS_PLAN.md` |

**Do not block G1–G4.** When host keys available:

- [ ] Run matrix across registered live providers (OpenAI-compatible, Anthropic, local Ollama if present, NVIDIA if configured).
- [ ] Record results; never mark CI green on missing keys.
- [ ] Budget precheck must wrap live smoke (`foundation_safety` path `live_smoke`).
- [ ] Update scorecard only after real matrix evidence.

**Offline allowed work now**

- [ ] Expand harness catalog of providers.
- [ ] Ensure harness exits non-zero when keys missing if `--allow-live`.
- [ ] Document exact env vars per provider.

---

## Explicitly not on this board

| Item | Owner |
|------|--------|
| Spend_guard / public contracts / MCP spend / TOP_30 / JSON-all-commands / cost fallbacks | **AGY** → `TASKBOARD_AGY.md` |
| M091 cold-start perf (50%) | Unassigned |
| Archived handoff checklist items | `docs/archive/2026-07-24-wave-handoffs/` |

---

## Coordination with AGY

| Topic | Grok | AGY |
|-------|------|-----|
| Streaming spend | Stream completeness + meta honesty | budget_precheck on stream path |
| Bandit rewards | Update from outcomes | Cost accuracy for reward inputs |
| Learning MCP tools | Lifecycle semantics | mcp_safety wrap / mutating tool lists |
| Scorecard regen | Only Grok IDs | Only AGY IDs |

---

## Full verify pack (Grok)

```text
pytest tests/test_learning_lifecycle_m061_m063.py tests/test_learning_engine_gaps.py tests/test_learning.py -q
pytest tests/test_msg_vega_plugin_bandit.py -q
pytest tests/test_m079_m027_m093.py tests/test_improvement_v4.py -q
rg "bias_candidates|call_stream|promote_durable|distill_knowledge" src
```

---

## Last session

| Field | Value |
|-------|--------|
| **When** | 2026-07-24 |
| **What** | Expanded Grok board with thorough implementation guidance per Must |
| **Still open** | All G1–G5 |
| **Archive** | `docs/archive/2026-07-24-wave-handoffs/` |
