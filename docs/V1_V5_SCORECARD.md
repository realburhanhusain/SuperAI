# SuperAI Improvement V1–V5 — Detailed scorecard

**Generated:** 2026-07-16  
**Total items:** 133  
**Purpose:** Honest status **and reasoning** per improvement item for V1 through V5 (plus MoSCoW honesty pass and not-important polish that sat on the same track).  

Companion to `docs/V6_SCORECARD.md` (400-item V6 backlog).

Each item lists:

1. **ID** (stable for this scorecard)
2. **Title** (plan wording)
3. **Status** (classification)
4. **Why** (evidence + gap that justified the status)

## Status legend

| Status | Meaning | When we use it |
|--------|---------|----------------|
| **full** | Production-usable for the stated plan intent | Code + tests (or equivalent) cover DoD |
| **foundation** | Real working code; DoD depth incomplete | Core mechanism exists; missing universality/UX/hardening |
| **stub** | Surface/flag/sample only | Placeholder only |
| **host** | Code path exists; needs keys/environment | Live proof requires credentials |
| **refuse** | Intentionally refuse-closed | Safety policy blocks shipping |
| **absent** | No meaningful implementation | Zero or near-zero code |

## How this relates to plan checklists

Older plans often mark items `[x]` or “100% sprint complete” after a **vertical slice**. This scorecard uses the same honesty bar as V6:

- **full** ≈ checklist `[x]` with real depth for that plan’s DoD
- **foundation** ≈ real code that later tracks still deepen (not a lie, not “finished forever”)
- **host** ≈ never claim live multi-provider success without keys

## Overall summary

| Status | Count | % |
|--------|------:|--:|
| full | 110 | 82.7% |
| foundation | 21 | 15.8% |
| host | 2 | 1.5% |
| **total** | **133** | **100%** |

- **full + foundation** ≈ **131** items have real code value.
- **host** = **2** (live smoke proof).

**Honest headline:** V1–V5 delivered the **orchestrator + agent + multi-CLI + cost/safety spine**. Most Must/Should items are **full** or **foundation**. Remaining gaps are universality (budget/contract on *every* path), true streaming, bandit continuity, and **host-gated live smoke** — not “nothing was built.”

### Counts by track

| Track | Items | full | foundation | host | other |
|-------|------:|-----:|-----------:|-----:|------:|
| V1 | 22 | 17 | 4 | 1 | 0 |
| V1-P8 | 8 | 8 | 0 | 0 | 0 |
| V2 | 17 | 14 | 3 | 0 | 0 |
| V3 | 15 | 13 | 2 | 0 | 0 |
| MoSCoW | 26 | 23 | 2 | 1 | 0 |
| NotImportant | 9 | 8 | 1 | 0 | 0 |
| V4 | 20 | 15 | 5 | 0 | 0 |
| V5 | 16 | 12 | 4 | 0 | 0 |

### Quick index (status only)

#### V1 — Improvement Plan (Phases 0–7 + Phase 99)

Source: `docs/IMPROVEMENT_PLAN.md`

| ID | Status | Title |
|----|--------|-------|
| V1-P0 | **full** | Phase 0 — Planning (IMPROVEMENT_PLAN, TASKBOARD, handoff) |
| V1-P1-1 | **foundation** | Phase 1 — Stable result contract |
| V1-P1-2 | **full** | Phase 1 — Mock/dry_run honesty (never false live success) |
| V1-P1-3 | **foundation** | Phase 1 — Budget hard-stop foundation |
| V1-P1-4 | **foundation** | Phase 1 — Cost fields on results |
| V1-P2-1 | **full** | Phase 2 — Default agent / front-door entry |
| V1-P2-2 | **full** | Phase 2 — Permission modes (plan/ask/auto/yolo) |
| V1-P2-3 | **full** | Phase 2 — Multi-turn ask session |
| V1-P3-1 | **full** | Phase 3 — Registry validation |
| V1-P3-2 | **full** | Phase 3 — Run profiles (cheap/balanced/quality/local-only) |
| V1-P3-3 | **full** | Phase 3 — Cost report / status spend visibility |
| V1-P4-1 | **full** | Phase 4 — Prefer open-weight/local failover |
| V1-P4-2 | **full** | Phase 4 — Smart board member sizing |
| V1-P4-3 | **full** | Phase 4 — Board result cache |
| V1-P5-1 | **full** | Phase 5 — In-process Read/Edit/Bash tools (workspace jail) |
| V1-P5-2 | **foundation** | Phase 5 — Streaming progress bus |
| V1-P5-3 | **full** | Phase 5 — Provider health UX (circuit column) |
| V1-P6-1 | **full** | Phase 6 — Auto Ollama discover (opt-in) |
| V1-P6-2 | **full** | Phase 6 — NL intent map expand |
| V1-P6-3 | **full** | Phase 6 — Windows PATH / CLI resolve hardening |
| V1-P7 | **full** | Phase 7 — Docs closeout |
| V1-P99 | **host** | Phase 99 — Live multi-provider smoke (host) |

#### V1 Phase 8 — Nice-to-have (N1–N8)

Source: `docs/PHASE8_PLAN.md`

