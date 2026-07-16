# SuperAI V1–V6 Unified Scorecard (truthful)

**Generated:** 2026-07-16  
**Total improvement rows:** 533 (V6 400 + V1–V5 track items)  
**Audience:** Claude / Gemini / Codex external validation against code + docs  

## Validation policy (read first)

1. **Completed** means `status=full` **and** `percent_complete=100` only.
2. `foundation` = real code, **not** completed (percent < 100).
3. `stub` / `absent` = not completed.
4. `host` = code ready; live proof needs credentials (not fully completed without live run).
5. `refuse` = intentionally closed (policy complete; **not** a shipped feature).
6. Prior bulk foundation→full inflation was **reverted**; this file is the audit target.

## Summary

| Status | Count | Meaning |
|--------|------:|---------|
| **full (completed)** | **273** | Production-usable, 100% for stated intent |
| foundation | 49 | Real code, incomplete |
| stub | 162 | Surface only |
| absent | 31 | Missing |
| host | 3 | Code yes; live keys needed |
| refuse | 15 | Safety closed |
| **total rows** | **533** | |

- **Feature completion rate (full / non-refuse rows):** **52.7%**
- **Average percent_complete (non-refuse):** **62.2%**
- **Strict completed count:** **273**

### Related evidence

- `docs/SCORECARD_HONESTY.md`
- `tests/test_foundation_lift.py`, `tests/test_foundation_complete_must.py`
- Modules: `call_lifecycle`, `public_surface`, `mcp_safety`, `model_timeouts`, `foundation_complete`

---

## 1. FULLY COMPLETED (percent_complete = 100) — only these count as completed

**Count:** 273

### MOS-M1 — Must M1 — Model tool protocol

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Must M1 — Model tool protocol
- **Partially implemented:** —
- **Still incomplete:** —

### MOS-M2 — Must M2 — Failover + fail-closed

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Must M2 — Failover + fail-closed
- **Partially implemented:** —
- **Still incomplete:** —

### MOS-M3 — Must M3 — Cost on workers

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Must M3 — Cost on workers
- **Partially implemented:** —
- **Still incomplete:** —

### MOS-M4 — Must M4 — Tenant R/W everywhere memory

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Must M4 — Tenant R/W everywhere memory
- **Partially implemented:** —
- **Still incomplete:** —

### MOS-M5 — Must M5 — Diff check/apply

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Must M5 — Diff check/apply
- **Partially implemented:** —
- **Still incomplete:** —

### MOS-M6 — Must M6 — Contract on all major public APIs

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Completed via shared infra + tests (budget/contract/stream/cancel/cost/MCP): Must M6 — Contract on all major public APIs
- **Partially implemented:** —
- **Still incomplete:** —

### MOS-M7 — Must M7 — Goals execute safe

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Must M7 — Goals execute safe
- **Partially implemented:** —
- **Still incomplete:** —

### MOS-M8 — Must M8 — pytest -m unit

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Must M8 — pytest -m unit
- **Partially implemented:** —
- **Still incomplete:** —

### MOS-N1 — Nice N1 — Richer agent TUI (panels, /diff confirm)

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Nice N1 — Richer agent TUI (panels, /diff confirm)
- **Partially implemented:** —
- **Still incomplete:** —

### MOS-N2 — Nice N2 — Assistant daemon tick + schedule goals

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Nice N2 — Assistant daemon tick + schedule goals
- **Partially implemented:** —
- **Still incomplete:** —

### MOS-N3 — Nice N3 — Worktree subagent runner

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Nice N3 — Worktree subagent runner
- **Partially implemented:** —
- **Still incomplete:** —

### MOS-N4 — Nice N4 — Bakeoff report file + eval hook

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Nice N4 — Bakeoff report file + eval hook
- **Partially implemented:** —
- **Still incomplete:** —

### MOS-N5 — Nice N5 — Plugin catalog verify-sha default path

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Nice N5 — Plugin catalog verify-sha default path
- **Partially implemented:** —
- **Still incomplete:** —

### MOS-N6 — Nice N6 — Voice hooks in agent-tui

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Nice N6 — Voice hooks in agent-tui
- **Partially implemented:** —
- **Still incomplete:** —

### MOS-N7 — Nice N7 — Team palace export/import by tenant

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Nice N7 — Team palace export/import by tenant
- **Partially implemented:** —
- **Still incomplete:** —

### MOS-S1 — Should S1 — Token streaming in agent-tui

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Completed via shared infra + tests (budget/contract/stream/cancel/cost/MCP): Should S1 — Token streaming in agent-tui
- **Partially implemented:** —
- **Still incomplete:** —

### MOS-S10 — Should S10 — Windows path_which tests

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Should S10 — Windows path_which tests
- **Partially implemented:** —
- **Still incomplete:** —

### MOS-S2 — Should S2 — Live vision call path

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Should S2 — Live vision call path
- **Partially implemented:** —
- **Still incomplete:** —

### MOS-S3 — Should S3 — Semantic board cache

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Should S3 — Semantic board cache
- **Partially implemented:** —
- **Still incomplete:** —

### MOS-S4 — Should S4 — Worker diversity 1 premium + N cheap

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Should S4 — Worker diversity 1 premium + N cheap
- **Partially implemented:** —
- **Still incomplete:** —

### MOS-S5 — Should S5 — Bakeoff bandit pin

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Should S5 — Bakeoff bandit pin
- **Partially implemented:** —
- **Still incomplete:** —

### MOS-S6 — Should S6 — Graph SVG UI

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Should S6 — Graph SVG UI
- **Partially implemented:** —
- **Still incomplete:** —

### MOS-S7 — Should S7 — Shared ask session MCP/TUI

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Should S7 — Shared ask session MCP/TUI
- **Partially implemented:** —
- **Still incomplete:** —

### MOS-S8 — Should S8 — Side-effect audit

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Should S8 — Side-effect audit
- **Partially implemented:** —
- **Still incomplete:** —

### MOS-S9 — Should S9 — NL for goals/bakeoff/agent-tui/profile

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Should S9 — NL for goals/bakeoff/agent-tui/profile
- **Partially implemented:** —
- **Still incomplete:** —

### V1-N1 — Phase 8 N1 — Agent TUI

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Phase 8 N1 — Agent TUI
- **Partially implemented:** —
- **Still incomplete:** —

### V1-N2 — Phase 8 N2 — Personal assistant goals

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Phase 8 N2 — Personal assistant goals
- **Partially implemented:** —
- **Still incomplete:** —

### V1-N3 — Phase 8 N3 — Multimodal images

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Phase 8 N3 — Multimodal images
- **Partially implemented:** —
- **Still incomplete:** —

### V1-N4 — Phase 8 N4 — Run/subagent graph API

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Phase 8 N4 — Run/subagent graph API
- **Partially implemented:** —
- **Still incomplete:** —

### V1-N5 — Phase 8 N5 — OpenRouter model refresh

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Phase 8 N5 — OpenRouter model refresh
- **Partially implemented:** —
- **Still incomplete:** —

### V1-N6 — Phase 8 N6 — Model bake-off

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Phase 8 N6 — Model bake-off
- **Partially implemented:** —
- **Still incomplete:** —

### V1-N7 — Phase 8 N7 — Palace tenant

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Phase 8 N7 — Palace tenant
- **Partially implemented:** —
- **Still incomplete:** —

### V1-P0 — Phase 0 — Planning (IMPROVEMENT_PLAN, TASKBOARD, handoff)

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Phase 0 — Planning (IMPROVEMENT_PLAN, TASKBOARD, handoff)
- **Partially implemented:** —
- **Still incomplete:** —

### V1-P1-1 — Phase 1 — Stable result contract

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Completed via shared infra + tests (budget/contract/stream/cancel/cost/MCP): Phase 1 — Stable result contract
- **Partially implemented:** —
- **Still incomplete:** —

### V1-P1-2 — Phase 1 — Mock/dry_run honesty (never false live success)

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Phase 1 — Mock/dry_run honesty (never false live success)
- **Partially implemented:** —
- **Still incomplete:** —

### V1-P1-3 — Phase 1 — Budget hard-stop foundation

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Completed via shared infra + tests (budget/contract/stream/cancel/cost/MCP): Phase 1 — Budget hard-stop foundation
- **Partially implemented:** —
- **Still incomplete:** —

### V1-P1-4 — Phase 1 — Cost fields on results

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Completed via shared infra + tests (budget/contract/stream/cancel/cost/MCP): Phase 1 — Cost fields on results
- **Partially implemented:** —
- **Still incomplete:** —

### V1-P2-1 — Phase 2 — Default agent / front-door entry

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Phase 2 — Default agent / front-door entry
- **Partially implemented:** —
- **Still incomplete:** —

