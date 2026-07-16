"""Generate docs/V6_SCORECARD.md — honest per-ID audit with titles + why."""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKLOG = ROOT / "docs" / "IMPROVEMENT_V6_BACKLOG.md"
OUT = ROOT / "docs" / "V6_SCORECARD.md"

# Status: full | foundation | stub | host | refuse | absent
# Each entry: (status, why) — why explains classification against backlog intent.


def load_titles() -> dict[str, str]:
    text = BACKLOG.read_text(encoding="utf-8")
    rows = re.findall(r"^\| ((?:M|S|N|P)\d{3}) \| ([^|]+) \|", text, re.M)
    return {i: t.strip() for i, t in rows}


# ---------------------------------------------------------------------------
# MUST M001–M100
# ---------------------------------------------------------------------------
M: dict[int, tuple[str, str]] = {
    1: (
        "foundation",
        "spend_guard / can_spend / enforce_or_block exist and are wired on agent, "
        "major boards, and several CLI spend paths, with unit coverage. Not rated full "
        "because the literal backlog says *every* path (every CLI subcommand, every MCP "
        "tool, every HTTP route) and a few thin wrappers still call models without the "
        "same hard ceiling.",
    ),
    2: (
        "foundation",
        "cost_accounting + registry rates feed ModelCaller and status/--cost. "
        "Rated foundation not full because some board/CLI paths still use estimates or "
        "token placeholders when providers omit usage metadata.",
    ),
    3: (
        "foundation",
        "cost_router and budget shrink boards before heavy multi-member work. "
        "Not full: there is no dedicated user-facing preflight UX that always shows "
        "estimated $ before launching every board.",
    ),
    4: (
        "full",
        "permission_mode plan and dry-run tool paths block disk/git mutation; "
        "tests cover plan-mode safety. Matches backlog intent.",
    ),
    5: (
        "full",
        "plan|ask|auto|yolo implemented with safe defaults; agent and CLI honor modes. "
        "Backlog permission model is met.",
    ),
    6: (
        "full",
        "Workspace jail on agent_tools and external CLI workers is fail-closed with tests. "
        "Matches jail requirement.",
    ),
    7: (
        "full",
        "side_effect_audit + run_trail record write/delete/run with run_id. "
        "Audit path is production-usable.",
    ),
    8: (
        "foundation",
        "result_contract shapes major APIs (agent, boards, public_api). Not full: "
        "not every Typer command returns the same stable contract envelope.",
    ),
    9: (
        "full",
        "error_codes taxonomy (budget, readiness, timeout, …) is defined and used on "
        "core failure paths; scripts can key off codes.",
    ),
    10: (
        "full",
        "readiness checks + agent live gate block live calls when providers are unready. "
        "Meets pre-call readiness intent.",
    ),
    11: (
        "full",
        "model_caller failover is ordered, bounded, and logged; local_first integrates. "
        "Meets failover backlog.",
    ),
    12: (
        "foundation",
        "Redaction patterns strip common secrets from logs/errors. Not full: no formal "
        "whole-surface secret scanner on every TUI/log sink.",
    ),
    13: (
        "full",
        "keyring_store + secrets CLI list/rotate paths exist and are tested. "
        "Secret store requirement met.",
    ),
    14: (
        "full",
        "net_safety SSRF guards on URL/fetch tools; unit tests cover private ranges. "
        "Meets SSRF item.",
    ),
    15: (
        "foundation",
        "Tool protocol + permission modes reduce injection blast radius. Not full: "
        "no dedicated prompt-injection classifier/guardrail product on tool loops.",
    ),
    16: (
        "full",
        "palace_tenant tags isolate shared memory by tenant; export/import honor tags. "
        "Isolation intent met.",
    ),
    17: (
        "foundation",
        "CancelToken stops agent loops cooperatively. Not full: not all multi-CLI board "
        "workers share the same cooperative cancel path.",
    ),
    18: (
        "foundation",
        "tool_timeouts module + subprocess timeouts exist. Not full: not every model/CLI "
        "path is guaranteed to honor one universal timeout policy.",
    ),
    19: (
        "full",
        "explain-run reconstructs trail from run_id via run_trail. Reproducibility intent met.",
    ),
    20: (
        "full",
        "Mock mode + smoke harness never mark live_passed without real calls. "
        "Honesty requirement met and tested.",
    ),
    21: (
        "full",
        "superai_agent sessions: resume/export paths + ask_session; multi-turn store works. "
        "Core session reliability met.",
    ),
    22: (
        "full",
        "tool_protocol with JSON-schema tools enforced in agent runtime. Strict protocol met.",
    ),
    23: (
        "full",
        "Runtime runs independent read/grep/glob tools in parallel. Efficiency intent met.",
    ),
    24: (
        "full",
        "tool_write is content-aware/idempotent for same content. Write safety met.",
    ),
    25: (
        "full",
        "change_set staging with /apply and /reject in agent TUI/runtime. Staging intent met.",
    ),
    26: (
        "full",
        "git_diff_apply check validates unified diffs before apply. Diff-check intent met.",
    ),
    27: (
        "foundation",
        "call_stream exists with fallback chunking when providers lack true SSE. "
        "Not full: not every provider path is proven real token streaming.",
    ),
    28: (
        "full",
        "context_pack packs under hard token budget for agent context. Packing intent met.",
    ),
    29: (
        "foundation",
        "session_compact exists; agent_todos hold tasks separately. Not full: compaction "
        "does not always preserve full decision/todo graph as a single first-class product.",
    ),
    30: (
        "full",
        "build/plan/ask roles with different tool/permission boundaries. Roles intent met.",
    ),
    31: (
        "full",
        "front_door + superai do + interactive route agent vs board vs orchestrator. "
        "Front-door routing met.",
    ),
    32: (
        "full",
        "front_door confidence / needs_confirm when routing is ambiguous. Ambiguity UX met.",
    ),
    33: (
        "full",
        "local_first tries local models then escalates on failure. Cost/flexibility intent met.",
    ),
    34: (
        "full",
        "task_complexity drives cheap-first for summarize/plan steps. Cheap-first intent met.",
    ),
    35: (
        "full",
        "smart_max_members ties complexity to board size. Member-count control met.",
    ),
    36: (
        "full",
        "Boards early-exit on strong consensus to save cost. Early-exit intent met.",
    ),
    37: (
        "full",
        "diversify_pool prefers 1 premium + N cheap workers. Diversity intent met.",
    ),
    38: (
        "full",
        "worktree_subagent isolates risky writes in git worktrees. Isolation intent met.",
    ),
    39: (
        "full",
        "tdd_loop + quality_gates support red/green first-class flows. TDD intent met.",
    ),
    40: (
        "full",
        "pr_review + multi_cli advisory with contracts. PR/diff review intent met.",
    ),
    41: (
        "full",
        "models-register accepts OpenAI-compatible endpoints. Universal registration met.",
    ),
    42: (
        "full",
        "Ollama / LM Studio / vLLM appear in provider_catalog and selection. Local first-class met.",
    ),
    43: (
        "full",
        "path_which + external_cli discovery, Windows-hardened. CLI discovery met.",
    ),
    44: (
        "full",
        "cli_models and name@model selection for external CLIs. Inner-model selection met.",
    ),
    45: (
        "full",
        "member_selection unifies API + CLI + local catalog. Unified catalog met.",
    ),
    46: (
        "full",
        "members --available / live probe of catalog members. Live availability met.",
    ),
    47: (
        "full",
        "provider_health circuits open/close on failures. Health-circuit intent met.",
    ),
    48: (
        "full",
        "rate_queue implements backoff/queue under limits. Rate-limit intent met.",
    ),
    49: (
        "full",
        "model_blacklist after repeated failures. Blacklist intent met.",
    ),
    50: (
        "foundation",
        "bandit_router learns from outcomes where wired. Not full: not continuously applied "
        "on every single model call as default routing.",
    ),
    51: (
        "full",
        "bakeoff produces report and can pin winner. Bakeoff intent met.",
    ),
    52: (
        "full",
        "compare command returns result contract. Compare intent met.",
    ),
    53: (
        "full",
        "council with voting modes implemented. Council intent met.",
    ),
    54: (
        "full",
        "multi_cli_advisory runs parallel opinions and merges. Parallel multi-CLI intent met.",
    ),
    55: (
        "full",
        "cost_router shrinks boards under budget. Cost shrink intent met.",
    ),
    56: (
        "full",
        "central_memory / memory inject before major runs. Palace inject intent met.",
    ),
    57: (
        "full",
        "write_back of successful outcomes into palace. Write-back intent met.",
    ),
    58: (
        "full",
        "semantic query with tenant tags. Search + isolation intent met.",
    ),
    59: (
        "full",
        "memory_inject ranks and token-caps packed memories. Smart inject intent met.",
    ),
    60: (
        "full",
        "memory-forget / TTL / GDPR-style erase paths exist. Forget/TTL intent met.",
    ),
    61: (
        "foundation",
        "learning_engine can promote durable patterns. Not full: promotion is not a "
        "hardened always-on product with strong promotion policy UX.",
    ),
    62: (
        "foundation",
        "Conflict-handling paths exist in learning/memory stack. Not full: no polished "
        "conflict-resolution UI/product flow for contradictory memories.",
    ),
    63: (
        "foundation",
        "distill/deprecate helpers exist for redundant memories. Not full: not a complete "
        "automatic lifecycle product with metrics/dashboards.",
    ),
    64: (
        "full",
        "wings/rooms navigation in Memory Palace. Navigation intent met.",
    ),
    65: (
        "full",
        "backup_manager supports encrypted local SuperAI state backup. Backup intent met.",
    ),
    66: (
        "full",
        "profile-bundle export/import. Profile portability intent met.",
    ),
    67: (
        "foundation",
        "Run history / runs exist and explain-run works. Not full: rich searchable "
        "history by task+cost+model is only partial.",
    ),
    68: (
        "foundation",
        "preferences module can bias routing. Not full: preference → routing loop is not "
        "deeply proven across all modes.",
    ),
    69: (
        "full",
        "skills library for reusable playbooks. Skills intent met.",
    ),
    70: (
        "full",
        "skill_permissions gate what skills may touch. Permission intent met.",
    ),
    71: (
        "full",
        "Zero-subcommand / default superai launches useful front door. UX intent met.",
    ),
    72: (
        "full",
        "superai do \"…\" one-shot routing works. One-shot intent met.",
    ),
    73: (
        "full",
        "doctor diagnoses readiness/config failures with actionable output. Doctor intent met.",
    ),
    74: (
        "full",
        "status --cost surfaces spend/health/cache-related info. Status intent met.",
    ),
    75: (
        "full",
        "install wizard (Windows-first) for onboard. Install intent met.",
    ),
    76: (
        "full",
        "host-tools check/install matrix for external CLIs. Host-tools intent met.",
    ),
    77: (
        "full",
        "superai_agent TUI shows tools/cost/permission live. Rich TUI intent met.",
    ),
    78: (
        "full",
        "Slash command palette (/commands help) in agent TUI. Palette intent met.",
    ),
    79: (
        "foundation",
        "JSON output on many automation-facing commands. Not full: not every Typer command "
        "supports a uniform --json automation mode.",
    ),
    80: (
        "foundation",
        "exit_codes module defines trustworthy codes. Not full: not all process exits "
        "are wired through the taxonomy consistently.",
    ),
    81: (
        "foundation",
        "Typer --help exists on commands. Not full: examples/quality are uneven across "
        "the large command surface.",
    ),
    82: (
        "foundation",
        "Typer shell completion is enabled. Not full: completion quality not validated "
        "as best-in-class for all nested commands.",
    ),
    83: (
        "full",
        "config get/set with validation paths. Config intent met.",
    ),
    84: (
        "full",
        "version / update check paths. Version intent met.",
    ),
    85: (
        "full",
        "diagnostics zip for support bundles. Diagnostics intent met.",
    ),
    86: (
        "full",
        "Unit suites (v4/v5/v6 safety/money) cover plan, budget, jail. Safety suite intent met.",
    ),
    87: (
        "full",
        "eval_golden offline set exists and is runnable. Golden eval intent met.",
    ),
    88: (
        "full",
        "smoke_harness never false-passes live. Honesty harness intent met.",
    ),
    89: (
        "host",
        "live_smoke_complete code path + phase6-smoke --allow-live exist, but live_passed "
        "requires host API keys/environment. Code is done; claim of live multi-provider "
        "proof is host-gated — not a code gap, not a free full claim.",
    ),
    90: (
        "foundation",
        "Contract tests cover major paths. Not full: not a systematic top-30 command "
        "contract suite as literally specified.",
    ),
    91: (
        "stub",
        "No formal cold-start performance budget enforced in CI. Only ad hoc timing "
        "awareness; backlog 'performance budgets' not productized.",
    ),
    92: (
        "foundation",
        "Deterministic mock fixtures used in unit/CI tests. Not full: fixture library "
        "is not a complete multi-provider mock matrix product.",
    ),
    93: (
        "foundation",
        "MCP superai_run path applies budget/contract safety. Not full: not every MCP "
        "surface has proven CLI-parity for all safety rules.",
    ),
    94: (
        "foundation",
        "Web token auth is optional for non-loopback. Not full: enterprise-grade auth "
        "posture is incomplete (no full SSO/RBAC web product).",
    ),
    95: (
        "full",
        "agent-graph SVG/graph of runs with models/tools/cost. Graph intent met.",
    ),
    96: (
        "full",
        "goals + schedule with caps; no yolo inherit by default. Goals safety intent met.",
    ),
    97: (
        "full",
        "Plugin install path with sha256 verify. Plugin integrity intent met.",
    ),
    98: (
        "full",
        "constitution + policy hooks for org rules. Policy intent met.",
    ),
    99: (
        "foundation",
        "Architecture/quickstart docs exist. Not full: dedicated threat-model doc is "
        "partial, not a complete formal threat model package.",
    ),
    100: (
        "foundation",
        "Mock vs live flags and honesty on smoke/dashboard pieces. Not full: every "
        "dashboard surface does not uniformly label mock vs live.",
    ),
}

