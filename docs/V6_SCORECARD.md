# SuperAI V6 Backlog — Line-by-line scorecard

**Generated:** 2026-07-16  
**Total items:** 400 (M100 + S100 + N100 + P100)  
**Purpose:** Honest status per ID — not inflated “all done.”  

## Status legend

| Status | Meaning |
|--------|---------|
| **full** | Production-usable for the stated intent |
| **foundation** | Real working code; DoD depth incomplete |
| **stub** | Surface/flag/sample only |
| **host** | Code path exists; needs keys/environment for full claim |
| **refuse** | Intentionally refuse-closed (safety) |
| **absent** | No meaningful implementation |

## Summary counts

| Status | Count | % of 400 |
|--------|------:|---------:|
| full | 93 | 23.2% |
| foundation | 98 | 24.5% |
| stub | 162 | 40.5% |
| host | 1 | 0.2% |
| refuse | 15 | 3.8% |
| absent | 31 | 7.8% |
| **total** | **400** | **100%** |

### Interpretation

- **full + foundation** ≈ **191** items have real code value.
- **stub + absent** ≈ **193** are not product-complete.
- **refuse** = **15** (P386–P400) correctly closed.
- **host** = **1** (live smoke proof needs credentials).

**Honest headline:** SuperAI has strong **Must** coverage (mostly full/foundation). Many **Should/Nice** items are foundation or stub/absent. **Parked** is mostly stubs/flags; abuse IDs are refuse-closed. **This is not 400× full production features.**

## Must (M001–M100)