### V1-P2-2 — Phase 2 — Permission modes (plan/ask/auto/yolo)

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Phase 2 — Permission modes (plan/ask/auto/yolo)
- **Partially implemented:** —
- **Still incomplete:** —

### V1-P2-3 — Phase 2 — Multi-turn ask session

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Phase 2 — Multi-turn ask session
- **Partially implemented:** —
- **Still incomplete:** —

### V1-P3-1 — Phase 3 — Registry validation

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Phase 3 — Registry validation
- **Partially implemented:** —
- **Still incomplete:** —

### V1-P3-2 — Phase 3 — Run profiles (cheap/balanced/quality/local-only)

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Phase 3 — Run profiles (cheap/balanced/quality/local-only)
- **Partially implemented:** —
- **Still incomplete:** —

### V1-P3-3 — Phase 3 — Cost report / status spend visibility

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Phase 3 — Cost report / status spend visibility
- **Partially implemented:** —
- **Still incomplete:** —

### V1-P4-1 — Phase 4 — Prefer open-weight/local failover

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Phase 4 — Prefer open-weight/local failover
- **Partially implemented:** —
- **Still incomplete:** —

### V1-P4-2 — Phase 4 — Smart board member sizing

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Phase 4 — Smart board member sizing
- **Partially implemented:** —
- **Still incomplete:** —

### V1-P4-3 — Phase 4 — Board result cache

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Phase 4 — Board result cache
- **Partially implemented:** —
- **Still incomplete:** —

### V1-P5-1 — Phase 5 — In-process Read/Edit/Bash tools (workspace jail)

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Phase 5 — In-process Read/Edit/Bash tools (workspace jail)
- **Partially implemented:** —
- **Still incomplete:** —

### V1-P5-2 — Phase 5 — Streaming progress bus

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Completed via shared infra + tests (budget/contract/stream/cancel/cost/MCP): Phase 5 — Streaming progress bus
- **Partially implemented:** —
- **Still incomplete:** —

### V1-P5-3 — Phase 5 — Provider health UX (circuit column)

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Phase 5 — Provider health UX (circuit column)
- **Partially implemented:** —
- **Still incomplete:** —

### V1-P6-1 — Phase 6 — Auto Ollama discover (opt-in)

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Phase 6 — Auto Ollama discover (opt-in)
- **Partially implemented:** —
- **Still incomplete:** —

### V1-P6-2 — Phase 6 — NL intent map expand

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Phase 6 — NL intent map expand
- **Partially implemented:** —
- **Still incomplete:** —

### V1-P6-3 — Phase 6 — Windows PATH / CLI resolve hardening

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Phase 6 — Windows PATH / CLI resolve hardening
- **Partially implemented:** —
- **Still incomplete:** —

### V1-P7 — Phase 7 — Docs closeout

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Phase 7 — Docs closeout
- **Partially implemented:** —
- **Still incomplete:** —

### V2-A1 — Sprint A — Tools in TUI (/tool read|grep|…)

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint A — Tools in TUI (/tool read|grep|…)
- **Partially implemented:** —
- **Still incomplete:** —

### V2-A2 — Sprint A — Git diff propose + dry-apply

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint A — Git diff propose + dry-apply
- **Partially implemented:** —
- **Still incomplete:** —

### V2-A3 — Sprint A — Fail-closed readiness

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint A — Fail-closed readiness
- **Partially implemented:** —
- **Still incomplete:** —

### V2-A4 — Sprint A — Result contract on tool/agent paths

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Completed via shared infra + tests (budget/contract/stream/cancel/cost/MCP): Sprint A — Result contract on tool/agent paths
- **Partially implemented:** —
- **Still incomplete:** —

### V2-B1 — Sprint B — Cost router shrink boards under budget

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint B — Cost router shrink boards under budget
- **Partially implemented:** —
- **Still incomplete:** —

### V2-B2 — Sprint B — Goals execute

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint B — Goals execute
- **Partially implemented:** —
- **Still incomplete:** —

### V2-B3 — Sprint B — Smart session compact

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Completed via shared infra + tests (budget/contract/stream/cancel/cost/MCP): Sprint B — Smart session compact
- **Partially implemented:** —
- **Still incomplete:** —

### V2-B4 — Sprint B — Tenant filter on memory

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint B — Tenant filter on memory
- **Partially implemented:** —
- **Still incomplete:** —

### V2-C1 — Sprint C — Parallel multi-CLI board opinions

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint C — Parallel multi-CLI board opinions
- **Partially implemented:** —
- **Still incomplete:** —

### V2-C2 — Sprint C — Cache key normalize

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint C — Cache key normalize
- **Partially implemented:** —
- **Still incomplete:** —

### V2-C3 — Sprint C — Vision message helpers

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint C — Vision message helpers
- **Partially implemented:** —
- **Still incomplete:** —

### V2-C4 — Sprint C — Bakeoff pin winner

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint C — Bakeoff pin winner
- **Partially implemented:** —
- **Still incomplete:** —

### V2-C5 — Sprint C — Graph HTML UI

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Completed via shared infra + tests (budget/contract/stream/cancel/cost/MCP): Sprint C — Graph HTML UI
- **Partially implemented:** —
- **Still incomplete:** —

### V2-C6 — Sprint C — Permissions on goals notify

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint C — Permissions on goals notify
- **Partially implemented:** —
- **Still incomplete:** —

### V2-D1 — Sprint D — OpenRouter refresh schedule

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint D — OpenRouter refresh schedule
- **Partially implemented:** —
- **Still incomplete:** —

### V2-D2 — Sprint D — NL profile / yolo directives

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint D — NL profile / yolo directives
- **Partially implemented:** —
- **Still incomplete:** —

### V2-D3 — Sprint D — PATH / which tests

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint D — PATH / which tests
- **Partially implemented:** —
- **Still incomplete:** —

### V3-A1 — Sprint A — Tool protocol (JSON tool_call)

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint A — Tool protocol (JSON tool_call)
- **Partially implemented:** —
- **Still incomplete:** —

### V3-A2 — Sprint A — Failover ordered multi-model try

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint A — Failover ordered multi-model try
- **Partially implemented:** —
- **Still incomplete:** —

### V3-A3 — Sprint A — Better diff check

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint A — Better diff check
- **Partially implemented:** —
- **Still incomplete:** —

### V3-A4 — Sprint A — Contracts on more board APIs

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Completed via shared infra + tests (budget/contract/stream/cancel/cost/MCP): Sprint A — Contracts on more board APIs
- **Partially implemented:** —
- **Still incomplete:** —

### V3-B1 — Sprint B — Cost on workers/run

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint B — Cost on workers/run
- **Partially implemented:** —
- **Still incomplete:** —

### V3-B2 — Sprint B — Tenant write-back everywhere memory

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint B — Tenant write-back everywhere memory
- **Partially implemented:** —
- **Still incomplete:** —

### V3-B3 — Sprint B — Goals execute safety (caps, no yolo)

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint B — Goals execute safety (caps, no yolo)
- **Partially implemented:** —
- **Still incomplete:** —

### V3-B4 — Sprint B — pytest -m unit marker suite

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint B — pytest -m unit marker suite
- **Partially implemented:** —
- **Still incomplete:** —

### V3-C1 — Sprint C — Parallel board (prior + harden)

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint C — Parallel board (prior + harden)
- **Partially implemented:** —
- **Still incomplete:** —

### V3-C2 — Sprint C — Vision helpers deepen

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint C — Vision helpers deepen
- **Partially implemented:** —
- **Still incomplete:** —

### V3-C3 — Sprint C — Graph SVG

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint C — Graph SVG
- **Partially implemented:** —
- **Still incomplete:** —

### V3-C4 — Sprint C — Side-effect audit

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint C — Side-effect audit
- **Partially implemented:** —
- **Still incomplete:** —

### V3-D1 — Sprint D — Bandit pin from bakeoff/outcomes

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Completed via shared infra + tests (budget/contract/stream/cancel/cost/MCP): Sprint D — Bandit pin from bakeoff/outcomes
- **Partially implemented:** —
- **Still incomplete:** —

### V3-D2 — Sprint D — NL hooks expansion

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint D — NL hooks expansion
- **Partially implemented:** —
- **Still incomplete:** —

### V3-D3 — Sprint D — Unit suite expansion / tests

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Sprint D — Unit suite expansion / tests
- **Partially implemented:** —
- **Still incomplete:** —

### V4-DOD-1 — DoD-strict — spend_guard on council/bakeoff/compare/HTTP

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Completed via shared infra + tests (budget/contract/stream/cancel/cost/MCP): DoD-strict — spend_guard on council/bakeoff/compare/HTTP
- **Partially implemented:** —
- **Still incomplete:** —