# ---------------------------------------------------------------------------
# SHOULD S101–S200
# ---------------------------------------------------------------------------
S: dict[int, tuple[str, str]] = {
    101: (
        "full",
        "agent_todos module + CLI todos track long-task lists. Matches agent todo intent.",
    ),
    102: (
        "full",
        "spec_mode supports plan → approve → implement flow. Spec-first intent met.",
    ),
    103: (
        "foundation",
        "plan vs build roles approximate architecture vs implementation. Not full: "
        "no dedicated architecture-mode flag/product distinct from plan.",
    ),
    104: (
        "stub",
        "No dedicated self-critique module that always re-checks before 'done'. "
        "Role debate/plan can approximate, but not a first-class critique pass.",
    ),
    105: (
        "foundation",
        "quality_gates can run pytest after edits. Not full: auto test *discovery* "
        "is not a complete product that always finds and runs the right suite.",
    ),
    106: (
        "foundation",
        "ruff optional in quality_gates. Not full: lint/typecheck not systematically "
        "integrated post-edit for all languages.",
    ),
    107: (
        "full",
        "workspace_index builds a repo map for large trees. Index intent met.",
    ),
    108: (
        "stub",
        "No real symbol index / LSP go-to-definition product. Grep/workspace_index only.",
    ),
    109: (
        "foundation",
        "ci_why + do path can triage CI failure logs. Not full: not a turnkey "
        "paste-log-and-auto-PR fix product.",
    ),
    110: (
        "foundation",
        "pr_review produces findings. Not full: file-level explain depth varies; "
        "not a complete PR review product rivaling specialist tools.",
    ),
    111: (
        "stub",
        "No safe multi-file rename engine with symbol awareness. Agents can edit files "
        "but there is no dedicated rename-safety product.",
    ),
    112: (
        "stub",
        "No dedicated dependency upgrade assistant product (changelog, lockfile, CI).",
    ),
    113: (
        "stub",
        "No migration dry-run product for DB/schema changes.",
    ),
    114: (
        "foundation",
        "Security patterns/redaction/net safety exist. Not full: not a full SCA/vuln "
        "scan product with dependency CVE database.",
    ),
    115: (
        "stub",
        "No license/compliance checker on new dependencies.",
    ),
    116: (
        "foundation",
        "git-helper assists commits/branches. Not full: not a complete branch-naming "
        "policy product with org templates.",
    ),
    117: (
        "stub",
        "No merge conflict solver product; users resolve conflicts outside SuperAI.",
    ),
    118: (
        "full",
        "git_diff_apply unified patch format with check/apply. Patch format intent met.",
    ),
    119: (
        "foundation",
        "Multimodal vision path exists for images. Not full: not a polished UI-bug "
        "screenshot workflow product end-to-end.",
    ),
    120: (
        "stub",
        "No PDF/doc attach pipeline for requirements ingestion as a product feature.",
    ),
    121: (
        "foundation",
        "browser_tool with optional Playwright. Not full: optional dep; not always-on "
        "browser automation product.",
    ),
    122: (
        "full",
        "notebook_runner executes notebooks. Notebook intent met.",
    ),
    123: (
        "foundation",
        "databao SQL path exists; allowlisting partial. Not full: not hardened "
        "SQL assistant product for all DBs.",
    ),
    124: (
        "foundation",
        "ci_why log triage helps CI. Same as S109 depth — useful foundation, not complete product.",
    ),
    125: (
        "full",
        "Session resume works in superai_agent. Resume intent met.",
    ),
    126: (
        "full",
        "result_cache opt-in for repeated work. Cache intent met.",
    ),
    127: (
        "stub",
        "No provider prompt-cache integration (Anthropic/OpenAI prompt caching APIs).",
    ),
    128: (
        "foundation",
        "local-then-escalate pattern exists (local_first). Not full: not a complete "
        "efficiency program across every task type.",
    ),
    129: (
        "stub",
        "No mid-task demotion controller that downgrades models mid-run systematically.",
    ),
    130: (
        "foundation",
        "Adaptive escalate on weak answers exists in routing paths. Not full: not a "
        "universal quality-score escalate product.",
    ),
    131: (
        "foundation",
        "Budget config per run exists. Not full: weak multi-project budget policy store.",
    ),
    132: (
        "stub",
        "No per-command budget map (command → $ ceiling table) as a product.",
    ),
    133: (
        "foundation",
        "cost_forecast module estimates spend. Not full: forecasting not productized "
        "across all board types with UI.",
    ),
    134: (
        "foundation",
        "Budget snapshot available. Not full: weak weekly spend report product.",
    ),
    135: (
        "foundation",
        "status --cost includes cache-related counts. Partial cost transparency.",
    ),
    136: (
        "stub",
        "No token waterfall UI (prompt/tools/memory/output breakdown visualization).",
    ),
    137: (
        "stub",
        "No stagger scheduler for rate-limited multi-job queues as a product.",
    ),
    138: (
        "foundation",
        "front_door + cheap-first cover simple routing efficiency. Not a complete "
        "cost-optimizer product for all modes.",
    ),
    139: (
        "stub",
        "No systematic tool-output compressor before re-injection into context.",
    ),
    140: (
        "foundation",
        "Read mtime cache reduces re-reads. Not full: not a complete FS cache product.",
    ),
    141: (
        "stub",
        "No dedicated embedding cache layer product.",
    ),
    142: (
        "stub",
        "No batch embed API for bulk memory indexing.",
    ),
    143: (
        "foundation",
        "Lazy imports used ad hoc in heavy modules. Not a formal cold-start program.",
    ),
    144: (
        "stub",
        "No cold-start optimization program with budgets/metrics (related to M091).",
    ),
    145: (
        "stub",
        "No model warmup daemon.",
    ),
    146: (
        "stub",
        "No history-based learner for max_members from past outcomes.",
    ),
    147: (
        "foundation",
        "CancelToken cancels agent work. Depth same as M017 — agent strong, boards partial.",
    ),
    148: (
        "stub",
        "Stream cancel incomplete — cannot always abort mid-token stream cleanly everywhere.",
    ),
    149: (
        "foundation",
        "Profiles can sticky-prefer cheap models via config. Not full productization.",
    ),
    150: (
        "foundation",
        "ab_routing module exists for experiments. Not full continuous A/B product.",
    ),
    151: (
        "full",
        "models-refresh-openrouter refreshes catalog. OpenRouter refresh intent met.",
    ),
    152: (
        "full",
        "capability_tags tag models (local, vision, …). Capability tagging intent met.",
    ),
    153: (
        "stub",
        "No hard per-model context-window enforcement that always truncates/rejects "
        "oversize prompts per registry window.",
    ),
    154: (
        "foundation",
        "tool_protocol JSON tools exist. Depth shared with M022; advanced schema retry "
        "not complete (see S155).",
    ),
    155: (
        "foundation",
        "validate-json helpers exist. Not full: no full schema-repair retry loop product.",
    ),
    156: (
        "foundation",
        "Native Anthropic/Google callers partial via OpenAI-compat and some paths. "
        "Not full first-class native SDKs for all features.",
    ),
    157: (
        "full",
        "path_which Windows-hardened discovery. Windows path intent met.",
    ),
    158: (
        "stub",
        "No dedicated WSL bridge product for CLI/agent.",
    ),
    159: (
        "foundation",
        "container_sandbox flag exists. Not full: not a complete sandbox product.",
    ),
    160: (
        "foundation",
        "net_safety public-only SSRF posture. Foundation shared with M014.",
    ),
    161: (
        "full",
        "tool_timeouts module + CLI timeouts command. Timeout config intent met for tools.",
    ),
    162: (
        "stub",
        "No global concurrency governor across all SuperAI jobs.",
    ),
    163: (
        "stub",
        "No interactive-vs-batch queue split product.",
    ),
    164: (
        "foundation",
        "model_pinning exists (bakeoff pin / config). Not full team policy store.",
    ),
    165: (
        "stub",
        "No team shared policy store for multi-user org settings.",
    ),
    166: (
        "foundation",
        "doctor/readiness messages help ops. Not a full ops runbook product.",
    ),
    167: (
        "stub",
        "No GPU detect for local model routing.",
    ),
    168: (
        "foundation",
        "OpenRouter catalog integration exists. Not 'perfect every model' (parked elsewhere).",
    ),
    169: (
        "foundation",
        "NVIDIA models appear in catalog (NIM path). Not full NIM product suite.",
    ),
    170: (
        "stub",
        "No multi-API-key rotation product.",
    ),
    171: (
        "full",
        "project_memory stores project-scoped notes. Project memory intent met.",
    ),
    172: (
        "stub",
        "No memory confidence scores UI.",
    ),
    173: (
        "stub",
        "No confirm-before-memory-write gate as a product UX.",
    ),
    174: (
        "foundation",
        "memory-palace search CLI exists; not a full Memory Palace TUI browser.",
    ),
    175: (
        "stub",
        "No injection-citations UI showing which memories were injected.",
    ),
    176: (
        "stub",
        "No conflict UI for contradictory memories (see M062 foundation).",
    ),
    177: (
        "full",
        "tenant-export/import CLI for tenant data. Portability intent met.",
    ),
    178: (
        "stub",
        "No org skills registry service (multi-user shared skills server).",
    ),
    179: (
        "foundation",
        "recipes act as templates/playbooks. Not a full marketplace of recipes.",
    ),
    180: (
        "foundation",
        "msg-inbound for messengers exists partially. Not full multi-channel product.",
    ),
    181: (
        "foundation",
        "goals can notify. Not full notification product across channels.",
    ),
    182: (
        "stub",
        "RBAC is enterprise_stubs only — not real multi-role enforcement product.",
    ),
    183: (
        "foundation",
        "Audit log export partial via trails/diagnostics. Not full SIEM-grade export product.",
    ),
    184: (
        "foundation",
        "memory-ttl exists (related M060). Foundation for retention policies.",
    ),
    185: (
        "foundation",
        "Encrypted backup exists; session encryption partial. Not full encryption product.",
    ),
    186: (
        "foundation",
        "Web app exposes memory/status pieces. Not a full session browser product.",
    ),
    187: (
        "stub",
        "No SSE progress stream product for web/CLI progress events.",
    ),
    188: (
        "foundation",
        "VS Code extension is thin/minimal. Not a full IDE extension product.",
    ),
    189: (
        "absent",
        "No JetBrains plugin in repo.",
    ),
    190: (
        "foundation",
        "PWA static shell exists. Not a full offline PWA product.",
    ),
    191: (
        "stub",
        "Seasonal theme only as parked flag — not a real theming product (also vanity).",
    ),
    192: (
        "absent",
        "No user keybind configuration system.",
    ),
    193: (
        "foundation",
        "Paste mode in agent TUI helps large pastes. Not full clipboard integration.",
    ),
    194: (
        "stub",
        "No rich clipboard API (images/files) product.",
    ),
    195: (
        "foundation",
        "init/onboard paths exist (install/onboard). Not as complete as onboard quest alone implies.",
    ),
    196: (
        "full",
        "recipes CLI/templates for common workflows. Recipes intent met.",
    ),
    197: (
        "foundation",
        "explain-run + agent-graph give partial run visualization. Not full mermaid "
        "everywhere product.",
    ),
    198: (
        "full",
        "profile-suggest recommends profiles. Suggest intent met.",
    ),
    199: (
        "full",
        "onboard quest guides first-run. Onboarding quest intent met.",
    ),
    200: (
        "full",
        "whats-new / changelog_cli surfaces releases. Whats-new intent met.",
    ),
}

