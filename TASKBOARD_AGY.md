# TASKBOARD — AGY (Spend / Contracts / CLI–MCP Surfaces)

**Owner:** AGY (Antigravity)  
**Peer board:** [`TASKBOARD_GROK.md`](TASKBOARD_GROK.md)  
**Index:** [`TASKBOARD.md`](TASKBOARD.md)  
**Scorecard:** [`docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md`](docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md)  
**Bar:** production code + thorough docs + full tests + product wiring (CLI/MCP where claimed). No false 100%.  
**Created:** 2026-07-24 · Split from near-complete Musts (>70%)  

**Legend:** `[ ]` open · `[~]` in progress · `[x]` done · `[!]` host-gated  

---

## Prior wave (archived — do not re-open)

| Track | Status | Archive |
|-------|--------|---------|
| Hardening Wave W0–W4 (M080/M015/M081/M082, S104–S132 pack) | **DONE** | `docs/archive/2026-07-24-wave-handoffs/` |
| Plan | **DONE** | `AGY_IMPROVEMENT_PLAN.md` in same archive |
| Findings re-reviews #1–#7 | Historical | `AGY_HANDOFF_PENDING_AND_INCOMPLETE.md` in archive |

---

## Active Musts (9) — near-complete foundation

Suggested order: **spend spine** first (V4-M1 → V4-DOD-1 → V5-M1 → V5-M2), then contracts, then JSON/MCP matrix, then cost fallbacks, then TOP_30.

### Wave A1 — Spend universality (85%)

| Status | ID | Title | Residual | Hints |
|--------|-----|--------|----------|-------|
| [ ] | **V4-M1** | Budget on all spend paths | Not every spend path | `spend_guard` major paths → remaining thin call sites |
| [ ] | **V4-DOD-1** | spend_guard on council/bakeoff/compare/HTTP | Residual thin wrappers | DoD sweep; no silent bypass |
| [ ] | **V5-M1** | CLI/public spend middleware | Not all CLI cmds | `public_api.wrap` key paths → remaining cmds |
| [ ] | **V5-M2** | MCP spend parity | Full MCP parity matrix incomplete | `superai_run` budget → full tool matrix |

### Wave A2 — Result contracts (85%)

| Status | ID | Title | Residual | Hints |
|--------|-----|--------|----------|-------|
| [ ] | **V4-M2** | Result contract everywhere public | Not everywhere public | contracts major paths → remaining public surfaces |

### Wave A3 — Automation surfaces (85%)

| Status | ID | Title | Residual | Hints |
|--------|-----|--------|----------|-------|
| [ ] | **M079** | JSON output mode for automation | Not all commands emit JSON by default | global `--json`; close residual cmds |
| [ ] | **M093** | MCP parity with CLI safety rules | Full MCP tool matrix not exhaustive | `mcp_safety` wrap; exhaustive matrix |

### Wave A4 — Cost accuracy (90%)

| Status | ID | Title | Residual | Hints |
|--------|-----|--------|----------|-------|
| [ ] | **V5-M4** | Accurate cost from registry | Estimate fallbacks remain | `cost_accounting`; honest estimates |

### Wave A5 — Contract test depth (80%)

| Status | ID | Title | Residual | Hints |
|--------|-----|--------|----------|-------|
| [ ] | **M090** | Contract tests on top 30 commands | Not live invocation of all 30 CLIs | TOP_30 + contract smoke → full live invoke offline |

---

## Explicitly not on this board

| Item | Owner |
|------|--------|
| M061–M063 learning product UX, M050/M068 routing, M027/V4-M4 streaming, M100 dashboard, M089 host smoke | **Grok** → `TASKBOARD_GROK.md` |
| M091 cold-start perf budgets (50%) | Unassigned backlog until near-complete set moves |
| Re-litigating closed W0–W4 checklist items | Archived; only re-open if regression |

---

## Coordination with Grok

- **Spend + stream:** If streaming paths spend tokens, AGY ensures spend_guard/contract wrap; Grok ensures stream completeness (M027/V4-M4).
- **JSON + MCP:** M079/M093 are AGY; memory MCP tools already exist — extend safety parity, do not regress memory CLI.
- **Scorecard:** Demote rather than overclaim; regenerate improved scorecard only for closed IDs with tests.

---

## Verify (copy/paste)

```text
pytest tests/test_foundation_safety_m001_m008_m018.py tests/test_foundation_complete_must.py tests/test_foundation_lift.py -q
pytest tests/test_cost_accounting_m002.py tests/test_result_contract.py -q
pytest tests/test_m079_m027_m093.py tests/test_mcp_server.py -q
pytest tests/test_improvement_v4.py tests/test_improvement_v5.py -q
# after each closed ID: update this board Last session + scorecard row if earned
```

---

## Last session

| Field | Value |
|-------|--------|
| **When** | 2026-07-24 |
| **What** | Board created; prior AGY handoff + W0–W4 plan archived; 9 Musts assigned |
| **Still open** | All A1–A5 items above |
| **Archive** | `docs/archive/2026-07-24-wave-handoffs/` |