| ID | Status | Title |
|----|--------|-------|
| V1-N1 | **full** | Phase 8 N1 — Agent TUI |
| V1-N2 | **full** | Phase 8 N2 — Personal assistant goals |
| V1-N3 | **full** | Phase 8 N3 — Multimodal images |
| V1-N4 | **full** | Phase 8 N4 — Run/subagent graph API |
| V1-N5 | **full** | Phase 8 N5 — OpenRouter model refresh |
| V1-N6 | **full** | Phase 8 N6 — Model bake-off |
| V1-N7 | **full** | Phase 8 N7 — Palace tenant |
| V1-N8 | **full** | Phase 8 N8 — Plugin marketplace browse |

#### V2 — Sprints A–D

Source: `docs/IMPROVEMENT_V2_PLAN.md`

| ID | Status | Title |
|----|--------|-------|
| V2-A1 | **full** | Sprint A — Tools in TUI (/tool read|grep|…) |
| V2-A2 | **full** | Sprint A — Git diff propose + dry-apply |
| V2-A3 | **full** | Sprint A — Fail-closed readiness |
| V2-A4 | **foundation** | Sprint A — Result contract on tool/agent paths |
| V2-B1 | **full** | Sprint B — Cost router shrink boards under budget |
| V2-B2 | **full** | Sprint B — Goals execute |
| V2-B3 | **foundation** | Sprint B — Smart session compact |
| V2-B4 | **full** | Sprint B — Tenant filter on memory |
| V2-C1 | **full** | Sprint C — Parallel multi-CLI board opinions |
| V2-C2 | **full** | Sprint C — Cache key normalize |
| V2-C3 | **full** | Sprint C — Vision message helpers |
| V2-C4 | **full** | Sprint C — Bakeoff pin winner |
| V2-C5 | **foundation** | Sprint C — Graph HTML UI |
| V2-C6 | **full** | Sprint C — Permissions on goals notify |
| V2-D1 | **full** | Sprint D — OpenRouter refresh schedule |
| V2-D2 | **full** | Sprint D — NL profile / yolo directives |
| V2-D3 | **full** | Sprint D — PATH / which tests |

#### V3 — Sprints A–D

Source: `docs/IMPROVEMENT_V3_PLAN.md`

| ID | Status | Title |
|----|--------|-------|
| V3-A1 | **full** | Sprint A — Tool protocol (JSON tool_call) |
| V3-A2 | **full** | Sprint A — Failover ordered multi-model try |
| V3-A3 | **full** | Sprint A — Better diff check |
| V3-A4 | **foundation** | Sprint A — Contracts on more board APIs |
| V3-B1 | **full** | Sprint B — Cost on workers/run |
| V3-B2 | **full** | Sprint B — Tenant write-back everywhere memory |
| V3-B3 | **full** | Sprint B — Goals execute safety (caps, no yolo) |
| V3-B4 | **full** | Sprint B — pytest -m unit marker suite |
| V3-C1 | **full** | Sprint C — Parallel board (prior + harden) |
| V3-C2 | **full** | Sprint C — Vision helpers deepen |
| V3-C3 | **full** | Sprint C — Graph SVG |
| V3-C4 | **full** | Sprint C — Side-effect audit |
| V3-D1 | **foundation** | Sprint D — Bandit pin from bakeoff/outcomes |
| V3-D2 | **full** | Sprint D — NL hooks expansion |
| V3-D3 | **full** | Sprint D — Unit suite expansion / tests |

#### MoSCoW 100% honesty pass (post-V3)

Source: `docs/MOSCOW_100_PLAN.md`

| ID | Status | Title |
|----|--------|-------|
| MOS-M1 | **full** | Must M1 — Model tool protocol |
| MOS-M2 | **full** | Must M2 — Failover + fail-closed |
| MOS-M3 | **full** | Must M3 — Cost on workers |
| MOS-M4 | **full** | Must M4 — Tenant R/W everywhere memory |
| MOS-M5 | **full** | Must M5 — Diff check/apply |
| MOS-M6 | **foundation** | Must M6 — Contract on all major public APIs |
| MOS-M7 | **full** | Must M7 — Goals execute safe |
| MOS-M8 | **full** | Must M8 — pytest -m unit |
| MOS-S1 | **foundation** | Should S1 — Token streaming in agent-tui |
| MOS-S2 | **full** | Should S2 — Live vision call path |
| MOS-S3 | **full** | Should S3 — Semantic board cache |
| MOS-S4 | **full** | Should S4 — Worker diversity 1 premium + N cheap |
| MOS-S5 | **full** | Should S5 — Bakeoff bandit pin |
| MOS-S6 | **full** | Should S6 — Graph SVG UI |
| MOS-S7 | **full** | Should S7 — Shared ask session MCP/TUI |
| MOS-S8 | **full** | Should S8 — Side-effect audit |
| MOS-S9 | **full** | Should S9 — NL for goals/bakeoff/agent-tui/profile |
| MOS-S10 | **full** | Should S10 — Windows path_which tests |
| MOS-N1 | **full** | Nice N1 — Richer agent TUI (panels, /diff confirm) |
| MOS-N2 | **full** | Nice N2 — Assistant daemon tick + schedule goals |
| MOS-N3 | **full** | Nice N3 — Worktree subagent runner |
| MOS-N4 | **full** | Nice N4 — Bakeoff report file + eval hook |
| MOS-N5 | **full** | Nice N5 — Plugin catalog verify-sha default path |
| MOS-N6 | **full** | Nice N6 — Voice hooks in agent-tui |
| MOS-N7 | **full** | Nice N7 — Team palace export/import by tenant |
| MOS-N8 | **host** | Nice N8 — Live multi-vendor smoke |