# ---------------------------------------------------------------------------
# NICE N201–N300
# ---------------------------------------------------------------------------
N: dict[int, tuple[str, str]] = {
    201: (
        "stub",
        "No Ctrl+K fuzzy command palette app. Slash /commands is not a full Ctrl+K palette.",
    ),
    202: (
        "foundation",
        "NL do/ask routes many intents. Not full: no guaranteed preview-for-any-command product.",
    ),
    203: (
        "full",
        "macros CLI for command aliases/macros. Macro intent met.",
    ),
    204: (
        "stub",
        "No pipeline operator chaining SuperAI modes as a shell product.",
    ),
    205: (
        "foundation",
        "watch_mode polls limited paths. Not a full robust file-watch product.",
    ),
    206: (
        "foundation",
        "goals/schedule exist; not a full always-on daemon product.",
    ),
    207: (
        "stub",
        "No SSH remote headless agent product.",
    ),
    208: (
        "stub",
        "No tmux-like multiplexed sessions product.",
    ),
    209: (
        "foundation",
        "TUI panels are partial (single rich TUI). Not full split-pane product.",
    ),
    210: (
        "absent",
        "No vim keybindings mode in TUI.",
    ),
    211: (
        "absent",
        "No mouse support mode in TUI.",
    ),
    212: (
        "stub",
        "Vision can use files; clipboard image paste not productized.",
    ),
    213: (
        "foundation",
        "voice_io optional module. Not full voice channel product.",
    ),
    214: (
        "foundation",
        "i18n module partial strings. Not full CLI/TUI internationalization.",
    ),
    215: (
        "absent",
        "No screen-reader / a11y TUI audit or mode.",
    ),
    216: (
        "stub",
        "Colorblind palettes only as theme flag surface — not real a11y palettes.",
    ),
    217: (
        "stub",
        "High-contrast only as theme flag surface — not real high-contrast theme pack.",
    ),
    218: (
        "stub",
        "No full demo replay tape product.",
    ),
    219: (
        "foundation",
        "Session export to markdown exists. Not full publish workflow product.",
    ),
    220: (
        "stub",
        "No shareable sanitized run bundle product.",
    ),
    221: (
        "foundation",
        "eval_golden is a private/offline harness. Not a public benchmark product.",
    ),
    222: (
        "stub",
        "No private model leaderboard on your repo product.",
    ),
    223: (
        "stub",
        "No YAML custom-agents DSL parser product.",
    ),
    224: (
        "foundation",
        "plugin-catalog exists. Not full marketplace UX.",
    ),
    225: (
        "foundation",
        "sha256 verify on plugins (M097). Signed plugins beyond hash not complete.",
    ),
    226: (
        "stub",
        "No skill versioning product.",
    ),
    227: (
        "full",
        "hooks pre/post tool hooks implemented. Hooks intent met.",
    ),
    228: (
        "foundation",
        "Simple policy module exists. Not full policy-as-code language product.",
    ),
    229: (
        "stub",
        "sso_status only — no real enterprise SSO integration.",
    ),
    230: (
        "absent",
        "No SCIM provisioning.",
    ),
    231: (
        "foundation",
        "lsp_bridge is compile/check stub-level. Not real LSP diagnostics product.",
    ),
    232: (
        "absent",
        "No go-to-definition via LSP.",
    ),
    233: (
        "absent",
        "No rename-symbol across project via LSP.",
    ),
    234: (
        "absent",
        "No extract-method assist product.",
    ),
    235: (
        "absent",
        "No dead-code detection tool product.",
    ),
    236: (
        "absent",
        "No complexity hotspots map product.",
    ),
    237: (
        "stub",
        "tdd_loop only — not coverage-guided test generation product.",
    ),
    238: (
        "absent",
        "No mutation testing integration.",
    ),
    239: (
        "absent",
        "No flaky test hunter product.",
    ),
    240: (
        "stub",
        "No snapshot test update-with-review UX product.",
    ),
    241: (
        "stub",
        "No docker compose helper product.",
    ),
    242: (
        "stub",
        "No k8s dry-run helper product.",
    ),
    243: (
        "stub",
        "No terraform plan explain product.",
    ),
    244: (
        "stub",
        "No GraphQL schema assist product.",
    ),
    245: (
        "stub",
        "No OpenAPI generate/validate product.",
    ),
    246: (
        "stub",
        "No proto/gRPC helpers product.",
    ),
    247: (
        "foundation",
        "ci_why can help mobile build logs generically. Not mobile-specific product.",
    ),
    248: (
        "absent",
        "No game-engine log mode.",
    ),
    249: (
        "foundation",
        "databao/notebook hybrid pieces exist. Not full dataframe notebook product.",
    ),
    250: (
        "foundation",
        "Palace embeddings + workspace_index approximate repo RAG. Not full local "
        "vector search product over all repo chunks.",
    ),
    251: (
        "stub",
        "No AST edit engine product.",
    ),
    252: (
        "stub",
        "gates ruff optional — not full formatter/linter product suite.",
    ),
    253: (
        "absent",
        "No import organizer tool.",
    ),
    254: (
        "absent",
        "No license header tool.",
    ),
    255: (
        "absent",
        "No CODEOWNERS routing product.",
    ),
    256: (
        "stub",
        "workspace_index is basic — not full advanced code intelligence.",
    ),
    257: (
        "stub",
        "No build-system detect product.",
    ),
    258: (
        "stub",
        "Index is not an incremental productized indexer.",
    ),
    259: (
        "foundation",
        "pr_review summaries exist. Depth limited vs specialist review tools.",
    ),
    260: (
        "full",
        "ci-why command/path implemented for CI failure explanation. Intent met at "
        "nice depth for log triage.",
    ),
    261: (
        "full",
        "role_debate multi-role debate implemented. Debate intent met.",
    ),
    262: (
        "stub",
        "No red/blue security team product beyond debate roles.",
    ),
    263: (
        "stub",
        "Debate roles only — not a full multi-persona orchestration theater product.",
    ),
    264: (
        "stub",
        "No QA-only-diff agent product.",
    ),
    265: (
        "stub",
        "No release captain product.",
    ),
    266: (
        "stub",
        "No incident commander product.",
    ),
    267: (
        "stub",
        "No runbook executor product.",
    ),
    268: (
        "stub",
        "No multi-repo PR coordination product.",
    ),
    269: (
        "stub",
        "No dependency PR stack product.",
    ),
    270: (
        "absent",
        "No feature-flag assistant product.",
    ),
    271: (
        "absent",
        "No canary analysis product.",
    ),
    272: (
        "absent",
        "No metrics anomaly product.",
    ),
    273: (
        "absent",
        "No cloud bill anomaly product.",
    ),
    274: (
        "absent",
        "No SLA report product.",
    ),
    275: (
        "stub",
        "Architecture docs can be done via plan agent — no dedicated architecture-doc agent.",
    ),
    276: (
        "stub",
        "ADR writing only approximate via plan agent — no dedicated ADR product.",
    ),
    277: (
        "stub",
        "Todos only — no full project management agent product.",
    ),
    278: (
        "foundation",
        "GitHub + ticket stub integrations. Not full ticket platform product.",
    ),
    279: (
        "absent",
        "No design tokens product.",
    ),
    280: (
        "stub",
        "Browser optional only — not full design-to-code product.",
    ),
    281: (
        "stub",
        "No homebrew formula depth productized.",
    ),
    282: (
        "stub",
        "No official Dockerfile productized as distribution channel.",
    ),
    283: (
        "absent",
        "No nix flake.",
    ),
    284: (
        "foundation",
        "packaging/github-action sample exists. Not full multi-CI marketplace.",
    ),
    285: (
        "absent",
        "No GitLab CI component.",
    ),
    286: (
        "foundation",
        "pre-commit sample hook exists. Not full hook marketplace.",
    ),
    287: (
        "absent",
        "No devcontainer feature.",
    ),
    288: (
        "absent",
        "No Codespaces template.",
    ),
    289: (
        "absent",
        "No Raycast extension.",
    ),
    290: (
        "stub",
        "Messenger stubs only — not full multi-messenger product suite.",
    ),
    291: (
        "foundation",
        "Telegram config/path partial. Not full production Telegram channel product.",
    ),
    292: (
        "foundation",
        "Slack partial. Not full Slack app product.",
    ),
    293: (
        "foundation",
        "notion_stub only. Not Notion product.",
    ),
    294: (
        "stub",
        "Export markdown only — not full docs platform integration.",
    ),
    295: (
        "absent",
        "No browser extension.",
    ),
    296: (
        "absent",
        "No Figma integration.",
    ),
    297: (
        "absent",
        "No Datadog pull integration.",
    ),
    298: (
        "foundation",
        "host-tools checks cloud CLIs presence. Not full cloud ops product.",
    ),
    299: (
        "foundation",
        "plugin-catalog lists plugins. Marketplace UX incomplete.",
    ),
    300: (
        "foundation",
        "recipes seed an awesome-list style catalog. Not a community ecosystem product.",
    ),
}

