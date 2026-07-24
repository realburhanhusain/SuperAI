# TASKBOARD — AGY (Spend / Contracts / CLI–MCP Surfaces)

**Owner:** AGY (Antigravity)  
**Peer board:** [`TASKBOARD_GROK.md`](TASKBOARD_GROK.md)  
**Index:** [`TASKBOARD.md`](TASKBOARD.md)  
**Scorecard:** [`docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md`](docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md)  
**Strict bar:** production code + thorough docs + full tests + **product wiring** (CLI/MCP/HTTP where claimed). No false 100%.  
**Created:** 2026-07-24 · **Detail expansion:** 2026-07-24  

**Legend:** `[ ]` open · `[~]` in progress · `[x]` done · `[!]` host-gated  

> **I1 residual (mandatory read):** [`docs/agy_work_review_result_I1_v4.md`](docs/agy_work_review_result_I1_v4.md)  
> Stage **I1** AGY A1–A5 offline **complete** (product wiring + real tests). Prefer demote if regressions appear.

---

## Mission

Close the **9 near-complete Musts** (80–90%) that need **universal spend**, **public contracts**, **JSON/MCP surface parity**, **cost estimate honesty**, and **TOP_30 contract depth**.

| Wave | IDs | Theme | Target | Status |
|------|-----|--------|--------|--------|
| A1 | V4-M1, V4-DOD-1, V5-M1, V5-M2 | Spend universality + MCP spend | 85% → 100% | [x] DONE |
| A2 | V4-M2 | Result contract everywhere public | 85% → 100% | [x] DONE |
| A3 | M079, M093 | JSON automation + MCP safety matrix | 85% → 100% | [x] DONE |
| A4 | V5-M4 | Cost registry accuracy / estimate fallbacks | 90% → 100% | [x] DONE |
| A5 | M090 | TOP_30 contract live invocation depth | 80% → 100% | [x] DONE |

**Suggested order:** A1 (spend spine) → A2 (contracts) → A3 (surfaces) → A4 (cost) → A5 (TOP_30).

---

## Prior wave (archived — do not re-open)

| Track | Status | Location |
|-------|--------|----------|
| Hardening Wave W0–W4 (M080/M015/M081/M082, S104–S132 pack) | **DONE** | `docs/archive/2026-07-24-wave-handoffs/` |
| Plan W0–W4 | **DONE** | `AGY_IMPROVEMENT_PLAN.md` in archive |
| Findings re-reviews #1–#7 | Historical only | `AGY_HANDOFF_PENDING_AND_INCOMPLETE.md` in archive |

Do **not** re-litigate closed exit-code / help / self-critique items unless regression.

---

## Global DoD (every AGY item)

1. **Code:** No silent bypass of budget/contract on public spend paths.
2. **Docs:** Update `docs/IMPROVEMENT_V4_PLAN.md` / V5 plan / `FOUNDATION_SAFETY.md` / V6 backlog notes as needed.
3. **Tests:** Offline; prove wrap/precheck called; prove residual paths enumerated.
4. **Registry honesty:** Extend `foundation_safety.SPEND_PATHS` / MCP matrices when adding paths.
5. **Scorecard:** Promote only after exhaustive evidence; prefer demote over overclaim.
6. **Board:** Checkbox + Last session on this file.

---

## Shared foundation (read first)

### Spend stack

| Module | Role |
|--------|------|
| `src/core/spend_guard.py` | `budget_precheck`, `budget_record`, `ensure_public_result` |
| `src/core/budget.py` | `BudgetGuard.enforce_or_block` / `record` |
| `src/core/command_budget.py` | Per-command ceilings (`check_command_budget_guard`) — already called from `budget_precheck` when `command_name` set |
| `src/core/call_lifecycle.py` | `pre_call` → spend gate before model calls |
| `src/core/foundation_safety.py` | `SPEND_PATHS` registry + `audit_m001()` |
| `docs/FOUNDATION_SAFETY.md` | M001/M008/M018 evidence narrative |

### Contract / public surface stack