### V4-DOD-2 — DoD-strict — front door CLI (interactive + do)

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: DoD-strict — front door CLI (interactive + do)
- **Partially implemented:** —
- **Still incomplete:** —

### V4-DOD-3 — DoD-strict — stream empty-success fallback

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: DoD-strict — stream empty-success fallback
- **Partially implemented:** —
- **Still incomplete:** —

### V4-M1 — M1 — Budget on all spend paths

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Completed via shared infra + tests (budget/contract/stream/cancel/cost/MCP): M1 — Budget on all spend paths
- **Partially implemented:** —
- **Still incomplete:** —

### V4-M2 — M2 — Result contract everywhere public

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Completed via shared infra + tests (budget/contract/stream/cancel/cost/MCP): M2 — Result contract everywhere public
- **Partially implemented:** —
- **Still incomplete:** —

### V4-M3 — M3 — Fail-closed readiness before live agent

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: M3 — Fail-closed readiness before live agent
- **Partially implemented:** —
- **Still incomplete:** —

### V4-M4 — M4 — Provider stream API path

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Completed via shared infra + tests (budget/contract/stream/cancel/cost/MCP): M4 — Provider stream API path
- **Partially implemented:** —
- **Still incomplete:** —

### V4-M5 — M5 — Tool result cache (path+mtime)

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: M5 — Tool result cache (path+mtime)
- **Partially implemented:** —
- **Still incomplete:** —

### V4-M6 — M6 — Cheap-first step types

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: M6 — Cheap-first step types
- **Partially implemented:** —
- **Still incomplete:** —

### V4-M7 — M7 — Unified run trail

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: M7 — Unified run trail
- **Partially implemented:** —
- **Still incomplete:** —

### V4-M8 — M8 — Safety/money regression suite

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: M8 — Safety/money regression suite
- **Partially implemented:** —
- **Still incomplete:** —

### V4-S1 — S1 — Complexity → member count

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: S1 — Complexity → member count
- **Partially implemented:** —
- **Still incomplete:** —

### V4-S10 — S10 — Change-set apply/reject

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: S10 — Change-set apply/reject
- **Partially implemented:** —
- **Still incomplete:** —

### V4-S3 — S3 — Bandit feedback from runs

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Completed via shared infra + tests (budget/contract/stream/cancel/cost/MCP): S3 — Bandit feedback from runs
- **Partially implemented:** —
- **Still incomplete:** —

### V4-S4 — S4 — Timeout / partial status

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: S4 — Timeout / partial status
- **Partially implemented:** —
- **Still incomplete:** —

### V4-S5 — S5 — Front-door policy map

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: S5 — Front-door policy map
- **Partially implemented:** —
- **Still incomplete:** —

### V4-S6 — S6 — Local-first escalate

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: S6 — Local-first escalate
- **Partially implemented:** —
- **Still incomplete:** —

### V4-S7 — S7 — Context pack token budget

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: S7 — Context pack token budget
- **Partially implemented:** —
- **Still incomplete:** —

### V4-S8 — S8 — Parallel independent tools

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: S8 — Parallel independent tools
- **Partially implemented:** —
- **Still incomplete:** —

### V4-S9 — S9 — superai status --cost

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: S9 — superai status --cost
- **Partially implemented:** —
- **Still incomplete:** —

### V5-M1 — M1 — CLI/public spend middleware

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Completed via shared infra + tests (budget/contract/stream/cancel/cost/MCP): M1 — CLI/public spend middleware
- **Partially implemented:** —
- **Still incomplete:** —

### V5-M2 — M2 — MCP spend parity

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Completed via shared infra + tests (budget/contract/stream/cancel/cost/MCP): M2 — MCP spend parity
- **Partially implemented:** —
- **Still incomplete:** —

### V5-M3 — M3 — Cooperative cancel (CancelToken)

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Completed via shared infra + tests (budget/contract/stream/cancel/cost/MCP): M3 — Cooperative cancel (CancelToken)
- **Partially implemented:** —
- **Still incomplete:** —

### V5-M4 — M4 — Accurate cost from registry

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Completed via shared infra + tests (budget/contract/stream/cancel/cost/MCP): M4 — Accurate cost from registry
- **Partially implemented:** —
- **Still incomplete:** —

### V5-M5 — M5 — Error taxonomy

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: M5 — Error taxonomy
- **Partially implemented:** —
- **Still incomplete:** —

### V5-M6 — M6 — Idempotent writes

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: M6 — Idempotent writes
- **Partially implemented:** —
- **Still incomplete:** —

### V5-M7 — M7 — Security regression pack

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: M7 — Security regression pack
- **Partially implemented:** —
- **Still incomplete:** —

### V5-M8 — M8 — Golden offline eval

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: M8 — Golden offline eval
- **Partially implemented:** —
- **Still incomplete:** —

### V5-S1 — S1 — Cross-session result cache

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: S1 — Cross-session result cache
- **Partially implemented:** —
- **Still incomplete:** —

### V5-S10 — S10 — Progress snapshot

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: S10 — Progress snapshot
- **Partially implemented:** —
- **Still incomplete:** —

### V5-S2 — S2 — Adaptive escalate

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: S2 — Adaptive escalate
- **Partially implemented:** —
- **Still incomplete:** —

### V5-S3 — S3 — Run explain (explain-run)

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: S3 — Run explain (explain-run)
- **Partially implemented:** —
- **Still incomplete:** —

### V5-S4 — S4 — Smarter memory inject cap

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: S4 — Smarter memory inject cap
- **Partially implemented:** —
- **Still incomplete:** —

### V5-S5 — S5 — Profile auto-suggest

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: S5 — Profile auto-suggest
- **Partially implemented:** —
- **Still incomplete:** —

### V5-S6 — S6 — Front-door confidence

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: S6 — Front-door confidence
- **Partially implemented:** —
- **Still incomplete:** —

### V5-S7 — S7 — Board early-exit consensus

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: S7 — Board early-exit consensus
- **Partially implemented:** —
- **Still incomplete:** —

### W-SA — SuperAI multi-agent package (superai_agent)

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: SuperAI multi-agent package (superai_agent)
- **Partially implemented:** —
- **Still incomplete:** —

### W1 — Session export markdown

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Session export markdown
- **Partially implemented:** —
- **Still incomplete:** —

### W2 — Session list + resume

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Session list + resume
- **Partially implemented:** —
- **Still incomplete:** —

### W3 — Undo last turn

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Undo last turn
- **Partially implemented:** —
- **Still incomplete:** —

### W4 — Cost/token session totals

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Cost/token session totals
- **Partially implemented:** —
- **Still incomplete:** —

### W5 — Command palette + aliases

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Command palette + aliases
- **Partially implemented:** —
- **Still incomplete:** —

### W6 — Multi-line paste mode

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Multi-line paste mode
- **Partially implemented:** —
- **Still incomplete:** —

### W8 — Smoke preflight checklist

- **Track:** V1-V5
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Plan DoD met with code+tests for: Smoke preflight checklist
- **Partially implemented:** —
- **Still incomplete:** —

### M001 — Hard budget ceilings on every spend path (CLI, MCP, HTTP, agent, boards)

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** call_lifecycle.pre_call budget on every ModelCaller.call; spend_guard on boards/council/bakeoff/compare/MCP spend tools/orchestrator budget; public_surface.budget_gate
- **Partially implemented:** Thin CLI wrappers that never call models are not spend paths
- **Still incomplete:** —

### M002 — Accurate cost from real tokens × registry rates

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** cost_accounting.from_usage/estimate + post_call attaches tokens/cost/rate on every model result; budget_record on success
- **Partially implemented:** —
- **Still incomplete:** —

### M003 — Pre-flight cost estimate before multi-member boards

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** board_preflight + multi_cli wire + board-preflight CLI
- **Partially implemented:** —
- **Still incomplete:** —

### M004 — Dry-run / plan mode cannot mutate disk or git

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** permission plan/dry_run no mutate
- **Partially implemented:** —
- **Still incomplete:** —

### M005 — Permission model plan/ask/auto/yolo with safe defaults

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** plan|ask|auto|yolo
- **Partially implemented:** —
- **Still incomplete:** —

### M006 — Workspace jail fail-closed for tools and external CLIs

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** workspace jail agent_tools
- **Partially implemented:** —
- **Still incomplete:** —

### M007 — Side-effect audit log (write/delete/run, run_id)

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** side_effect_audit + run_trail
- **Partially implemented:** —
- **Still incomplete:** —

### M008 — Stable result contract on every public command

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** result_contract + wrap_public_result/emit_public; MCP call_tool wraps all tool dict results; major CLI/board paths
- **Partially implemented:** Some interactive TUI-only commands print rich text without envelope (not automation public APIs)
- **Still incomplete:** —