# ---------------------------------------------------------------------------
# PARKED P301–P400
# ---------------------------------------------------------------------------
P: dict[int, tuple[str, str]] = {}

# Vanity / branding / distraction (P301–P320)
_VANITY_WHY = (
    "stub: only cataloged under parked_features / optional vanity flags if any. "
    "Not scheduled for product work — backlog marks these as distraction. "
    "Rated stub (surface only) rather than absent when a flag/catalog entry exists; "
    "either way they are not real product features."
)
for i in range(301, 321):
    P[i] = ("stub", _VANITY_WHY)

# Platform overreach experimental (P321–P345)
_PLATFORM_WHY = (
    "stub: experimental/platform-overreach items intentionally not built as products. "
    "May have zero code or a refuse-to-prioritize note in parked catalog. "
    "SuperAI stays local-first orchestrator — not SaaS/IDE/OS/hardware replacement."
)
for i in range(321, 346):
    P[i] = ("stub", _PLATFORM_WHY)

# Enterprise theater (P346–P365)
_ENT_WHY = (
    "stub: enterprise_stubs / sso_status / rbac stubs only. "
    "No real SOC2/FedRAMP/SCIM/SIEM/DLP product. Intentionally parked until strategy changes."
)
for i in range(346, 366):
    P[i] = ("stub", _ENT_WHY)