| ID | Status | Evidence / gap |
|----|--------|----------------|
| M001 | **foundation** | spend_guard on major paths; not every CLI command |
| M002 | **foundation** | cost_accounting + ModelCaller; some paths still estimate |
| M003 | **foundation** | boards via cost_router/budget; weak dedicated preflight UX |
| M004 | **full** | permission_mode plan + dry_run tools |
| M005 | **full** | plan|ask|auto|yolo |
| M006 | **full** | workspace jail agent_tools + CLI |
| M007 | **full** | side_effect_audit + run_trail |
| M008 | **foundation** | contract on major APIs; not literally every CLI cmd |
| M009 | **full** | error_codes taxonomy |
| M010 | **full** | readiness + agent live gate |
| M011 | **full** | model_caller failover + local_first |
| M012 | **foundation** | redaction patterns; not formal secret scan everywhere |
| M013 | **full** | keyring_store + secrets CLI |
| M014 | **full** | net_safety SSRF |
| M015 | **foundation** | tool protocol + permission; no injection classifier |
| M016 | **full** | palace_tenant tags |
| M017 | **foundation** | CancelToken in agent; not all board workers |
| M018 | **foundation** | tool_timeouts + subprocess timeouts; not universal |
| M019 | **full** | explain-run + run_trail |
| M020 | **full** | mock mode + smoke harness never false-pass |
| M021 | **full** | superai_agent sessions + ask_session |
| M022 | **full** | tool_protocol |
| M023 | **full** | parallel read tools in runtime |
| M024 | **full** | idempotent tool_write |
| M025 | **full** | change_set + /apply /reject |
| M026 | **full** | git_diff_apply check |
| M027 | **foundation** | call_stream with fallback chunking |
| M028 | **full** | context_pack |
| M029 | **foundation** | session_compact; agent_todos separate |
| M030 | **full** | build/plan/ask roles |
| M031 | **full** | front_door + do + interactive |
| M032 | **full** | confidence/needs_confirm |
| M033 | **full** | local_first escalate |
| M034 | **full** | task_complexity cheap-first |
| M035 | **full** | smart_max_members + complexity |
| M036 | **full** | board early-exit consensus |
| M037 | **full** | diversify_pool |
| M038 | **full** | worktree_subagent |
| M039 | **full** | tdd_loop + quality_gates |
| M040 | **full** | pr_review + multi_cli |
| M041 | **full** | models-register OpenAI-compat |
| M042 | **full** | ollama/lmstudio/vllm in catalog |
| M043 | **full** | path_which + external_cli |
| M044 | **full** | cli_models + name@model |
| M045 | **full** | member_selection catalog |
| M046 | **full** | members --available / live probe |
| M047 | **full** | provider_health circuits |
| M048 | **full** | rate_queue |
| M049 | **full** | model_blacklist |
| M050 | **foundation** | bandit_router; not continuous every call |
| M051 | **full** | bakeoff report+pin |
| M052 | **full** | compare + contract |
| M053 | **full** | council voting |
| M054 | **full** | multi_cli_advisory parallel |
| M055 | **full** | cost_router shrink |
| M056 | **full** | central_memory inject |
| M057 | **full** | write_back |
| M058 | **full** | query_semantic + tenant |
| M059 | **full** | memory_inject rank pack |
| M060 | **full** | memory-forget/ttl/gdpr |
| M061 | **foundation** | learning_engine promote |
| M062 | **foundation** | learning conflict paths |
| M063 | **foundation** | distill/deprecate |
| M064 | **full** | wings/rooms |
| M065 | **full** | backup_manager encrypted |
| M066 | **full** | profile-bundle |
| M067 | **foundation** | history/runs; cost search partial |
| M068 | **foundation** | preferences module |
| M069 | **full** | skills |
| M070 | **full** | skill_permissions |
| M071 | **full** | default superai front door |
| M072 | **full** | superai do |
| M073 | **full** | doctor |
| M074 | **full** | status --cost |
| M075 | **full** | install wizard |
| M076 | **full** | host-tools |
| M077 | **full** | superai_agent TUI |
| M078 | **full** | slash palette /commands |
| M079 | **foundation** | JSON on many cmds; not all CLI cmds |
| M080 | **foundation** | exit_codes module; not wired all exits |
| M081 | **foundation** | typer help; uneven examples |
| M082 | **foundation** | typer completion enabled |
| M083 | **full** | config get/set |
| M084 | **full** | version_check/update |
| M085 | **full** | diagnostics zip |
| M086 | **full** | test_improvement_v4/v5 safety |
| M087 | **full** | eval_golden |
| M088 | **full** | smoke_harness |
| M089 | **host** | live_smoke_complete; needs keys for live_passed |
| M090 | **foundation** | contract tests major paths not full top-30 suite |
| M091 | **stub** | no formal cold-start budget CI gate |
| M092 | **foundation** | mock fixtures in tests |
| M093 | **foundation** | MCP budget/contract on superai_run |
| M094 | **foundation** | web token auth optional |
| M095 | **full** | agent-graph SVG |
| M096 | **full** | goals + schedule caps |
| M097 | **full** | plugin sha path |
| M098 | **full** | constitution + policy |
| M099 | **foundation** | docs exist; threat model partial |
| M100 | **foundation** | mock/live flags; dashboard partial honesty |

## Should (S101–S200)