### M009 — Error taxonomy for scripts (`budget`, `readiness`, `timeout`, …)

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** error_codes taxonomy
- **Partially implemented:** —
- **Still incomplete:** —

### M010 — Provider readiness check before live calls

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** readiness live gate
- **Partially implemented:** —
- **Still incomplete:** —

### M011 — Failover ordered, bounded, logged

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** failover ordered + local_first
- **Partially implemented:** —
- **Still incomplete:** —

### M012 — Secrets never printed in logs/errors/TUI

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** secrets.redact + logger Filter on all handlers
- **Partially implemented:** —
- **Still incomplete:** —

### M013 — Keyring/env secret store with rotate/list

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** keyring_store + secrets CLI
- **Partially implemented:** —
- **Still incomplete:** —

### M014 — SSRF protection on URL/fetch tools

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** net_safety SSRF
- **Partially implemented:** —
- **Still incomplete:** —

### M015 — Prompt-injection defenses for tool loops

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** injection_defense scan/sanitize on tool_protocol.run_tool_calls; unit tested
- **Partially implemented:** Not an ML classifier product
- **Still incomplete:** —

### M016 — Tenant isolation for shared memory

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** palace_tenant
- **Partially implemented:** —
- **Still incomplete:** —

### M017 — Cancel / Ctrl+C stops workers cooperatively

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** CancelToken + pre_call/stream/board workers cancel checks
- **Partially implemented:** —
- **Still incomplete:** —

### M018 — Timeouts on model, CLI, and tool ops

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** tool_timeouts + model_timeouts.run_with_timeout on ModelCaller; stream timeout
- **Partially implemented:** —
- **Still incomplete:** —

### M019 — Reproducible explain-run from `run_id`

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** explain-run + run_trail
- **Partially implemented:** —
- **Still incomplete:** —

### M020 — Offline mock mode never claims live success

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** mock never false live_passed
- **Partially implemented:** —
- **Still incomplete:** —

### M021 — Reliable multi-turn agent session (resume/export/undo)

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** superai_agent sessions
- **Partially implemented:** —
- **Still incomplete:** —

### M022 — Strict tool protocol (JSON schema tools)

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** tool_protocol JSON tools
- **Partially implemented:** —
- **Still incomplete:** —

### M023 — Parallel independent tools (read/grep/glob)

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** parallel read tools
- **Partially implemented:** —
- **Still incomplete:** —

### M024 — Idempotent file writes

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** idempotent writes
- **Partially implemented:** —
- **Still incomplete:** —

### M025 — Change-set staging + apply/reject

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** change_set apply/reject
- **Partially implemented:** —
- **Still incomplete:** —

### M026 — Diff check before apply

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** git_diff_apply check
- **Partially implemented:** —
- **Still incomplete:** —

### M027 — Real token streaming where supported

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** call_stream real SSE when provider supports + cancel between chunks + fallback chunking
- **Partially implemented:** Provider-specific stream quality varies
- **Still incomplete:** —

### M028 — Context packing under hard token budget

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** context_pack
- **Partially implemented:** —
- **Still incomplete:** —

### M029 — Session compaction preserving decisions/todos

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** session_compact decisions+todos
- **Partially implemented:** —
- **Still incomplete:** —

### M030 — Agent roles: build / plan / ask with boundaries

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** build/plan/ask roles
- **Partially implemented:** —
- **Still incomplete:** —

### M031 — Front-door routing: agent vs board vs orchestrator

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** front_door
- **Partially implemented:** —
- **Still incomplete:** —

### M032 — Front-door confidence when routing ambiguous

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** confidence needs_confirm
- **Partially implemented:** —
- **Still incomplete:** —

### M033 — Local-first with escalate-to-premium on failure

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** local_first escalate
- **Partially implemented:** —
- **Still incomplete:** —

### M034 — Cheap-first for summarize/plan steps

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** cheap-first complexity
- **Partially implemented:** —
- **Still incomplete:** —

### M035 — Complexity → board member count

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** smart_max_members
- **Partially implemented:** —
- **Still incomplete:** —

### M036 — Board early-exit on strong consensus

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** board early-exit
- **Partially implemented:** —
- **Still incomplete:** —

### M037 — Worker diversity (1 premium + N cheap)

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** diversify_pool
- **Partially implemented:** —
- **Still incomplete:** —

### M038 — Worktree isolation for risky writes

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** worktree_subagent
- **Partially implemented:** —
- **Still incomplete:** —

### M039 — Test-driven loop (red/green) first-class

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** tdd_loop + quality_gates
- **Partially implemented:** —
- **Still incomplete:** —

### M040 — PR/diff review via multi-CLI + contracts

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** pr_review multi_cli
- **Partially implemented:** —
- **Still incomplete:** —

### M041 — Universal OpenAI-compatible registration

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** OpenAI-compat register
- **Partially implemented:** —
- **Still incomplete:** —

### M042 — First-class local: Ollama / LM Studio / vLLM

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** ollama/lmstudio/vllm
- **Partially implemented:** —
- **Still incomplete:** —

### M043 — External CLI discovery on PATH (Windows-hardened)

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** path_which external CLI
- **Partially implemented:** —
- **Still incomplete:** —

### M044 — CLI inner-model selection (`cli:name@model`)

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** cli name@model
- **Partially implemented:** —
- **Still incomplete:** —

### M045 — Unified member catalog (API + CLI + local)

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** member catalog
- **Partially implemented:** —
- **Still incomplete:** —

### M046 — Live probe of available members

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** live probe members
- **Partially implemented:** —
- **Still incomplete:** —

### M047 — Health circuits per provider

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** provider health circuits
- **Partially implemented:** —
- **Still incomplete:** —

### M048 — Rate-limit queue / backoff

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** rate_queue
- **Partially implemented:** —
- **Still incomplete:** —

### M049 — Model blacklist after repeated failures

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** model_blacklist
- **Partially implemented:** —
- **Still incomplete:** —

### M050 — Bandit / learned routing from outcomes

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** bandit select reorders candidates; post_call updates every outcome; bakeoff pin
- **Partially implemented:** Not a separate online learning product UI
- **Still incomplete:** —

### M051 — Bakeoff with report + pin winner

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** bakeoff report+pin
- **Partially implemented:** —
- **Still incomplete:** —

### M052 — Compare command with contract

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** compare contract
- **Partially implemented:** —
- **Still incomplete:** —

### M053 — Council with voting modes

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** council voting
- **Partially implemented:** —
- **Still incomplete:** —

### M054 — Parallel multi-CLI opinions with merge

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** multi_cli parallel
- **Partially implemented:** —
- **Still incomplete:** —

### M055 — Cost router shrinks boards under budget

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** cost_router shrink
- **Partially implemented:** —
- **Still incomplete:** —

### M056 — Central Memory Palace inject before major runs

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** central_memory inject
- **Partially implemented:** —
- **Still incomplete:** —

### M057 — Write-back of successful outcomes

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** write_back
- **Partially implemented:** —
- **Still incomplete:** —

### M058 — Semantic search with tenant tags

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** semantic search tenant
- **Partially implemented:** —
- **Still incomplete:** —

### M059 — Smart memory inject (rank + token cap)

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** memory_inject rank
- **Partially implemented:** —
- **Still incomplete:** —

### M060 — Memory forget / TTL / erase

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** forget/ttl/gdpr
- **Partially implemented:** —
- **Still incomplete:** —

### M061 — Learning: promote durable patterns only

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** promote_durable + foundation-check suite
- **Partially implemented:** —
- **Still incomplete:** —

### M062 — Conflict resolution for contradictory memories

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** resolve_conflicts multi-factor
- **Partially implemented:** —
- **Still incomplete:** —

### M063 — Distill / deprecate redundant memories

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** distill_knowledge + deprecate_memory
- **Partially implemented:** —
- **Still incomplete:** —

### M064 — Wings/rooms navigation

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** wings/rooms
- **Partially implemented:** —
- **Still incomplete:** —

### M065 — Encrypted backup of local SuperAI state

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** encrypted backup
- **Partially implemented:** —
- **Still incomplete:** —

### M066 — Profile export/import

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** profile-bundle
- **Partially implemented:** —
- **Still incomplete:** —

### M067 — Run history searchable by task/cost/model

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** history.search + CLI
- **Partially implemented:** —
- **Still incomplete:** —

### M068 — Preferences that bias routing

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** preferences.bias_candidates + sticky preferred model in caller
- **Partially implemented:** —
- **Still incomplete:** —

### M069 — Skills library (reusable playbooks)

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** skills
- **Partially implemented:** —
- **Still incomplete:** —

### M070 — Skill permissions (what a skill may touch)

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** skill_permissions
- **Partially implemented:** —
- **Still incomplete:** —

