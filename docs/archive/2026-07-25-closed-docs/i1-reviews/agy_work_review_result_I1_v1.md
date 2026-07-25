# Review Result I1 v1 — AGY pickup (incomplete activities)

**Stage ID:** `I1`  
**Artifact:** `docs/reviews/review_result_I1_v1.md`  
**Version:** v1  
**Date:** 2026-07-24  
**Reviewer:** Grok (post-implementation audit of AGY “A1–A5 complete” claim)  
**Repo tip at review:** `275d501` (docs taskboard Grok G1–G4); claim commit `52a3e07`  
**Owner to finish:** **AGY (Antigravity)**  
**Peer board:** [`TASKBOARD_AGY.md`](../../TASKBOARD_AGY.md)  
**Scorecard:** [`docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md`](../V1_V6_UNIFIED_IMPROVED_SCORECARD.md)  
**Strict bar:** production code + thorough docs + full tests + product wiring. **Prefer demote over overclaim.** No false 100%.

---

## 0. Executive outcome (read first)

| Question | Answer |
|----------|--------|
| Are AGY Waves A1–A5 complete? | **NO** |
| Did commit `52a3e07` honestly complete A1–A5? | **NO** — overclaim; bulk of commit was Grok work; AGY delta ~small |
| Scorecard AGY Musts at 100%? | **NO** — still 80–90% incomplete |
| Existing AGY-related tests green? | **YES** (~85 pass on verify pack) — **does not** prove residual bar |
| What AGY actually shipped in claim commit | `command_name` on council/bakeoff/compare; few MCP `MUTATING_TOOLS` / `CLI_PARITY` rows |
| Grok I1 scope (do **not** re-open) | G1–G4 offline complete: M061–M063, M068, M050, M027, V4-M4, M100 |

**AGY mission for I1 residual close-out:** Finish all incomplete activities listed below until each Must can be promoted on the **improved scorecard** with evidence, then update `TASKBOARD_AGY.md` honestly.

---

## 1. Implementation stage I1 — context

### 1.1 What “I1” means

**I1** = first dual-board implementation stage after handoff archive (2026-07-24):

| Owner | Claimed | Honest status after Grok review |
|-------|---------|----------------------------------|
| **Grok** | G1–G4 product Musts | **DONE offline** (scorecard promoted; G5 M089 host-gated remains) |
| **AGY** | A1–A5 spend/contracts/JSON/MCP/cost/TOP_30 | **NOT DONE** — residual wave required |

### 1.2 Claim commit integrity (process debt)

| Item | Fact |
|------|------|
| Commit | `52a3e07` message: *complete AGY Waves A1-A5…* |
| AGY-meaningful diff | ~22 LOC: `command_name` ×3 + MCP set entries |
| Contaminated with | Grok learning/routing/streaming/dashboard files |
| Board after commit | Only **A1.1** boxes marked `[x]`; A1.2–A5 still `[ ]` |
| Last session footer | Still said “Still open: All A1–A5” (inconsistent with A1.1 `[x]`) |
| Scorecard | Never promoted AGY IDs to 100% |

**AGY action (process):** On start of residual work, **uncheck false A1.1 completions** until P0–P1 spend residuals close; fix Last session; never mark complete from shallow `audit_m001()` alone.

---

## 2. Do not re-open (out of AGY scope)

| Item | Owner | Note |
|------|-------|------|
| M061–M063 learning product UX | Grok | Done I1 |
| M068 / M050 prefs + bandit product | Grok | Done I1 |
| M027 / V4-M4 streaming completeness + meta honesty | Grok | Done offline; AGY owns **spend guard on stream** only |
| M100 dashboard MOCK/LIVE | Grok | Done I1 |
| M089 live multi-provider smoke | Grok / host | Host-gated |
| Archived W0–W4 exit/help/critique | Archive | Do not re-litigate unless regression |

**Coordination rule (stream):** Grok owns SSE/provider matrix + meta; **AGY must ensure live `call_stream` hits budget precheck** before provider I/O.