#### Not-important polish (W1–W8 + superai_agent)

Source: `docs/NOT_IMPORTANT_PLAN.md`

| ID | Status | Title |
|----|--------|-------|
| W1 | **full** | Session export markdown |
| W2 | **full** | Session list + resume |
| W3 | **full** | Undo last turn |
| W4 | **full** | Cost/token session totals |
| W5 | **full** | Command palette + aliases |
| W6 | **full** | Multi-line paste mode |
| W7 | **foundation** | VS Code extension depth |
| W8 | **full** | Smoke preflight checklist |
| W-SA | **full** | SuperAI multi-agent package (superai_agent) |

#### V4 — Trust / efficiency / front door / change-set

Source: `docs/IMPROVEMENT_V4_PLAN.md`

| ID | Status | Title |
|----|--------|-------|
| V4-M1 | **foundation** | M1 — Budget on all spend paths |
| V4-M2 | **foundation** | M2 — Result contract everywhere public |
| V4-M3 | **full** | M3 — Fail-closed readiness before live agent |
| V4-M4 | **foundation** | M4 — Provider stream API path |
| V4-M5 | **full** | M5 — Tool result cache (path+mtime) |
| V4-M6 | **full** | M6 — Cheap-first step types |
| V4-M7 | **full** | M7 — Unified run trail |
| V4-M8 | **full** | M8 — Safety/money regression suite |
| V4-S1 | **full** | S1 — Complexity → member count |
| V4-S3 | **foundation** | S3 — Bandit feedback from runs |
| V4-S4 | **full** | S4 — Timeout / partial status |
| V4-S5 | **full** | S5 — Front-door policy map |
| V4-S6 | **full** | S6 — Local-first escalate |
| V4-S7 | **full** | S7 — Context pack token budget |
| V4-S8 | **full** | S8 — Parallel independent tools |
| V4-S9 | **full** | S9 — superai status --cost |
| V4-S10 | **full** | S10 — Change-set apply/reject |
| V4-DOD-1 | **foundation** | DoD-strict — spend_guard on council/bakeoff/compare/HTTP |
| V4-DOD-2 | **full** | DoD-strict — front door CLI (interactive + do) |
| V4-DOD-3 | **full** | DoD-strict — stream empty-success fallback |

#### V5 — Operational maturity

Source: `docs/IMPROVEMENT_V5_PLAN.md`

| ID | Status | Title |
|----|--------|-------|
| V5-M1 | **foundation** | M1 — CLI/public spend middleware |
| V5-M2 | **foundation** | M2 — MCP spend parity |
| V5-M3 | **foundation** | M3 — Cooperative cancel (CancelToken) |
| V5-M4 | **foundation** | M4 — Accurate cost from registry |
| V5-M5 | **full** | M5 — Error taxonomy |
| V5-M6 | **full** | M6 — Idempotent writes |
| V5-M7 | **full** | M7 — Security regression pack |
| V5-M8 | **full** | M8 — Golden offline eval |
| V5-S1 | **full** | S1 — Cross-session result cache |
| V5-S2 | **full** | S2 — Adaptive escalate |
| V5-S3 | **full** | S3 — Run explain (explain-run) |
| V5-S4 | **full** | S4 — Smarter memory inject cap |
| V5-S5 | **full** | S5 — Profile auto-suggest |
| V5-S6 | **full** | S6 — Front-door confidence |
| V5-S7 | **full** | S7 — Board early-exit consensus |
| V5-S10 | **full** | S10 — Progress snapshot |

---

# Detailed assessments (every item)

## V1 — Improvement Plan (Phases 0–7 + Phase 99)

Source plan: `docs/IMPROVEMENT_PLAN.md`

### V1-P0 — Phase 0 — Planning (IMPROVEMENT_PLAN, TASKBOARD, handoff)

- **Status:** `full`
- **Why:** Plan docs, TASKBOARD, and session handoff were written and used as the execution source of truth. Planning is complete by definition of this phase.

### V1-P1-1 — Phase 1 — Stable result contract

- **Status:** `foundation`
- **Why:** result_contract.py exists and is used on major paths with unit tests. Not full: later V6 honesty (M008) still finds uneven CLI coverage — not literally every public command.

### V1-P1-2 — Phase 1 — Mock/dry_run honesty (never false live success)

- **Status:** `full`
- **Why:** Mock mode and dry_run paths refuse to claim live success; smoke harness and tests enforce honesty. Matches Phase 1 intent.

### V1-P1-3 — Phase 1 — Budget hard-stop foundation

- **Status:** `foundation`
- **Why:** Budget / spend guard foundations landed and were deepened in V4/V5. Not full vs 'every spend path' (still foundation in V6 M001).

### V1-P1-4 — Phase 1 — Cost fields on results