P[366] = (
    "foundation",
    "Agent-only mode can prefer API models over shelling external CLIs — partial "
    "reimplementation avoidance strategy, not full vendor CLI reimplementation.",
)
P[367] = (
    "stub",
    "No full reimplementation of vendor CLIs inside SuperAI (correctly avoided).",
)
P[368] = (
    "foundation",
    "Chroma remains experimental/optional import path historically; product default is "
    "not dual memory stacks. Partial experimental flag only — not second full memory product.",
)

_OVERBUILD_WHY = (
    "stub: overbuild / clone-every-SaaS items not implemented. Catalog entry only. "
    "SuperAI is not trying to be JupyterLab/Postman/Datadog/Jira/Notion/Figma/etc."
)
for i in range(369, 386):
    P[i] = ("stub", _OVERBUILD_WHY)

_REFUSE_WHY = (
    "refuse: hard refuse-closed for safety/abuse/unscoped autonomy. "
    "parked_features / policy returns refuse; must not be implemented as product features. "
    "Rated refuse (intentional close), not absent (we did not 'forget' them)."
)
for i in range(386, 401):
    P[i] = ("refuse", _REFUSE_WHY)

# Per-item overrides where title-specific reason helps clarity
P_OVERRIDES: dict[int, tuple[str, str]] = {
    301: (
        "stub",
        "Rebranding SuperAI is product marketing, not engineering depth. No rename work "
        "done; cataloged as parked vanity.",
    ),
    302: (
        "stub",
        "Pixel-matching OpenCode/Claude Code UI is explicitly not our differentiator. "
        "superai_agent TUI is SuperAI-branded, not a clone.",
    ),
    323: (
        "stub",
        "Multi-tenant SaaS before local excellence rejected as strategy; local-first remains.",
    ),
    336: (
        "stub",
        "No proprietary protocol replacing MCP — MCP parity is the direction (M093).",
    ),
    366: P[366],
    367: P[367],
    368: P[368],
    386: (
        "refuse",
        "Fully autonomous company-running agent is unscoped and unsafe; refuse-closed.",
    ),
    387: (
        "refuse",
        "Recursive self-improvement without gates is unsafe; refuse-closed.",
    ),
    388: (
        "refuse",
        "Unrestricted yolo as default would violate safe defaults (M005); refuse-closed.",
    ),
    389: (
        "refuse",
        "Internet-wide unconstrained browsing violates SSRF/safety posture; refuse-closed.",
    ),
    390: (
        "refuse",
        "Auto-PRs to random public repos is abuse-adjacent; refuse-closed.",
    ),
    391: (
        "refuse",
        "Auto-trading is high-risk unscoped financial automation; refuse-closed.",
    ),
    392: (
        "refuse",
        "Certified legal advice agent is liability/unsafe scope; refuse-closed.",
    ),
    393: (
        "refuse",
        "Medical diagnosis agent is liability/unsafe scope; refuse-closed.",
    ),
    394: (
        "refuse",
        "Jailbreak playground product would undermine safety; refuse-closed.",
    ),
    395: (
        "refuse",
        "Prompt-virus research tools are dual-use abuse risk; refuse-closed.",
    ),
    396: (
        "refuse",
        "Deepfake media tools are abuse-prone; refuse-closed.",
    ),
    397: (
        "refuse",
        "Mass scraping suite is abuse/legal risk; refuse-closed.",
    ),
    398: (
        "refuse",
        "CAPTCHA farms are abuse infrastructure; refuse-closed.",
    ),
    399: (
        "refuse",
        "AGI mode branding is dishonest hype; refuse-closed for product integrity.",
    ),
    400: (
        "refuse",
        "Infinite backlog without Phase 6 smoke honesty gate undermines verification; "
        "refuse-closed as process anti-pattern.",
    ),
}
P.update(P_OVERRIDES)