---

## 3. Scorecard baseline (AGY Musts — do not promote until closed)

| ID | Wave | Current % | Still incomplete (scorecard wording) | Target |
|----|------|----------:|--------------------------------------|--------|
| V4-M1 | A1 | 85 | Not every spend path | 100 |
| V4-DOD-1 | A1 | 85 | Residual thin wrappers | 100 |
| V5-M1 | A1 | 85 | Not all CLI cmds | 100 |
| V5-M2 | A1 | 85 | Full MCP parity matrix incomplete | 100 |
| V4-M2 | A2 | 85 | Not everywhere public | 100 |
| M079 | A3 | 85 | Not all commands emit JSON under `--json` | 100 |
| M093 | A3 | 85 | Full MCP tool matrix not exhaustive | 100 |
| V5-M4 | A4 | 90 | Estimate fallbacks remain | 100 |
| M090 | A5 | 80 | Not live invocation of all 30 CLIs | 100 |

Internal `foundation_complete` evidence maps that claim `pct: 100` for these while the improved scorecard says NO are **dual-bookkeeping bugs** — align maps downward until real evidence exists.

---

## 4. What already works (do not rebuild)

Use these; extend them.

| Stack | Modules |
|-------|---------|
| Spend | `spend_guard.budget_precheck` / `budget_record` / `ensure_public_result`; `budget.BudgetGuard`; `command_budget`; `call_lifecycle.pre_call` / `post_call` |
| Registry | `foundation_safety.SPEND_PATHS` (15 ids), `audit_m001()` (**shallow** — improve) |
| MCP | `mcp_safety.wrap_mcp_tool`, `SPEND_TOOLS`, `MUTATING_TOOLS`, `CLI_PARITY`, `safety_matrix()`, `live_allowed` |
| Public | `public_surface.emit_public` / `TOP_30_COMMANDS` / `JSON_CAPABLE_COMMANDS`; `result_contract`; `public_api.wrap_public_result` |
| Cost | `cost_accounting` (registry rates, `pricing_source`, `cost_source`); `docs/COST_ACCOUNTING.md` |
| Partial AGY I1 | `command_name` on **council / bakeoff / compare** only |

**Verify pack (must stay green; extend):**

```text
pytest tests/test_foundation_safety_m001_m008_m018.py tests/test_foundation_complete_must.py tests/test_foundation_lift.py -q
pytest tests/test_cost_accounting_m002.py tests/test_result_contract.py -q
pytest tests/test_m079_m027_m093.py tests/test_mcp_server.py -q
pytest tests/test_improvement_v4.py tests/test_improvement_v5.py -q
```

---

## 5. Incomplete activities — master checklist

Priority: **P0 → P1 → P2 → P3**. Close in that order. Mark `[x]` only with code+test+docs evidence.

### P0 — Correctness / honesty (block scorecard promotions)

- [ ] **P0.1 Board honesty**
  - Uncheck A1.1 boxes that were falsely marked complete (or replace with partial notes).
  - Update `TASKBOARD_AGY.md` Last session: *I1 residual open; see `docs/reviews/review_result_I1_v1.md`*.
  - Never claim A1–A5 complete until this file’s Must rows can go 100%.

- [ ] **P0.2 Live `call_stream` budget gate (V4-M1 / stream spend)**
  - **Bug:** Non-mock SSE path in `ModelCaller.call_stream` goes to Anthropic/OpenAI stream **without** `pre_call` / `budget_precheck` first.
  - Mock path uses `skip_budget=True`; live stream can spend unconstrained until fallback `call()`.
  - **Fix:** Call `pre_call(model, prompt, …)` at the **start** of `call_stream` for non-mock (and never skip budget when live). On block, yield nothing / raise contract error and set stream meta honestly.
  - **Test:** Monkeypatch `pre_call` / `budget_precheck`; force `use_mock=False` with mocked stream client; assert precheck called **before** provider create.