- **Status:** `foundation`
- **Why:** Cost fields appear on contracts and status paths. Accuracy still depends on provider usage metadata (V5/V6 cost_accounting foundation).

### V1-P2-1 — Phase 2 — Default agent / front-door entry

- **Status:** `full`
- **Why:** Default superai entry and agent paths exist (later front_door/do deepen). Phase 2 'agent front door' intent is met for product use.

### V1-P2-2 — Phase 2 — Permission modes (plan/ask/auto/yolo)

- **Status:** `full`
- **Why:** permission_mode.py with safe defaults; agent and CLI honor modes; tests cover plan-mode no-write. Full for Phase 2 scope.

### V1-P2-3 — Phase 2 — Multi-turn ask session

- **Status:** `full`
- **Why:** ask_session / SuperAI session store supports multi-turn resume/export. Tests cover session behavior. Full for Phase 2.

### V1-P3-1 — Phase 3 — Registry validation

- **Status:** `full`
- **Why:** registry_validate validates model registry entries. Usable for install/doctor.

### V1-P3-2 — Phase 3 — Run profiles (cheap/balanced/quality/local-only)

- **Status:** `full`
- **Why:** run_profiles module defines cost/quality profiles used by routing/agent. Profile intent met.

### V1-P3-3 — Phase 3 — Cost report / status spend visibility

- **Status:** `full`
- **Why:** status --cost and related snapshots report budget/spend. Phase 3 cost report intent met (later V4 S9 deepens).

### V1-P4-1 — Phase 4 — Prefer open-weight/local failover

- **Status:** `full`
- **Why:** Failover and later local_first prefer local/OW then premium. Phase 4 routing efficiency intent met.

### V1-P4-2 — Phase 4 — Smart board member sizing

- **Status:** `full`
- **Why:** smart_max_members / complexity-driven board size exists. Efficiency intent met.

### V1-P4-3 — Phase 4 — Board result cache

- **Status:** `full`
- **Why:** board_cache with TTL (+ later semantic key) reduces repeat board cost. Tests in test_board_cache.py. Full for Phase 4.

### V1-P5-1 — Phase 5 — In-process Read/Edit/Bash tools (workspace jail)

- **Status:** `full`
- **Why:** agent_tools with jail fail-closed; used by agent runtime/TUI. Tests cover tools and permissions. Full for Phase 5 basic tools.

### V1-P5-2 — Phase 5 — Streaming progress bus

- **Status:** `foundation`
- **Why:** progress_events bus + later token_stream exist. Not full true SSE on all providers (V4/V6 stream still foundation with fallback chunking).

### V1-P5-3 — Phase 5 — Provider health UX (circuit column)

- **Status:** `full`
- **Why:** provider_health circuits + status/doctor surface health. Phase 5 health UX met.

### V1-P6-1 — Phase 6 — Auto Ollama discover (opt-in)

- **Status:** `full`
- **Why:** auto_ollama_discover config/path registers local Ollama models. Intent met.

### V1-P6-2 — Phase 6 — NL intent map expand

- **Status:** `full`
- **Why:** nl_intent / ask routing expanded beyond original narrow map; do/front_door later. Phase 6 NL expand intent met.

### V1-P6-3 — Phase 6 — Windows PATH / CLI resolve hardening

- **Status:** `full`
- **Why:** path_which Windows-aware resolution with expanded tests (MoSCoW S10). Full.

### V1-P7 — Phase 7 — Docs closeout

- **Status:** `full`
- **Why:** IMPROVEMENT_PLAN and related track docs updated to code-complete status. Docs closeout done.

### V1-P99 — Phase 99 — Live multi-provider smoke (host)

- **Status:** `host`
- **Why:** Smoke harness + phase6-smoke paths exist and never false-pass. Live_passed requires host API keys — postponed by policy, not missing code.

#### Track rollup

| Status | Count |
|--------|------:|
| full | 17 |
| foundation | 4 |
| host | 1 |

## V1 Phase 8 — Nice-to-have (N1–N8)

Source plan: `docs/PHASE8_PLAN.md`

### V1-N1 — Phase 8 N1 — Agent TUI

- **Status:** `full`
- **Why:** agent_tui / superai agent-tui + superai_agent TUI with tools/cost/permissions. test_phase8 + later agent tests. Full product TUI for SuperAI brand.

### V1-N2 — Phase 8 N2 — Personal assistant goals

- **Status:** `full`
- **Why:** assistant_goals + superai goals (add/heartbeat/execute/notify/tick). Caps and safety deepened in MoSCoW/V3. Full for Phase 8 N2.

### V1-N3 — Phase 8 N3 — Multimodal images

- **Status:** `full`
- **Why:** multimodal + ask --image / vision_attachments path through ModelCaller. Tests cover missing image + vision call path. Full for Phase 8.

### V1-N4 — Phase 8 N4 — Run/subagent graph API

- **Status:** `full`
- **Why:** agent_graph + agent-graph CLI + /api/agent-graph (SVG). Tests for graph. Full.

### V1-N5 — Phase 8 N5 — OpenRouter model refresh

- **Status:** `full`
- **Why:** models-refresh-openrouter (+ schedule in V2). Catalog refresh works. Full.

### V1-N6 — Phase 8 N6 — Model bake-off