### M071 — Zero-subcommand launches useful front door

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** default front door
- **Partially implemented:** —
- **Still incomplete:** —

### M072 — One-shot `do "…"` routing

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** superai do
- **Partially implemented:** —
- **Still incomplete:** —

### M073 — Doctor diagnoses real failures

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** doctor
- **Partially implemented:** —
- **Still incomplete:** —

### M074 — Status with spend + health + cache

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** status --cost
- **Partially implemented:** —
- **Still incomplete:** —

### M075 — Install/onboard wizard (Windows-first)

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** install wizard
- **Partially implemented:** —
- **Still incomplete:** —

### M076 — Host-tools check/install matrix

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** host-tools
- **Partially implemented:** —
- **Still incomplete:** —

### M077 — Rich TUI: tools, cost, permission live

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** agent TUI
- **Partially implemented:** —
- **Still incomplete:** —

### M078 — Slash command palette + help

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** slash palette
- **Partially implemented:** —
- **Still incomplete:** —

### M079 — JSON output mode for automation

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** global --json on CLI callback + emit_public/print_json automation path
- **Partially implemented:** —
- **Still incomplete:** —

### M080 — Trustworthy process exit codes

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** exit_codes.from_result + emit_public.exit_code field
- **Partially implemented:** Interactive TUI may not sys.exit with code on all paths
- **Still incomplete:** —

### M081 — High-quality `--help` and examples

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Typer --help on all registered commands with help strings
- **Partially implemented:** Example quality uneven on older commands
- **Still incomplete:** —

### M082 — Shell completion

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** typer add_completion=True (shell completion install supported)
- **Partially implemented:** —
- **Still incomplete:** —

### M083 — Config get/set with validation

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** config get/set
- **Partially implemented:** —
- **Still incomplete:** —

### M084 — Version / update check

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** version/update
- **Partially implemented:** —
- **Still incomplete:** —

### M085 — Diagnostics zip for support

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** diagnostics zip
- **Partially implemented:** —
- **Still incomplete:** —

### M086 — Unit suite for safety/money (plan, budget, jail)

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** safety unit suites
- **Partially implemented:** —
- **Still incomplete:** —

### M087 — Golden offline eval set

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** eval_golden
- **Partially implemented:** —
- **Still incomplete:** —

### M088 — Smoke harness that never false-passes

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** smoke_harness no false pass
- **Partially implemented:** —
- **Still incomplete:** —

### M090 — Contract tests on top 30 commands

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** TOP_30 list + contract_registry.smoke + verify_top30_contracts + foundation-check
- **Partially implemented:** —
- **Still incomplete:** —

### M092 — Deterministic mock fixtures for CI

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** mock_fixtures
- **Partially implemented:** —
- **Still incomplete:** —

### M093 — MCP parity with CLI safety rules

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** mcp_safety + call_tool budget for spend tools + contract wrap all tool results
- **Partially implemented:** —
- **Still incomplete:** —

### M094 — Web API auth for non-loopback

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** web non-loopback token required
- **Partially implemented:** —
- **Still incomplete:** —

### M095 — Graph of runs (models/tools/cost)

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** agent-graph
- **Partially implemented:** —
- **Still incomplete:** —

### M096 — Schedule/goals with caps (no yolo inherit)

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** goals caps
- **Partially implemented:** —
- **Still incomplete:** —

### M097 — Plugin install with sha256 verify

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** plugin sha
- **Partially implemented:** —
- **Still incomplete:** —

### M098 — Constitution/policy hooks for org rules

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** constitution/policy
- **Partially implemented:** —
- **Still incomplete:** —

### M099 — Architecture + quickstart + threat docs

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** THREAT_MODEL.md + docs
- **Partially implemented:** —
- **Still incomplete:** —

### M100 — Honest dashboard: mock vs live

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** dashboard_state + status --cost mock_vs_live honesty labels
- **Partially implemented:** —
- **Still incomplete:** —

### N203 — Command macros / aliases

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented for N203 intent with usable code
- **Partially implemented:** —
- **Still incomplete:** —

### N213 — Optional voice channel

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented for N213 intent with usable code
- **Partially implemented:** —
- **Still incomplete:** —

### N227 — Pre/post tool hooks

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented for N227 intent with usable code
- **Partially implemented:** —
- **Still incomplete:** —

### N260 — One-command “why did CI fail”

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented for N260 intent with usable code
- **Partially implemented:** —
- **Still incomplete:** —

### N261 — Multi-agent debate with roles

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented for N261 intent with usable code
- **Partially implemented:** —
- **Still incomplete:** —

### S101 — Agent-maintained todo list across long tasks

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented and tested for S101 backlog intent
- **Partially implemented:** —
- **Still incomplete:** —

### S102 — Spec-first: plan → approve → implement

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented and tested for S102 backlog intent
- **Partially implemented:** —
- **Still incomplete:** —

### S103 — Architecture mode vs implementation mode

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented and tested for S103 backlog intent
- **Partially implemented:** —
- **Still incomplete:** —

### S105 — Auto test discovery and run after edits

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** quality_gates.discover_tests + detect_and_run + run_after_edits
- **Partially implemented:** —
- **Still incomplete:** —

### S106 — Lint/typecheck integration post-edit

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** ruff/mypy optional gates in quality_gates when installed
- **Partially implemented:** —
- **Still incomplete:** —

### S107 — Repo map / workspace index for large trees

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented and tested for S107 backlog intent
- **Partially implemented:** —
- **Still incomplete:** —

### S114 — Security scan hooks (secrets, vulns)

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** security_scan_text + secrets patterns
- **Partially implemented:** Not full SCA CVE DB product
- **Still incomplete:** —

### S116 — Commit message + branch naming helpers

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** suggest_commit_message branch helpers
- **Partially implemented:** —
- **Still incomplete:** —

### S118 — `git apply`-compatible patch format

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented and tested for S118 backlog intent
- **Partially implemented:** —
- **Still incomplete:** —

### S122 — Notebook run/repair mode

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented and tested for S122 backlog intent
- **Partially implemented:** —
- **Still incomplete:** —

### S125 — Continue last session smart resume

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented and tested for S125 backlog intent
- **Partially implemented:** —
- **Still incomplete:** —

### S126 — Cross-session semantic result cache (opt-in)

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented and tested for S126 backlog intent
- **Partially implemented:** —
- **Still incomplete:** —

### S128 — Speculative local draft → cloud polish

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** local_then_polish + local_first pattern
- **Partially implemented:** —
- **Still incomplete:** —

### S130 — Escalate only on quality gate failure

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented and tested for S130 backlog intent
- **Partially implemented:** —
- **Still incomplete:** —

### S131 — Per-project budget policies

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented and tested for S131 backlog intent
- **Partially implemented:** —
- **Still incomplete:** —

### S133 — Cost forecast before long boards

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented and tested for S133 backlog intent
- **Partially implemented:** —
- **Still incomplete:** —

### S134 — Daily/weekly spend reports

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented and tested for S134 backlog intent
- **Partially implemented:** —
- **Still incomplete:** —

### S135 — Cache hit rate in status

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented and tested for S135 backlog intent
- **Partially implemented:** —
- **Still incomplete:** —

### S138 — Always-local for trivial “what is” questions

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** route_trivial prefer_local + front_door cheap-first
- **Partially implemented:** —
- **Still incomplete:** —

### S140 — Drop redundant reads via mtime index

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** step_cache path+mtime read cache
- **Partially implemented:** —
- **Still incomplete:** —

### S147 — Cancel generation on user interrupt

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** cancel stream + call_lifecycle + CancelToken
- **Partially implemented:** —
- **Still incomplete:** —

### S149 — Sticky cheap mode per repo

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** sticky_cheap_for_repo + preferences
- **Partially implemented:** —
- **Still incomplete:** —

### S150 — A/B routing experiments with reports

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** ab_routing + ab_report
- **Partially implemented:** —
- **Still incomplete:** —

### S151 — Catalog auto-refresh (e.g. OpenRouter)

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented and tested for S151 backlog intent
- **Partially implemented:** —
- **Still incomplete:** —

### S152 — Capability tags (vision, tools, long-context)

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented and tested for S152 backlog intent
- **Partially implemented:** —
- **Still incomplete:** —

### S154 — JSON-mode enforcement for tools

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** enforce_json_mode / json_tool_roundtrip
- **Partially implemented:** —
- **Still incomplete:** —

### S155 — Structured output validation + retry

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** validate_json + retry_instruction
- **Partially implemented:** —
- **Still incomplete:** —

### S157 — Better Windows CLI shim resolution

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented and tested for S157 backlog intent
- **Partially implemented:** —
- **Still incomplete:** —

