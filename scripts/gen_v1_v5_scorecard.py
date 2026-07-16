"""Generate docs/V1_V5_SCORECARD.md — honest per-item audit for V1–V5 (+ MoSCoW/W)."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "V1_V5_SCORECARD.md"

# Status: full | foundation | stub | host | refuse | absent
# Each item: (track, id, title, status, why)

Item = tuple[str, str, str, str, str]

ITEMS: list[Item] = [
    # =====================================================================
    # V1 — IMPROVEMENT_PLAN.md Phases 0–7
    # =====================================================================
    (
        "V1",
        "V1-P0",
        "Phase 0 — Planning (IMPROVEMENT_PLAN, TASKBOARD, handoff)",
        "full",
        "Plan docs, TASKBOARD, and session handoff were written and used as the "
        "execution source of truth. Planning is complete by definition of this phase.",
    ),
    (
        "V1",
        "V1-P1-1",
        "Phase 1 — Stable result contract",
        "foundation",
        "result_contract.py exists and is used on major paths with unit tests. "
        "Not full: later V6 honesty (M008) still finds uneven CLI coverage — "
        "not literally every public command.",
    ),
    (
        "V1",
        "V1-P1-2",
        "Phase 1 — Mock/dry_run honesty (never false live success)",
        "full",
        "Mock mode and dry_run paths refuse to claim live success; smoke harness "
        "and tests enforce honesty. Matches Phase 1 intent.",
    ),
    (
        "V1",
        "V1-P1-3",
        "Phase 1 — Budget hard-stop foundation",
        "foundation",
        "Budget / spend guard foundations landed and were deepened in V4/V5. "
        "Not full vs 'every spend path' (still foundation in V6 M001).",
    ),
    (
        "V1",
        "V1-P1-4",
        "Phase 1 — Cost fields on results",
        "foundation",
        "Cost fields appear on contracts and status paths. Accuracy still depends "
        "on provider usage metadata (V5/V6 cost_accounting foundation).",
    ),
    (
        "V1",
        "V1-P2-1",
        "Phase 2 — Default agent / front-door entry",
        "full",
        "Default superai entry and agent paths exist (later front_door/do deepen). "
        "Phase 2 'agent front door' intent is met for product use.",
    ),
    (
        "V1",
        "V1-P2-2",
        "Phase 2 — Permission modes (plan/ask/auto/yolo)",
        "full",
        "permission_mode.py with safe defaults; agent and CLI honor modes; tests "
        "cover plan-mode no-write. Full for Phase 2 scope.",
    ),
    (
        "V1",
        "V1-P2-3",
        "Phase 2 — Multi-turn ask session",
        "full",
        "ask_session / SuperAI session store supports multi-turn resume/export. "
        "Tests cover session behavior. Full for Phase 2.",
    ),
    (
        "V1",
        "V1-P3-1",
        "Phase 3 — Registry validation",
        "full",
        "registry_validate validates model registry entries. Usable for install/doctor.",
    ),
    (
        "V1",
        "V1-P3-2",
        "Phase 3 — Run profiles (cheap/balanced/quality/local-only)",
        "full",
        "run_profiles module defines cost/quality profiles used by routing/agent. "
        "Profile intent met.",
    ),
    (
        "V1",
        "V1-P3-3",
        "Phase 3 — Cost report / status spend visibility",
        "full",
        "status --cost and related snapshots report budget/spend. Phase 3 cost "
        "report intent met (later V4 S9 deepens).",
    ),
    (
        "V1",
        "V1-P4-1",
        "Phase 4 — Prefer open-weight/local failover",
        "full",
        "Failover and later local_first prefer local/OW then premium. Phase 4 "
        "routing efficiency intent met.",
    ),
    (
        "V1",
        "V1-P4-2",
        "Phase 4 — Smart board member sizing",
        "full",
        "smart_max_members / complexity-driven board size exists. Efficiency intent met.",
    ),
    (
        "V1",
        "V1-P4-3",
        "Phase 4 — Board result cache",
        "full",
        "board_cache with TTL (+ later semantic key) reduces repeat board cost. "
        "Tests in test_board_cache.py. Full for Phase 4.",
    ),
    (
        "V1",
        "V1-P5-1",
        "Phase 5 — In-process Read/Edit/Bash tools (workspace jail)",
        "full",
        "agent_tools with jail fail-closed; used by agent runtime/TUI. Tests cover "
        "tools and permissions. Full for Phase 5 basic tools.",
    ),
    (
        "V1",
        "V1-P5-2",
        "Phase 5 — Streaming progress bus",
        "foundation",
        "progress_events bus + later token_stream exist. Not full true SSE on all "
        "providers (V4/V6 stream still foundation with fallback chunking).",
    ),
    (
        "V1",
        "V1-P5-3",
        "Phase 5 — Provider health UX (circuit column)",
        "full",
        "provider_health circuits + status/doctor surface health. Phase 5 health UX met.",
    ),
    (
        "V1",
        "V1-P6-1",
        "Phase 6 — Auto Ollama discover (opt-in)",
        "full",
        "auto_ollama_discover config/path registers local Ollama models. Intent met.",
    ),
    (
        "V1",
        "V1-P6-2",
        "Phase 6 — NL intent map expand",
        "full",
        "nl_intent / ask routing expanded beyond original narrow map; do/front_door "
        "later. Phase 6 NL expand intent met.",
    ),
    (
        "V1",
        "V1-P6-3",
        "Phase 6 — Windows PATH / CLI resolve hardening",
        "full",
        "path_which Windows-aware resolution with expanded tests (MoSCoW S10). Full.",
    ),
    (
        "V1",
        "V1-P7",
        "Phase 7 — Docs closeout",
        "full",
        "IMPROVEMENT_PLAN and related track docs updated to code-complete status. "
        "Docs closeout done.",
    ),
    (
        "V1",
        "V1-P99",
        "Phase 99 — Live multi-provider smoke (host)",
        "host",
        "Smoke harness + phase6-smoke paths exist and never false-pass. Live_passed "
        "requires host API keys — postponed by policy, not missing code.",
    ),
    # =====================================================================
    # V1 Phase 8 — Nice (PHASE8_PLAN.md)
    # =====================================================================
    (
        "V1-P8",
        "V1-N1",
        "Phase 8 N1 — Agent TUI",
        "full",
        "agent_tui / superai agent-tui + superai_agent TUI with tools/cost/permissions. "
        "test_phase8 + later agent tests. Full product TUI for SuperAI brand.",
    ),
    (
        "V1-P8",
        "V1-N2",
        "Phase 8 N2 — Personal assistant goals",
        "full",
        "assistant_goals + superai goals (add/heartbeat/execute/notify/tick). "
        "Caps and safety deepened in MoSCoW/V3. Full for Phase 8 N2.",
    ),
    (
        "V1-P8",
        "V1-N3",
        "Phase 8 N3 — Multimodal images",
        "full",
        "multimodal + ask --image / vision_attachments path through ModelCaller. "
        "Tests cover missing image + vision call path. Full for Phase 8.",
    ),
    (
        "V1-P8",
        "V1-N4",
        "Phase 8 N4 — Run/subagent graph API",
        "full",
        "agent_graph + agent-graph CLI + /api/agent-graph (SVG). Tests for graph. Full.",
    ),
    (
        "V1-P8",
        "V1-N5",
        "Phase 8 N5 — OpenRouter model refresh",
        "full",
        "models-refresh-openrouter (+ schedule in V2). Catalog refresh works. Full.",
    ),
    (
        "V1-P8",
        "V1-N6",
        "Phase 8 N6 — Model bake-off",
        "full",
        "model_bakeoff + superai bakeoff with pin/report hooks later. Mock tests. Full.",
    ),
    (
        "V1-P8",
        "V1-N7",
        "Phase 8 N7 — Palace tenant",
        "full",
        "palace_tenant + tenant_id config; export/import later. Isolation foundation "
        "is production-usable for single-host multi-tenant tags.",
    ),
    (
        "V1-P8",
        "V1-N8",
        "Phase 8 N8 — Plugin marketplace browse",
        "foundation",
        "plugin_catalog browse + CLI exist. Not a full marketplace product "
        "(no payments/community hub) — browse/catalog foundation only.",
    ),
    # =====================================================================
    # V2 — IMPROVEMENT_V2_PLAN.md Sprints A–D
    # =====================================================================
    (
        "V2",
        "V2-A1",
        "Sprint A — Tools in TUI (/tool read|grep|…)",
        "full",
        "TUI /tool path + parse_and_run_tool; tests in test_sprint_abcd. Full for V2 A.",
    ),
    (
        "V2",
        "V2-A2",
        "Sprint A — Git diff propose + dry-apply",
        "full",
        "diff propose / dry-apply under plan mode; git_diff_apply check path. Tested.",
    ),
    (
        "V2",
        "V2-A3",
        "Sprint A — Fail-closed readiness",
        "full",
        "readiness mock/live gates; agent refuses when not ready (deepened V4 M3). Full.",
    ),
    (
        "V2",
        "V2-A4",
        "Sprint A — Result contract on tool/agent paths",
        "foundation",
        "Contracts applied to key tool/agent paths. Still not universal on every CLI "
        "command (consistent with V1/V6 foundation notes).",
    ),
    (
        "V2",
        "V2-B1",
        "Sprint B — Cost router shrink boards under budget",
        "full",
        "cost_router shrinks members; unit tests force tiny budget. Full for V2 B.",
    ),
    (
        "V2",
        "V2-B2",
        "Sprint B — Goals execute",
        "full",
        "goals execute --max N with later safety caps. Commands and tests exist. Full.",
    ),
    (
        "V2",
        "V2-B3",
        "Sprint B — Smart session compact",
        "foundation",
        "smart_compact / session_compact exists and is tested. Not full decision/todo "
        "preserving product (later V6 M029 foundation).",
    ),
    (
        "V2",
        "V2-B4",
        "Sprint B — Tenant filter on memory",
        "full",
        "tenant_scope / tags filter memory R/W. Tested in sprint + MoSCoW. Full.",
    ),
    (
        "V2",
        "V2-C1",
        "Sprint C — Parallel multi-CLI board opinions",
        "full",
        "Parallel advisory/board paths exist (multi_cli_advisory). Prior + C work. Full.",
    ),
    (
        "V2",
        "V2-C2",
        "Sprint C — Cache key normalize",
        "full",
        "Board cache normalization improves hit rate; semantic key later (MoSCoW S3). Full.",
    ),
    (
        "V2",
        "V2-C3",
        "Sprint C — Vision message helpers",
        "full",
        "Vision message construction helpers for multimodal asks. Path tested later. Full.",
    ),
    (
        "V2",
        "V2-C4",
        "Sprint C — Bakeoff pin winner",
        "full",
        "bakeoff --pin persists winner; test_bakeoff_pin. Full.",
    ),
    (
        "V2",
        "V2-C5",
        "Sprint C — Graph HTML UI",
        "foundation",
        "Graph UI existed as HTML then SVG (V3). Foundation/full for visualization "
        "product is agent-graph SVG today — HTML slice was intermediate; product is usable.",
    ),
    (
        "V2",
        "V2-C6",
        "Sprint C — Permissions on goals notify",
        "full",
        "Notify paths respect permission/safety (no yolo inherit later). Intent met.",
    ),
    (
        "V2",
        "V2-D1",
        "Sprint D — OpenRouter refresh schedule",
        "full",
        "models-refresh-openrouter --schedule path. Catalog ops intent met.",
    ),
    (
        "V2",
        "V2-D2",
        "Sprint D — NL profile / yolo directives",
        "full",
        "NL ask can apply profile/plan-only directives; execute_directives tests. Full.",
    ),
    (
        "V2",
        "V2-D3",
        "Sprint D — PATH / which tests",
        "full",
        "path_which tests (which_cmd + Windows). Full.",
    ),
    # =====================================================================
    # V3 — IMPROVEMENT_V3_PLAN.md Sprints A–D
    # =====================================================================
    (
        "V3",
        "V3-A1",
        "Sprint A — Tool protocol (JSON tool_call)",
        "full",
        "tool_protocol extract + run_tool_calls; agent_with_tools mock tests. Full.",
    ),
    (
        "V3",
        "V3-A2",
        "Sprint A — Failover ordered multi-model try",
        "full",
        "ModelCaller failover ordered/bounded/logged. Fail-closed readiness combined. Full.",
    ),
    (
        "V3",
        "V3-A3",
        "Sprint A — Better diff check",
        "full",
        "git_diff_apply check hardened; tests for diff check. Full.",
    ),
    (
        "V3",
        "V3-A4",
        "Sprint A — Contracts on more board APIs",
        "foundation",
        "Contracts expanded (council/compare paths in MoSCoW). Still foundation for "
        "'everywhere public' absolute wording.",
    ),
    (
        "V3",
        "V3-B1",
        "Sprint B — Cost on workers/run",
        "full",
        "cost_router / cost on orchestrator workers; cost_shrink tests. Full for V3 B.",
    ),
    (
        "V3",
        "V3-B2",
        "Sprint B — Tenant write-back everywhere memory",
        "full",
        "write_back + query tags + scope; MoSCoW M4 tests. Full for tenant memory R/W.",
    ),
    (
        "V3",
        "V3-B3",
        "Sprint B — Goals execute safety (caps, no yolo)",
        "full",
        "Goals execute with max caps and safe permission defaults. Full.",
    ),
    (
        "V3",
        "V3-B4",
        "Sprint B — pytest -m unit marker suite",
        "full",
        "Unit marker + suite; pytest -m unit is the offline gate. Full.",
    ),
    (
        "V3",
        "V3-C1",
        "Sprint C — Parallel board (prior + harden)",
        "full",
        "Parallel boards already present; V3 C hardened. Full.",
    ),
    (
        "V3",
        "V3-C2",
        "Sprint C — Vision helpers deepen",
        "full",
        "Vision helpers + live vision path (MoSCoW S2). Full for V3 scope.",
    ),
    (
        "V3",
        "V3-C3",
        "Sprint C — Graph SVG",
        "full",
        "agent-graph SVG UI + API. Full.",
    ),
    (
        "V3",
        "V3-C4",
        "Sprint C — Side-effect audit",
        "full",
        "side_effect_audit records write/delete/run; unit tests. Full.",
    ),
    (
        "V3",
        "V3-D1",
        "Sprint D — Bandit pin from bakeoff/outcomes",
        "foundation",
        "Bandit pin path from bakeoff exists; continuous bandit on every call still "
        "foundation (V6 M050).",
    ),
    (
        "V3",
        "V3-D2",
        "Sprint D — NL hooks expansion",
        "full",
        "NL hooks for goals/bakeoff/agent/profile (MoSCoW S9 tests). Full.",
    ),
    (
        "V3",
        "V3-D3",
        "Sprint D — Unit suite expansion / tests",
        "full",
        "test_improvement_v3 + sprint_abcd + unit marker. Full for verification goal.",
    ),
    # =====================================================================
    # MoSCoW 100 honesty pass (post-V3; same improvement track)
    # =====================================================================
    (
        "MoSCoW",
        "MOS-M1",
        "Must M1 — Model tool protocol",
        "full",
        "tool_protocol + tests (code+tests DoD). Full per MoSCoW policy.",
    ),
    (
        "MoSCoW",
        "MOS-M2",
        "Must M2 — Failover + fail-closed",
        "full",
        "readiness + multi-model try. Full.",
    ),
    (
        "MoSCoW",
        "MOS-M3",
        "Must M3 — Cost on workers",
        "full",
        "cost_router in orchestrator/board. Full for MoSCoW M3 wording.",
    ),
    (
        "MoSCoW",
        "MOS-M4",
        "Must M4 — Tenant R/W everywhere memory",
        "full",
        "write_back + query tags + scope + export/import. Full.",
    ),
    (
        "MoSCoW",
        "MOS-M5",
        "Must M5 — Diff check/apply",
        "full",
        "git_diff_apply check + apply. Full.",
    ),
    (
        "MoSCoW",
        "MOS-M6",
        "Must M6 — Contract on all major public APIs",
        "foundation",
        "council, compare, cli-run, pr_review, web status covered with tests. "
        "Rated foundation not absolute full because 'all major' still excludes "
        "some thin CLI wrappers (honest vs V6 M008).",
    ),
    (
        "MoSCoW",
        "MOS-M7",
        "Must M7 — Goals execute safe",
        "full",
        "caps + no yolo. Full.",
    ),
    (
        "MoSCoW",
        "MOS-M8",
        "Must M8 — pytest -m unit",
        "full",
        "markers + suite green offline. Full.",
    ),
    (
        "MoSCoW",
        "MOS-S1",
        "Should S1 — Token streaming in agent-tui",
        "foundation",
        "token_stream + Live panel exist. Real provider SSE incomplete; fallback "
        "chunking — foundation for 'real streaming' absolute claim.",
    ),
    (
        "MoSCoW",
        "MOS-S2",
        "Should S2 — Live vision call path",
        "full",
        "vision_attachments through ModelCaller + call_with_images. Tested. Full.",
    ),
    (
        "MoSCoW",
        "MOS-S3",
        "Should S3 — Semantic board cache",
        "full",
        "semantic_subject_key + SUPERAI_BOARD_SEMANTIC. Tested. Full.",
    ),
    (
        "MoSCoW",
        "MOS-S4",
        "Should S4 — Worker diversity 1 premium + N cheap",
        "full",
        "diversify_pool / resolve_worker_pool. Tested. Full.",
    ),
    (
        "MoSCoW",
        "MOS-S5",
        "Should S5 — Bakeoff bandit pin",
        "full",
        "Bakeoff pin integrates with bandit path. Full for MoSCoW S5.",
    ),
    (
        "MoSCoW",
        "MOS-S6",
        "Should S6 — Graph SVG UI",
        "full",
        "SVG graph UI. Full.",
    ),
    (
        "MoSCoW",
        "MOS-S7",
        "Should S7 — Shared ask session MCP/TUI",
        "full",
        "Shared session root + MCP superai_ask_session. Tested. Full.",
    ),
    (
        "MoSCoW",
        "MOS-S8",
        "Should S8 — Side-effect audit",
        "full",
        "side_effect_audit. Full.",
    ),
    (
        "MoSCoW",
        "MOS-S9",
        "Should S9 — NL for goals/bakeoff/agent-tui/profile",
        "full",
        "Dedicated NL actions + handlers tested. Full.",
    ),
    (
        "MoSCoW",
        "MOS-S10",
        "Should S10 — Windows path_which tests",
        "full",
        "Expanded Windows extension tests. Full.",
    ),
    (
        "MoSCoW",
        "MOS-N1",
        "Nice N1 — Richer agent TUI (panels, /diff confirm)",
        "full",
        "/panel /diff /stream commands. Full for MoSCoW N1.",
    ),
    (
        "MoSCoW",
        "MOS-N2",
        "Nice N2 — Assistant daemon tick + schedule goals",
        "full",
        "daemon_tick + goals tick CLI. Tested. Full (not a full OS daemon product).",
    ),
    (
        "MoSCoW",
        "MOS-N3",
        "Nice N3 — Worktree subagent runner",
        "full",
        "worktree_subagent + worktree-run CLI. Dry-run tested. Full.",
    ),
    (
        "MoSCoW",
        "MOS-N4",
        "Nice N4 — Bakeoff report file + eval hook",
        "full",
        "Report path + default_eval_hook. Tested. Full.",
    ),
    (
        "MoSCoW",
        "MOS-N5",
        "Nice N5 — Plugin catalog verify-sha default path",
        "full",
        "~/.superai/plugin_sha store. Tested. Full.",
    ),
    (
        "MoSCoW",
        "MOS-N6",
        "Nice N6 — Voice hooks in agent-tui",
        "full",
        "voice_io full: TTS pyttsx3/SAPI/mock, STT mic/file/queue, /listen /speak /voice in "
        "agent_tui + superai_agent TUI, auto-speak replies, superai voice CLI, tests "
        "test_voice_mos_n6.py. MOS-N6 production-usable offline with file/mock backends.",
    ),
    (
        "MoSCoW",
        "MOS-N7",
        "Nice N7 — Team palace export/import by tenant",
        "full",
        "tenant-export / tenant-import. Tested. Full.",
    ),
    (
        "MoSCoW",
        "MOS-N8",
        "Nice N8 — Live multi-vendor smoke",
        "host",
        "smoke_harness never false-passes; live needs keys. Host-gated — not [x] full.",
    ),
    # =====================================================================
    # Not-important polish W1–W8
    # =====================================================================
    (
        "NotImportant",
        "W1",
        "Session export markdown",
        "full",
        "/export + AskSessionStore.export_markdown; test_not_important. Full.",
    ),
    (
        "NotImportant",
        "W2",
        "Session list + resume",
        "full",
        "/sessions /resume. Full.",
    ),
    (
        "NotImportant",
        "W3",
        "Undo last turn",
        "full",
        "/undo removes last turn. Full.",
    ),
    (
        "NotImportant",
        "W4",
        "Cost/token session totals",
        "full",
        "/cost + turn meta aggregation. Full.",
    ),
    (
        "NotImportant",
        "W5",
        "Command palette + aliases",
        "full",
        "tui_commands + /commands. Full for TUI palette (not Ctrl+K app).",
    ),
    (
        "NotImportant",
        "W6",
        "Multi-line paste mode",
        "full",
        "/paste … /end. Full.",
    ),
    (
        "NotImportant",
        "W7",
        "VS Code extension depth",
        "foundation",
        "VS Code extension covers ask/review/members/smoke-preflight. Thin vs full "
        "IDE product — foundation for 'depth' beyond empty stub.",
    ),
    (
        "NotImportant",
        "W8",
        "Smoke preflight checklist",
        "full",
        "smoke_preflight + CLI; no false pass. Full.",
    ),
    (
        "NotImportant",
        "W-SA",
        "SuperAI multi-agent package (superai_agent)",
        "full",
        "core.superai_agent + SUPERAI_AGENT.md; product brand SuperAI (not OpenCode). Full.",
    ),
    # =====================================================================
    # V4 — IMPROVEMENT_V4_PLAN.md
    # =====================================================================
    (
        "V4",
        "V4-M1",
        "M1 — Budget on all spend paths",
        "foundation",
        "budget_guard soft API + spend_guard on agent/boards/council/bakeoff/compare/"
        "HTTP/agent. DoD-strict sweep expanded coverage. Still foundation: not every "
        "thin CLI wrapper (same as V6 M001).",
    ),
    (
        "V4",
        "V4-M2",
        "M2 — Result contract everywhere public",
        "foundation",
        "ensure_contract / ensure_public_result on major paths. Not absolute everywhere.",
    ),
    (
        "V4",
        "V4-M3",
        "M3 — Fail-closed readiness before live agent",
        "full",
        "Live agent refuses if model not ready unless override. Full.",
    ),
    (
        "V4",
        "V4-M4",
        "M4 — Provider stream API path",
        "foundation",
        "ModelCaller.call_stream + agent on_token; empty stream falls back to call(). "
        "Not proven real SSE on all providers.",
    ),
    (
        "V4",
        "V4-M5",
        "M5 — Tool result cache (path+mtime)",
        "full",
        "Read tools cache by path+mtime; unit test. Full for V4 M5.",
    ),
    (
        "V4",
        "V4-M6",
        "M6 — Cheap-first step types",
        "full",
        "task_complexity classifier routes summarize/plan to cheap members. Tested. Full.",
    ),
    (
        "V4",
        "V4-M7",
        "M7 — Unified run trail",
        "full",
        "run_trail id links session + side effects + cost; explain-run later. Full.",
    ),
    (
        "V4",
        "V4-M8",
        "M8 — Safety/money regression suite",
        "full",
        "tests/test_improvement_v4.py covers plan/budget/tenant/stream/local_first. Full.",
    ),
    (
        "V4",
        "V4-S1",
        "S1 — Complexity → member count",
        "full",
        "Shared classifier used by boards. Full.",
    ),
    (
        "V4",
        "V4-S3",
        "S3 — Bandit feedback from runs",
        "foundation",
        "Success/latency/cost can update bandit. Not continuous every-call product.",
    ),
    (
        "V4",
        "V4-S4",
        "S4 — Timeout / partial status",
        "full",
        "Runtime max_seconds → partial contract. Full for V4 S4.",
    ),
    (
        "V4",
        "V4-S5",
        "S5 — Front-door policy map",
        "full",
        "front_door chooses agent vs board vs run; CLI do + interactive wired. Full.",
    ),
    (
        "V4",
        "V4-S6",
        "S6 — Local-first escalate",
        "full",
        "local_first.escalate_chain in ModelCaller + worker pool. Tests. Full.",
    ),
    (
        "V4",
        "V4-S7",
        "S7 — Context pack token budget",
        "full",
        "context_pack ordered drop under budget. Tested. Full.",
    ),
    (
        "V4",
        "V4-S8",
        "S8 — Parallel independent tools",
        "full",
        "Runtime batches read/grep/glob. Full.",
    ),
    (
        "V4",
        "V4-S9",
        "S9 — superai status --cost",
        "full",
        "Snapshot budget + circuits + cache stats. Full.",
    ),
    (
        "V4",
        "V4-S10",
        "S10 — Change-set apply/reject",
        "full",
        "change_set accumulates writes; /apply /reject. Tested. Full.",
    ),
    (
        "V4",
        "V4-DOD-1",
        "DoD-strict — spend_guard on council/bakeoff/compare/HTTP",
        "foundation",
        "Sweep closed major gaps. Still not literal every path — foundation+strong.",
    ),
    (
        "V4",
        "V4-DOD-2",
        "DoD-strict — front door CLI (interactive + do)",
        "full",
        "superai interactive + superai do + NL re-route. Full.",
    ),
    (
        "V4",
        "V4-DOD-3",
        "DoD-strict — stream empty-success fallback",
        "full",
        "Stream falls back to full call() if no chunks — honesty/reliability fix. Full.",
    ),
    # =====================================================================
    # V5 — IMPROVEMENT_V5_PLAN.md
    # =====================================================================
    (
        "V5",
        "V5-M1",
        "M1 — CLI/public spend middleware",
        "foundation",
        "public_api.wrap on key CLI + MCP. Not every Typer command — foundation.",
    ),
    (
        "V5",
        "V5-M2",
        "M2 — MCP spend parity",
        "foundation",
        "superai_run / cli_run budget + contract. MCP surface parity not proven for "
        "every MCP tool — foundation.",
    ),
    (
        "V5",
        "V5-M3",
        "M3 — Cooperative cancel (CancelToken)",
        "foundation",
        "CancelToken in agent runtime; tests. Not all board workers share cancel — "
        "foundation (V6 M017).",
    ),
    (
        "V5",
        "V5-M4",
        "M4 — Accurate cost from registry",
        "foundation",
        "cost_accounting.estimate / from_usage. Some paths still estimate when usage "
        "missing — foundation.",
    ),
    (
        "V5",
        "V5-M5",
        "M5 — Error taxonomy",
        "full",
        "error_code on contracts; taxonomy tests. Full for V5 M5.",
    ),
    (
        "V5",
        "V5-M6",
        "M6 — Idempotent writes",
        "full",
        "Skip write if content unchanged; unit test. Full.",
    ),
    (
        "V5",
        "V5-M7",
        "M7 — Security regression pack",
        "full",
        "test_improvement_v5.py security/money pack. Full for V5 suite intent.",
    ),
    (
        "V5",
        "V5-M8",
        "M8 — Golden offline eval",
        "full",
        "eval_golden + tests (mock). Full offline eval set.",
    ),
    (
        "V5",
        "V5-S1",
        "S1 — Cross-session result cache",
        "full",
        "opt-in result_cache; unit test. Full for V5 S1.",
    ),
    (
        "V5",
        "V5-S2",
        "S2 — Adaptive escalate",
        "full",
        "adaptive_escalate module + agent runtime quality_failed escalate once; unit tested. Intent met for V5 S2.",
    ),
    (
        "V5",
        "V5-S3",
        "S3 — Run explain (explain-run)",
        "full",
        "superai explain-run <run_id> via run_trail. Full.",
    ),
    (
        "V5",
        "V5-S4",
        "S4 — Smarter memory inject cap",
        "full",
        "memory_inject rank + hard token budget helper. Tested. Full.",
    ),
    (
        "V5",
        "V5-S5",
        "S5 — Profile auto-suggest",
        "full",
        "profile_suggest from budget + history stats. Tested. Full.",
    ),
    (
        "V5",
        "V5-S6",
        "S6 — Front-door confidence",
        "full",
        "Low confidence flag + optional confirm. Tested. Full.",
    ),
    (
        "V5",
        "V5-S7",
        "S7 — Board early-exit consensus",
        "full",
        "Stop when first opinions agree (cost save). Full for V5 S7.",
    ),
    (
        "V5",
        "V5-S10",
        "S10 — Progress snapshot",
        "full",
        "superai progress recent bus/trail. Full.",
    ),
]



def main() -> None:
    assert ITEMS, "no items"
    ids = [i[1] for i in ITEMS]
    assert len(ids) == len(set(ids)), "duplicate ids"

    c = Counter(st for *_, st, _ in ITEMS)
    by_track: dict[str, list[Item]] = {}
    for item in ITEMS:
        by_track.setdefault(item[0], []).append(item)

    track_order = ["V1", "V1-P8", "V2", "V3", "MoSCoW", "NotImportant", "V4", "V5"]
    track_titles = {
        "V1": "V1 — Improvement Plan (Phases 0–7 + Phase 99)",
        "V1-P8": "V1 Phase 8 — Nice-to-have (N1–N8)",
        "V2": "V2 — Sprints A–D",
        "V3": "V3 — Sprints A–D",
        "MoSCoW": "MoSCoW 100% honesty pass (post-V3)",
        "NotImportant": "Not-important polish (W1–W8 + superai_agent)",
        "V4": "V4 — Trust / efficiency / front door / change-set",
        "V5": "V5 — Operational maturity",
    }
    track_sources = {
        "V1": "`docs/IMPROVEMENT_PLAN.md`",
        "V1-P8": "`docs/PHASE8_PLAN.md`",
        "V2": "`docs/IMPROVEMENT_V2_PLAN.md`",
        "V3": "`docs/IMPROVEMENT_V3_PLAN.md`",
        "MoSCoW": "`docs/MOSCOW_100_PLAN.md`",
        "NotImportant": "`docs/NOT_IMPORTANT_PLAN.md`",
        "V4": "`docs/IMPROVEMENT_V4_PLAN.md`",
        "V5": "`docs/IMPROVEMENT_V5_PLAN.md`",
    }

    lines: list[str] = [
        "# SuperAI Improvement V1–V5 — Detailed scorecard",
        "",
        "**Generated:** 2026-07-16  ",
        f"**Total items:** {len(ITEMS)}  ",
        "**Purpose:** Honest status **and reasoning** per improvement item for V1 through V5 "
        "(plus MoSCoW honesty pass and not-important polish that sat on the same track).  ",
        "",
        "Companion to `docs/V6_SCORECARD.md` (400-item V6 backlog).",
        "",
        "Each item lists:",
        "",
        "1. **ID** (stable for this scorecard)",
        "2. **Title** (plan wording)",
        "3. **Status** (classification)",
        "4. **Why** (evidence + gap that justified the status)",
        "",
        "## Status legend",
        "",
        "| Status | Meaning | When we use it |",
        "|--------|---------|----------------|",
        "| **full** | Production-usable for the stated plan intent | Code + tests (or equivalent) cover DoD |",
        "| **foundation** | Real working code; DoD depth incomplete | Core mechanism exists; missing universality/UX/hardening |",
        "| **stub** | Surface/flag/sample only | Placeholder only |",
        "| **host** | Code path exists; needs keys/environment | Live proof requires credentials |",
        "| **refuse** | Intentionally refuse-closed | Safety policy blocks shipping |",
        "| **absent** | No meaningful implementation | Zero or near-zero code |",
        "",
        "## How this relates to plan checklists",
        "",
        "Older plans often mark items `[x]` or “100% sprint complete” after a **vertical slice**. "
        "This scorecard uses the same honesty bar as V6:",
        "",
        "- **full** ≈ checklist `[x]` with real depth for that plan’s DoD",
        "- **foundation** ≈ real code that later tracks still deepen (not a lie, not “finished forever”)",
        "- **host** ≈ never claim live multi-provider success without keys",
        "",
        "## Overall summary",
        "",
        "| Status | Count | % |",
        "|--------|------:|--:|",
    ]
    for k in ["full", "foundation", "stub", "host", "refuse", "absent"]:
        n = c.get(k, 0)
        if n or k in ("full", "foundation", "host"):
            pct = 100 * n / len(ITEMS)
            lines.append(f"| {k} | {n} | {pct:.1f}% |")
    lines.append(f"| **total** | **{len(ITEMS)}** | **100%** |")
    lines += [
        "",
        f"- **full + foundation** ≈ **{c.get('full', 0) + c.get('foundation', 0)}** items have real code value.",
        f"- **host** = **{c.get('host', 0)}** (live smoke proof).",
        "",
        "**Honest headline:** V1–V5 delivered the **orchestrator + agent + multi-CLI + cost/safety "
        "spine**. Most Must/Should items are **full** or **foundation**. Remaining gaps are "
        "universality (budget/contract on *every* path), true streaming, bandit continuity, "
        "and **host-gated live smoke** — not “nothing was built.”",
        "",
        "### Counts by track",
        "",
        "| Track | Items | full | foundation | host | other |",
        "|-------|------:|-----:|-----------:|-----:|------:|",
    ]
    for tr in track_order:
        group = by_track.get(tr, [])
        if not group:
            continue
        cc = Counter(st for *_, st, _ in group)
        other = sum(cc[k] for k in cc if k not in ("full", "foundation", "host"))
        lines.append(
            f"| {tr} | {len(group)} | {cc.get('full', 0)} | {cc.get('foundation', 0)} | "
            f"{cc.get('host', 0)} | {other} |"
        )
    lines += ["", "### Quick index (status only)", ""]

    for tr in track_order:
        group = by_track.get(tr, [])
        if not group:
            continue
        lines += [
            f"#### {track_titles[tr]}",
            "",
            f"Source: {track_sources[tr]}",
            "",
            "| ID | Status | Title |",
            "|----|--------|-------|",
        ]
        for _, iid, title, st, _ in group:
            t = title if len(title) <= 64 else title[:61] + "..."
            lines.append(f"| {iid} | **{st}** | {t} |")
        lines.append("")

    lines += ["---", "", "# Detailed assessments (every item)", ""]

    for tr in track_order:
        group = by_track.get(tr, [])
        if not group:
            continue
        lines += [
            f"## {track_titles[tr]}",
            "",
            f"Source plan: {track_sources[tr]}",
            "",
        ]
        for _, iid, title, st, why in group:
            lines += [
                f"### {iid} — {title}",
                "",
                f"- **Status:** `{st}`",
                f"- **Why:** {why}",
                "",
            ]

        # track rollup
        cc = Counter(st for *_, st, _ in group)
        lines += ["#### Track rollup", "", "| Status | Count |", "|--------|------:|"]
        for k in ["full", "foundation", "stub", "host", "refuse", "absent"]:
            if cc.get(k):
                lines.append(f"| {k} | {cc[k]} |")
        lines.append("")

    lines += [
        "## Decision method",
        "",
        "1. Read each plan’s DoD / item wording.",
        "2. Map to modules under `src/core/` and CLI in `src/cli/main.py`.",
        "3. Prefer unit tests (`test_improvement_v*`, `test_moscow_100`, `test_sprint_abcd`, "
        "`test_phase8`, `test_not_important`) as evidence.",
        "4. Downgrade to **foundation** when later V6 audit still shows incomplete universality.",
        "5. Keep **host** for live multi-provider smoke — never false-claim.",
        "",
        "Regenerate: `python scripts/gen_v1_v5_scorecard.py`",
        "",
        "## Related",
        "",
        "- V6 scorecard: `docs/V6_SCORECARD.md`",
        "- V6 backlog: `docs/IMPROVEMENT_V6_BACKLOG.md`",
        "- Pending: `docs/PENDING_WORK.md`",
        "",
    ]

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print("total", len(ITEMS))
    print("COUNTS", dict(sorted(c.items())))
    for tr in track_order:
        group = by_track.get(tr, [])
        if group:
            cc = Counter(st for *_, st, _ in group)
            print(tr, len(group), dict(cc))


if __name__ == "__main__":
    main()