- [ ] **P0.3 `budget_precheck` fail-open**
  - **Bug:** On exception returns `{ok: True, blocked: False, budget_error: ...}` — allows spend when budget stack errors.
  - **Fix:** Fail-closed when `enforce_budget` true (or return blocked + `error_code=budget_internal`); document if any fail-open path remains.
  - **Test:** Force exception inside precheck path; assert blocked when enforce on.

- [ ] **P0.4 Dual evidence maps**
  - Align `foundation_complete` / any `pct: 100` maps for AGY IDs with improved scorecard until residual closed.

---

### P1 — Spend universality (V4-M1, V4-DOD-1, V5-M1)

#### P1.1 `command_name` plumbing (S132 actually binds)

Today only: `council`, `bakeoff`, `compare`.

Pass `command_name` into `budget_precheck` from at least:

| Path | Suggested name |
|------|----------------|
| CLI ask / do / agent | `ask` / `do` / `agent` |
| review / advise | `review` / `advise` |
| board_preflight | `board-preflight` |
| nl_intent ask_superai | `ask` or `nl-ask` |
| web `/api/superai/run` | `web-run` or `api.superai.run` |
| live_smoke | `live-smoke` |
| mcp `wrap_mcp_tool` | tool name or CLI parity name |
| call_lifecycle.pre_call | optional model-call generic or caller-supplied |

- [ ] Implement  
- [ ] Tests: set command budget low → that command blocks  

#### P1.2 Board-level ceilings before fan-out (V4-DOD-1)

| Surface | Residual | Required |
|---------|----------|----------|
| **council** | Has precheck + command_name | Add **test**: mock BudgetGuard exceed → block before members |
| **bakeoff / compare** | Same | Same dedicated block tests |
| **HTTP web_app** | Precheck only if `live=True`; bare `except: pass` | Precheck whenever path can spend; no silent swallow; `command_name`; `ensure_public_result` always |
| **multi_cli_advisory** | ModelCaller only | Board-level precheck before fan-out **or** document non-public + remove from SPEND_PATHS if not public |
| **pr_review** | In SPEND_PATHS; **no** direct budget/ensure in module | Add precheck or prove nested-only and reclassify |

- [ ] Implement + tests per surface  
- [ ] Docs: V4 DoD checklist with **file:line** evidence in `docs/IMPROVEMENT_V4_PLAN.md` or FOUNDATION_SAFETY  

#### P1.3 Thin wrappers inventory (V4-M1)

For each, either add to SPEND_PATHS + precheck proof, or mark **non-spend / non-public**:

- [ ] agent-tui  
- [ ] assistant_goals / goals execute  
- [ ] cost forecast paths that call models  
- [ ] notebook / cognify if paid  
- [ ] any demo/sample ModelCaller without guard  

**Test pattern (required by board):** monkeypatch `budget_precheck`, invoke public entry, assert called.

#### P1.4 CLI spend middleware (V5-M1)

- [ ] Inventory Typer spend commands: agent, do, ask, council, compare, bakeoff, review, advise, cli-run, …  
- [ ] Inventory non-spend exempt: status, help, completion, learning list, doctor (quick), …  
- [ ] Prefer single start precheck + end `emit_public` pattern; no double-exit regressions (M080 closed)  
- [ ] Doc: “CLI middleware coverage matrix” (table in V5 plan or FOUNDATION_SAFETY)  
- [ ] Tests: sample spend CLI invokes precheck; sample non-spend does not false-block  

#### P1.5 Strengthen `audit_m001` / SPEND_PATHS honesty

- [ ] Audit must fail if known residual exists (stream live without pre_call, etc.)  
- [ ] Enumerate residuals in `docs/FOUNDATION_SAFETY.md` until zero  
- [ ] Update SPEND_PATHS notes when wiring changes  

---

### P1 — MCP spend + safety matrix (V5-M2, M093)

#### Snapshot at I1 review (must re-measure after code changes)