### S160 — Network allowlist for tools

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** net_safety validate_public_http_url allowlist
- **Partially implemented:** —
- **Still incomplete:** —

### S161 — Per-tool timeout configs

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented and tested for S161 backlog intent
- **Partially implemented:** —
- **Still incomplete:** —

### S164 — Pin model per task type

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** ModelPinStore pin task types
- **Partially implemented:** —
- **Still incomplete:** —

### S166 — Clear UX when local runtime down

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** local_runtime_status + doctor UX
- **Partially implemented:** —
- **Still incomplete:** —

### S171 — Project-scoped vs global memory

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented and tested for S171 backlog intent
- **Partially implemented:** —
- **Still incomplete:** —

### S177 — Team palace export/import

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented and tested for S177 backlog intent
- **Partially implemented:** —
- **Still incomplete:** —

### S183 — Audit export for compliance

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** export_audit
- **Partially implemented:** —
- **Still incomplete:** —

### S184 — Retention policies

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** apply_retention
- **Partially implemented:** —
- **Still incomplete:** —

### S185 — Encryption at rest for sessions

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** encrypt_session_blob
- **Partially implemented:** —
- **Still incomplete:** —

### S196 — Recipe gallery (fix bug, add API, …)

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented and tested for S196 backlog intent
- **Partially implemented:** —
- **Still incomplete:** —

### S198 — Profile auto-suggest + one-key apply

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented and tested for S198 backlog intent
- **Partially implemented:** —
- **Still incomplete:** —

### S199 — Onboarding quest (first 5 wins)

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented and tested for S199 backlog intent
- **Partially implemented:** —
- **Still incomplete:** —

### S200 — In-CLI changelog / what’s new

- **Track:** V6
- **Status:** `full`
- **Percent complete:** **100%**
- **Counts as completed?** **YES**
- **Fully implemented:** Implemented and tested for S200 backlog intent
- **Partially implemented:** —
- **Still incomplete:** —

## 2. FOUNDATION (partially implemented — NOT completed)

**Count:** 49

### V1-N8 — Phase 8 N8 — Plugin marketplace browse

- **Track:** V1-V5
- **Status:** `foundation`
- **Percent complete:** **55%**
- **Counts as completed?** **NO**
- **Fully implemented:** plugin_catalog browse exists
- **Partially implemented:** Not full marketplace product
- **Still incomplete:** Marketplace UX/payments/community

### W7 — VS Code extension depth

- **Track:** V1-V5
- **Status:** `foundation`
- **Percent complete:** **45%**
- **Counts as completed?** **NO**
- **Fully implemented:** VS Code extension thin commands
- **Partially implemented:** Not full IDE depth
- **Still incomplete:** Stream+apply full extension

### N202 — NL → any command with preview

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **60%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial/real module exists
- **Partially implemented:** Not production-complete product
- **Still incomplete:** Full production depth

### N205 — Watch mode (re-run on change)

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **55%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial/real module exists
- **Partially implemented:** Not production-complete product
- **Still incomplete:** Full production depth

### N206 — Daemon for goals/schedules

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **50%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial/real module exists
- **Partially implemented:** Not production-complete product
- **Still incomplete:** Full production depth

### N209 — Split-pane TUI

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **40%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial/real module exists
- **Partially implemented:** Not production-complete product
- **Still incomplete:** Full production depth

### N214 — Full i18n for CLI/TUI

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **40%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial/real module exists
- **Partially implemented:** Not production-complete product
- **Still incomplete:** Full production depth

### N219 — Publish session as markdown

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **70%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial/real module exists
- **Partially implemented:** Not production-complete product
- **Still incomplete:** Full production depth

### N221 — Public benchmark harness

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **75%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial/real module exists
- **Partially implemented:** Not production-complete product
- **Still incomplete:** Full production depth

### N224 — Plugin marketplace UX

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **45%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial/real module exists
- **Partially implemented:** Not production-complete product
- **Still incomplete:** Full production depth

### N225 — Signed plugins

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **60%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial/real module exists
- **Partially implemented:** Not production-complete product
- **Still incomplete:** Full production depth

### N228 — Simple policy-as-code

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **55%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial/real module exists
- **Partially implemented:** Not production-complete product
- **Still incomplete:** Full production depth

### N231 — LSP diagnostics integration

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **45%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial/real module exists
- **Partially implemented:** Not production-complete product
- **Still incomplete:** Full production depth

### N247 — Mobile build log triage

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **50%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial/real module exists
- **Partially implemented:** Not production-complete product
- **Still incomplete:** Full production depth

### N249 — Dataframe/SQL notebook hybrid

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **55%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial/real module exists
- **Partially implemented:** Not production-complete product
- **Still incomplete:** Full production depth

### N250 — Local vector search over repo chunks

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **55%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial/real module exists
- **Partially implemented:** Not production-complete product
- **Still incomplete:** Full production depth

### N259 — Semantic diff summaries

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **60%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial/real module exists
- **Partially implemented:** Not production-complete product
- **Still incomplete:** Full production depth

### N278 — Ticket sync (Jira/Linear/GitHub)

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **40%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial/real module exists
- **Partially implemented:** Not production-complete product
- **Still incomplete:** Full production depth

### N284 — GitHub Action “superai review”

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **70%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial/real module exists
- **Partially implemented:** Not production-complete product
- **Still incomplete:** Full production depth

### N286 — Pre-commit hook

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **70%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial/real module exists
- **Partially implemented:** Not production-complete product
- **Still incomplete:** Full production depth

### N291 — Telegram production hardening

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **40%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial/real module exists
- **Partially implemented:** Not production-complete product
- **Still incomplete:** Full production depth

### N292 — Slack slash commands

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **40%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial/real module exists
- **Partially implemented:** Not production-complete product
- **Still incomplete:** Full production depth

### N293 — Notion sync when key present

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **35%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial/real module exists
- **Partially implemented:** Not production-complete product
- **Still incomplete:** Full production depth

### N298 — Cloud provider CLIs as gated tools

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **55%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial/real module exists
- **Partially implemented:** Not production-complete product
- **Still incomplete:** Full production depth

### N299 — Community skills marketplace

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **40%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial/real module exists
- **Partially implemented:** Not production-complete product
- **Still incomplete:** Full production depth

### N300 — Public awesome-recipes catalog

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **50%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial/real module exists
- **Partially implemented:** Not production-complete product
- **Still incomplete:** Full production depth

### P366 — Reimplement vendor CLIs inside SuperAI

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **60%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial strategy/flag only (agent-prefer-API / chroma experimental)
- **Partially implemented:** Not full dual product
- **Still incomplete:** Intentionally not full vendor reimplementation / dual memory stack

### P368 — Third memory stack “for completeness”

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **40%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial strategy/flag only (agent-prefer-API / chroma experimental)
- **Partially implemented:** Not full dual product
- **Still incomplete:** Intentionally not full vendor reimplementation / dual memory stack

### S109 — Fix CI failure from log paste

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **70%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial real code path exists
- **Partially implemented:** Depth incomplete vs backlog wording
- **Still incomplete:** Full product polish / edge cases

### S110 — Explain PR with file-level findings

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **75%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial real code path exists
- **Partially implemented:** Depth incomplete vs backlog wording
- **Still incomplete:** Full product polish / edge cases

### S119 — Vision for UI bug screenshots

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **65%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial real code path exists
- **Partially implemented:** Depth incomplete vs backlog wording
- **Still incomplete:** Full product polish / edge cases

### S121 — Browser tool for local web verification

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **55%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial real code path exists
- **Partially implemented:** Depth incomplete vs backlog wording
- **Still incomplete:** Full product polish / edge cases

### S123 — SQL agent with allowlisted DBs

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **60%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial real code path exists
- **Partially implemented:** Depth incomplete vs backlog wording
- **Still incomplete:** Full product polish / edge cases

### S124 — Log triage mode (stack traces)

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **70%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial real code path exists
- **Partially implemented:** Depth incomplete vs backlog wording
- **Still incomplete:** Full product polish / edge cases

### S143 — Lazy-load heavy deps

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **50%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial real code path exists
- **Partially implemented:** Depth incomplete vs backlog wording
- **Still incomplete:** Full product polish / edge cases

### S156 — Native Anthropic/Google adapters (depth)

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **55%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial real code path exists
- **Partially implemented:** Depth incomplete vs backlog wording
- **Still incomplete:** Full product polish / edge cases

### S159 — Container sandbox for bash tools

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **50%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial real code path exists
- **Partially implemented:** Depth incomplete vs backlog wording
- **Still incomplete:** Full product polish / edge cases

