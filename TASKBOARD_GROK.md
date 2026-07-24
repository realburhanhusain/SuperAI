# TASKBOARD — Grok (Memory / Learning / Routing Honesty)

**Owner:** Grok  
**Peer board:** [`TASKBOARD_AGY.md`](TASKBOARD_AGY.md)  
**Index:** [`TASKBOARD.md`](TASKBOARD.md)  
**Scorecard:** [`docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md`](docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md)  
**Bar:** production code + thorough docs + full tests (strict). Promote scorecard rows only after evidence.  
**Created:** 2026-07-24 · Split from near-complete Musts (>70%)  

**Legend:** `[ ]` open · `[~]` in progress · `[x]` done · `[!]` host-gated  

---

## Prior wave (archived — do not re-open)

| Track | Status | Archive |
|-------|--------|---------|
| Memory P1–P9 offline + integrity handoff | **DONE** | `docs/archive/2026-07-24-wave-handoffs/GROK_HANDOFF_PENDING_AND_INCOMPLETE.md` |
| AGY hardening reassignment (exits, help, S105/S109) | **DONE** | same archive folder + historical `TASKBOARD.md` sections |

---

## Active Musts (9) — near-complete / host

Suggested order: **M061 → M062 → M063** first (learning product), then routing/bandit, then streaming, then dashboard; **M089** only when host keys are intentional.

### Wave G1 — Learning lifecycle product (85%)

| Status | ID | Title | Residual | Hints |
|--------|-----|--------|----------|-------|
| [ ] | **M061** | Learning: promote durable patterns only | Product UX incomplete | `learning_engine` / lifecycle CLI; `tests/test_learning_lifecycle_m061_m063.py` |
| [ ] | **M062** | Conflict resolution for contradictory memories | Conflict UI incomplete | resolve path + product surface; docs `LEARNING_LIFECYCLE.md` |
| [ ] | **M063** | Distill / deprecate redundant memories | Lifecycle product incomplete | distill/deprecate + honest noop; no false 100% |

### Wave G2 — Routing & preferences (80–85%)

| Status | ID | Title | Residual | Hints |
|--------|-----|--------|----------|-------|
| [ ] | **M068** | Preferences that bias routing | Deep routing bias not fully proven | `preferences.bias_candidates`; prove end-to-end bias |
| [ ] | **M050** | Bandit / learned routing from outcomes | Not continuous-product UI | bandit reorder+update → product surface |

### Wave G3 — Streaming honesty (85%)

| Status | ID | Title | Residual | Hints |
|--------|-----|--------|----------|-------|
| [ ] | **M027** | Real token streaming where supported | Not all providers proven live | `call_stream` SSE + fallback; document offline vs live |
| [ ] | **V4-M4** | Provider stream API path | Provider coverage incomplete | Pair with M027; coordinate contract shape with AGY V4-M2 |

### Wave G4 — Dashboard honesty (80%)

| Status | ID | Title | Residual | Hints |
|--------|-----|--------|----------|-------|
| [ ] | **M100** | Honest dashboard: mock vs live | Full dashboard product incomplete | honesty labels; `cli/dashboard.py` |

### Wave G5 — Host-gated (90%) — last

| Status | ID | Title | Residual | Hints |
|--------|-----|--------|----------|-------|
| [!] | **M089** | Live multi-provider smoke matrix | Live keys required | Phase 99; also `V1-P99` / `MOS-N8` on index board. Do **not** block offline work. |

---

## Explicitly not on this board

| Item | Owner |
|------|--------|
| Spend_guard / public contracts / MCP spend / TOP_30 contracts / JSON-all-commands | **AGY** → `TASKBOARD_AGY.md` |
| M091 cold-start perf budgets (50%) | Unassigned backlog until near-complete set moves |
| Live OTLP collector / cloud control plane | Host-optional; not scorecard Must in this split |

---

## Coordination with AGY

- **Streaming results + cost fields:** Grok owns stream path completeness (M027/V4-M4); AGY owns contract/spend wrappers (V4-M2, V5-M1). Align before claiming 100%.
- **Scorecard regen:** Prefer regenerating improved scorecard only for IDs you close; do not bulk-promote foundations.
- **Do not** re-open archived handoff checklists; link them only as history.

---

## Verify (copy/paste)

```text
pytest tests/test_learning_lifecycle_m061_m063.py tests/test_learning.py tests/test_learning_engine_gaps.py -q
pytest tests/test_m079_m027_m093.py -q
pytest tests/test_msg_vega_plugin_bandit.py -q
# after each closed ID: update this board Last session + scorecard row if earned
```

---

## Last session

| Field | Value |
|-------|--------|
| **When** | 2026-07-24 |
| **What** | Board created; prior Grok handoff archived; 9 Musts assigned |
| **Still open** | All G1–G5 items above |
| **Archive** | `docs/archive/2026-07-24-wave-handoffs/` |