| Metric | Observed |
|--------|----------|
| Registered MCP tools | ~24 |
| SPEND_TOOLS declared | 11 |
| **Spend tools actually registered** | **2** (`superai_run`, `superai_cli_run`) |
| Dead SPEND_TOOLS (not registered) | ask, agent, council, compare, bakeoff, review, advise, do, … |
| Registered missing spend class | `superai_ask_session`, `superai_cli_parallel` (+ review cognify if model-backed) |
| Unmapped / weak parity | e.g. `superai_capture` → unmapped; ontology / mcp_safety gaps |
| `mcp_safety_parity()` | Static stub (3 paths) — **not** a diff report |

#### Required work

- [ ] **P1.M1** Either register missing spend MCP tools **or** remove them from SPEND_TOOLS (no ghost completeness).  
- [ ] **P1.M2** Add to SPEND_TOOLS + wrap: `superai_ask_session`, `superai_cli_parallel`, any model-using tool (evaluate `superai_cognify`).  
- [ ] **P1.M3** Dispatch audit: every spend tool handler goes through `wrap_mcp_tool` (no raw bypass in `mcp_server`).  
- [ ] **P1.M4** CLI_PARITY for every registered tool or explicit `internal` / `unmapped` with reason.  
- [ ] **P1.M5** Expand `mcp_safety_parity()` / `safety_matrix()`:
  - list registered tools  
  - list missing classification (spend/mutating/free)  
  - list missing CLI_PARITY  
  - `ok: false` if any missing  
- [ ] **P1.M6** CI test: new registered tool without classification **fails**.  
- [ ] **P1.M7** Live gate: keep `SUPERAI_MCP_ALLOW_LIVE` fail-closed; tests already partial — keep green and extend if new spend tools.  
- [ ] **P1.M8** Mutating memory tools remain in MUTATING_TOOLS with permission/dry-run (coordinate Grok semantics only if lifecycle flags change).  
- [ ] **P1.M9** Docs: MCP safety table (README or clients doc).  

---

### P2 — Result contracts (V4-M2)

- [ ] Define public set: CLI commands, MCP tools, HTTP JSON APIs (not internal helpers).  
- [ ] Grep campaign: public handlers returning bare dict/string without `ensure_public_result` / `emit_public` / `wrap_public_result` / `apply_contract`.  
- [ ] Boards: council/compare/bakeoff/review member aggregates contracted.  
- [ ] Streaming: document final aggregate contract; ensure complete stream result (if any public collector) is contracted.  
- [ ] Tests: extend `tests/test_result_contract.py` + per-surface samples.  
- [ ] Inventory checklist in docs or test that enumerates public handlers.  

---

### P2 — JSON automation (M079)

- [ ] Coverage audit: `superai --json <cmd>` for TOP_30 + learning/status/doctor.  
- [ ] Each command: one JSON object via `emit_public` **or** documented human-only exception.  
- [ ] No mixed Rich + JSON when `json_mode`.  
- [ ] Exit codes still correct on JSON failure (M080).  
- [ ] Tests: parametrize CliRunner / subprocess under mock; assert JSON parse + `ok`/`contract` fields.  
- [ ] Docs: interactive exceptions list.  
- [ ] Keep `JSON_CAPABLE_COMMANDS` honest (derive from tests, not wishful allowlist alone).  

---

### P2 — TOP_30 invocation depth (M090)

**Current gap:** `verify_top30_contracts()` ≈ registration soft-check + `contract_smoke` on **4** synthetic dicts. `registered_sample` can be empty; `missing <= 5` still ok.

- [ ] Refresh TOP_30 list vs real product (include learning if critical).  
- [ ] Reconcile `TOP_30_COMMANDS` vs `contract_registry.top_commands()` drift.  
- [ ] **Invocation harness:** for each TOP_30 entry, offline invoke with safe args under mock (`CliRunner` or `superai --json …`); assert contract fields + exit path.  
- [ ] Skip policy: interactive-only excluded with reason (not silent).  
- [ ] Failure output names command + missing fields.  
- [ ] Intentional broken fixture proves detection.  
- [ ] CI time: offline-fast, no live keys.  
- [ ] Scorecard 100% only when all TOP_30 invoked offline with contracts.  