def _id_key(prefix: str, n: int) -> str:
    return f"M{n:03d}" if prefix == "M" else f"{prefix}{n}"


def _section(
    lines: list[str],
    title: str,
    prefix: str,
    data: dict[int, tuple[str, str]],
    lo: int,
    hi: int,
    titles: dict[str, str],
) -> None:
    lines += [f"## {title}", ""]
    for i in range(lo, hi + 1):
        st, why = data[i]
        iid = _id_key(prefix, i)
        item_title = titles.get(iid, "(title missing from backlog)")
        lines += [
            f"### {iid} — {item_title}",
            "",
            f"- **Status:** `{st}`",
            f"- **Why:** {why}",
            "",
        ]




# Honest upgrades only (2026-07-16 re-audit). DO NOT bulk-lift foundations.
# Only IDs with clear new production-usable completion beyond prior foundation rating.
HONEST_UPGRADES = {
    3: ("full", "board_preflight.estimate/enforce wired into multi_cli_advisory + CLI board-preflight; unit tested. Pre-flight board cost is production-usable."),
    12: ("full", "secrets.redact_* plus logging Filter on console/file/daily handlers redacts secrets in logs. Production-usable secret scrubbing on log sinks."),
    29: ("full", "session_compact preserves decisions + open todos before truncation; extract_decisions_and_todos tested. Compaction DoD met."),
    67: ("full", "TaskHistory.search by task/model/cost + history-search CLI; unit tested. Searchable history met."),
    92: ("full", "mock_fixtures module with deterministic CI fixtures; unit tested. Mock fixture library met for offline CI."),
    94: ("full", "web_app requires SUPERAI_WEB_TOKEN for non-loopback /api; loopback may omit token for local dev. Non-loopback auth met."),
    99: ("full", "docs/THREAT_MODEL.md plus architecture/quickstart docs. Threat/architecture docs met."),
}
# S-number upgrades (keys are backlog numbers 101-200)
HONEST_UPGRADES_S = {
    103: ("full", "architecture_mode.resolve_mode + mode CLI; architecture vs implementation boundaries clear. Intent met."),
    130: ("full", "adaptive_escalate.quality_failed/pick_premium + agent runtime escalate on weak answer; unit tested. Intent met."),
    131: ("full", "project_budget policies + CLI project-budget; unit tested. Per-project budget policies met."),
    133: ("full", "board_preflight/cost forecast before multi-member boards. Forecast/preflight met."),
    134: ("full", "spend_report daily/weekly from budget+history; CLI spend-report. Spend report met."),
    135: ("full", "status --cost includes cache_hit_rate and spend totals via spend_report. Cache/spend visibility met."),
}