| ID | Status | Evidence / gap |
|----|--------|----------------|
| S101 | **full** | agent_todos |
| S102 | **full** | spec_mode |
| S103 | **foundation** | roles plan vs build; no separate arch flag |
| S104 | **stub** | no dedicated self-critique module |
| S105 | **foundation** | quality_gates pytest |
| S106 | **foundation** | ruff optional in gates |
| S107 | **full** | workspace_index |
| S108 | **stub** | no real symbol index/LSP goto |
| S109 | **foundation** | ci_why + do path |
| S110 | **foundation** | pr_review |
| S111 | **stub** | no safe multi-file rename engine |
| S112 | **stub** | no dedicated dep upgrade agent |
| S113 | **stub** | no migration dry-run product |
| S114 | **foundation** | security patterns; not full SCA |
| S115 | **stub** | no license checker |
| S116 | **foundation** | git-helper |
| S117 | **stub** | no merge conflict solver |
| S118 | **full** | git_diff_apply unified |
| S119 | **foundation** | multimodal vision path |
| S120 | **stub** | no PDF attach pipeline |
| S121 | **foundation** | browser_tool playwright optional |
| S122 | **full** | notebook_runner |
| S123 | **foundation** | databao SQL; allowlist partial |
| S124 | **foundation** | ci_why log triage |
| S125 | **full** | session resume |
| S126 | **full** | result_cache opt-in |
| S127 | **stub** | no provider prompt-cache integration |
| S128 | **foundation** | local then escalate pattern |
| S129 | **stub** | no mid-task demotion controller |
| S130 | **foundation** | adaptive escalate on weak answer |
| S131 | **foundation** | budget config per run; weak project policies |
| S132 | **stub** | no per-command budget map |
| S133 | **foundation** | cost_forecast module |
| S134 | **foundation** | budget snapshot; weak weekly report |
| S135 | **foundation** | status --cost cache counts |
| S136 | **stub** | no token waterfall UI |
| S137 | **stub** | no stagger scheduler |
| S138 | **foundation** | front_door + cheap-first |
| S139 | **stub** | no systematic tool output compressor |
| S140 | **foundation** | read mtime cache |
| S141 | **stub** | no dedicated embedding cache layer |
| S142 | **stub** | no batch embed API |
| S143 | **foundation** | lazy imports ad hoc |
| S144 | **stub** | no cold-start optimization program |
| S145 | **stub** | no model warmup daemon |
| S146 | **stub** | no history-based max_members learner |
| S147 | **foundation** | CancelToken |
| S148 | **stub** | stream cancel incomplete |
| S149 | **foundation** | profiles cheap sticky via config |
| S150 | **foundation** | ab_routing |
| S151 | **full** | models-refresh-openrouter |
| S152 | **full** | capability_tags |
| S153 | **stub** | no per-model context window enforcement |
| S154 | **foundation** | tool_protocol JSON |
| S155 | **foundation** | validate-json; not full schema retry |
| S156 | **foundation** | native anthropic/google callers partial |
| S157 | **full** | path_which windows |
| S158 | **stub** | no dedicated WSL bridge |
| S159 | **foundation** | container_sandbox flag |
| S160 | **foundation** | net_safety public-only |
| S161 | **full** | tool_timeouts |
| S162 | **stub** | no global concurrency governor |
| S163 | **stub** | no interactive vs batch queue split |
| S164 | **foundation** | model_pinning |
| S165 | **stub** | no team shared policy store |
| S166 | **foundation** | doctor/readiness messages |
| S167 | **stub** | no GPU detect |
| S168 | **foundation** | openrouter catalog |
| S169 | **foundation** | nvidia models in catalog |
| S170 | **stub** | no multi-key rotation |
| S171 | **full** | project_memory |
| S172 | **stub** | no memory confidence scores UI |
| S173 | **stub** | no confirm-before-memory-write gate |
| S174 | **foundation** | memory-palace search CLI not full TUI |
| S175 | **stub** | no injection citations UI |
| S176 | **stub** | no conflict UI |
| S177 | **full** | tenant-export/import |
| S178 | **stub** | no org skills registry service |
| S179 | **foundation** | recipes as templates |
| S180 | **foundation** | msg-inbound |
| S181 | **foundation** | goals notify |
| S182 | **stub** | rbac stub only |
| S183 | **foundation** | audit log export partial |
| S184 | **foundation** | memory-ttl |
| S185 | **foundation** | encrypted backup; session encrypt partial |
| S186 | **foundation** | web app memory/status; not full session browser |
| S187 | **stub** | no SSE progress |
| S188 | **foundation** | vscode extension thin |
| S189 | **absent** | no JetBrains plugin |
| S190 | **foundation** | PWA static shell |
| S191 | **stub** | parked seasonal theme flag only |
| S192 | **absent** | no keybind config |
| S193 | **foundation** | paste mode in agent TUI |
| S194 | **stub** | no rich clipboard API |
| S195 | **foundation** | init/onboard |
| S196 | **full** | recipes |
| S197 | **foundation** | explain-run; mermaid via agent-graph partial |
| S198 | **full** | profile-suggest |
| S199 | **full** | onboard quest |
| S200 | **full** | whats-new |