- **Status:** `full`
- **Why:** model_bakeoff + superai bakeoff with pin/report hooks later. Mock tests. Full.

### V1-N7 — Phase 8 N7 — Palace tenant

- **Status:** `full`
- **Why:** palace_tenant + tenant_id config; export/import later. Isolation foundation is production-usable for single-host multi-tenant tags.

### V1-N8 — Phase 8 N8 — Plugin marketplace browse

- **Status:** `full`
- **Why:** Production marketplace browse: bundled catalog JSON, search/tag/category/sort, installed overlay, get/categories/status CLI, sha-safe install hooks. Docs: PLUGIN_MARKETPLACE.md + PHASE8 N8. Tests: test_plugin_marketplace_n8.py. Out of scope: payments/community hub.

#### Track rollup

| Status | Count |
|--------|------:|
| full | 8 |

## V2 — Sprints A–D

Source plan: `docs/IMPROVEMENT_V2_PLAN.md`

### V2-A1 — Sprint A — Tools in TUI (/tool read|grep|…)

- **Status:** `full`
- **Why:** TUI /tool path + parse_and_run_tool; tests in test_sprint_abcd. Full for V2 A.

### V2-A2 — Sprint A — Git diff propose + dry-apply

- **Status:** `full`
- **Why:** diff propose / dry-apply under plan mode; git_diff_apply check path. Tested.

### V2-A3 — Sprint A — Fail-closed readiness

- **Status:** `full`
- **Why:** readiness mock/live gates; agent refuses when not ready (deepened V4 M3). Full.

### V2-A4 — Sprint A — Result contract on tool/agent paths

- **Status:** `foundation`
- **Why:** Contracts applied to key tool/agent paths. Still not universal on every CLI command (consistent with V1/V6 foundation notes).

### V2-B1 — Sprint B — Cost router shrink boards under budget

- **Status:** `full`
- **Why:** cost_router shrinks members; unit tests force tiny budget. Full for V2 B.

### V2-B2 — Sprint B — Goals execute

- **Status:** `full`
- **Why:** goals execute --max N with later safety caps. Commands and tests exist. Full.

### V2-B3 — Sprint B — Smart session compact

- **Status:** `foundation`
- **Why:** smart_compact / session_compact exists and is tested. Not full decision/todo preserving product (later V6 M029 foundation).

### V2-B4 — Sprint B — Tenant filter on memory

- **Status:** `full`
- **Why:** tenant_scope / tags filter memory R/W. Tested in sprint + MoSCoW. Full.

### V2-C1 — Sprint C — Parallel multi-CLI board opinions

- **Status:** `full`
- **Why:** Parallel advisory/board paths exist (multi_cli_advisory). Prior + C work. Full.

### V2-C2 — Sprint C — Cache key normalize

- **Status:** `full`
- **Why:** Board cache normalization improves hit rate; semantic key later (MoSCoW S3). Full.

### V2-C3 — Sprint C — Vision message helpers

- **Status:** `full`
- **Why:** Vision message construction helpers for multimodal asks. Path tested later. Full.

### V2-C4 — Sprint C — Bakeoff pin winner

- **Status:** `full`
- **Why:** bakeoff --pin persists winner; test_bakeoff_pin. Full.

### V2-C5 — Sprint C — Graph HTML UI

- **Status:** `foundation`
- **Why:** Graph UI existed as HTML then SVG (V3). Foundation/full for visualization product is agent-graph SVG today — HTML slice was intermediate; product is usable.

### V2-C6 — Sprint C — Permissions on goals notify

- **Status:** `full`
- **Why:** Notify paths respect permission/safety (no yolo inherit later). Intent met.

### V2-D1 — Sprint D — OpenRouter refresh schedule

- **Status:** `full`
- **Why:** models-refresh-openrouter --schedule path. Catalog ops intent met.

### V2-D2 — Sprint D — NL profile / yolo directives

- **Status:** `full`
- **Why:** NL ask can apply profile/plan-only directives; execute_directives tests. Full.

### V2-D3 — Sprint D — PATH / which tests

- **Status:** `full`
- **Why:** path_which tests (which_cmd + Windows). Full.

#### Track rollup

| Status | Count |
|--------|------:|
| full | 14 |
| foundation | 3 |

## V3 — Sprints A–D

Source plan: `docs/IMPROVEMENT_V3_PLAN.md`

### V3-A1 — Sprint A — Tool protocol (JSON tool_call)

- **Status:** `full`
- **Why:** tool_protocol extract + run_tool_calls; agent_with_tools mock tests. Full.

### V3-A2 — Sprint A — Failover ordered multi-model try

- **Status:** `full`
- **Why:** ModelCaller failover ordered/bounded/logged. Fail-closed readiness combined. Full.

### V3-A3 — Sprint A — Better diff check

- **Status:** `full`
- **Why:** git_diff_apply check hardened; tests for diff check. Full.

### V3-A4 — Sprint A — Contracts on more board APIs

- **Status:** `foundation`
- **Why:** Contracts expanded (council/compare paths in MoSCoW). Still foundation for 'everywhere public' absolute wording.

### V3-B1 — Sprint B — Cost on workers/run