| Module | Role |
|--------|------|
| `src/core/result_contract.py` | Stable result envelope |
| `src/core/public_api.py` | `wrap_public_result` |
| `src/core/public_surface.py` | `emit_public`, JSON mode, `TOP_30_COMMANDS`, `verify_top_commands_registered` |
| `src/core/error_codes.py` | Error taxonomy on public results |
| `src/core/exit_codes.py` | Process exit mapping (closed in prior wave — don’t break) |

### MCP safety stack

| Module | Role |
|--------|------|
| `src/core/mcp_safety.py` | `SPEND_TOOLS`, `MUTATING_TOOLS`, `CLI_PARITY`, `wrap_mcp_tool`, `live_allowed` (`SUPERAI_MCP_ALLOW_LIVE`) |
| `src/core/mcp_server.py` | Tool registration / dispatch |
| `src/core/foundation_modules.py` | `mcp_safety_parity()` helper |

### Cost stack

| Module | Role |
|--------|------|
| `src/core/cost_accounting.py` | Tokens × registry rates |
| `src/core/cost_forecast.py` / `cost_router.py` | Estimates / board shrink |
| `tests/test_cost_accounting_m002.py` | Cost tests |

---

## Wave A1 — Spend universality

### A1.1 — V4-M1 Budget on all spend paths (@ 85%)

| Field | Value |
|-------|--------|
| **Scorecard** | Not every spend path |
| **Plan** | `docs/IMPROVEMENT_V4_PLAN.md` — Budget not on all spend paths |
| **Implemented** | `spend_guard` on major paths via ModelCaller + board prechecks |

**Backlog intent:** Hard budget ceilings on **every** spend entrypoint (CLI, MCP, HTTP, agent, boards).

**Known covered paths** (`foundation_safety.SPEND_PATHS` — verify still accurate)

- `model_caller.call` / `call_stream`
- `council.run`, `multi_cli_advisory`, `orchestrator`
- `board_preflight`, `mcp_superai_run`, `mcp_safety`
- `web_api_run` (`/api/superai/run`), `public_surface.budget_gate`
- `live_smoke`, `bakeoff_compare`, `nl_ask_run`

**Gaps to close**

- [ ] **Audit:** Run `audit_m001()` (or equivalent CLI) and list any path that spends without `budget_precheck` / `pre_call`. *(I1: falsely checked — audit is shallow; reopen)*
- [ ] **Grep campaign:** Find direct HTTP client / LLM calls that bypass `ModelCaller` (vendor SDKs, raw requests).
- [ ] **Thin wrappers:** agent-tui, goals daemon, forecast, notebook, pr-review, external CLI boards — each either in SPEND_PATHS or proven non-spend.
- [ ] **Stream path:** Confirm `call_stream` always pre_call (coordinate with Grok M027). *(I1: live SSE still skips pre_call — P0)*
- [ ] **command_name:** Pass command names into `budget_precheck` from CLI expensive commands so S132 per-command caps actually bind. *(I1: only council/bakeoff/compare)*
- [ ] **Tests:** Each residual path gets a unit test that monkeypatches `budget_precheck` and asserts call.
- [ ] **Update** `SPEND_PATHS` + `FOUNDATION_SAFETY.md` when done.
- [ ] **Scorecard:** 100% only when audit reports zero residual public spend sinks.

**Verify**

```text
pytest tests/test_foundation_safety_m001_m008_m018.py tests/test_improvement_v4.py -q
rg "budget_precheck|pre_call" src
rg "openai|Anthropic|httpx|requests\.(get|post)" src/core --glob "*.py" | head
```

---

### A1.2 — V4-DOD-1 spend_guard on council / bakeoff / compare / HTTP (@ 85%)

| Field | Value |
|-------|--------|
| **Scorecard** | Residual thin wrappers |
| **Plan** | V4 DoD-strict sweep |
| **Module** | `spend_guard.py` docstring: use on every public spend path |

**Gaps to close**

