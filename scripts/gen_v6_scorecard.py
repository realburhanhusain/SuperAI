"""Generate docs/V6_SCORECARD.md — honest per-ID audit."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

# Status: full | foundation | stub | host | refuse | absent

M = {
    1: ("foundation", "spend_guard on major paths; not every CLI command"),
    2: ("foundation", "cost_accounting + ModelCaller; some paths still estimate"),
    3: ("foundation", "boards via cost_router/budget; weak dedicated preflight UX"),
    4: ("full", "permission_mode plan + dry_run tools"),
    5: ("full", "plan|ask|auto|yolo"),
    6: ("full", "workspace jail agent_tools + CLI"),
    7: ("full", "side_effect_audit + run_trail"),
    8: ("foundation", "contract on major APIs; not literally every CLI cmd"),
    9: ("full", "error_codes taxonomy"),
    10: ("full", "readiness + agent live gate"),
    11: ("full", "model_caller failover + local_first"),
    12: ("foundation", "redaction patterns; not formal secret scan everywhere"),
    13: ("full", "keyring_store + secrets CLI"),
    14: ("full", "net_safety SSRF"),
    15: ("foundation", "tool protocol + permission; no injection classifier"),
    16: ("full", "palace_tenant tags"),
    17: ("foundation", "CancelToken in agent; not all board workers"),
    18: ("foundation", "tool_timeouts + subprocess timeouts; not universal"),
    19: ("full", "explain-run + run_trail"),
    20: ("full", "mock mode + smoke harness never false-pass"),
    21: ("full", "superai_agent sessions + ask_session"),
    22: ("full", "tool_protocol"),
    23: ("full", "parallel read tools in runtime"),
    24: ("full", "idempotent tool_write"),
    25: ("full", "change_set + /apply /reject"),
    26: ("full", "git_diff_apply check"),
    27: ("foundation", "call_stream with fallback chunking"),
    28: ("full", "context_pack"),
    29: ("foundation", "session_compact; agent_todos separate"),
    30: ("full", "build/plan/ask roles"),
    31: ("full", "front_door + do + interactive"),
    32: ("full", "confidence/needs_confirm"),
    33: ("full", "local_first escalate"),
    34: ("full", "task_complexity cheap-first"),
    35: ("full", "smart_max_members + complexity"),
    36: ("full", "board early-exit consensus"),
    37: ("full", "diversify_pool"),
    38: ("full", "worktree_subagent"),
    39: ("full", "tdd_loop + quality_gates"),
    40: ("full", "pr_review + multi_cli"),
    41: ("full", "models-register OpenAI-compat"),
    42: ("full", "ollama/lmstudio/vllm in catalog"),
    43: ("full", "path_which + external_cli"),
    44: ("full", "cli_models + name@model"),
    45: ("full", "member_selection catalog"),
    46: ("full", "members --available / live probe"),
    47: ("full", "provider_health circuits"),
    48: ("full", "rate_queue"),
    49: ("full", "model_blacklist"),
    50: ("foundation", "bandit_router; not continuous every call"),
    51: ("full", "bakeoff report+pin"),
    52: ("full", "compare + contract"),
    53: ("full", "council voting"),
    54: ("full", "multi_cli_advisory parallel"),
    55: ("full", "cost_router shrink"),
    56: ("full", "central_memory inject"),
    57: ("full", "write_back"),
    58: ("full", "query_semantic + tenant"),
    59: ("full", "memory_inject rank pack"),
    60: ("full", "memory-forget/ttl/gdpr"),
    61: ("foundation", "learning_engine promote"),
    62: ("foundation", "learning conflict paths"),
    63: ("foundation", "distill/deprecate"),
    64: ("full", "wings/rooms"),
    65: ("full", "backup_manager encrypted"),
    66: ("full", "profile-bundle"),
    67: ("foundation", "history/runs; cost search partial"),
    68: ("foundation", "preferences module"),
    69: ("full", "skills"),
    70: ("full", "skill_permissions"),
    71: ("full", "default superai front door"),
    72: ("full", "superai do"),
    73: ("full", "doctor"),
    74: ("full", "status --cost"),
    75: ("full", "install wizard"),
    76: ("full", "host-tools"),
    77: ("full", "superai_agent TUI"),
    78: ("full", "slash palette /commands"),
    79: ("foundation", "JSON on many cmds; not all CLI cmds"),
    80: ("foundation", "exit_codes module; not wired all exits"),
    81: ("foundation", "typer help; uneven examples"),
    82: ("foundation", "typer completion enabled"),
    83: ("full", "config get/set"),
    84: ("full", "version_check/update"),
    85: ("full", "diagnostics zip"),
    86: ("full", "test_improvement_v4/v5 safety"),
    87: ("full", "eval_golden"),
    88: ("full", "smoke_harness"),
    89: ("host", "live_smoke_complete; needs keys for live_passed"),
    90: ("foundation", "contract tests major paths not full top-30 suite"),
    91: ("stub", "no formal cold-start budget CI gate"),
    92: ("foundation", "mock fixtures in tests"),
    93: ("foundation", "MCP budget/contract on superai_run"),
    94: ("foundation", "web token auth optional"),
    95: ("full", "agent-graph SVG"),
    96: ("full", "goals + schedule caps"),
    97: ("full", "plugin sha path"),
    98: ("full", "constitution + policy"),
    99: ("foundation", "docs exist; threat model partial"),
    100: ("foundation", "mock/live flags; dashboard partial honesty"),
}

S = {
    101: ("full", "agent_todos"),
    102: ("full", "spec_mode"),
    103: ("foundation", "roles plan vs build; no separate arch flag"),
    104: ("stub", "no dedicated self-critique module"),
    105: ("foundation", "quality_gates pytest"),
    106: ("foundation", "ruff optional in gates"),
    107: ("full", "workspace_index"),
    108: ("stub", "no real symbol index/LSP goto"),
    109: ("foundation", "ci_why + do path"),
    110: ("foundation", "pr_review"),
    111: ("stub", "no safe multi-file rename engine"),
    112: ("stub", "no dedicated dep upgrade agent"),
    113: ("stub", "no migration dry-run product"),
    114: ("foundation", "security patterns; not full SCA"),
    115: ("stub", "no license checker"),
    116: ("foundation", "git-helper"),
    117: ("stub", "no merge conflict solver"),
    118: ("full", "git_diff_apply unified"),
    119: ("foundation", "multimodal vision path"),
    120: ("stub", "no PDF attach pipeline"),
    121: ("foundation", "browser_tool playwright optional"),
    122: ("full", "notebook_runner"),
    123: ("foundation", "databao SQL; allowlist partial"),
    124: ("foundation", "ci_why log triage"),
    125: ("full", "session resume"),
    126: ("full", "result_cache opt-in"),
    127: ("stub", "no provider prompt-cache integration"),
    128: ("foundation", "local then escalate pattern"),
    129: ("stub", "no mid-task demotion controller"),
    130: ("foundation", "adaptive escalate on weak answer"),
    131: ("foundation", "budget config per run; weak project policies"),
    132: ("stub", "no per-command budget map"),
    133: ("foundation", "cost_forecast module"),
    134: ("foundation", "budget snapshot; weak weekly report"),
    135: ("foundation", "status --cost cache counts"),
    136: ("stub", "no token waterfall UI"),
    137: ("stub", "no stagger scheduler"),
    138: ("foundation", "front_door + cheap-first"),
    139: ("stub", "no systematic tool output compressor"),
    140: ("foundation", "read mtime cache"),
    141: ("stub", "no dedicated embedding cache layer"),
    142: ("stub", "no batch embed API"),
    143: ("foundation", "lazy imports ad hoc"),
    144: ("stub", "no cold-start optimization program"),
    145: ("stub", "no model warmup daemon"),
    146: ("stub", "no history-based max_members learner"),
    147: ("foundation", "CancelToken"),
    148: ("stub", "stream cancel incomplete"),
    149: ("foundation", "profiles cheap sticky via config"),
    150: ("foundation", "ab_routing"),
    151: ("full", "models-refresh-openrouter"),
    152: ("full", "capability_tags"),
    153: ("stub", "no per-model context window enforcement"),
    154: ("foundation", "tool_protocol JSON"),
    155: ("foundation", "validate-json; not full schema retry"),
    156: ("foundation", "native anthropic/google callers partial"),
    157: ("full", "path_which windows"),
    158: ("stub", "no dedicated WSL bridge"),
    159: ("foundation", "container_sandbox flag"),
    160: ("foundation", "net_safety public-only"),
    161: ("full", "tool_timeouts"),
    162: ("stub", "no global concurrency governor"),
    163: ("stub", "no interactive vs batch queue split"),
    164: ("foundation", "model_pinning"),
    165: ("stub", "no team shared policy store"),
    166: ("foundation", "doctor/readiness messages"),
    167: ("stub", "no GPU detect"),
    168: ("foundation", "openrouter catalog"),
    169: ("foundation", "nvidia models in catalog"),
    170: ("stub", "no multi-key rotation"),
    171: ("full", "project_memory"),
    172: ("stub", "no memory confidence scores UI"),
    173: ("stub", "no confirm-before-memory-write gate"),
    174: ("foundation", "memory-palace search CLI not full TUI"),
    175: ("stub", "no injection citations UI"),
    176: ("stub", "no conflict UI"),
    177: ("full", "tenant-export/import"),
    178: ("stub", "no org skills registry service"),
    179: ("foundation", "recipes as templates"),
    180: ("foundation", "msg-inbound"),
    181: ("foundation", "goals notify"),
    182: ("stub", "rbac stub only"),
    183: ("foundation", "audit log export partial"),
    184: ("foundation", "memory-ttl"),
    185: ("foundation", "encrypted backup; session encrypt partial"),
    186: ("foundation", "web app memory/status; not full session browser"),
    187: ("stub", "no SSE progress"),
    188: ("foundation", "vscode extension thin"),
    189: ("absent", "no JetBrains plugin"),
    190: ("foundation", "PWA static shell"),
    191: ("stub", "parked seasonal theme flag only"),
    192: ("absent", "no keybind config"),
    193: ("foundation", "paste mode in agent TUI"),
    194: ("stub", "no rich clipboard API"),
    195: ("foundation", "init/onboard"),
    196: ("full", "recipes"),
    197: ("foundation", "explain-run; mermaid via agent-graph partial"),
    198: ("full", "profile-suggest"),
    199: ("full", "onboard quest"),
    200: ("full", "whats-new"),
}

N = {
    201: ("stub", "no Ctrl+K palette app"),
    202: ("foundation", "NL do/ask routes"),
    203: ("full", "macros"),
    204: ("stub", "no pipeline operator"),
    205: ("foundation", "watch_mode poll limited"),
    206: ("foundation", "goals/schedule not full daemon"),
    207: ("stub", "no SSH remote agent product"),
    208: ("stub", "no tmux multiplex"),
    209: ("foundation", "TUI panels partial"),
    210: ("absent", "no vim mode"),
    211: ("absent", "no mouse TUI"),
    212: ("stub", "vision files not clipboard paste"),
    213: ("foundation", "voice_io optional"),
    214: ("foundation", "i18n module partial"),
    215: ("absent", "no a11y TUI audit"),
    216: ("stub", "theme flag only"),
    217: ("stub", "theme flag only"),
    218: ("stub", "no full replay tape product"),
    219: ("foundation", "session export md"),
    220: ("stub", "no shareable sanitized bundle"),
    221: ("foundation", "eval_golden"),
    222: ("stub", "no private leaderboard"),
    223: ("stub", "no YAML agent DSL parser product"),
    224: ("foundation", "plugin-catalog"),
    225: ("foundation", "sha256 verify"),
    226: ("stub", "no skill versioning"),
    227: ("full", "hooks pre/post"),
    228: ("foundation", "policy module simple"),
    229: ("stub", "sso_status only"),
    230: ("absent", "no SCIM"),
    231: ("foundation", "lsp_bridge compile stub"),
    232: ("absent", "no goto-def"),
    233: ("absent", "no rename symbol"),
    234: ("absent", "no extract method"),
    235: ("absent", "no dead code tool"),
    236: ("absent", "no complexity map"),
    237: ("stub", "tdd only"),
    238: ("absent", "no mutation testing"),
    239: ("absent", "no flaky hunter"),
    240: ("stub", "no snapshot review UX"),
    241: ("stub", "no compose helper product"),
    242: ("stub", "no k8s dry-run product"),
    243: ("stub", "no terraform explain"),
    244: ("stub", "no graphql assist"),
    245: ("stub", "no openapi product"),
    246: ("stub", "no grpc helpers"),
    247: ("foundation", "ci_why"),
    248: ("absent", "no game engine log mode"),
    249: ("foundation", "databao/notebook"),
    250: ("foundation", "palace embeddings; not full repo RAG product"),
    251: ("stub", "no AST edit engine"),
    252: ("stub", "gates ruff optional"),
    253: ("absent", "no import organizer"),
    254: ("absent", "no license header tool"),
    255: ("absent", "no CODEOWNERS routing"),
    256: ("stub", "workspace_index basic"),
    257: ("stub", "no build system detect"),
    258: ("stub", "index not incremental product"),
    259: ("foundation", "pr_review summaries"),
    260: ("full", "ci-why"),
    261: ("full", "role_debate"),
    262: ("stub", "no red/blue security product"),
    263: ("stub", "debate roles only"),
    264: ("stub", "no QA-only-diff agent"),
    265: ("stub", "no release captain product"),
    266: ("stub", "no incident commander"),
    267: ("stub", "no runbook executor product"),
    268: ("stub", "no multi-repo PR coord"),
    269: ("stub", "no dep PR stack"),
    270: ("absent", "no feature flag assistant"),
    271: ("absent", "no canary analysis"),
    272: ("absent", "no metrics anomaly"),
    273: ("absent", "no cloud bill anomaly"),
    274: ("absent", "no SLA report"),
    275: ("stub", "can do via plan agent"),
    276: ("stub", "can do via plan agent"),
    277: ("stub", "todos only"),
    278: ("foundation", "github + ticket stub"),
    279: ("absent", "no design tokens"),
    280: ("stub", "browser optional"),
    281: ("stub", "no homebrew formula depth"),
    282: ("stub", "no official Dockerfile productized"),
    283: ("absent", "no nix flake"),
    284: ("foundation", "packaging/github-action sample"),
    285: ("absent", "no gitlab component"),
    286: ("foundation", "pre-commit sample"),
    287: ("absent", "no devcontainer feature"),
    288: ("absent", "no codespaces template"),
    289: ("absent", "no raycast"),
    290: ("stub", "messengers only"),
    291: ("foundation", "telegram config partial"),
    292: ("foundation", "slack partial"),
    293: ("foundation", "notion_stub"),
    294: ("stub", "export md only"),
    295: ("absent", "no browser extension"),
    296: ("absent", "no figma"),
    297: ("absent", "no datadog pull"),
    298: ("foundation", "host-tools cloud CLIs check"),
    299: ("foundation", "plugin-catalog"),
    300: ("foundation", "recipes as awesome list seed"),
}

P: dict[int, tuple[str, str]] = {}
for i in range(301, 321):
    P[i] = ("stub", "vanity flags via parked_features")
for i in range(321, 346):
    P[i] = ("stub", "platform experimental stub")
for i in range(346, 366):
    P[i] = ("stub", "enterprise_stubs / rbac/sso status")
P[366] = ("foundation", "agent-only mode prefers API over CLI")
P[367] = ("stub", "no full CLI reimplementation")
P[368] = ("foundation", "chroma experimental flag + optional import")
for i in range(369, 386):
    P[i] = ("stub", "overbuild stub catalog entry")
for i in range(386, 401):
    P[i] = ("refuse", "hard refuse safety policy")


def main() -> None:
    all_st = []
    for d in (M, S, N, P):
        all_st.extend(st for st, _ in d.values())
    c = Counter(all_st)

    lines: list[str] = []
    lines += [
        "# SuperAI V6 Backlog — Line-by-line scorecard",
        "",
        "**Generated:** 2026-07-16  ",
        "**Total items:** 400 (M100 + S100 + N100 + P100)  ",
        "**Purpose:** Honest status per ID — not inflated “all done.”  ",
        "",
        "## Status legend",
        "",
        "| Status | Meaning |",
        "|--------|---------|",
        "| **full** | Production-usable for the stated intent |",
        "| **foundation** | Real working code; DoD depth incomplete |",
        "| **stub** | Surface/flag/sample only |",
        "| **host** | Code path exists; needs keys/environment for full claim |",
        "| **refuse** | Intentionally refuse-closed (safety) |",
        "| **absent** | No meaningful implementation |",
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
        "**Honest headline:** SuperAI has strong **Must** coverage (mostly full/foundation). "
        "Many **Should/Nice** items are foundation or stub/absent. **Parked** is mostly stubs/flags; "
        "abuse IDs are refuse-closed. **This is not 400× full production features.**",
        "",
        "## Must (M001–M100)",
        "",
        "| ID | Status | Evidence / gap |",
        "|----|--------|----------------|",
    ]
    for i in range(1, 101):
        st, note = M[i]
        lines.append(f"| M{i:03d} | **{st}** | {note} |")

    lines += [
        "",
        "## Should (S101–S200)",
        "",
        "| ID | Status | Evidence / gap |",
        "|----|--------|----------------|",
    ]
    for i in range(101, 201):
        st, note = S[i]
        lines.append(f"| S{i} | **{st}** | {note} |")

    lines += [
        "",
        "## Nice (N201–N300)",
        "",
        "| ID | Status | Evidence / gap |",
        "|----|--------|----------------|",
    ]
    for i in range(201, 301):
        st, note = N[i]
        lines.append(f"| N{i} | **{st}** | {note} |")

    lines += [
        "",
        "## Parked (P301–P400)",
        "",
        "| ID | Status | Evidence / gap |",
        "|----|--------|----------------|",
    ]
    for i in range(301, 401):
        st, note = P[i]
        lines.append(f"| P{i} | **{st}** | {note} |")

    lines += ["", "## Bucket rollups", ""]
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

    out = Path("docs/V6_SCORECARD.md")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print("COUNTS", dict(c))
    print("must full", sum(1 for st, _ in M.values() if st == "full"))
    print("must foundation", sum(1 for st, _ in M.values() if st == "foundation"))
    print("should full", sum(1 for st, _ in S.values() if st == "full"))
    print("nice full", sum(1 for st, _ in N.values() if st == "full"))
    print("nice absent", sum(1 for st, _ in N.values() if st == "absent"))
    print("park refuse", sum(1 for st, _ in P.values() if st == "refuse"))


if __name__ == "__main__":
    main()