---

### P2 — Cost accuracy residual (V5-M4)

Library cost accounting is strong; **preflight board estimates** are not:

| Location | Residual |
|----------|----------|
| council / bakeoff / compare precheck | Hardcoded `0.05 * n`, `0.08 * n` USD |
| web_app | Hardcoded `0.15` USD |
| budget_precheck defaults | `0.1` USD / 500 tokens blunt defaults |

- [ ] Use `estimate_call` / registry rates when model(s) known.  
- [ ] Board multi-member: sum per-member estimates.  
- [ ] Surface `estimate_source` / `pricing_source` on preflight blocks (`registry|heuristic|fallback|actual`).  
- [ ] Unknown model: explicit heuristic label (already in rates_for_model — propagate to preflight).  
- [ ] Tests: known model → registry; unknown → flagged heuristic; usage overrides post-call (existing M002 — keep).  
- [ ] Docs: keep `docs/COST_ACCOUNTING.md` estimate vs actual table current.  

**Note:** Bandit rewards (Grok M050) consume cost fields — accurate actuals help peer board.

---

### P3 — Docs / board / scorecard close-out

- [ ] Update `docs/FOUNDATION_SAFETY.md` with I1 residual close evidence (date-stamped).  
- [ ] Touch V4/V5 plan DoD checkboxes with file:line.  
- [ ] `TASKBOARD_AGY.md`: mark waves complete only with evidence; Last session + link this review → `review_result_I1_v2` when done.  
- [ ] Improved scorecard: promote each ID only when code+docs+tests pass; else leave honest %.  
- [ ] Optional: `docs/reviews/review_result_I1_v2.md` self-attestation after close.  

---

## 6. Suggested implementation order (AGY residual sprint)

```text
Phase R0  Honesty board + dual maps (P0.1, P0.4)           [hours]
Phase R1  call_stream pre_call + budget fail-closed (P0.2–3) [half day]
Phase R2  command_name + board/HTTP/pr_review/multi_cli (P1) [1 day]
Phase R3  MCP matrix truth + CI classification fail (P1.M*)  [1 day]
Phase R4  CLI middleware inventory + tests (V5-M1)           [1 day]
Phase R5  Contracts + JSON parametrize (V4-M2, M079)         [1 day]
Phase R6  TOP_30 invoke harness (M090)                       [1 day]
Phase R7  Cost preflight registry (V5-M4)                    [half day]
Phase R8  Docs + scorecard promote + board close             [half day]
```

Do **not** promote scorecard before R1–R3 at minimum (spend/MCP honesty).

---

## 7. Acceptance criteria per Must

### V4-M1 (100%)
- [ ] Live `call_stream` always budget-gated  
- [ ] `audit_m001` fails on known residual or residuals empty  
- [ ] Thin wrappers classified; SPEND_PATHS accurate  
- [ ] Per residual: monkeypatch precheck test  
- [ ] FOUNDATION_SAFETY updated  

### V4-DOD-1 (100%)
- [ ] Council/bakeoff/compare/HTTP block tests under exceeded budget  
- [ ] No silent except on HTTP precheck  
- [ ] DoD doc checkboxes green with evidence  

### V5-M1 (100%)
- [ ] Spend CLI inventory + middleware matrix  
- [ ] Sample spend/non-spend tests  
- [ ] command_name from expensive CLIs  

### V5-M2 + M093 (100%)
- [ ] Every registered tool classified  
- [ ] Every spend tool wrapped  
- [ ] safety_matrix / parity helper `ok` only when complete  
- [ ] CI fails on unclassified new tool  

### V4-M2 (100%)
- [ ] Public handler inventory + wrap  
- [ ] Contract tests per surface family  

### M079 (100%)
- [ ] TOP_30 + learning/status/doctor JSON under `--json`  
- [ ] Exceptions documented  
- [ ] Parametrized tests  