- **Status:** `full`
- **Why:** cost_router / cost on orchestrator workers; cost_shrink tests. Full for V3 B.

### V3-B2 — Sprint B — Tenant write-back everywhere memory

- **Status:** `full`
- **Why:** write_back + query tags + scope; MoSCoW M4 tests. Full for tenant memory R/W.

### V3-B3 — Sprint B — Goals execute safety (caps, no yolo)

- **Status:** `full`
- **Why:** Goals execute with max caps and safe permission defaults. Full.

### V3-B4 — Sprint B — pytest -m unit marker suite

- **Status:** `full`
- **Why:** Unit marker + suite; pytest -m unit is the offline gate. Full.

### V3-C1 — Sprint C — Parallel board (prior + harden)

- **Status:** `full`
- **Why:** Parallel boards already present; V3 C hardened. Full.

### V3-C2 — Sprint C — Vision helpers deepen

- **Status:** `full`
- **Why:** Vision helpers + live vision path (MoSCoW S2). Full for V3 scope.

### V3-C3 — Sprint C — Graph SVG

- **Status:** `full`
- **Why:** agent-graph SVG UI + API. Full.

### V3-C4 — Sprint C — Side-effect audit

- **Status:** `full`
- **Why:** side_effect_audit records write/delete/run; unit tests. Full.

### V3-D1 — Sprint D — Bandit pin from bakeoff/outcomes

- **Status:** `foundation`
- **Why:** Bandit pin path from bakeoff exists; continuous bandit on every call still foundation (V6 M050).

### V3-D2 — Sprint D — NL hooks expansion

- **Status:** `full`
- **Why:** NL hooks for goals/bakeoff/agent/profile (MoSCoW S9 tests). Full.

### V3-D3 — Sprint D — Unit suite expansion / tests

- **Status:** `full`
- **Why:** test_improvement_v3 + sprint_abcd + unit marker. Full for verification goal.

#### Track rollup

| Status | Count |
|--------|------:|
| full | 13 |
| foundation | 2 |

## MoSCoW 100% honesty pass (post-V3)

Source plan: `docs/MOSCOW_100_PLAN.md`

### MOS-M1 — Must M1 — Model tool protocol

- **Status:** `full`
- **Why:** tool_protocol + tests (code+tests DoD). Full per MoSCoW policy.

### MOS-M2 — Must M2 — Failover + fail-closed

- **Status:** `full`
- **Why:** readiness + multi-model try. Full.

### MOS-M3 — Must M3 — Cost on workers

- **Status:** `full`
- **Why:** cost_router in orchestrator/board. Full for MoSCoW M3 wording.

### MOS-M4 — Must M4 — Tenant R/W everywhere memory

- **Status:** `full`
- **Why:** write_back + query tags + scope + export/import. Full.

### MOS-M5 — Must M5 — Diff check/apply

- **Status:** `full`
- **Why:** git_diff_apply check + apply. Full.

### MOS-M6 — Must M6 — Contract on all major public APIs

- **Status:** `foundation`
- **Why:** council, compare, cli-run, pr_review, web status covered with tests. Rated foundation not absolute full because 'all major' still excludes some thin CLI wrappers (honest vs V6 M008).

### MOS-M7 — Must M7 — Goals execute safe

- **Status:** `full`
- **Why:** caps + no yolo. Full.

### MOS-M8 — Must M8 — pytest -m unit

- **Status:** `full`
- **Why:** markers + suite green offline. Full.

### MOS-S1 — Should S1 — Token streaming in agent-tui

- **Status:** `foundation`
- **Why:** token_stream + Live panel exist. Real provider SSE incomplete; fallback chunking — foundation for 'real streaming' absolute claim.

### MOS-S2 — Should S2 — Live vision call path

- **Status:** `full`
- **Why:** vision_attachments through ModelCaller + call_with_images. Tested. Full.

### MOS-S3 — Should S3 — Semantic board cache

- **Status:** `full`
- **Why:** semantic_subject_key + SUPERAI_BOARD_SEMANTIC. Tested. Full.

### MOS-S4 — Should S4 — Worker diversity 1 premium + N cheap

- **Status:** `full`
- **Why:** diversify_pool / resolve_worker_pool. Tested. Full.

### MOS-S5 — Should S5 — Bakeoff bandit pin

- **Status:** `full`
- **Why:** Bakeoff pin integrates with bandit path. Full for MoSCoW S5.

### MOS-S6 — Should S6 — Graph SVG UI

- **Status:** `full`
- **Why:** SVG graph UI. Full.

### MOS-S7 — Should S7 — Shared ask session MCP/TUI

- **Status:** `full`
- **Why:** Shared session root + MCP superai_ask_session. Tested. Full.

### MOS-S8 — Should S8 — Side-effect audit

- **Status:** `full`
- **Why:** side_effect_audit. Full.

### MOS-S9 — Should S9 — NL for goals/bakeoff/agent-tui/profile

- **Status:** `full`
- **Why:** Dedicated NL actions + handlers tested. Full.

### MOS-S10 — Should S10 — Windows path_which tests

- **Status:** `full`
- **Why:** Expanded Windows extension tests. Full.

### MOS-N1 — Nice N1 — Richer agent TUI (panels, /diff confirm)