## Nice (N201–N300)

| ID | Status | Evidence / gap |
|----|--------|----------------|
| N201 | **stub** | no Ctrl+K palette app |
| N202 | **foundation** | NL do/ask routes |
| N203 | **full** | macros |
| N204 | **stub** | no pipeline operator |
| N205 | **foundation** | watch_mode poll limited |
| N206 | **foundation** | goals/schedule not full daemon |
| N207 | **stub** | no SSH remote agent product |
| N208 | **stub** | no tmux multiplex |
| N209 | **foundation** | TUI panels partial |
| N210 | **absent** | no vim mode |
| N211 | **absent** | no mouse TUI |
| N212 | **stub** | vision files not clipboard paste |
| N213 | **foundation** | voice_io optional |
| N214 | **foundation** | i18n module partial |
| N215 | **absent** | no a11y TUI audit |
| N216 | **stub** | theme flag only |
| N217 | **stub** | theme flag only |
| N218 | **stub** | no full replay tape product |
| N219 | **foundation** | session export md |
| N220 | **stub** | no shareable sanitized bundle |
| N221 | **foundation** | eval_golden |
| N222 | **stub** | no private leaderboard |
| N223 | **stub** | no YAML agent DSL parser product |
| N224 | **foundation** | plugin-catalog |
| N225 | **foundation** | sha256 verify |
| N226 | **stub** | no skill versioning |
| N227 | **full** | hooks pre/post |
| N228 | **foundation** | policy module simple |
| N229 | **stub** | sso_status only |
| N230 | **absent** | no SCIM |
| N231 | **foundation** | lsp_bridge compile stub |
| N232 | **absent** | no goto-def |
| N233 | **absent** | no rename symbol |
| N234 | **absent** | no extract method |
| N235 | **absent** | no dead code tool |
| N236 | **absent** | no complexity map |
| N237 | **stub** | tdd only |
| N238 | **absent** | no mutation testing |
| N239 | **absent** | no flaky hunter |
| N240 | **stub** | no snapshot review UX |
| N241 | **stub** | no compose helper product |
| N242 | **stub** | no k8s dry-run product |
| N243 | **stub** | no terraform explain |
| N244 | **stub** | no graphql assist |
| N245 | **stub** | no openapi product |
| N246 | **stub** | no grpc helpers |
| N247 | **foundation** | ci_why |
| N248 | **absent** | no game engine log mode |
| N249 | **foundation** | databao/notebook |
| N250 | **foundation** | palace embeddings; not full repo RAG product |
| N251 | **stub** | no AST edit engine |
| N252 | **stub** | gates ruff optional |
| N253 | **absent** | no import organizer |
| N254 | **absent** | no license header tool |
| N255 | **absent** | no CODEOWNERS routing |
| N256 | **stub** | workspace_index basic |
| N257 | **stub** | no build system detect |
| N258 | **stub** | index not incremental product |
| N259 | **foundation** | pr_review summaries |
| N260 | **full** | ci-why |
| N261 | **full** | role_debate |
| N262 | **stub** | no red/blue security product |
| N263 | **stub** | debate roles only |
| N264 | **stub** | no QA-only-diff agent |
| N265 | **stub** | no release captain product |
| N266 | **stub** | no incident commander |
| N267 | **stub** | no runbook executor product |
| N268 | **stub** | no multi-repo PR coord |
| N269 | **stub** | no dep PR stack |
| N270 | **absent** | no feature flag assistant |
| N271 | **absent** | no canary analysis |
| N272 | **absent** | no metrics anomaly |
| N273 | **absent** | no cloud bill anomaly |
| N274 | **absent** | no SLA report |
| N275 | **stub** | can do via plan agent |
| N276 | **stub** | can do via plan agent |
| N277 | **stub** | todos only |
| N278 | **foundation** | github + ticket stub |
| N279 | **absent** | no design tokens |
| N280 | **stub** | browser optional |
| N281 | **stub** | no homebrew formula depth |
| N282 | **stub** | no official Dockerfile productized |
| N283 | **absent** | no nix flake |
| N284 | **foundation** | packaging/github-action sample |
| N285 | **absent** | no gitlab component |
| N286 | **foundation** | pre-commit sample |
| N287 | **absent** | no devcontainer feature |
| N288 | **absent** | no codespaces template |
| N289 | **absent** | no raycast |
| N290 | **stub** | messengers only |
| N291 | **foundation** | telegram config partial |
| N292 | **foundation** | slack partial |
| N293 | **foundation** | notion_stub |
| N294 | **stub** | export md only |
| N295 | **absent** | no browser extension |
| N296 | **absent** | no figma |
| N297 | **absent** | no datadog pull |
| N298 | **foundation** | host-tools cloud CLIs check |
| N299 | **foundation** | plugin-catalog |
| N300 | **foundation** | recipes as awesome list seed |