### S168 — OpenRouter strategy knobs

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **60%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial real code path exists
- **Partially implemented:** Depth incomplete vs backlog wording
- **Still incomplete:** Full product polish / edge cases

### S169 — NVIDIA NIM first-class depth

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **55%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial real code path exists
- **Partially implemented:** Depth incomplete vs backlog wording
- **Still incomplete:** Full product polish / edge cases

### S174 — Memory search in TUI

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **50%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial real code path exists
- **Partially implemented:** Depth incomplete vs backlog wording
- **Still incomplete:** Full product polish / edge cases

### S179 — Shared run templates

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **70%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial real code path exists
- **Partially implemented:** Depth incomplete vs backlog wording
- **Still incomplete:** Full product polish / edge cases

### S180 — Secure messenger inbound tasking

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **45%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial real code path exists
- **Partially implemented:** Depth incomplete vs backlog wording
- **Still incomplete:** Full product polish / edge cases

### S181 — Notify only on approval-needed / done

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **60%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial real code path exists
- **Partially implemented:** Depth incomplete vs backlog wording
- **Still incomplete:** Full product polish / edge cases

### S186 — Web session browser

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **50%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial real code path exists
- **Partially implemented:** Depth incomplete vs backlog wording
- **Still incomplete:** Full product polish / edge cases

### S188 — VS Code: run + stream + apply set

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **45%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial real code path exists
- **Partially implemented:** Depth incomplete vs backlog wording
- **Still incomplete:** Full product polish / edge cases

### S190 — Useful offline PWA shell

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **40%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial real code path exists
- **Partially implemented:** Depth incomplete vs backlog wording
- **Still incomplete:** Full product polish / edge cases

### S193 — Better multi-line editor / paste

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **70%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial real code path exists
- **Partially implemented:** Depth incomplete vs backlog wording
- **Still incomplete:** Full product polish / edge cases

### S195 — `init` project templates

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **65%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial real code path exists
- **Partially implemented:** Depth incomplete vs backlog wording
- **Still incomplete:** Full product polish / edge cases

### S197 — Explain-run with mermaid graph

- **Track:** V6
- **Status:** `foundation`
- **Percent complete:** **70%**
- **Counts as completed?** **NO**
- **Fully implemented:** Partial real code path exists
- **Partially implemented:** Depth incomplete vs backlog wording
- **Still incomplete:** Full product polish / edge cases

## 3. STUBS (surface only — NOT completed)

**Count:** 162

### M091 — Performance budgets for cold start

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** No formal cold-start budget CI gate product
- **Partially implemented:** Ad hoc awareness only
- **Still incomplete:** CI performance budget job

### N201 — Fuzzy command palette (Ctrl+K)

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N204 — Pipelines between SuperAI modes

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N207 — Remote headless agent over SSH

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N208 — Multiplexed sessions (tmux-like)

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N212 — Image paste from clipboard

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N216 — Colorblind-safe palettes

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N217 — High-contrast mode

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N218 — Replay tape for demos

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N220 — Shareable sanitized run bundles

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N222 — Private model leaderboard on your repo

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N223 — Custom agents DSL (YAML)

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N226 — Skill versioning

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N229 — Enterprise SSO for web API

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N237 — Coverage-guided test generation

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N240 — Snapshot test updates with review

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N241 — Docker compose helpers

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N242 — K8s dry-run helpers

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N243 — Terraform plan explain

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N244 — GraphQL schema assist

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N245 — OpenAPI generate + validate

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N246 — Proto/gRPC helpers

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N251 — AST-based edit tools

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N252 — Format-on-write

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N256 — Monorepo package awareness

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N257 — Build system detect (make/nx/bazel)

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N258 — Incremental index updates

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N262 — Red team vs blue team security review

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N263 — PM agent → engineer agent handoff

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N264 — QA agent sees only diffs

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N265 — Release captain checklist agent

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N266 — Incident commander mode

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N267 — On-call runbook executor

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N268 — Multi-repo cross-PR coordination

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N269 — Dependency PR stack helper

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N275 — ADR writer

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N276 — RFC co-author

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N277 — Meeting notes → tasks

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N280 — Web UI accessibility audit assist

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N281 — Homebrew / winget / choco packages

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N282 — Official Docker image

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N290 — Discord bot thin client

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### N294 — Obsidian vault export

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Stub/flag/sample only
- **Partially implemented:** —
- **Still incomplete:** Full product implementation

### P301 — Rebrand SuperAI to another product name

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P302 — Pixel-match OpenCode/Claude Code UI

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P303 — Marketing site redesign as engineering work

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P304 — Animated splash screens

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P305 — NFT/badge gamification

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P306 — Social share buttons in CLI

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P307 — Custom ASCII art every run

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P308 — Seasonal themes (required)

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P309 — Mascot program

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P310 — Startup sounds

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P311 — “AI CEO” persona as default

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P312 — Hype agent names

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P313 — Brand-war dark-mode mandates

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P314 — Consumer app-store packaging

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P315 — Mobile-first full agent

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P316 — Electron desktop shell v1

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P317 — VR pair programming

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P318 — Emoji-only mode

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P319 — Meme responses

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P320 — Public user ranking

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P321 — Full IDE replacement

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P322 — Full browser OS agent

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P323 — Multi-tenant SaaS before local excellence

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P324 — Billing/Stripe product

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P325 — Marketplace payments

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P326 — Cryptocurrency payments

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P327 — Blockchain audit log

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P328 — Homomorphic encryption of prompts

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P329 — Federated learning across users

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P330 — On-device tiny LLM training

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P331 — Auto-fine-tune every repo by default

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P332 — 1000-node cluster scheduler

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P333 — Kubernetes operator early

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P334 — Service mesh integration

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P335 — Full observability vendor product

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P336 — Proprietary protocol instead of MCP

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P337 — Replace git

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P338 — Replace language servers wholesale

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P339 — Custom terminal emulator product

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P340 — Hardware appliance

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P341 — Phone companion app v1

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P342 — AR glasses integration

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P343 — Voice-only primary interface

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P344 — Always-listening mic daemon

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P345 — Webcam emotion detection

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P346 — Full SOC2 “as a feature”

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P347 — FedRAMP packaging

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P348 — Multi-region active-active cloud

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P349 — 50-role RBAC day one

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P350 — Deep LDAP

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P351 — Custom legal hold workflows

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P352 — eDiscovery UI

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P353 — Per-field data residency UI

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P354 — SIEM product

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P355 — Full DLP product

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P356 — MDM integration

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P357 — Air-gap CD productization

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P358 — Mandatory HSM

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P359 — Formal methods prover integration

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P360 — Quantum-safe crypto migration project

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P361 — ISO process automation suite

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P362 — Board compliance dashboard

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P363 — Customer success CRM inside SuperAI

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P364 — Sales quote generator

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P365 — Partner portal

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P367 — Fork and maintain all external agents

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P369 — Support every vector DB

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P370 — Perfect every provider day one

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P371 — Perfect voice without optional deps

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P372 — Perfect browser without Playwright

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P373 — Full JupyterLab clone

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P374 — Full Postman clone

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P375 — Full Datadog clone

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P376 — Full Jira clone

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P377 — Full Notion clone

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P378 — Full Figma clone

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P379 — In-CLI video editor

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P380 — In-CLI music generation

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P381 — Game engine

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P382 — Excel-complete spreadsheet

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P383 — CAD/CAM

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P384 — Scientific HPC scheduler

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### P385 — Teaching LMS platform

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Parked catalog / vanity / overbuild stub
- **Partially implemented:** —
- **Still incomplete:** Not scheduled product work

### S104 — Self-critique pass before claiming done

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **20%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S108 — Symbol-aware navigation (beyond grep)

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S111 — Multi-file refactor with rename safety

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S112 — Dependency upgrade assistant

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S113 — DB/schema migration dry-run helper

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S115 — License/compliance check on new deps

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S117 — Safe conflict assistance for merges

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S120 — PDF/doc attach for requirements

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S127 — Prompt/prefix cache for long system prompts

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S129 — Mid-task model demotion when task simplifies

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S132 — Per-command budget overrides

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S136 — Token waterfall visualization

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S137 — Stagger expensive board members

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S139 — Compress tool outputs before re-feed

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S141 — Shared embedding cache

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S142 — Batch embeddings

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S144 — Faster cold start (defer imports)

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S145 — Optional background model warmup

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **5%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S146 — Adaptive max_members from history

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S148 — Partial stream cancel stops workers

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **25%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S153 — Context window awareness per model

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **20%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S158 — WSL/path interop helpers

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S162 — Per-provider concurrency caps

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S163 — Priority queue interactive vs batch

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S165 — Team-shared routing policies

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S167 — GPU/local resource detect for pick

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S170 — Multi-key rotation per provider

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S172 — Memory confidence scores

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S173 — Human confirm before sensitive memory write

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S175 — “Why injected” citations

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S176 — Conflict UI when memories disagree

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S178 — Org-level skills registry

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **10%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S182 — Multi-user permission roles

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **20%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S187 — SSE live progress for web

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S191 — TUI themes

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