- **Status:** `full`
- **Why:** /panel /diff /stream commands. Full for MoSCoW N1.

### MOS-N2 — Nice N2 — Assistant daemon tick + schedule goals

- **Status:** `full`
- **Why:** daemon_tick + goals tick CLI. Tested. Full (not a full OS daemon product).

### MOS-N3 — Nice N3 — Worktree subagent runner

- **Status:** `full`
- **Why:** worktree_subagent + worktree-run CLI. Dry-run tested. Full.

### MOS-N4 — Nice N4 — Bakeoff report file + eval hook

- **Status:** `full`
- **Why:** Report path + default_eval_hook. Tested. Full.

### MOS-N5 — Nice N5 — Plugin catalog verify-sha default path

- **Status:** `full`
- **Why:** ~/.superai/plugin_sha store. Tested. Full.

### MOS-N6 — Nice N6 — Voice hooks in agent-tui

- **Status:** `full`
- **Why:** voice_io full: TTS pyttsx3/SAPI/mock, STT mic/file/queue, /listen /speak /voice in agent_tui + superai_agent TUI, auto-speak replies, superai voice CLI, tests test_voice_mos_n6.py. MOS-N6 production-usable offline with file/mock backends.

### MOS-N7 — Nice N7 — Team palace export/import by tenant

- **Status:** `full`
- **Why:** tenant-export / tenant-import. Tested. Full.

### MOS-N8 — Nice N8 — Live multi-vendor smoke

- **Status:** `host`
- **Why:** smoke_harness never false-passes; live needs keys. Host-gated — not [x] full.

#### Track rollup

| Status | Count |
|--------|------:|
| full | 23 |
| foundation | 2 |
| host | 1 |

## Not-important polish (W1–W8 + superai_agent)

Source plan: `docs/NOT_IMPORTANT_PLAN.md`

### W1 — Session export markdown

- **Status:** `full`
- **Why:** /export + AskSessionStore.export_markdown; test_not_important. Full.

### W2 — Session list + resume

- **Status:** `full`
- **Why:** /sessions /resume. Full.

### W3 — Undo last turn

- **Status:** `full`
- **Why:** /undo removes last turn. Full.

### W4 — Cost/token session totals

- **Status:** `full`
- **Why:** /cost + turn meta aggregation. Full.

### W5 — Command palette + aliases

- **Status:** `full`
- **Why:** tui_commands + /commands. Full for TUI palette (not Ctrl+K app).

### W6 — Multi-line paste mode

- **Status:** `full`
- **Why:** /paste … /end. Full.

### W7 — VS Code extension depth

- **Status:** `foundation`
- **Why:** VS Code extension covers ask/review/members/smoke-preflight. Thin vs full IDE product — foundation for 'depth' beyond empty stub.

### W8 — Smoke preflight checklist

- **Status:** `full`
- **Why:** smoke_preflight + CLI; no false pass. Full.

### W-SA — SuperAI multi-agent package (superai_agent)

- **Status:** `full`
- **Why:** core.superai_agent + SUPERAI_AGENT.md; product brand SuperAI (not OpenCode). Full.

#### Track rollup

| Status | Count |
|--------|------:|
| full | 8 |
| foundation | 1 |

## V4 — Trust / efficiency / front door / change-set

Source plan: `docs/IMPROVEMENT_V4_PLAN.md`

### V4-M1 — M1 — Budget on all spend paths

- **Status:** `foundation`
- **Why:** budget_guard soft API + spend_guard on agent/boards/council/bakeoff/compare/HTTP/agent. DoD-strict sweep expanded coverage. Still foundation: not every thin CLI wrapper (same as V6 M001).

### V4-M2 — M2 — Result contract everywhere public

- **Status:** `foundation`
- **Why:** ensure_contract / ensure_public_result on major paths. Not absolute everywhere.

### V4-M3 — M3 — Fail-closed readiness before live agent

- **Status:** `full`
- **Why:** Live agent refuses if model not ready unless override. Full.

### V4-M4 — M4 — Provider stream API path

- **Status:** `foundation`
- **Why:** ModelCaller.call_stream + agent on_token; empty stream falls back to call(). Not proven real SSE on all providers.

### V4-M5 — M5 — Tool result cache (path+mtime)

- **Status:** `full`
- **Why:** Read tools cache by path+mtime; unit test. Full for V4 M5.

### V4-M6 — M6 — Cheap-first step types

- **Status:** `full`
- **Why:** task_complexity classifier routes summarize/plan to cheap members. Tested. Full.

### V4-M7 — M7 — Unified run trail

- **Status:** `full`
- **Why:** run_trail id links session + side effects + cost; explain-run later. Full.

### V4-M8 — M8 — Safety/money regression suite

- **Status:** `full`
- **Why:** tests/test_improvement_v4.py covers plan/budget/tenant/stream/local_first. Full.

### V4-S1 — S1 — Complexity → member count

- **Status:** `full`
- **Why:** Shared classifier used by boards. Full.

### V4-S3 — S3 — Bandit feedback from runs

- **Status:** `foundation`
- **Why:** Success/latency/cost can update bandit. Not continuous every-call product.

### V4-S4 — S4 — Timeout / partial status