## Parked (P301–P400)

| ID | Status | Evidence / gap |
|----|--------|----------------|
| P301 | **stub** | vanity flags via parked_features |
| P302 | **stub** | vanity flags via parked_features |
| P303 | **stub** | vanity flags via parked_features |
| P304 | **stub** | vanity flags via parked_features |
| P305 | **stub** | vanity flags via parked_features |
| P306 | **stub** | vanity flags via parked_features |
| P307 | **stub** | vanity flags via parked_features |
| P308 | **stub** | vanity flags via parked_features |
| P309 | **stub** | vanity flags via parked_features |
| P310 | **stub** | vanity flags via parked_features |
| P311 | **stub** | vanity flags via parked_features |
| P312 | **stub** | vanity flags via parked_features |
| P313 | **stub** | vanity flags via parked_features |
| P314 | **stub** | vanity flags via parked_features |
| P315 | **stub** | vanity flags via parked_features |
| P316 | **stub** | vanity flags via parked_features |
| P317 | **stub** | vanity flags via parked_features |
| P318 | **stub** | vanity flags via parked_features |
| P319 | **stub** | vanity flags via parked_features |
| P320 | **stub** | vanity flags via parked_features |
| P321 | **stub** | platform experimental stub |
| P322 | **stub** | platform experimental stub |
| P323 | **stub** | platform experimental stub |
| P324 | **stub** | platform experimental stub |
| P325 | **stub** | platform experimental stub |
| P326 | **stub** | platform experimental stub |
| P327 | **stub** | platform experimental stub |
| P328 | **stub** | platform experimental stub |
| P329 | **stub** | platform experimental stub |
| P330 | **stub** | platform experimental stub |
| P331 | **stub** | platform experimental stub |
| P332 | **stub** | platform experimental stub |
| P333 | **stub** | platform experimental stub |
| P334 | **stub** | platform experimental stub |
| P335 | **stub** | platform experimental stub |
| P336 | **stub** | platform experimental stub |
| P337 | **stub** | platform experimental stub |
| P338 | **stub** | platform experimental stub |
| P339 | **stub** | platform experimental stub |
| P340 | **stub** | platform experimental stub |
| P341 | **stub** | platform experimental stub |
| P342 | **stub** | platform experimental stub |
| P343 | **stub** | platform experimental stub |
| P344 | **stub** | platform experimental stub |
| P345 | **stub** | platform experimental stub |
| P346 | **stub** | enterprise_stubs / rbac/sso status |
| P347 | **stub** | enterprise_stubs / rbac/sso status |
| P348 | **stub** | enterprise_stubs / rbac/sso status |
| P349 | **stub** | enterprise_stubs / rbac/sso status |
| P350 | **stub** | enterprise_stubs / rbac/sso status |
| P351 | **stub** | enterprise_stubs / rbac/sso status |
| P352 | **stub** | enterprise_stubs / rbac/sso status |
| P353 | **stub** | enterprise_stubs / rbac/sso status |
| P354 | **stub** | enterprise_stubs / rbac/sso status |
| P355 | **stub** | enterprise_stubs / rbac/sso status |
| P356 | **stub** | enterprise_stubs / rbac/sso status |
| P357 | **stub** | enterprise_stubs / rbac/sso status |
| P358 | **stub** | enterprise_stubs / rbac/sso status |
| P359 | **stub** | enterprise_stubs / rbac/sso status |
| P360 | **stub** | enterprise_stubs / rbac/sso status |
| P361 | **stub** | enterprise_stubs / rbac/sso status |
| P362 | **stub** | enterprise_stubs / rbac/sso status |
| P363 | **stub** | enterprise_stubs / rbac/sso status |
| P364 | **stub** | enterprise_stubs / rbac/sso status |
| P365 | **stub** | enterprise_stubs / rbac/sso status |
| P366 | **foundation** | agent-only mode prefers API over CLI |
| P367 | **stub** | no full CLI reimplementation |
| P368 | **foundation** | chroma experimental flag + optional import |
| P369 | **stub** | overbuild stub catalog entry |
| P370 | **stub** | overbuild stub catalog entry |
| P371 | **stub** | overbuild stub catalog entry |
| P372 | **stub** | overbuild stub catalog entry |
| P373 | **stub** | overbuild stub catalog entry |
| P374 | **stub** | overbuild stub catalog entry |
| P375 | **stub** | overbuild stub catalog entry |
| P376 | **stub** | overbuild stub catalog entry |
| P377 | **stub** | overbuild stub catalog entry |
| P378 | **stub** | overbuild stub catalog entry |
| P379 | **stub** | overbuild stub catalog entry |
| P380 | **stub** | overbuild stub catalog entry |
| P381 | **stub** | overbuild stub catalog entry |
| P382 | **stub** | overbuild stub catalog entry |
| P383 | **stub** | overbuild stub catalog entry |
| P384 | **stub** | overbuild stub catalog entry |
| P385 | **stub** | overbuild stub catalog entry |
| P386 | **refuse** | hard refuse safety policy |
| P387 | **refuse** | hard refuse safety policy |
| P388 | **refuse** | hard refuse safety policy |
| P389 | **refuse** | hard refuse safety policy |
| P390 | **refuse** | hard refuse safety policy |
| P391 | **refuse** | hard refuse safety policy |
| P392 | **refuse** | hard refuse safety policy |
| P393 | **refuse** | hard refuse safety policy |
| P394 | **refuse** | hard refuse safety policy |
| P395 | **refuse** | hard refuse safety policy |
| P396 | **refuse** | hard refuse safety policy |
| P397 | **refuse** | hard refuse safety policy |
| P398 | **refuse** | hard refuse safety policy |
| P399 | **refuse** | hard refuse safety policy |
| P400 | **refuse** | hard refuse safety policy |

## Bucket rollups

### Must M001–M100

| Status | Count |
|--------|------:|
| full | 72 |
| foundation | 26 |
| stub | 1 |
| host | 1 |

### Should S101–S200

| Status | Count |
|--------|------:|
| full | 17 |
| foundation | 45 |
| stub | 36 |
| absent | 2 |

### Nice N201–N300

| Status | Count |
|--------|------:|
| full | 4 |
| foundation | 25 |
| stub | 42 |
| absent | 29 |

### Parked P301–P400

| Status | Count |
|--------|------:|
| foundation | 2 |
| stub | 83 |
| refuse | 15 |

## Recommended next engineering (from this audit)

1. Raise **M001 / M008 / M079 / M080** foundation → full (all public entrypoints).
2. Treat **S108 / S111** (symbol/refactor) as a dedicated coding-agent epic.
3. Do not claim **N231–N260** full — most are absent/stub.
4. Run **M089** with keys: `superai phase6-smoke --allow-live`.
5. Keep **P386–P400** refuse-closed.

## Related

- Backlog: `docs/IMPROVEMENT_V6_BACKLOG.md`
- Runtime: `superai v6-status`
- Parked: `superai parked catalog`