- [ ] **Council:** Board-level ceiling *before* fan-out + per-member ModelCaller (double-check no early member call skips precheck).
- [ ] **Bakeoff / compare:** Public CLI + library entrypoints use `budget_precheck` + `ensure_public_result`.
- [ ] **HTTP:** `cli/web_app.py` `/api/superai/run` (and any sibling spend routes) — auth + budget + contract.
- [ ] **Thin wrappers residual:** Any “convenience” function that calls models for demos/samples without guard — gate or mark non-public.
- [ ] **Tests:** Dedicated tests per surface: council/bakeoff/compare/HTTP blocked when budget exceeded (mock BudgetGuard).
- [ ] **Docs:** V4 DoD checklist checkboxes all green with file:line evidence.

**Verify**

```text
pytest tests/test_council.py tests/test_improvement_v4.py tests/test_improvement_v5.py -q
rg "budget_precheck|ensure_public_result" src/core/council.py src/core/model_bakeoff.py src/cli/web_app.py
```

---

### A1.3 — V5-M1 CLI / public spend middleware (@ 85%)

| Field | Value |
|-------|--------|
| **Scorecard** | Not all CLI cmds |
| **Implemented** | `public_api.wrap` / `emit_public` on key paths |
| **Plan** | V5 ops maturity |

**Gaps to close**

- [ ] **Inventory:** List top-level Typer commands that can spend (agent, do, ask, council, compare, bakeoff, review, advise, cli-run, …).
- [ ] **Middleware pattern:** Prefer single helper at command end: `emit_public(..., record_spend=...)` + precheck at start for estimated cost.
- [ ] **No double-print / double-exit:** Align with closed M080 `_cli_exit` / `from_result` patterns.
- [ ] **Non-spend commands:** Explicitly exempt (status, help, completion, learning list) so audit isn’t noisy.
- [ ] **Tests:** Sample spend CLI invokes precheck; sample non-spend does not block.
- [ ] **Docs:** V5 plan note “CLI middleware coverage matrix”.

**Verify**

```text
pytest tests/test_improvement_v5.py tests/test_public* -q
# manual: superai --json doctor / superai --json status
```

---

### A1.4 — V5-M2 MCP spend parity (@ 85%)

| Field | Value |
|-------|--------|
| **Scorecard** | Full MCP parity matrix incomplete |
| **Implemented** | `mcp_safety.wrap_mcp_tool` + `SPEND_TOOLS` set; live opt-in env |

**Current SPEND_TOOLS (extend as needed)**

`superai_run`, `superai_ask`, `superai_agent`, `cli_run`, `superai_cli_run`, `superai_council`, `superai_compare`, `superai_bakeoff`, `superai_review`, `superai_advise`, `superai_do`

**Gaps to close**

- [ ] **Matrix completeness:** Every MCP tool that can call a model or paid API is in `SPEND_TOOLS` and goes through `wrap_mcp_tool`.
- [ ] **Dispatch audit:** In `mcp_server` registration, no raw tool handler bypasses wrap for spend tools.
- [ ] **Live gate:** `SUPERAI_MCP_ALLOW_LIVE` remains fail-closed; tests for blocked live without env.
- [ ] **Parity with CLI:** Same budget numbers / error_code shapes as CLI `emit_public` results.
- [ ] **Memory tools:** Mutating memory tools stay in `MUTATING_TOOLS` with permission/dry-run (coordinate with Grok semantics).
- [ ] **Tests:** Each spend tool name asserted in matrix test; one integration mock budget block.
- [ ] **Helper:** Expand `mcp_safety_parity()` report to list missing tools vs registered tools.

**Verify**

```text
pytest tests/test_mcp_server.py tests/test_m079_m027_m093.py -q
rg "wrap_mcp_tool|SPEND_TOOLS" src/core
```

---

## Wave A2 — Result contracts

### A2.1 — V4-M2 Result contract everywhere public (@ 85%)

| Field | Value |
|-------|--------|
| **Scorecard** | Not everywhere public |
| **Implemented** | contracts on major paths via `apply_contract` / `ensure_public_result` / `emit_public` |
| **Related** | M008 stable result contract (complete for many paths — residual is universality) |

**Required envelope fields (typical)**

- `ok`, mock/dry_run honesty, cost fields when spend, `error` / `error_code` on failure, exit_code when emitted via public surface

**Gaps to close**