- **Status:** `full`
- **Why:** Runtime max_seconds → partial contract. Full for V4 S4.

### V4-S5 — S5 — Front-door policy map

- **Status:** `full`
- **Why:** front_door chooses agent vs board vs run; CLI do + interactive wired. Full.

### V4-S6 — S6 — Local-first escalate

- **Status:** `full`
- **Why:** local_first.escalate_chain in ModelCaller + worker pool. Tests. Full.

### V4-S7 — S7 — Context pack token budget

- **Status:** `full`
- **Why:** context_pack ordered drop under budget. Tested. Full.

### V4-S8 — S8 — Parallel independent tools

- **Status:** `full`
- **Why:** Runtime batches read/grep/glob. Full.

### V4-S9 — S9 — superai status --cost

- **Status:** `full`
- **Why:** Snapshot budget + circuits + cache stats. Full.

### V4-S10 — S10 — Change-set apply/reject

- **Status:** `full`
- **Why:** change_set accumulates writes; /apply /reject. Tested. Full.

### V4-DOD-1 — DoD-strict — spend_guard on council/bakeoff/compare/HTTP

- **Status:** `foundation`
- **Why:** Sweep closed major gaps. Still not literal every path — foundation+strong.

### V4-DOD-2 — DoD-strict — front door CLI (interactive + do)

- **Status:** `full`
- **Why:** superai interactive + superai do + NL re-route. Full.

### V4-DOD-3 — DoD-strict — stream empty-success fallback

- **Status:** `full`
- **Why:** Stream falls back to full call() if no chunks — honesty/reliability fix. Full.

#### Track rollup

| Status | Count |
|--------|------:|
| full | 15 |
| foundation | 5 |

## V5 — Operational maturity

Source plan: `docs/IMPROVEMENT_V5_PLAN.md`

### V5-M1 — M1 — CLI/public spend middleware

- **Status:** `foundation`
- **Why:** public_api.wrap on key CLI + MCP. Not every Typer command — foundation.

### V5-M2 — M2 — MCP spend parity

- **Status:** `foundation`
- **Why:** superai_run / cli_run budget + contract. MCP surface parity not proven for every MCP tool — foundation.

### V5-M3 — M3 — Cooperative cancel (CancelToken)

- **Status:** `foundation`
- **Why:** CancelToken in agent runtime; tests. Not all board workers share cancel — foundation (V6 M017).

### V5-M4 — M4 — Accurate cost from registry

- **Status:** `foundation`
- **Why:** cost_accounting.estimate / from_usage. Some paths still estimate when usage missing — foundation.

### V5-M5 — M5 — Error taxonomy

- **Status:** `full`
- **Why:** error_code on contracts; taxonomy tests. Full for V5 M5.

### V5-M6 — M6 — Idempotent writes

- **Status:** `full`
- **Why:** Skip write if content unchanged; unit test. Full.

### V5-M7 — M7 — Security regression pack

- **Status:** `full`
- **Why:** test_improvement_v5.py security/money pack. Full for V5 suite intent.

### V5-M8 — M8 — Golden offline eval

- **Status:** `full`
- **Why:** eval_golden + tests (mock). Full offline eval set.

### V5-S1 — S1 — Cross-session result cache

- **Status:** `full`
- **Why:** opt-in result_cache; unit test. Full for V5 S1.

### V5-S2 — S2 — Adaptive escalate

- **Status:** `full`
- **Why:** adaptive_escalate module + agent runtime quality_failed escalate once; unit tested. Intent met for V5 S2.

### V5-S3 — S3 — Run explain (explain-run)

- **Status:** `full`
- **Why:** superai explain-run <run_id> via run_trail. Full.

### V5-S4 — S4 — Smarter memory inject cap

- **Status:** `full`
- **Why:** memory_inject rank + hard token budget helper. Tested. Full.

### V5-S5 — S5 — Profile auto-suggest

- **Status:** `full`
- **Why:** profile_suggest from budget + history stats. Tested. Full.

### V5-S6 — S6 — Front-door confidence

- **Status:** `full`
- **Why:** Low confidence flag + optional confirm. Tested. Full.

### V5-S7 — S7 — Board early-exit consensus

- **Status:** `full`
- **Why:** Stop when first opinions agree (cost save). Full for V5 S7.

### V5-S10 — S10 — Progress snapshot

- **Status:** `full`
- **Why:** superai progress recent bus/trail. Full.

#### Track rollup

| Status | Count |
|--------|------:|
| full | 12 |
| foundation | 4 |

## Decision method

1. Read each plan’s DoD / item wording.
2. Map to modules under `src/core/` and CLI in `src/cli/main.py`.
3. Prefer unit tests (`test_improvement_v*`, `test_moscow_100`, `test_sprint_abcd`, `test_phase8`, `test_not_important`) as evidence.
4. Downgrade to **foundation** when later V6 audit still shows incomplete universality.
5. Keep **host** for live multi-provider smoke — never false-claim.

Regenerate: `python scripts/gen_v1_v5_scorecard.py`

## Related

- V6 scorecard: `docs/V6_SCORECARD.md`
- V6 backlog: `docs/IMPROVEMENT_V6_BACKLOG.md`
- Pending: `docs/PENDING_WORK.md`