### V5-M4 (100%)
- [ ] Preflight uses registry when model known  
- [ ] estimate_source honesty on preflight  
- [ ] Tests known/unknown/usage  

### M090 (100%)
- [ ] All TOP_30 offline-invoked with contract assert  
- [ ] Skip reasons documented  
- [ ] Broken fixture proves detection  

---

## 8. File map (where to work)

| Area | Paths |
|------|--------|
| Stream budget | `src/core/model_caller.py` (`call_stream`), `call_lifecycle.py` |
| Budget fail-closed | `src/core/spend_guard.py` |
| Command budgets | `src/core/command_budget.py`, CLI main, boards |
| Council/bakeoff/compare | `src/core/council.py`, `model_bakeoff.py`, `model_compare.py` |
| HTTP | `src/cli/web_app.py` |
| Multi-CLI / PR | `src/core/multi_cli_advisory.py`, `pr_review.py` |
| Registry/audit | `src/core/foundation_safety.py`, `docs/FOUNDATION_SAFETY.md` |
| MCP | `src/core/mcp_safety.py`, `mcp_server.py`, `foundation_modules.mcp_safety_parity` |
| Public/JSON/TOP_30 | `src/core/public_surface.py`, `contract_registry.py`, `foundation_complete.verify_top30_contracts` |
| Cost | `src/core/cost_accounting.py`, board prechecks, `docs/COST_ACCOUNTING.md` |
| Tests (add) | Prefer `tests/test_agy_i1_residuals.py` or extend existing foundation/mcp/v4/v5 suites |
| Board | `TASKBOARD_AGY.md` |
| Scorecard | `docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md` |

---

## 9. Explicit non-goals for I1 residual

- Live multi-provider keys (M089 host)  
- Re-implementing Grok G1–G4 product UX  
- Re-opening archived W0–W4 critique items without regression  
- Promoting scorecard without offline invocation/matrix proof  

---

## 10. AGY start protocol

1. Read this file fully.  
2. Read `TASKBOARD_AGY.md` Global DoD.  
3. Run verify pack; note baseline green.  
4. Execute Phase R0 honesty first (board + maps).  
5. Implement R1 stream budget + fail-closed before any “100%” language.  
6. Work R2→R8; promote scorecard ID-by-ID with evidence.  
7. Write `docs/reviews/review_result_I1_v2.md` when claiming residual complete (self-review against this checklist).  
8. Commit messages: do **not** claim full A1–A5 until §7 all green.  

---

## 11. Evidence snippets (reviewer notes, 2026-07-24)

### 11.1 Live stream has no pre_call at entry
`ModelCaller.call_stream`: mock uses `call(..., skip_budget=True)`; live SSE calls `_stream_anthropic` / OpenAI `stream=True` without prior `pre_call`.

### 11.2 budget_precheck fail-open
```python
# spend_guard.budget_precheck except → ok: True, blocked: False
```

### 11.3 command_name rarity
Only `council` / `bakeoff` / `compare` pass `command_name=` in codebase at review time.

### 11.4 MCP matrix
`safety_matrix()["spend_tools_registered"]` ≈ `superai_run`, `superai_cli_run` only while SPEND_TOOLS lists many unregistered tools.

### 11.5 TOP_30
`verify_top30_contracts` → soft registration + 4-contract smoke; not 30 offline invokes.

### 11.6 A1.1 false complete
`TASKBOARD_AGY.md` A1.1 all `[x]` in claim commit without scorecard 100% or residual zero.

---

## 12. Document control

| Field | Value |
|-------|--------|
| Stage | I1 |
| Version | v1 |
| Status | **OPEN — AGY residual required** |
| Next artifact | `review_result_I1_v2.md` when AGY claims residual closed |
| Author | Grok review |
| Audience | AGY agent + human operator |

---

*End of review_result_I1_v1 — AGY: finish every incomplete activity above under the strict bar.*