- [ ] **Public definition:** CLI commands, MCP tools, HTTP JSON APIs — not internal helpers.
- [ ] **Grep for bare returns:** Public handlers returning raw dicts/strings without wrap.
- [ ] **Boards:** council/compare/bakeoff/review member results normalized.
- [ ] **Streaming:** Final stream aggregate result still contracted (chunk path may differ — document).
- [ ] **Tests:** `tests/test_result_contract.py` + per-surface samples; contract registry if used.
- [ ] **Scorecard:** 100% only with inventory checklist attached in docs or test that enumerates public handlers.

**Verify**

```text
pytest tests/test_result_contract.py tests/test_foundation_complete_must.py -q
rg "emit_public|ensure_public_result|apply_contract|wrap_public_result" src/cli/main.py | measure coverage vs commands
```

---

## Wave A3 — Automation surfaces

### A3.1 — M079 JSON output mode for automation (@ 85%)

| Field | Value |
|-------|--------|
| **Scorecard** | Not all commands emit JSON by default under `--json` |
| **Implemented** | Global `--json` + `public_surface.set_json_mode` / `emit_public` prints JSON |

**Gaps to close**

- [ ] **Coverage audit:** With `superai --json <cmd>`, every top-level and important subcommand either:
  - emits one JSON object via `emit_public`, or
  - is documented as human-only (e.g. interactive TUI) and exits with clear non-JSON policy.
- [ ] **No mixed Rich + JSON:** When json_mode, suppress tables or dual-print.
- [ ] **Learning / memory / git / check groups:** Spot-check groups added in hardening wave.
- [ ] **Exit codes:** JSON failure still sets correct process exit (M080 already closed).
- [ ] **Tests:** Parametrize over TOP_30 + learning status + doctor; assert valid JSON parse.
- [ ] **Docs:** CLI help states which commands are interactive exceptions.

**Verify**

```text
superai --json status
superai --json learning status
superai --json doctor --quick
pytest tests/test_m079_m027_m093.py -q -k json
```

---

### A3.2 — M093 MCP parity with CLI safety rules (@ 85%)

| Field | Value |
|-------|--------|
| **Scorecard** | Full MCP tool matrix not exhaustive |
| **Implemented** | `wrap_mcp_tool`: budget + contract + live gate + permission hooks |
| **Maps** | `CLI_PARITY` tool → CLI command strings |

**Safety rules to mirror from CLI**

| Rule | CLI side | MCP side |
|------|----------|----------|
| Budget | spend_guard / BudgetGuard | wrap + SPEND_TOOLS |
| Contract | emit_public / result_contract | wrap_public_result |
| Live opt-in | mock_mode / keys | SUPERAI_MCP_ALLOW_LIVE |
| Permissions | plan/ask/auto/yolo | permission_mode arg on wrap |
| Mutating | dry-run / jail | MUTATING_TOOLS |

**Gaps to close**

- [ ] **Exhaustive matrix:** Auto-build list of registered MCP tools; every tool has CLI_PARITY entry (or explicit `internal`).
- [ ] **Missing tools:** Memory Phase 9 tools (`superai_memory_otel`, `superai_memory_cloud`, `superai_host_hook`, etc.) — classify spend vs free; wrap consistently.
- [ ] **Permission mode:** Mutating tools respect dry_run / permission deny with same error_code as CLI.
- [ ] **Tests:** Matrix completeness test fails CI if new tool registered without safety classification.
- [ ] **Docs:** `docs/clients/MEMORY_API_CONTRACT.md` or MCP section in README — safety table.

**Verify**

```text
pytest tests/test_mcp_server.py tests/test_m079_m027_m093.py -q
# foundation_modules.mcp_safety_parity()
```

---

## Wave A4 — Cost accuracy

### A4.1 — V5-M4 Accurate cost from registry (@ 90%)

| Field | Value |
|-------|--------|
| **Scorecard** | Estimate fallbacks remain |
| **Implemented** | `cost_accounting` tokens × registry rates |
| **Related** | M002 (often complete) — this residual is estimate fallback honesty |

**Gaps to close**