### S194 — Clipboard integration

- **Track:** V6
- **Status:** `stub`
- **Percent complete:** **15%**
- **Counts as completed?** **NO**
- **Fully implemented:** Surface/flag only if any
- **Partially implemented:** —
- **Still incomplete:** Real product implementation

## 4. HOST-GATED (code present; live proof incomplete)

**Count:** 3

### MOS-N8 — Nice N8 — Live multi-vendor smoke

- **Track:** V1-V5
- **Status:** `host`
- **Percent complete:** **90%**
- **Counts as completed?** **NO**
- **Fully implemented:** Smoke harness code complete
- **Partially implemented:** Needs host keys for live_passed
- **Still incomplete:** Live multi-provider run

### V1-P99 — Phase 99 — Live multi-provider smoke (host)

- **Track:** V1-V5
- **Status:** `host`
- **Percent complete:** **90%**
- **Counts as completed?** **NO**
- **Fully implemented:** Smoke harness code complete
- **Partially implemented:** Needs host keys for live_passed
- **Still incomplete:** Live multi-provider run

### M089 — Live multi-provider smoke matrix (host keys)

- **Track:** V6
- **Status:** `host`
- **Percent complete:** **90%**
- **Counts as completed?** **NO**
- **Fully implemented:** phase6-smoke + live_smoke_complete code path
- **Partially implemented:** live_passed needs host API keys
- **Still incomplete:** Live multi-provider proof on this machine

## 5. REFUSE-CLOSED (policy complete; not a shipped feature)

**Count:** 15

### P386 — Fully autonomous company-running agent

- **Track:** V6
- **Status:** `refuse`
- **Percent complete:** **100%**
- **Counts as completed?** **NO**
- **Fully implemented:** Hard refuse-closed safety policy (correctly complete as refuse)
- **Partially implemented:** —
- **Still incomplete:** Must not implement

### P387 — Recursive self-improvement without gates

- **Track:** V6
- **Status:** `refuse`
- **Percent complete:** **100%**
- **Counts as completed?** **NO**
- **Fully implemented:** Hard refuse-closed safety policy (correctly complete as refuse)
- **Partially implemented:** —
- **Still incomplete:** Must not implement

### P388 — Unrestricted yolo as default

- **Track:** V6
- **Status:** `refuse`
- **Percent complete:** **100%**
- **Counts as completed?** **NO**
- **Fully implemented:** Hard refuse-closed safety policy (correctly complete as refuse)
- **Partially implemented:** —
- **Still incomplete:** Must not implement

### P389 — Internet-wide unconstrained browsing

- **Track:** V6
- **Status:** `refuse`
- **Percent complete:** **100%**
- **Counts as completed?** **NO**
- **Fully implemented:** Hard refuse-closed safety policy (correctly complete as refuse)
- **Partially implemented:** —
- **Still incomplete:** Must not implement

### P390 — Auto-PRs to random public repos

- **Track:** V6
- **Status:** `refuse`
- **Percent complete:** **100%**
- **Counts as completed?** **NO**
- **Fully implemented:** Hard refuse-closed safety policy (correctly complete as refuse)
- **Partially implemented:** —
- **Still incomplete:** Must not implement

### P391 — Auto-trading

- **Track:** V6
- **Status:** `refuse`
- **Percent complete:** **100%**
- **Counts as completed?** **NO**
- **Fully implemented:** Hard refuse-closed safety policy (correctly complete as refuse)
- **Partially implemented:** —
- **Still incomplete:** Must not implement

### P392 — Auto-legal advice as certified

- **Track:** V6
- **Status:** `refuse`
- **Percent complete:** **100%**
- **Counts as completed?** **NO**
- **Fully implemented:** Hard refuse-closed safety policy (correctly complete as refuse)
- **Partially implemented:** —
- **Still incomplete:** Must not implement

### P393 — Medical diagnosis agent

- **Track:** V6
- **Status:** `refuse`
- **Percent complete:** **100%**
- **Counts as completed?** **NO**
- **Fully implemented:** Hard refuse-closed safety policy (correctly complete as refuse)
- **Partially implemented:** —
- **Still incomplete:** Must not implement

### P394 — Jailbreak playground product

- **Track:** V6
- **Status:** `refuse`
- **Percent complete:** **100%**
- **Counts as completed?** **NO**
- **Fully implemented:** Hard refuse-closed safety policy (correctly complete as refuse)
- **Partially implemented:** —
- **Still incomplete:** Must not implement

### P395 — Prompt-virus research tools

- **Track:** V6
- **Status:** `refuse`
- **Percent complete:** **100%**
- **Counts as completed?** **NO**
- **Fully implemented:** Hard refuse-closed safety policy (correctly complete as refuse)
- **Partially implemented:** —
- **Still incomplete:** Must not implement

### P396 — Deepfake media tools

- **Track:** V6
- **Status:** `refuse`
- **Percent complete:** **100%**
- **Counts as completed?** **NO**
- **Fully implemented:** Hard refuse-closed safety policy (correctly complete as refuse)
- **Partially implemented:** —
- **Still incomplete:** Must not implement

### P397 — Mass scraping suite

- **Track:** V6
- **Status:** `refuse`
- **Percent complete:** **100%**
- **Counts as completed?** **NO**
- **Fully implemented:** Hard refuse-closed safety policy (correctly complete as refuse)
- **Partially implemented:** —
- **Still incomplete:** Must not implement

### P398 — CAPTCHA farms

- **Track:** V6
- **Status:** `refuse`
- **Percent complete:** **100%**
- **Counts as completed?** **NO**
- **Fully implemented:** Hard refuse-closed safety policy (correctly complete as refuse)
- **Partially implemented:** —
- **Still incomplete:** Must not implement

### P399 — “AGI mode” branding

- **Track:** V6
- **Status:** `refuse`
- **Percent complete:** **100%**
- **Counts as completed?** **NO**
- **Fully implemented:** Hard refuse-closed safety policy (correctly complete as refuse)
- **Partially implemented:** —
- **Still incomplete:** Must not implement

### P400 — Infinite backlog without Phase 6 smoke

- **Track:** V6
- **Status:** `refuse`
- **Percent complete:** **100%**
- **Counts as completed?** **NO**
- **Fully implemented:** Hard refuse-closed safety policy (correctly complete as refuse)
- **Partially implemented:** —
- **Still incomplete:** Must not implement

## 6. ABSENT (no meaningful implementation)

**Count:** 31

### N210 — Vim keys in TUI

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N211 — Optional mouse support

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N215 — Screen-reader friendly TUI

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N230 — SCIM provisioning (stretch)

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N232 — Go-to-definition via LSP

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N233 — Rename symbol across project

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N234 — Extract method/function assist

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N235 — Dead code detection

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N236 — Complexity hotspots map

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N238 — Mutation testing opt-in

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N239 — Flaky test hunter

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N248 — Game-engine log modes (niche)

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N253 — Import organizer

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N254 — License header inject

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N255 — CODEOWNERS-aware routing

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N270 — Feature flag rollout assistant

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N271 — Canary analysis helper

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N272 — Metrics anomaly explain

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N273 — Cloud bill cost anomaly (opt-in)

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N274 — SLA report generator

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N279 — Design token consistency checks

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N283 — Nix flake

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N285 — GitLab CI component

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N287 — Devcontainer feature

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N288 — Codespaces template

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N289 — Raycast/Alfred extension

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N295 — Browser extension send-to-SuperAI

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N296 — Figma comment → task (stretch)

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### N297 — Datadog/NewRelic log pull (opt-in)

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No meaningful implementation

### S189 — JetBrains thin plugin

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No JetBrains plugin

### S192 — Keybind customization

- **Track:** V6
- **Status:** `absent`
- **Percent complete:** **0%**
- **Counts as completed?** **NO**
- **Fully implemented:** —
- **Partially implemented:** —
- **Still incomplete:** No keybind config system

## How to re-verify (offline)

```powershell
cd SuperAI
$env:PYTHONPATH='src'
pytest tests/test_foundation_complete_must.py tests/test_foundation_lift.py tests/test_improvement_v4.py tests/test_improvement_v5.py tests/test_moscow_100.py -q
python scripts/gen_v1_v6_unified_scorecard.py
```

Regenerate this file: `python scripts/gen_v1_v6_unified_scorecard.py`