def apply_honest_upgrades() -> None:
    for i, val in HONEST_UPGRADES.items():
        if i in M:
            M[i] = val
    for i, val in HONEST_UPGRADES_S.items():
        if i in S:
            S[i] = val


def main() -> None:
    titles = load_titles()
    apply_honest_upgrades()
    assert len(titles) == 400, len(titles)
    for d, lo, hi, prefix in [
        (M, 1, 100, "M"),
        (S, 101, 200, "S"),
        (N, 201, 300, "N"),
        (P, 301, 400, "P"),
    ]:
        for i in range(lo, hi + 1):
            assert i in d, (prefix, i)

    all_st = []
    for d in (M, S, N, P):
        all_st.extend(st for st, _ in d.values())
    c = Counter(all_st)

    lines: list[str] = [
        "# SuperAI V6 Backlog — Detailed line-by-line scorecard",
        "",
        "**Generated:** 2026-07-16  ",
        "**Total items:** 400 (M100 + S100 + N100 + P100)  ",
        "**Purpose:** Truthful status per ID for external review (Claude/Gemini/Codex).",
        "**Re-audit:** 2026-07-16 — prior bulk foundation→full upgrade **reverted**. Only a few IDs re-earned full with evidence.",
        "**Policy:** full = production-usable for stated intent with real code (+ tests where applicable). foundation = real code, incomplete DoD. Never inflate.",
        "",
        "Each item lists:",
        "",
        "1. **Backlog title** (from `docs/IMPROVEMENT_V6_BACKLOG.md`)",
        "2. **Status** (classification)",
        "3. **Why** (evidence + gap that justified the status)",
        "",
        "## Status legend",
        "",
        "| Status | Meaning | When we use it |",
        "|--------|---------|----------------|",
        "| **full** | Production-usable for the stated intent | Real code + tests (or equivalent proof) covering the backlog wording |",
        "| **foundation** | Real working code; DoD depth incomplete | Core mechanism exists; missing universality, UX, or hardening |",
        "| **stub** | Surface/flag/sample only | Catalog flag, sample hook, or thin placeholder — not a product |",
        "| **host** | Code path exists; needs keys/environment | Implementation done; live proof requires host credentials |",
        "| **refuse** | Intentionally refuse-closed (safety) | Explicit policy: must not ship as a feature |",
        "| **absent** | No meaningful implementation | Zero or near-zero code for this intent |",
        "",
        "## Summary counts",
        "",
        "| Status | Count | % of 400 |",
        "|--------|------:|---------:|",
    ]
    for k in ["full", "foundation", "stub", "host", "refuse", "absent"]:
        n = c.get(k, 0)
        lines.append(f"| {k} | {n} | {100 * n / 400:.1f}% |")
    lines.append(f"| **total** | **{sum(c.values())}** | **100%** |")
    lines += [
        "",
        "### Interpretation",
        "",
        f"- **full + foundation** ≈ **{c.get('full', 0) + c.get('foundation', 0)}** items have real code value.",
        f"- **stub + absent** ≈ **{c.get('stub', 0) + c.get('absent', 0)}** are not product-complete.",
        f"- **refuse** = **{c.get('refuse', 0)}** (P386–P400) correctly closed.",
        f"- **host** = **{c.get('host', 0)}** (live smoke proof needs credentials).",
        "",
        "**Honest headline:** Strong **Must** coverage (mostly full/foundation). Many "
        "**Should/Nice** items are foundation or stub/absent. **Parked** is mostly "
        "stubs/flags; abuse IDs are refuse-closed. **This is not 400× full production features.**",
        "",
        "### Quick index tables (status only)",
        "",
        "Full narrative for every ID is below. These tables are for scanning.",
        "",
    ]

    # Compact tables
    for name, data, lo, hi, prefix in [
        ("Must M001–M100", M, 1, 100, "M"),
        ("Should S101–S200", S, 101, 200, "S"),
        ("Nice N201–N300", N, 201, 300, "N"),
        ("Parked P301–P400", P, 301, 400, "P"),
    ]:
        lines += [
            f"#### {name}",
            "",
            "| ID | Status | Title |",
            "|----|--------|-------|",
        ]
        for i in range(lo, hi + 1):
            iid = _id_key(prefix, i)
            st = data[i][0]
            t = titles.get(iid, "")
            if len(t) > 60:
                t = t[:57] + "..."
            lines.append(f"| {iid} | **{st}** | {t} |")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("# Detailed assessments (every ID)")
    lines.append("")

    _section(lines, "Must (M001–M100) — detailed", "M", M, 1, 100, titles)
    _section(lines, "Should (S101–S200) — detailed", "S", S, 101, 200, titles)
    _section(lines, "Nice (N201–N300) — detailed", "N", N, 201, 300, titles)
    _section(lines, "Parked (P301–P400) — detailed", "P", P, 301, 400, titles)

    lines += [
        "## Bucket rollups",
        "",
    ]
    for name, d, lo, hi in [
        ("Must M001–M100", M, 1, 100),
        ("Should S101–S200", S, 101, 200),
        ("Nice N201–N300", N, 201, 300),
        ("Parked P301–P400", P, 301, 400),
    ]:
        cc = Counter(d[i][0] for i in range(lo, hi + 1))
        lines += [f"### {name}", "", "| Status | Count |", "|--------|------:|"]
        for k in ["full", "foundation", "stub", "host", "refuse", "absent"]:
            if cc.get(k):
                lines.append(f"| {k} | {cc[k]} |")
        lines.append("")

    lines += [
        "## How status decisions were made",
        "",
        "1. **Compare backlog wording** to actual modules/CLI/tests in-repo.",
        "2. **full** only if the stated intent is usable end-to-end for daily product use.",
        "3. **foundation** if real code exists but universality, UX, or hardening is incomplete.",
        "4. **stub** if only flags, samples, or placeholders exist.",
        "5. **absent** if no meaningful implementation.",
        "6. **host** if code is complete but live proof needs credentials.",
        "7. **refuse** if policy intentionally blocks implementation (safety).",
        "",
        "Regenerate: `python scripts/gen_v6_scorecard.py`",
        "",
        "## Recommended next engineering (from this audit)",
        "",
        "1. Raise **M001 / M008 / M079 / M080** foundation → full (all public entrypoints).",
        "2. Treat **S108 / S111** (symbol/refactor) as a dedicated coding-agent epic.",
        "3. Do not claim **N231–N260** full — most are absent/stub.",
        "4. Run **M089** with keys: `superai phase6-smoke --allow-live`.",
        "5. Keep **P386–P400** refuse-closed.",
        "",
        "## Related",
        "",
        "- Backlog: `docs/IMPROVEMENT_V6_BACKLOG.md`",
        "- Runtime: `superai v6-status`",
        "- Parked: `superai parked catalog`",
        "",
    ]

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print("COUNTS", dict(sorted(c.items())))
    print("must full", sum(1 for st, _ in M.values() if st == "full"))
    print("must foundation", sum(1 for st, _ in M.values() if st == "foundation"))
    print("should full", sum(1 for st, _ in S.values() if st == "full"))
    print("nice full", sum(1 for st, _ in N.values() if st == "full"))
    print("nice absent", sum(1 for st, _ in N.values() if st == "absent"))
    print("park refuse", sum(1 for st, _ in P.values() if st == "refuse"))
    print("chars", OUT.stat().st_size)


if __name__ == "__main__":
    main()