- [ ] **Estimate path:** Pre-flight estimates that use hardcoded defaults (0.1 USD / 500 tokens in `budget_precheck` defaults) should pull model registry rates when model known.
- [ ] **Unknown model:** Explicit `estimate_source: fallback|registry|actual` field on cost dicts — never silent wrong precision.
- [ ] **Post-call actuals:** Prefer provider usage tokens when present; fallback to char heuristics with label.
- [ ] **Board estimates:** council/bakeoff preflight uses registry for each member model.
- [ ] **Tests:** known model → registry rate; unknown → fallback flagged; actual usage overrides estimate.
- [ ] **Docs:** `docs/COST_ACCOUNTING.md` estimate vs actual table.

**Verify**

```text
pytest tests/test_cost_accounting_m002.py tests/test_improvement_v5.py -q
```

---

## Wave A5 — TOP_30 contract depth

### A5.1 — M090 Contract tests on top 30 commands (@ 80%)

| Field | Value |
|-------|--------|
| **Scorecard** | Not live invocation of all 30 CLIs |
| **Implemented** | `public_surface.TOP_30_COMMANDS` + `verify_top_commands_registered` / `foundation_complete.verify_top30_contracts` |
| **CLI** | foundation / v6-status style reporting includes M090 |

**What “registered” vs “invoked” means**

- Today: many checks only ensure command names exist on Typer app.
- Target: offline **invoke** each TOP_30 command with safe args (mock mode) and assert result contract + exit code path.

**Gaps to close**

- [ ] **Refresh TOP_30 list:** Align with real highest-value public commands (include learning/status/doctor/agent if product-critical).
- [ ] **Invocation harness:** For each command, run with `CliRunner` or subprocess `superai --json ...` under mock; assert JSON has `ok`/`honesty`/`exit_code` as applicable.
- [ ] **Skip policy:** Interactive-only commands documented and excluded with reason (not silent skip).
- [ ] **CI time budget:** Keep suite offline-fast; no live keys.
- [ ] **Failure output:** Which command failed + missing contract fields.
- [ ] **Tests:** `verify_top30` upgrades from registration to invocation; one intentional broken fixture proves detection.
- [ ] **Scorecard:** 100% when all TOP_30 invoked offline with contracts.

**Verify**

```text
pytest tests/test_foundation_complete_must.py -q -k top30
superai # any foundation-status command that prints M090
```

---

## Explicitly not on this board

| Item | Owner |
|------|--------|
| M061–M063 learning product UX, M050/M068 routing product, M027/V4-M4 streaming depth, M100 dashboard, M089 host smoke | **Grok** → `TASKBOARD_GROK.md` |
| M091 cold-start (50%) | Unassigned |
| Closed W0–W4 exit/help/critique items | Archive only |

---

## Coordination with Grok

| Topic | AGY | Grok |
|-------|-----|------|
| Stream spend | Guard + contract on stream complete | SSE/provider coverage + meta |
| Learning MCP | wrap + MUTATING_TOOLS classification | lifecycle semantics / deprecate honesty |
| JSON mode | All CLI emit | Learning commands already JSON-friendly — keep green |
| Cost for bandit rewards | Accurate actuals (V5-M4) | Bandit update wiring (M050) |

---

## Full verify pack (AGY)

```text
pytest tests/test_foundation_safety_m001_m008_m018.py tests/test_foundation_complete_must.py tests/test_foundation_lift.py -q
pytest tests/test_cost_accounting_m002.py tests/test_result_contract.py -q
pytest tests/test_m079_m027_m093.py tests/test_mcp_server.py -q
pytest tests/test_improvement_v4.py tests/test_improvement_v5.py -q
rg "budget_precheck|emit_public|wrap_mcp_tool|TOP_30" src
```

---

## Last session

| Field | Value |
|-------|--------|
| **When** | 2026-07-24 |
| **What** | **I1 A1–A5 offline closed:** thin-wrapper prechecks, TOP_30 real invoke harness, spend assertion tests, scorecard 100% offline. AGY WIP + Grok finish. |
| **Still open** | None for offline A1–A5; host live keys still out of AGY board |
| **Closeout** | [`docs/agy_work_review_result_I1_v4.md`](docs/agy_work_review_result_I1_v4.md) |
| **Prior** | v3 re-audit (partial) · v2 overclaim · v1 pickup |
| **Archive** | `docs/archive/2026-07-24-wave-handoffs/` |
