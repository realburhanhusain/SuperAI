# SuperAI V6 Backlog — Detailed line-by-line scorecard

**Generated:** 2026-07-16  
**Total items:** 400 (M100 + S100 + N100 + P100)  
**Purpose:** Honest status **and reasoning** per ID — not inflated “all done.”  

Each item lists:

1. **Backlog title** (from `docs/IMPROVEMENT_V6_BACKLOG.md`)
2. **Status** (classification)
3. **Why** (evidence + gap that justified the status)

## Status legend

| Status | Meaning | When we use it |
|--------|---------|----------------|
| **full** | Production-usable for the stated intent | Real code + tests (or equivalent proof) covering the backlog wording |
| **foundation** | Real working code; DoD depth incomplete | Core mechanism exists; missing universality, UX, or hardening |
| **stub** | Surface/flag/sample only | Catalog flag, sample hook, or thin placeholder — not a product |
| **host** | Code path exists; needs keys/environment | Implementation done; live proof requires host credentials |
| **refuse** | Intentionally refuse-closed (safety) | Explicit policy: must not ship as a feature |
| **absent** | No meaningful implementation | Zero or near-zero code for this intent |

## Summary counts

| Status | Count | % of 400 |
|--------|------:|---------:|
| full | 191 | 47.8% |
| foundation | 0 | 0.0% |
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

**Honest headline:** Strong **Must** coverage (mostly full/foundation). Many **Should/Nice** items are foundation or stub/absent. **Parked** is mostly stubs/flags; abuse IDs are refuse-closed. **This is not 400× full production features.**

### Quick index tables (status only)

Full narrative for every ID is below. These tables are for scanning.

#### Must M001–M100

| ID | Status | Title |
|----|--------|-------|
| M001 | **full** | Hard budget ceilings on every spend path (CLI, MCP, HTTP,... |
| M002 | **full** | Accurate cost from real tokens × registry rates |
| M003 | **full** | Pre-flight cost estimate before multi-member boards |
| M004 | **full** | Dry-run / plan mode cannot mutate disk or git |
| M005 | **full** | Permission model plan/ask/auto/yolo with safe defaults |
| M006 | **full** | Workspace jail fail-closed for tools and external CLIs |
| M007 | **full** | Side-effect audit log (write/delete/run, run_id) |
| M008 | **full** | Stable result contract on every public command |
| M009 | **full** | Error taxonomy for scripts (`budget`, `readiness`, `timeo... |
| M010 | **full** | Provider readiness check before live calls |
| M011 | **full** | Failover ordered, bounded, logged |
| M012 | **full** | Secrets never printed in logs/errors/TUI |
| M013 | **full** | Keyring/env secret store with rotate/list |
| M014 | **full** | SSRF protection on URL/fetch tools |
| M015 | **full** | Prompt-injection defenses for tool loops |
| M016 | **full** | Tenant isolation for shared memory |
| M017 | **full** | Cancel / Ctrl+C stops workers cooperatively |
| M018 | **full** | Timeouts on model, CLI, and tool ops |
| M019 | **full** | Reproducible explain-run from `run_id` |
| M020 | **full** | Offline mock mode never claims live success |
| M021 | **full** | Reliable multi-turn agent session (resume/export/undo) |
| M022 | **full** | Strict tool protocol (JSON schema tools) |
| M023 | **full** | Parallel independent tools (read/grep/glob) |
| M024 | **full** | Idempotent file writes |
| M025 | **full** | Change-set staging + apply/reject |
| M026 | **full** | Diff check before apply |
| M027 | **full** | Real token streaming where supported |
| M028 | **full** | Context packing under hard token budget |
| M029 | **full** | Session compaction preserving decisions/todos |
| M030 | **full** | Agent roles: build / plan / ask with boundaries |
| M031 | **full** | Front-door routing: agent vs board vs orchestrator |
| M032 | **full** | Front-door confidence when routing ambiguous |
| M033 | **full** | Local-first with escalate-to-premium on failure |
| M034 | **full** | Cheap-first for summarize/plan steps |
| M035 | **full** | Complexity → board member count |
| M036 | **full** | Board early-exit on strong consensus |
| M037 | **full** | Worker diversity (1 premium + N cheap) |
| M038 | **full** | Worktree isolation for risky writes |
| M039 | **full** | Test-driven loop (red/green) first-class |
| M040 | **full** | PR/diff review via multi-CLI + contracts |
| M041 | **full** | Universal OpenAI-compatible registration |
| M042 | **full** | First-class local: Ollama / LM Studio / vLLM |
| M043 | **full** | External CLI discovery on PATH (Windows-hardened) |
| M044 | **full** | CLI inner-model selection (`cli:name@model`) |
| M045 | **full** | Unified member catalog (API + CLI + local) |
| M046 | **full** | Live probe of available members |
| M047 | **full** | Health circuits per provider |
| M048 | **full** | Rate-limit queue / backoff |
| M049 | **full** | Model blacklist after repeated failures |
| M050 | **full** | Bandit / learned routing from outcomes |
| M051 | **full** | Bakeoff with report + pin winner |
| M052 | **full** | Compare command with contract |
| M053 | **full** | Council with voting modes |
| M054 | **full** | Parallel multi-CLI opinions with merge |
| M055 | **full** | Cost router shrinks boards under budget |
| M056 | **full** | Central Memory Palace inject before major runs |
| M057 | **full** | Write-back of successful outcomes |
| M058 | **full** | Semantic search with tenant tags |
| M059 | **full** | Smart memory inject (rank + token cap) |
| M060 | **full** | Memory forget / TTL / erase |
| M061 | **full** | Learning: promote durable patterns only |
| M062 | **full** | Conflict resolution for contradictory memories |
| M063 | **full** | Distill / deprecate redundant memories |
| M064 | **full** | Wings/rooms navigation |
| M065 | **full** | Encrypted backup of local SuperAI state |
| M066 | **full** | Profile export/import |
| M067 | **full** | Run history searchable by task/cost/model |
| M068 | **full** | Preferences that bias routing |
| M069 | **full** | Skills library (reusable playbooks) |
| M070 | **full** | Skill permissions (what a skill may touch) |
| M071 | **full** | Zero-subcommand launches useful front door |
| M072 | **full** | One-shot `do "…"` routing |
| M073 | **full** | Doctor diagnoses real failures |
| M074 | **full** | Status with spend + health + cache |
| M075 | **full** | Install/onboard wizard (Windows-first) |
| M076 | **full** | Host-tools check/install matrix |
| M077 | **full** | Rich TUI: tools, cost, permission live |
| M078 | **full** | Slash command palette + help |
| M079 | **full** | JSON output mode for automation |
| M080 | **full** | Trustworthy process exit codes |
| M081 | **full** | High-quality `--help` and examples |
| M082 | **full** | Shell completion |
| M083 | **full** | Config get/set with validation |
| M084 | **full** | Version / update check |
| M085 | **full** | Diagnostics zip for support |
| M086 | **full** | Unit suite for safety/money (plan, budget, jail) |
| M087 | **full** | Golden offline eval set |
| M088 | **full** | Smoke harness that never false-passes |
| M089 | **host** | Live multi-provider smoke matrix (host keys) |
| M090 | **full** | Contract tests on top 30 commands |
| M091 | **stub** | Performance budgets for cold start |
| M092 | **full** | Deterministic mock fixtures for CI |
| M093 | **full** | MCP parity with CLI safety rules |
| M094 | **full** | Web API auth for non-loopback |
| M095 | **full** | Graph of runs (models/tools/cost) |
| M096 | **full** | Schedule/goals with caps (no yolo inherit) |
| M097 | **full** | Plugin install with sha256 verify |
| M098 | **full** | Constitution/policy hooks for org rules |
| M099 | **full** | Architecture + quickstart + threat docs |
| M100 | **full** | Honest dashboard: mock vs live |

#### Should S101–S200

| ID | Status | Title |
|----|--------|-------|
| S101 | **full** | Agent-maintained todo list across long tasks |
| S102 | **full** | Spec-first: plan → approve → implement |
| S103 | **full** | Architecture mode vs implementation mode |
| S104 | **stub** | Self-critique pass before claiming done |
| S105 | **full** | Auto test discovery and run after edits |
| S106 | **full** | Lint/typecheck integration post-edit |
| S107 | **full** | Repo map / workspace index for large trees |
| S108 | **stub** | Symbol-aware navigation (beyond grep) |
| S109 | **full** | Fix CI failure from log paste |
| S110 | **full** | Explain PR with file-level findings |
| S111 | **stub** | Multi-file refactor with rename safety |
| S112 | **stub** | Dependency upgrade assistant |
| S113 | **stub** | DB/schema migration dry-run helper |
| S114 | **full** | Security scan hooks (secrets, vulns) |
| S115 | **stub** | License/compliance check on new deps |
| S116 | **full** | Commit message + branch naming helpers |
| S117 | **stub** | Safe conflict assistance for merges |
| S118 | **full** | `git apply`-compatible patch format |
| S119 | **full** | Vision for UI bug screenshots |
| S120 | **stub** | PDF/doc attach for requirements |
| S121 | **full** | Browser tool for local web verification |
| S122 | **full** | Notebook run/repair mode |
| S123 | **full** | SQL agent with allowlisted DBs |
| S124 | **full** | Log triage mode (stack traces) |
| S125 | **full** | Continue last session smart resume |
| S126 | **full** | Cross-session semantic result cache (opt-in) |
| S127 | **stub** | Prompt/prefix cache for long system prompts |
| S128 | **full** | Speculative local draft → cloud polish |
| S129 | **stub** | Mid-task model demotion when task simplifies |
| S130 | **full** | Escalate only on quality gate failure |
| S131 | **full** | Per-project budget policies |
| S132 | **stub** | Per-command budget overrides |
| S133 | **full** | Cost forecast before long boards |
| S134 | **full** | Daily/weekly spend reports |
| S135 | **full** | Cache hit rate in status |
| S136 | **stub** | Token waterfall visualization |
| S137 | **stub** | Stagger expensive board members |
| S138 | **full** | Always-local for trivial “what is” questions |
| S139 | **stub** | Compress tool outputs before re-feed |
| S140 | **full** | Drop redundant reads via mtime index |
| S141 | **stub** | Shared embedding cache |
| S142 | **stub** | Batch embeddings |
| S143 | **full** | Lazy-load heavy deps |
| S144 | **stub** | Faster cold start (defer imports) |
| S145 | **stub** | Optional background model warmup |
| S146 | **stub** | Adaptive max_members from history |
| S147 | **full** | Cancel generation on user interrupt |
| S148 | **stub** | Partial stream cancel stops workers |
| S149 | **full** | Sticky cheap mode per repo |
| S150 | **full** | A/B routing experiments with reports |
| S151 | **full** | Catalog auto-refresh (e.g. OpenRouter) |
| S152 | **full** | Capability tags (vision, tools, long-context) |
| S153 | **stub** | Context window awareness per model |
| S154 | **full** | JSON-mode enforcement for tools |
| S155 | **full** | Structured output validation + retry |
| S156 | **full** | Native Anthropic/Google adapters (depth) |
| S157 | **full** | Better Windows CLI shim resolution |
| S158 | **stub** | WSL/path interop helpers |
| S159 | **full** | Container sandbox for bash tools |
| S160 | **full** | Network allowlist for tools |
| S161 | **full** | Per-tool timeout configs |
| S162 | **stub** | Per-provider concurrency caps |
| S163 | **stub** | Priority queue interactive vs batch |
| S164 | **full** | Pin model per task type |
| S165 | **stub** | Team-shared routing policies |
| S166 | **full** | Clear UX when local runtime down |
| S167 | **stub** | GPU/local resource detect for pick |
| S168 | **full** | OpenRouter strategy knobs |
| S169 | **full** | NVIDIA NIM first-class depth |
| S170 | **stub** | Multi-key rotation per provider |
| S171 | **full** | Project-scoped vs global memory |
| S172 | **stub** | Memory confidence scores |
| S173 | **stub** | Human confirm before sensitive memory write |
| S174 | **full** | Memory search in TUI |
| S175 | **stub** | “Why injected” citations |
| S176 | **stub** | Conflict UI when memories disagree |
| S177 | **full** | Team palace export/import |
| S178 | **stub** | Org-level skills registry |
| S179 | **full** | Shared run templates |
| S180 | **full** | Secure messenger inbound tasking |
| S181 | **full** | Notify only on approval-needed / done |
| S182 | **stub** | Multi-user permission roles |
| S183 | **full** | Audit export for compliance |
| S184 | **full** | Retention policies |
| S185 | **full** | Encryption at rest for sessions |
| S186 | **full** | Web session browser |
| S187 | **stub** | SSE live progress for web |
| S188 | **full** | VS Code: run + stream + apply set |
| S189 | **absent** | JetBrains thin plugin |
| S190 | **full** | Useful offline PWA shell |
| S191 | **stub** | TUI themes |
| S192 | **absent** | Keybind customization |
| S193 | **full** | Better multi-line editor / paste |
| S194 | **stub** | Clipboard integration |
| S195 | **full** | `init` project templates |
| S196 | **full** | Recipe gallery (fix bug, add API, …) |
| S197 | **full** | Explain-run with mermaid graph |
| S198 | **full** | Profile auto-suggest + one-key apply |
| S199 | **full** | Onboarding quest (first 5 wins) |
| S200 | **full** | In-CLI changelog / what’s new |

#### Nice N201–N300

| ID | Status | Title |
|----|--------|-------|
| N201 | **stub** | Fuzzy command palette (Ctrl+K) |
| N202 | **full** | NL → any command with preview |
| N203 | **full** | Command macros / aliases |
| N204 | **stub** | Pipelines between SuperAI modes |
| N205 | **full** | Watch mode (re-run on change) |
| N206 | **full** | Daemon for goals/schedules |
| N207 | **stub** | Remote headless agent over SSH |
| N208 | **stub** | Multiplexed sessions (tmux-like) |
| N209 | **full** | Split-pane TUI |
| N210 | **absent** | Vim keys in TUI |
| N211 | **absent** | Optional mouse support |
| N212 | **stub** | Image paste from clipboard |
| N213 | **full** | Optional voice channel |
| N214 | **full** | Full i18n for CLI/TUI |
| N215 | **absent** | Screen-reader friendly TUI |
| N216 | **stub** | Colorblind-safe palettes |
| N217 | **stub** | High-contrast mode |
| N218 | **stub** | Replay tape for demos |
| N219 | **full** | Publish session as markdown |
| N220 | **stub** | Shareable sanitized run bundles |
| N221 | **full** | Public benchmark harness |
| N222 | **stub** | Private model leaderboard on your repo |
| N223 | **stub** | Custom agents DSL (YAML) |
| N224 | **full** | Plugin marketplace UX |
| N225 | **full** | Signed plugins |
| N226 | **stub** | Skill versioning |
| N227 | **full** | Pre/post tool hooks |
| N228 | **full** | Simple policy-as-code |
| N229 | **stub** | Enterprise SSO for web API |
| N230 | **absent** | SCIM provisioning (stretch) |
| N231 | **full** | LSP diagnostics integration |
| N232 | **absent** | Go-to-definition via LSP |
| N233 | **absent** | Rename symbol across project |
| N234 | **absent** | Extract method/function assist |
| N235 | **absent** | Dead code detection |
| N236 | **absent** | Complexity hotspots map |
| N237 | **stub** | Coverage-guided test generation |
| N238 | **absent** | Mutation testing opt-in |
| N239 | **absent** | Flaky test hunter |
| N240 | **stub** | Snapshot test updates with review |
| N241 | **stub** | Docker compose helpers |
| N242 | **stub** | K8s dry-run helpers |
| N243 | **stub** | Terraform plan explain |
| N244 | **stub** | GraphQL schema assist |
| N245 | **stub** | OpenAPI generate + validate |
| N246 | **stub** | Proto/gRPC helpers |
| N247 | **full** | Mobile build log triage |
| N248 | **absent** | Game-engine log modes (niche) |
| N249 | **full** | Dataframe/SQL notebook hybrid |
| N250 | **full** | Local vector search over repo chunks |
| N251 | **stub** | AST-based edit tools |
| N252 | **stub** | Format-on-write |
| N253 | **absent** | Import organizer |
| N254 | **absent** | License header inject |
| N255 | **absent** | CODEOWNERS-aware routing |
| N256 | **stub** | Monorepo package awareness |
| N257 | **stub** | Build system detect (make/nx/bazel) |
| N258 | **stub** | Incremental index updates |
| N259 | **full** | Semantic diff summaries |
| N260 | **full** | One-command “why did CI fail” |
| N261 | **full** | Multi-agent debate with roles |
| N262 | **stub** | Red team vs blue team security review |
| N263 | **stub** | PM agent → engineer agent handoff |
| N264 | **stub** | QA agent sees only diffs |
| N265 | **stub** | Release captain checklist agent |
| N266 | **stub** | Incident commander mode |
| N267 | **stub** | On-call runbook executor |
| N268 | **stub** | Multi-repo cross-PR coordination |
| N269 | **stub** | Dependency PR stack helper |
| N270 | **absent** | Feature flag rollout assistant |
| N271 | **absent** | Canary analysis helper |
| N272 | **absent** | Metrics anomaly explain |
| N273 | **absent** | Cloud bill cost anomaly (opt-in) |
| N274 | **absent** | SLA report generator |
| N275 | **stub** | ADR writer |
| N276 | **stub** | RFC co-author |
| N277 | **stub** | Meeting notes → tasks |
| N278 | **full** | Ticket sync (Jira/Linear/GitHub) |
| N279 | **absent** | Design token consistency checks |
| N280 | **stub** | Web UI accessibility audit assist |
| N281 | **stub** | Homebrew / winget / choco packages |
| N282 | **stub** | Official Docker image |
| N283 | **absent** | Nix flake |
| N284 | **full** | GitHub Action “superai review” |
| N285 | **absent** | GitLab CI component |
| N286 | **full** | Pre-commit hook |
| N287 | **absent** | Devcontainer feature |
| N288 | **absent** | Codespaces template |
| N289 | **absent** | Raycast/Alfred extension |
| N290 | **stub** | Discord bot thin client |
| N291 | **full** | Telegram production hardening |
| N292 | **full** | Slack slash commands |
| N293 | **full** | Notion sync when key present |
| N294 | **stub** | Obsidian vault export |
| N295 | **absent** | Browser extension send-to-SuperAI |
| N296 | **absent** | Figma comment → task (stretch) |
| N297 | **absent** | Datadog/NewRelic log pull (opt-in) |
| N298 | **full** | Cloud provider CLIs as gated tools |
| N299 | **full** | Community skills marketplace |
| N300 | **full** | Public awesome-recipes catalog |

#### Parked P301–P400

| ID | Status | Title |
|----|--------|-------|
| P301 | **stub** | Rebrand SuperAI to another product name |
| P302 | **stub** | Pixel-match OpenCode/Claude Code UI |
| P303 | **stub** | Marketing site redesign as engineering work |
| P304 | **stub** | Animated splash screens |
| P305 | **stub** | NFT/badge gamification |
| P306 | **stub** | Social share buttons in CLI |
| P307 | **stub** | Custom ASCII art every run |
| P308 | **stub** | Seasonal themes (required) |
| P309 | **stub** | Mascot program |
| P310 | **stub** | Startup sounds |
| P311 | **stub** | “AI CEO” persona as default |
| P312 | **stub** | Hype agent names |
| P313 | **stub** | Brand-war dark-mode mandates |
| P314 | **stub** | Consumer app-store packaging |
| P315 | **stub** | Mobile-first full agent |
| P316 | **stub** | Electron desktop shell v1 |
| P317 | **stub** | VR pair programming |
| P318 | **stub** | Emoji-only mode |
| P319 | **stub** | Meme responses |
| P320 | **stub** | Public user ranking |
| P321 | **stub** | Full IDE replacement |
| P322 | **stub** | Full browser OS agent |
| P323 | **stub** | Multi-tenant SaaS before local excellence |
| P324 | **stub** | Billing/Stripe product |
| P325 | **stub** | Marketplace payments |
| P326 | **stub** | Cryptocurrency payments |
| P327 | **stub** | Blockchain audit log |
| P328 | **stub** | Homomorphic encryption of prompts |
| P329 | **stub** | Federated learning across users |
| P330 | **stub** | On-device tiny LLM training |
| P331 | **stub** | Auto-fine-tune every repo by default |
| P332 | **stub** | 1000-node cluster scheduler |
| P333 | **stub** | Kubernetes operator early |
| P334 | **stub** | Service mesh integration |
| P335 | **stub** | Full observability vendor product |
| P336 | **stub** | Proprietary protocol instead of MCP |
| P337 | **stub** | Replace git |
| P338 | **stub** | Replace language servers wholesale |
| P339 | **stub** | Custom terminal emulator product |
| P340 | **stub** | Hardware appliance |
| P341 | **stub** | Phone companion app v1 |
| P342 | **stub** | AR glasses integration |
| P343 | **stub** | Voice-only primary interface |
| P344 | **stub** | Always-listening mic daemon |
| P345 | **stub** | Webcam emotion detection |
| P346 | **stub** | Full SOC2 “as a feature” |
| P347 | **stub** | FedRAMP packaging |
| P348 | **stub** | Multi-region active-active cloud |
| P349 | **stub** | 50-role RBAC day one |
| P350 | **stub** | Deep LDAP |
| P351 | **stub** | Custom legal hold workflows |
| P352 | **stub** | eDiscovery UI |
| P353 | **stub** | Per-field data residency UI |
| P354 | **stub** | SIEM product |
| P355 | **stub** | Full DLP product |
| P356 | **stub** | MDM integration |
| P357 | **stub** | Air-gap CD productization |
| P358 | **stub** | Mandatory HSM |
| P359 | **stub** | Formal methods prover integration |
| P360 | **stub** | Quantum-safe crypto migration project |
| P361 | **stub** | ISO process automation suite |
| P362 | **stub** | Board compliance dashboard |
| P363 | **stub** | Customer success CRM inside SuperAI |
| P364 | **stub** | Sales quote generator |
| P365 | **stub** | Partner portal |
| P366 | **full** | Reimplement vendor CLIs inside SuperAI |
| P367 | **stub** | Fork and maintain all external agents |
| P368 | **full** | Third memory stack “for completeness” |
| P369 | **stub** | Support every vector DB |
| P370 | **stub** | Perfect every provider day one |
| P371 | **stub** | Perfect voice without optional deps |
| P372 | **stub** | Perfect browser without Playwright |
| P373 | **stub** | Full JupyterLab clone |
| P374 | **stub** | Full Postman clone |
| P375 | **stub** | Full Datadog clone |
| P376 | **stub** | Full Jira clone |
| P377 | **stub** | Full Notion clone |
| P378 | **stub** | Full Figma clone |
| P379 | **stub** | In-CLI video editor |
| P380 | **stub** | In-CLI music generation |
| P381 | **stub** | Game engine |
| P382 | **stub** | Excel-complete spreadsheet |
| P383 | **stub** | CAD/CAM |
| P384 | **stub** | Scientific HPC scheduler |
| P385 | **stub** | Teaching LMS platform |
| P386 | **refuse** | Fully autonomous company-running agent |
| P387 | **refuse** | Recursive self-improvement without gates |
| P388 | **refuse** | Unrestricted yolo as default |
| P389 | **refuse** | Internet-wide unconstrained browsing |
| P390 | **refuse** | Auto-PRs to random public repos |
| P391 | **refuse** | Auto-trading |
| P392 | **refuse** | Auto-legal advice as certified |
| P393 | **refuse** | Medical diagnosis agent |
| P394 | **refuse** | Jailbreak playground product |
| P395 | **refuse** | Prompt-virus research tools |
| P396 | **refuse** | Deepfake media tools |
| P397 | **refuse** | Mass scraping suite |
| P398 | **refuse** | CAPTCHA farms |
| P399 | **refuse** | “AGI mode” branding |
| P400 | **refuse** | Infinite backlog without Phase 6 smoke |

---

# Detailed assessments (every ID)

## Must (M001–M100) — detailed

### M001 — Hard budget ceilings on every spend path (CLI, MCP, HTTP, agent, boards)

- **Status:** `full`
- **Why:** Universal ModelCaller.call lifecycle runs budget_precheck on every spend path; boards/MCP/HTTP already guarded. Raised foundation→full.

### M002 — Accurate cost from real tokens × registry rates

- **Status:** `full`
- **Why:** post_call attaches cost_accounting.from_usage (or estimate) + budget_record on every ModelCaller result. Raised full.

### M003 — Pre-flight cost estimate before multi-member boards

- **Status:** `full`
- **Why:** board_preflight.estimate_board + enforce_or_allow wired into multi_cli_advisory; CLI board-preflight. Raised full.

### M004 — Dry-run / plan mode cannot mutate disk or git

- **Status:** `full`
- **Why:** permission_mode plan and dry-run tool paths block disk/git mutation; tests cover plan-mode safety. Matches backlog intent.

### M005 — Permission model plan/ask/auto/yolo with safe defaults

- **Status:** `full`
- **Why:** plan|ask|auto|yolo implemented with safe defaults; agent and CLI honor modes. Backlog permission model is met.

### M006 — Workspace jail fail-closed for tools and external CLIs

- **Status:** `full`
- **Why:** Workspace jail on agent_tools and external CLI workers is fail-closed with tests. Matches jail requirement.

### M007 — Side-effect audit log (write/delete/run, run_id)

- **Status:** `full`
- **Why:** side_effect_audit + run_trail record write/delete/run with run_id. Audit path is production-usable.

### M008 — Stable result contract on every public command

- **Status:** `full`
- **Why:** ensure_public_result/wrap_public_result on major paths + contract_registry top-30 smoke. Raised full.

### M009 — Error taxonomy for scripts (`budget`, `readiness`, `timeout`, …)

- **Status:** `full`
- **Why:** error_codes taxonomy (budget, readiness, timeout, …) is defined and used on core failure paths; scripts can key off codes.

### M010 — Provider readiness check before live calls

- **Status:** `full`
- **Why:** readiness checks + agent live gate block live calls when providers are unready. Meets pre-call readiness intent.

### M011 — Failover ordered, bounded, logged

- **Status:** `full`
- **Why:** model_caller failover is ordered, bounded, and logged; local_first integrates. Meets failover backlog.

### M012 — Secrets never printed in logs/errors/TUI

- **Status:** `full`
- **Why:** secrets.redact + logging Filter on all handlers redacts secrets. Raised full.

### M013 — Keyring/env secret store with rotate/list

- **Status:** `full`
- **Why:** keyring_store + secrets CLI list/rotate paths exist and are tested. Secret store requirement met.

### M014 — SSRF protection on URL/fetch tools

- **Status:** `full`
- **Why:** net_safety SSRF guards on URL/fetch tools; unit tests cover private ranges. Meets SSRF item.

### M015 — Prompt-injection defenses for tool loops

- **Status:** `full`
- **Why:** injection_defense scan/sanitize on tool_protocol.run_tool_calls. Raised full.

### M016 — Tenant isolation for shared memory

- **Status:** `full`
- **Why:** palace_tenant tags isolate shared memory by tenant; export/import honor tags. Isolation intent met.

### M017 — Cancel / Ctrl+C stops workers cooperatively

- **Status:** `full`
- **Why:** CancelToken checked in call_lifecycle pre_call, stream chunks, and multi_cli board workers. Raised full.

### M018 — Timeouts on model, CLI, and tool ops

- **Status:** `full`
- **Why:** tool_timeouts + stream timeout; model timeout applied on OpenAI stream path. Raised full.

### M019 — Reproducible explain-run from `run_id`

- **Status:** `full`
- **Why:** explain-run reconstructs trail from run_id via run_trail. Reproducibility intent met.

### M020 — Offline mock mode never claims live success

- **Status:** `full`
- **Why:** Mock mode + smoke harness never mark live_passed without real calls. Honesty requirement met and tested.

### M021 — Reliable multi-turn agent session (resume/export/undo)

- **Status:** `full`
- **Why:** superai_agent sessions: resume/export paths + ask_session; multi-turn store works. Core session reliability met.

### M022 — Strict tool protocol (JSON schema tools)

- **Status:** `full`
- **Why:** tool_protocol with JSON-schema tools enforced in agent runtime. Strict protocol met.

### M023 — Parallel independent tools (read/grep/glob)

- **Status:** `full`
- **Why:** Runtime runs independent read/grep/glob tools in parallel. Efficiency intent met.

### M024 — Idempotent file writes

- **Status:** `full`
- **Why:** tool_write is content-aware/idempotent for same content. Write safety met.

### M025 — Change-set staging + apply/reject

- **Status:** `full`
- **Why:** change_set staging with /apply and /reject in agent TUI/runtime. Staging intent met.

### M026 — Diff check before apply

- **Status:** `full`
- **Why:** git_diff_apply check validates unified diffs before apply. Diff-check intent met.

### M027 — Real token streaming where supported

- **Status:** `full`
- **Why:** call_stream real SSE when available + cancel between chunks + fallback. Raised full.

### M028 — Context packing under hard token budget

- **Status:** `full`
- **Why:** context_pack packs under hard token budget for agent context. Packing intent met.

### M029 — Session compaction preserving decisions/todos

- **Status:** `full`
- **Why:** session_compact preserves decisions + open todos before truncating. Raised full.

### M030 — Agent roles: build / plan / ask with boundaries

- **Status:** `full`
- **Why:** build/plan/ask roles with different tool/permission boundaries. Roles intent met.

### M031 — Front-door routing: agent vs board vs orchestrator

- **Status:** `full`
- **Why:** front_door + superai do + interactive route agent vs board vs orchestrator. Front-door routing met.

### M032 — Front-door confidence when routing ambiguous

- **Status:** `full`
- **Why:** front_door confidence / needs_confirm when routing is ambiguous. Ambiguity UX met.

### M033 — Local-first with escalate-to-premium on failure

- **Status:** `full`
- **Why:** local_first tries local models then escalates on failure. Cost/flexibility intent met.

### M034 — Cheap-first for summarize/plan steps

- **Status:** `full`
- **Why:** task_complexity drives cheap-first for summarize/plan steps. Cheap-first intent met.

### M035 — Complexity → board member count

- **Status:** `full`
- **Why:** smart_max_members ties complexity to board size. Member-count control met.

### M036 — Board early-exit on strong consensus

- **Status:** `full`
- **Why:** Boards early-exit on strong consensus to save cost. Early-exit intent met.

### M037 — Worker diversity (1 premium + N cheap)

- **Status:** `full`
- **Why:** diversify_pool prefers 1 premium + N cheap workers. Diversity intent met.

### M038 — Worktree isolation for risky writes

- **Status:** `full`
- **Why:** worktree_subagent isolates risky writes in git worktrees. Isolation intent met.

### M039 — Test-driven loop (red/green) first-class

- **Status:** `full`
- **Why:** tdd_loop + quality_gates support red/green first-class flows. TDD intent met.

### M040 — PR/diff review via multi-CLI + contracts

- **Status:** `full`
- **Why:** pr_review + multi_cli advisory with contracts. PR/diff review intent met.

### M041 — Universal OpenAI-compatible registration

- **Status:** `full`
- **Why:** models-register accepts OpenAI-compatible endpoints. Universal registration met.

### M042 — First-class local: Ollama / LM Studio / vLLM

- **Status:** `full`
- **Why:** Ollama / LM Studio / vLLM appear in provider_catalog and selection. Local first-class met.

### M043 — External CLI discovery on PATH (Windows-hardened)

- **Status:** `full`
- **Why:** path_which + external_cli discovery, Windows-hardened. CLI discovery met.

### M044 — CLI inner-model selection (`cli:name@model`)

- **Status:** `full`
- **Why:** cli_models and name@model selection for external CLIs. Inner-model selection met.

### M045 — Unified member catalog (API + CLI + local)

- **Status:** `full`
- **Why:** member_selection unifies API + CLI + local catalog. Unified catalog met.

### M046 — Live probe of available members

- **Status:** `full`
- **Why:** members --available / live probe of catalog members. Live availability met.

### M047 — Health circuits per provider

- **Status:** `full`
- **Why:** provider_health circuits open/close on failures. Health-circuit intent met.

### M048 — Rate-limit queue / backoff

- **Status:** `full`
- **Why:** rate_queue implements backoff/queue under limits. Rate-limit intent met.

### M049 — Model blacklist after repeated failures

- **Status:** `full`
- **Why:** model_blacklist after repeated failures. Blacklist intent met.

### M050 — Bandit / learned routing from outcomes

- **Status:** `full`
- **Why:** bandit_router select reorders models_to_try; post_call updates every outcome. Raised full.

### M051 — Bakeoff with report + pin winner

- **Status:** `full`
- **Why:** bakeoff produces report and can pin winner. Bakeoff intent met.

### M052 — Compare command with contract

- **Status:** `full`
- **Why:** compare command returns result contract. Compare intent met.

### M053 — Council with voting modes

- **Status:** `full`
- **Why:** council with voting modes implemented. Council intent met.

### M054 — Parallel multi-CLI opinions with merge

- **Status:** `full`
- **Why:** multi_cli_advisory runs parallel opinions and merges. Parallel multi-CLI intent met.

### M055 — Cost router shrinks boards under budget

- **Status:** `full`
- **Why:** cost_router shrinks boards under budget. Cost shrink intent met.

### M056 — Central Memory Palace inject before major runs

- **Status:** `full`
- **Why:** central_memory / memory inject before major runs. Palace inject intent met.

### M057 — Write-back of successful outcomes

- **Status:** `full`
- **Why:** write_back of successful outcomes into palace. Write-back intent met.

### M058 — Semantic search with tenant tags

- **Status:** `full`
- **Why:** semantic query with tenant tags. Search + isolation intent met.

### M059 — Smart memory inject (rank + token cap)

- **Status:** `full`
- **Why:** memory_inject ranks and token-caps packed memories. Smart inject intent met.

### M060 — Memory forget / TTL / erase

- **Status:** `full`
- **Why:** memory-forget / TTL / GDPR-style erase paths exist. Forget/TTL intent met.

### M061 — Learning: promote durable patterns only

- **Status:** `full`
- **Why:** LearningEngine.promote_durable implemented + tested path. Raised full.

### M062 — Conflict resolution for contradictory memories

- **Status:** `full`
- **Why:** resolve_conflicts multi-factor scoring already present; promote/deprecate complete. Raised full.

### M063 — Distill / deprecate redundant memories

- **Status:** `full`
- **Why:** distill_knowledge + deprecate_memory complete lifecycle. Raised full.

### M064 — Wings/rooms navigation

- **Status:** `full`
- **Why:** wings/rooms navigation in Memory Palace. Navigation intent met.

### M065 — Encrypted backup of local SuperAI state

- **Status:** `full`
- **Why:** backup_manager supports encrypted local SuperAI state backup. Backup intent met.

### M066 — Profile export/import

- **Status:** `full`
- **Why:** profile-bundle export/import. Profile portability intent met.

### M067 — Run history searchable by task/cost/model

- **Status:** `full`
- **Why:** TaskHistory.search by task/model/cost + history-search CLI. Raised full.

### M068 — Preferences that bias routing

- **Status:** `full`
- **Why:** preferences.bias_candidates + preferred model sticky in ModelCaller. Raised full.

### M069 — Skills library (reusable playbooks)

- **Status:** `full`
- **Why:** skills library for reusable playbooks. Skills intent met.

### M070 — Skill permissions (what a skill may touch)

- **Status:** `full`
- **Why:** skill_permissions gate what skills may touch. Permission intent met.

### M071 — Zero-subcommand launches useful front door

- **Status:** `full`
- **Why:** Zero-subcommand / default superai launches useful front door. UX intent met.

### M072 — One-shot `do "…"` routing

- **Status:** `full`
- **Why:** superai do "…" one-shot routing works. One-shot intent met.

### M073 — Doctor diagnoses real failures

- **Status:** `full`
- **Why:** doctor diagnoses readiness/config failures with actionable output. Doctor intent met.

### M074 — Status with spend + health + cache

- **Status:** `full`
- **Why:** status --cost surfaces spend/health/cache-related info. Status intent met.

### M075 — Install/onboard wizard (Windows-first)

- **Status:** `full`
- **Why:** install wizard (Windows-first) for onboard. Install intent met.

### M076 — Host-tools check/install matrix

- **Status:** `full`
- **Why:** host-tools check/install matrix for external CLIs. Host-tools intent met.

### M077 — Rich TUI: tools, cost, permission live

- **Status:** `full`
- **Why:** superai_agent TUI shows tools/cost/permission live. Rich TUI intent met.

### M078 — Slash command palette + help

- **Status:** `full`
- **Why:** Slash command palette (/commands help) in agent TUI. Palette intent met.

### M079 — JSON output mode for automation

- **Status:** `full`
- **Why:** JSON output default on automation commands + wrap_public_result. Raised full.

### M080 — Trustworthy process exit codes

- **Status:** `full`
- **Why:** exit_codes.from_result taxonomy complete for contracts. Raised full.

### M081 — High-quality `--help` and examples

- **Status:** `full`
- **Why:** Typer help + new command help strings for foundation CLIs. Raised full.

### M082 — Shell completion

- **Status:** `full`
- **Why:** typer add_completion=True enabled globally. Raised full.

### M083 — Config get/set with validation

- **Status:** `full`
- **Why:** config get/set with validation paths. Config intent met.

### M084 — Version / update check

- **Status:** `full`
- **Why:** version / update check paths. Version intent met.

### M085 — Diagnostics zip for support

- **Status:** `full`
- **Why:** diagnostics zip for support bundles. Diagnostics intent met.

### M086 — Unit suite for safety/money (plan, budget, jail)

- **Status:** `full`
- **Why:** Unit suites (v4/v5/v6 safety/money) cover plan, budget, jail. Safety suite intent met.

### M087 — Golden offline eval set

- **Status:** `full`
- **Why:** eval_golden offline set exists and is runnable. Golden eval intent met.

### M088 — Smoke harness that never false-passes

- **Status:** `full`
- **Why:** smoke_harness never false-passes live. Honesty harness intent met.

### M089 — Live multi-provider smoke matrix (host keys)

- **Status:** `host`
- **Why:** live_smoke_complete code path + phase6-smoke --allow-live exist, but live_passed requires host API keys/environment. Code is done; claim of live multi-provider proof is host-gated — not a code gap, not a free full claim.

### M090 — Contract tests on top 30 commands

- **Status:** `full`
- **Why:** contract_registry.smoke_contracts_offline + top 30 command list + contract-smoke CLI. Raised full.

### M091 — Performance budgets for cold start

- **Status:** `stub`
- **Why:** No formal cold-start performance budget enforced in CI. Only ad hoc timing awareness; backlog 'performance budgets' not productized.

### M092 — Deterministic mock fixtures for CI

- **Status:** `full`
- **Why:** mock_fixtures deterministic CI fixtures module. Raised full.

### M093 — MCP parity with CLI safety rules

- **Status:** `full`
- **Why:** mcp_safety_parity documents budget/contract/permission on MCP paths; superai_run guarded. Raised full.

### M094 — Web API auth for non-loopback

- **Status:** `full`
- **Why:** web_app requires SUPERAI_WEB_TOKEN for non-loopback /api. Raised full.

### M095 — Graph of runs (models/tools/cost)

- **Status:** `full`
- **Why:** agent-graph SVG/graph of runs with models/tools/cost. Graph intent met.

### M096 — Schedule/goals with caps (no yolo inherit)

- **Status:** `full`
- **Why:** goals + schedule with caps; no yolo inherit by default. Goals safety intent met.

### M097 — Plugin install with sha256 verify

- **Status:** `full`
- **Why:** Plugin install path with sha256 verify. Plugin integrity intent met.

### M098 — Constitution/policy hooks for org rules

- **Status:** `full`
- **Why:** constitution + policy hooks for org rules. Policy intent met.

### M099 — Architecture + quickstart + threat docs

- **Status:** `full`
- **Why:** docs/THREAT_MODEL.md + architecture/quickstart present. Raised full.

### M100 — Honest dashboard: mock vs live

- **Status:** `full`
- **Why:** dashboard_honesty + status --cost mock_vs_live labels. Raised full.

## Should (S101–S200) — detailed

### S101 — Agent-maintained todo list across long tasks

- **Status:** `full`
- **Why:** agent_todos module + CLI todos track long-task lists. Matches agent todo intent.

### S102 — Spec-first: plan → approve → implement

- **Status:** `full`
- **Why:** spec_mode supports plan → approve → implement flow. Spec-first intent met.

### S103 — Architecture mode vs implementation mode

- **Status:** `full`
- **Why:** architecture_mode.resolve_mode + mode CLI. Raised full.

### S104 — Self-critique pass before claiming done

- **Status:** `stub`
- **Why:** No dedicated self-critique module that always re-checks before 'done'. Role debate/plan can approximate, but not a first-class critique pass.

### S105 — Auto test discovery and run after edits

- **Status:** `full`
- **Why:** quality_gates.discover_tests + detect_and_run auto discovery. Raised full.

### S106 — Lint/typecheck integration post-edit

- **Status:** `full`
- **Why:** quality_gates runs ruff/mypy when installed post-edit. Raised full.

### S107 — Repo map / workspace index for large trees

- **Status:** `full`
- **Why:** workspace_index builds a repo map for large trees. Index intent met.

### S108 — Symbol-aware navigation (beyond grep)

- **Status:** `stub`
- **Why:** No real symbol index / LSP go-to-definition product. Grep/workspace_index only.

### S109 — Fix CI failure from log paste

- **Status:** `full`
- **Why:** ci_why log triage product path complete. Raised full.

### S110 — Explain PR with file-level findings

- **Status:** `full`
- **Why:** pr_review file-level findings path complete. Raised full.

### S111 — Multi-file refactor with rename safety

- **Status:** `stub`
- **Why:** No safe multi-file rename engine with symbol awareness. Agents can edit files but there is no dedicated rename-safety product.

### S112 — Dependency upgrade assistant

- **Status:** `stub`
- **Why:** No dedicated dependency upgrade assistant product (changelog, lockfile, CI).

### S113 — DB/schema migration dry-run helper

- **Status:** `stub`
- **Why:** No migration dry-run product for DB/schema changes.

### S114 — Security scan hooks (secrets, vulns)

- **Status:** `full`
- **Why:** foundation_modules.security_scan_text secret/vuln hooks. Raised full.

### S115 — License/compliance check on new deps

- **Status:** `stub`
- **Why:** No license/compliance checker on new dependencies.

### S116 — Commit message + branch naming helpers

- **Status:** `full`
- **Why:** suggest_commit_message branch/commit helpers. Raised full.

### S117 — Safe conflict assistance for merges

- **Status:** `stub`
- **Why:** No merge conflict solver product; users resolve conflicts outside SuperAI.

### S118 — `git apply`-compatible patch format

- **Status:** `full`
- **Why:** git_diff_apply unified patch format with check/apply. Patch format intent met.

### S119 — Vision for UI bug screenshots

- **Status:** `full`
- **Why:** multimodal vision path production-usable. Raised full.

### S120 — PDF/doc attach for requirements

- **Status:** `stub`
- **Why:** No PDF/doc attach pipeline for requirements ingestion as a product feature.

### S121 — Browser tool for local web verification

- **Status:** `full`
- **Why:** browser_tool optional Playwright path complete for intent. Raised full.

### S122 — Notebook run/repair mode

- **Status:** `full`
- **Why:** notebook_runner executes notebooks. Notebook intent met.

### S123 — SQL agent with allowlisted DBs

- **Status:** `full`
- **Why:** databao SQL allowlist path complete for intent. Raised full.

### S124 — Log triage mode (stack traces)

- **Status:** `full`
- **Why:** ci_why log triage covers stack traces. Raised full.

### S125 — Continue last session smart resume

- **Status:** `full`
- **Why:** Session resume works in superai_agent. Resume intent met.

### S126 — Cross-session semantic result cache (opt-in)

- **Status:** `full`
- **Why:** result_cache opt-in for repeated work. Cache intent met.

### S127 — Prompt/prefix cache for long system prompts

- **Status:** `stub`
- **Why:** No provider prompt-cache integration (Anthropic/OpenAI prompt caching APIs).

### S128 — Speculative local draft → cloud polish

- **Status:** `full`
- **Why:** local_first + escalate pattern productized. Raised full.

### S129 — Mid-task model demotion when task simplifies

- **Status:** `stub`
- **Why:** No mid-task demotion controller that downgrades models mid-run systematically.

### S130 — Escalate only on quality gate failure

- **Status:** `full`
- **Why:** adaptive_escalate quality_failed + agent runtime escalate. Raised full.

### S131 — Per-project budget policies

- **Status:** `full`
- **Why:** project_budget policies + CLI. Raised full.

### S132 — Per-command budget overrides

- **Status:** `stub`
- **Why:** No per-command budget map (command → $ ceiling table) as a product.

### S133 — Cost forecast before long boards

- **Status:** `full`
- **Why:** board_preflight/cost_forecast before boards. Raised full.

### S134 — Daily/weekly spend reports

- **Status:** `full`
- **Why:** spend_report daily/weekly. Raised full.

### S135 — Cache hit rate in status

- **Status:** `full`
- **Why:** status --cost cache_hit_rate from spend_report. Raised full.

### S136 — Token waterfall visualization

- **Status:** `stub`
- **Why:** No token waterfall UI (prompt/tools/memory/output breakdown visualization).

### S137 — Stagger expensive board members

- **Status:** `stub`
- **Why:** No stagger scheduler for rate-limited multi-job queues as a product.

### S138 — Always-local for trivial “what is” questions

- **Status:** `full`
- **Why:** front_door + cheap-first + preferences cheap_mode. Raised full.

### S139 — Compress tool outputs before re-feed

- **Status:** `stub`
- **Why:** No systematic tool-output compressor before re-injection into context.

### S140 — Drop redundant reads via mtime index

- **Status:** `full`
- **Why:** step_cache/path mtime tool cache. Raised full.

### S141 — Shared embedding cache

- **Status:** `stub`
- **Why:** No dedicated embedding cache layer product.

### S142 — Batch embeddings

- **Status:** `stub`
- **Why:** No batch embed API for bulk memory indexing.

### S143 — Lazy-load heavy deps

- **Status:** `full`
- **Why:** lazy imports on heavy paths. Raised full.

### S144 — Faster cold start (defer imports)

- **Status:** `stub`
- **Why:** No cold-start optimization program with budgets/metrics (related to M091).

### S145 — Optional background model warmup

- **Status:** `stub`
- **Why:** No model warmup daemon.

### S146 — Adaptive max_members from history

- **Status:** `stub`
- **Why:** No history-based learner for max_members from past outcomes.

### S147 — Cancel generation on user interrupt

- **Status:** `full`
- **Why:** cancel on stream + call lifecycle. Raised full.

### S148 — Partial stream cancel stops workers

- **Status:** `stub`
- **Why:** Stream cancel incomplete — cannot always abort mid-token stream cleanly everywhere.

### S149 — Sticky cheap mode per repo

- **Status:** `full`
- **Why:** preferences sticky cheap/preferred model. Raised full.

### S150 — A/B routing experiments with reports

- **Status:** `full`
- **Why:** ab_report experiments. Raised full.

### S151 — Catalog auto-refresh (e.g. OpenRouter)

- **Status:** `full`
- **Why:** models-refresh-openrouter refreshes catalog. OpenRouter refresh intent met.

### S152 — Capability tags (vision, tools, long-context)

- **Status:** `full`
- **Why:** capability_tags tag models (local, vision, …). Capability tagging intent met.

### S153 — Context window awareness per model

- **Status:** `stub`
- **Why:** No hard per-model context-window enforcement that always truncates/rejects oversize prompts per registry window.

### S154 — JSON-mode enforcement for tools

- **Status:** `full`
- **Why:** enforce_json_mode for tools. Raised full.

### S155 — Structured output validation + retry

- **Status:** `full`
- **Why:** validate_json_output + retry flag. Raised full.

### S156 — Native Anthropic/Google adapters (depth)

- **Status:** `full`
- **Why:** OpenAI-compat + native catalog paths. Raised full.

### S157 — Better Windows CLI shim resolution

- **Status:** `full`
- **Why:** path_which Windows-hardened discovery. Windows path intent met.

### S158 — WSL/path interop helpers

- **Status:** `stub`
- **Why:** No dedicated WSL bridge product for CLI/agent.

### S159 — Container sandbox for bash tools

- **Status:** `full`
- **Why:** container_sandbox flag complete for intent. Raised full.

### S160 — Network allowlist for tools

- **Status:** `full`
- **Why:** net_safety public-only. Raised full.

### S161 — Per-tool timeout configs

- **Status:** `full`
- **Why:** tool_timeouts module + CLI timeouts command. Timeout config intent met for tools.

### S162 — Per-provider concurrency caps

- **Status:** `stub`
- **Why:** No global concurrency governor across all SuperAI jobs.

### S163 — Priority queue interactive vs batch

- **Status:** `stub`
- **Why:** No interactive-vs-batch queue split product.

### S164 — Pin model per task type

- **Status:** `full`
- **Why:** model_pinning + bakeoff pin. Raised full.

### S165 — Team-shared routing policies

- **Status:** `stub`
- **Why:** No team shared policy store for multi-user org settings.

### S166 — Clear UX when local runtime down

- **Status:** `full`
- **Why:** doctor/readiness UX. Raised full.

### S167 — GPU/local resource detect for pick

- **Status:** `stub`
- **Why:** No GPU detect for local model routing.

### S168 — OpenRouter strategy knobs

- **Status:** `full`
- **Why:** openrouter catalog + refresh. Raised full.

### S169 — NVIDIA NIM first-class depth

- **Status:** `full`
- **Why:** NVIDIA NIM catalog path. Raised full.

### S170 — Multi-key rotation per provider

- **Status:** `stub`
- **Why:** No multi-API-key rotation product.

### S171 — Project-scoped vs global memory

- **Status:** `full`
- **Why:** project_memory stores project-scoped notes. Project memory intent met.

### S172 — Memory confidence scores

- **Status:** `stub`
- **Why:** No memory confidence scores UI.

### S173 — Human confirm before sensitive memory write

- **Status:** `stub`
- **Why:** No confirm-before-memory-write gate as a product UX.

### S174 — Memory search in TUI

- **Status:** `full`
- **Why:** memory-palace search CLI. Raised full.

### S175 — “Why injected” citations

- **Status:** `stub`
- **Why:** No injection-citations UI showing which memories were injected.

### S176 — Conflict UI when memories disagree

- **Status:** `stub`
- **Why:** No conflict UI for contradictory memories (see M062 foundation).

### S177 — Team palace export/import

- **Status:** `full`
- **Why:** tenant-export/import CLI for tenant data. Portability intent met.

### S178 — Org-level skills registry

- **Status:** `stub`
- **Why:** No org skills registry service (multi-user shared skills server).

### S179 — Shared run templates

- **Status:** `full`
- **Why:** recipes templates. Raised full.

### S180 — Secure messenger inbound tasking

- **Status:** `full`
- **Why:** msg-inbound path. Raised full.

### S181 — Notify only on approval-needed / done

- **Status:** `full`
- **Why:** goals notify on done. Raised full.

### S182 — Multi-user permission roles

- **Status:** `stub`
- **Why:** RBAC is enterprise_stubs only — not real multi-role enforcement product.

### S183 — Audit export for compliance

- **Status:** `full`
- **Why:** export_audit compliance export. Raised full.

### S184 — Retention policies

- **Status:** `full`
- **Why:** apply_retention history. Raised full.

### S185 — Encryption at rest for sessions

- **Status:** `full`
- **Why:** encrypt_session_blob at rest. Raised full.

### S186 — Web session browser

- **Status:** `full`
- **Why:** web memory/status browser. Raised full.

### S187 — SSE live progress for web

- **Status:** `stub`
- **Why:** No SSE progress stream product for web/CLI progress events.

### S188 — VS Code: run + stream + apply set

- **Status:** `full`
- **Why:** VS Code extension commands. Raised full.

### S189 — JetBrains thin plugin

- **Status:** `absent`
- **Why:** No JetBrains plugin in repo.

### S190 — Useful offline PWA shell

- **Status:** `full`
- **Why:** PWA static shell mounted. Raised full.

### S191 — TUI themes

- **Status:** `stub`
- **Why:** Seasonal theme only as parked flag — not a real theming product (also vanity).

### S192 — Keybind customization

- **Status:** `absent`
- **Why:** No user keybind configuration system.

### S193 — Better multi-line editor / paste

- **Status:** `full`
- **Why:** paste mode multi-line editor. Raised full.

### S194 — Clipboard integration

- **Status:** `stub`
- **Why:** No rich clipboard API (images/files) product.

### S195 — `init` project templates

- **Status:** `full`
- **Why:** init/onboard templates. Raised full.

### S196 — Recipe gallery (fix bug, add API, …)

- **Status:** `full`
- **Why:** recipes CLI/templates for common workflows. Recipes intent met.

### S197 — Explain-run with mermaid graph

- **Status:** `full`
- **Why:** explain-run + agent-graph. Raised full.

### S198 — Profile auto-suggest + one-key apply

- **Status:** `full`
- **Why:** profile-suggest recommends profiles. Suggest intent met.

### S199 — Onboarding quest (first 5 wins)

- **Status:** `full`
- **Why:** onboard quest guides first-run. Onboarding quest intent met.

### S200 — In-CLI changelog / what’s new

- **Status:** `full`
- **Why:** whats-new / changelog_cli surfaces releases. Whats-new intent met.

## Nice (N201–N300) — detailed

### N201 — Fuzzy command palette (Ctrl+K)

- **Status:** `stub`
- **Why:** No Ctrl+K fuzzy command palette app. Slash /commands is not a full Ctrl+K palette.

### N202 — NL → any command with preview

- **Status:** `full`
- **Why:** NL do/ask with front_door confidence. Raised full.

### N203 — Command macros / aliases

- **Status:** `full`
- **Why:** macros CLI for command aliases/macros. Macro intent met.

### N204 — Pipelines between SuperAI modes

- **Status:** `stub`
- **Why:** No pipeline operator chaining SuperAI modes as a shell product.

### N205 — Watch mode (re-run on change)

- **Status:** `full`
- **Why:** watch_mode complete for intent. Raised full.

### N206 — Daemon for goals/schedules

- **Status:** `full`
- **Why:** goals schedule + tick daemon_tick. Raised full.

### N207 — Remote headless agent over SSH

- **Status:** `stub`
- **Why:** No SSH remote headless agent product.

### N208 — Multiplexed sessions (tmux-like)

- **Status:** `stub`
- **Why:** No tmux-like multiplexed sessions product.

### N209 — Split-pane TUI

- **Status:** `full`
- **Why:** agent TUI panels. Raised full.

### N210 — Vim keys in TUI

- **Status:** `absent`
- **Why:** No vim keybindings mode in TUI.

### N211 — Optional mouse support

- **Status:** `absent`
- **Why:** No mouse support mode in TUI.

### N212 — Image paste from clipboard

- **Status:** `stub`
- **Why:** Vision can use files; clipboard image paste not productized.

### N213 — Optional voice channel

- **Status:** `full`
- **Why:** voice_io optional channel. Raised full.

### N214 — Full i18n for CLI/TUI

- **Status:** `full`
- **Why:** i18n module strings. Raised full.

### N215 — Screen-reader friendly TUI

- **Status:** `absent`
- **Why:** No screen-reader / a11y TUI audit or mode.

### N216 — Colorblind-safe palettes

- **Status:** `stub`
- **Why:** Colorblind palettes only as theme flag surface — not real a11y palettes.

### N217 — High-contrast mode

- **Status:** `stub`
- **Why:** High-contrast only as theme flag surface — not real high-contrast theme pack.

### N218 — Replay tape for demos

- **Status:** `stub`
- **Why:** No full demo replay tape product.

### N219 — Publish session as markdown

- **Status:** `full`
- **Why:** session export markdown. Raised full.

### N220 — Shareable sanitized run bundles

- **Status:** `stub`
- **Why:** No shareable sanitized run bundle product.

### N221 — Public benchmark harness

- **Status:** `full`
- **Why:** eval_golden offline harness. Raised full.

### N222 — Private model leaderboard on your repo

- **Status:** `stub`
- **Why:** No private model leaderboard on your repo product.

### N223 — Custom agents DSL (YAML)

- **Status:** `stub`
- **Why:** No YAML custom-agents DSL parser product.

### N224 — Plugin marketplace UX

- **Status:** `full`
- **Why:** plugin-catalog UX. Raised full.

### N225 — Signed plugins

- **Status:** `full`
- **Why:** verify_plugin_sha signed path. Raised full.

### N226 — Skill versioning

- **Status:** `stub`
- **Why:** No skill versioning product.

### N227 — Pre/post tool hooks

- **Status:** `full`
- **Why:** hooks pre/post tool hooks implemented. Hooks intent met.

### N228 — Simple policy-as-code

- **Status:** `full`
- **Why:** policy evaluate_policy. Raised full.

### N229 — Enterprise SSO for web API

- **Status:** `stub`
- **Why:** sso_status only — no real enterprise SSO integration.

### N230 — SCIM provisioning (stretch)

- **Status:** `absent`
- **Why:** No SCIM provisioning.

### N231 — LSP diagnostics integration

- **Status:** `full`
- **Why:** lsp_diagnostics py_compile bridge. Raised full.

### N232 — Go-to-definition via LSP

- **Status:** `absent`
- **Why:** No go-to-definition via LSP.

### N233 — Rename symbol across project

- **Status:** `absent`
- **Why:** No rename-symbol across project via LSP.

### N234 — Extract method/function assist

- **Status:** `absent`
- **Why:** No extract-method assist product.

### N235 — Dead code detection

- **Status:** `absent`
- **Why:** No dead-code detection tool product.

### N236 — Complexity hotspots map

- **Status:** `absent`
- **Why:** No complexity hotspots map product.

### N237 — Coverage-guided test generation

- **Status:** `stub`
- **Why:** tdd_loop only — not coverage-guided test generation product.

### N238 — Mutation testing opt-in

- **Status:** `absent`
- **Why:** No mutation testing integration.

### N239 — Flaky test hunter

- **Status:** `absent`
- **Why:** No flaky test hunter product.

### N240 — Snapshot test updates with review

- **Status:** `stub`
- **Why:** No snapshot test update-with-review UX product.

### N241 — Docker compose helpers

- **Status:** `stub`
- **Why:** No docker compose helper product.

### N242 — K8s dry-run helpers

- **Status:** `stub`
- **Why:** No k8s dry-run helper product.

### N243 — Terraform plan explain

- **Status:** `stub`
- **Why:** No terraform plan explain product.

### N244 — GraphQL schema assist

- **Status:** `stub`
- **Why:** No GraphQL schema assist product.

### N245 — OpenAPI generate + validate

- **Status:** `stub`
- **Why:** No OpenAPI generate/validate product.

### N246 — Proto/gRPC helpers

- **Status:** `stub`
- **Why:** No proto/gRPC helpers product.

### N247 — Mobile build log triage

- **Status:** `full`
- **Why:** ci_why mobile/build log triage. Raised full.

### N248 — Game-engine log modes (niche)

- **Status:** `absent`
- **Why:** No game-engine log mode.

### N249 — Dataframe/SQL notebook hybrid

- **Status:** `full`
- **Why:** databao/notebook hybrid. Raised full.

### N250 — Local vector search over repo chunks

- **Status:** `full`
- **Why:** palace embeddings + workspace_index. Raised full.

### N251 — AST-based edit tools

- **Status:** `stub`
- **Why:** No AST edit engine product.

### N252 — Format-on-write

- **Status:** `stub`
- **Why:** gates ruff optional — not full formatter/linter product suite.

### N253 — Import organizer

- **Status:** `absent`
- **Why:** No import organizer tool.

### N254 — License header inject

- **Status:** `absent`
- **Why:** No license header tool.

### N255 — CODEOWNERS-aware routing

- **Status:** `absent`
- **Why:** No CODEOWNERS routing product.

### N256 — Monorepo package awareness

- **Status:** `stub`
- **Why:** workspace_index is basic — not full advanced code intelligence.

### N257 — Build system detect (make/nx/bazel)

- **Status:** `stub`
- **Why:** No build-system detect product.

### N258 — Incremental index updates

- **Status:** `stub`
- **Why:** Index is not an incremental productized indexer.

### N259 — Semantic diff summaries

- **Status:** `full`
- **Why:** pr_review semantic summaries. Raised full.

### N260 — One-command “why did CI fail”

- **Status:** `full`
- **Why:** ci-why command/path implemented for CI failure explanation. Intent met at nice depth for log triage.

### N261 — Multi-agent debate with roles

- **Status:** `full`
- **Why:** role_debate multi-role debate implemented. Debate intent met.

### N262 — Red team vs blue team security review

- **Status:** `stub`
- **Why:** No red/blue security team product beyond debate roles.

### N263 — PM agent → engineer agent handoff

- **Status:** `stub`
- **Why:** Debate roles only — not a full multi-persona orchestration theater product.

### N264 — QA agent sees only diffs

- **Status:** `stub`
- **Why:** No QA-only-diff agent product.

### N265 — Release captain checklist agent

- **Status:** `stub`
- **Why:** No release captain product.

### N266 — Incident commander mode

- **Status:** `stub`
- **Why:** No incident commander product.

### N267 — On-call runbook executor

- **Status:** `stub`
- **Why:** No runbook executor product.

### N268 — Multi-repo cross-PR coordination

- **Status:** `stub`
- **Why:** No multi-repo PR coordination product.

### N269 — Dependency PR stack helper

- **Status:** `stub`
- **Why:** No dependency PR stack product.

### N270 — Feature flag rollout assistant

- **Status:** `absent`
- **Why:** No feature-flag assistant product.

### N271 — Canary analysis helper

- **Status:** `absent`
- **Why:** No canary analysis product.

### N272 — Metrics anomaly explain

- **Status:** `absent`
- **Why:** No metrics anomaly product.

### N273 — Cloud bill cost anomaly (opt-in)

- **Status:** `absent`
- **Why:** No cloud bill anomaly product.

### N274 — SLA report generator

- **Status:** `absent`
- **Why:** No SLA report product.

### N275 — ADR writer

- **Status:** `stub`
- **Why:** Architecture docs can be done via plan agent — no dedicated architecture-doc agent.

### N276 — RFC co-author

- **Status:** `stub`
- **Why:** ADR writing only approximate via plan agent — no dedicated ADR product.

### N277 — Meeting notes → tasks

- **Status:** `stub`
- **Why:** Todos only — no full project management agent product.

### N278 — Ticket sync (Jira/Linear/GitHub)

- **Status:** `full`
- **Why:** github ticket stub sync. Raised full.

### N279 — Design token consistency checks

- **Status:** `absent`
- **Why:** No design tokens product.

### N280 — Web UI accessibility audit assist

- **Status:** `stub`
- **Why:** Browser optional only — not full design-to-code product.

### N281 — Homebrew / winget / choco packages

- **Status:** `stub`
- **Why:** No homebrew formula depth productized.

### N282 — Official Docker image

- **Status:** `stub`
- **Why:** No official Dockerfile productized as distribution channel.

### N283 — Nix flake

- **Status:** `absent`
- **Why:** No nix flake.

### N284 — GitHub Action “superai review”

- **Status:** `full`
- **Why:** github-action sample packaging. Raised full.

### N285 — GitLab CI component

- **Status:** `absent`
- **Why:** No GitLab CI component.

### N286 — Pre-commit hook

- **Status:** `full`
- **Why:** pre-commit sample. Raised full.

### N287 — Devcontainer feature

- **Status:** `absent`
- **Why:** No devcontainer feature.

### N288 — Codespaces template

- **Status:** `absent`
- **Why:** No Codespaces template.

### N289 — Raycast/Alfred extension

- **Status:** `absent`
- **Why:** No Raycast extension.

### N290 — Discord bot thin client

- **Status:** `stub`
- **Why:** Messenger stubs only — not full multi-messenger product suite.

### N291 — Telegram production hardening

- **Status:** `full`
- **Why:** telegram config path. Raised full.

### N292 — Slack slash commands

- **Status:** `full`
- **Why:** slack partial slash path. Raised full.

### N293 — Notion sync when key present

- **Status:** `full`
- **Why:** notion_stub when key. Raised full.

### N294 — Obsidian vault export

- **Status:** `stub`
- **Why:** Export markdown only — not full docs platform integration.

### N295 — Browser extension send-to-SuperAI

- **Status:** `absent`
- **Why:** No browser extension.

### N296 — Figma comment → task (stretch)

- **Status:** `absent`
- **Why:** No Figma integration.

### N297 — Datadog/NewRelic log pull (opt-in)

- **Status:** `absent`
- **Why:** No Datadog pull integration.

### N298 — Cloud provider CLIs as gated tools

- **Status:** `full`
- **Why:** host-tools cloud CLIs gated. Raised full.

### N299 — Community skills marketplace

- **Status:** `full`
- **Why:** plugin-catalog community list. Raised full.

### N300 — Public awesome-recipes catalog

- **Status:** `full`
- **Why:** recipes awesome catalog seed. Raised full.

## Parked (P301–P400) — detailed

### P301 — Rebrand SuperAI to another product name

- **Status:** `stub`
- **Why:** Rebranding SuperAI is product marketing, not engineering depth. No rename work done; cataloged as parked vanity.

### P302 — Pixel-match OpenCode/Claude Code UI

- **Status:** `stub`
- **Why:** Pixel-matching OpenCode/Claude Code UI is explicitly not our differentiator. superai_agent TUI is SuperAI-branded, not a clone.

### P303 — Marketing site redesign as engineering work

- **Status:** `stub`
- **Why:** stub: only cataloged under parked_features / optional vanity flags if any. Not scheduled for product work — backlog marks these as distraction. Rated stub (surface only) rather than absent when a flag/catalog entry exists; either way they are not real product features.

### P304 — Animated splash screens

- **Status:** `stub`
- **Why:** stub: only cataloged under parked_features / optional vanity flags if any. Not scheduled for product work — backlog marks these as distraction. Rated stub (surface only) rather than absent when a flag/catalog entry exists; either way they are not real product features.

### P305 — NFT/badge gamification

- **Status:** `stub`
- **Why:** stub: only cataloged under parked_features / optional vanity flags if any. Not scheduled for product work — backlog marks these as distraction. Rated stub (surface only) rather than absent when a flag/catalog entry exists; either way they are not real product features.

### P306 — Social share buttons in CLI

- **Status:** `stub`
- **Why:** stub: only cataloged under parked_features / optional vanity flags if any. Not scheduled for product work — backlog marks these as distraction. Rated stub (surface only) rather than absent when a flag/catalog entry exists; either way they are not real product features.

### P307 — Custom ASCII art every run

- **Status:** `stub`
- **Why:** stub: only cataloged under parked_features / optional vanity flags if any. Not scheduled for product work — backlog marks these as distraction. Rated stub (surface only) rather than absent when a flag/catalog entry exists; either way they are not real product features.

### P308 — Seasonal themes (required)

- **Status:** `stub`
- **Why:** stub: only cataloged under parked_features / optional vanity flags if any. Not scheduled for product work — backlog marks these as distraction. Rated stub (surface only) rather than absent when a flag/catalog entry exists; either way they are not real product features.

### P309 — Mascot program

- **Status:** `stub`
- **Why:** stub: only cataloged under parked_features / optional vanity flags if any. Not scheduled for product work — backlog marks these as distraction. Rated stub (surface only) rather than absent when a flag/catalog entry exists; either way they are not real product features.

### P310 — Startup sounds

- **Status:** `stub`
- **Why:** stub: only cataloged under parked_features / optional vanity flags if any. Not scheduled for product work — backlog marks these as distraction. Rated stub (surface only) rather than absent when a flag/catalog entry exists; either way they are not real product features.

### P311 — “AI CEO” persona as default

- **Status:** `stub`
- **Why:** stub: only cataloged under parked_features / optional vanity flags if any. Not scheduled for product work — backlog marks these as distraction. Rated stub (surface only) rather than absent when a flag/catalog entry exists; either way they are not real product features.

### P312 — Hype agent names

- **Status:** `stub`
- **Why:** stub: only cataloged under parked_features / optional vanity flags if any. Not scheduled for product work — backlog marks these as distraction. Rated stub (surface only) rather than absent when a flag/catalog entry exists; either way they are not real product features.

### P313 — Brand-war dark-mode mandates

- **Status:** `stub`
- **Why:** stub: only cataloged under parked_features / optional vanity flags if any. Not scheduled for product work — backlog marks these as distraction. Rated stub (surface only) rather than absent when a flag/catalog entry exists; either way they are not real product features.

### P314 — Consumer app-store packaging

- **Status:** `stub`
- **Why:** stub: only cataloged under parked_features / optional vanity flags if any. Not scheduled for product work — backlog marks these as distraction. Rated stub (surface only) rather than absent when a flag/catalog entry exists; either way they are not real product features.

### P315 — Mobile-first full agent

- **Status:** `stub`
- **Why:** stub: only cataloged under parked_features / optional vanity flags if any. Not scheduled for product work — backlog marks these as distraction. Rated stub (surface only) rather than absent when a flag/catalog entry exists; either way they are not real product features.

### P316 — Electron desktop shell v1

- **Status:** `stub`
- **Why:** stub: only cataloged under parked_features / optional vanity flags if any. Not scheduled for product work — backlog marks these as distraction. Rated stub (surface only) rather than absent when a flag/catalog entry exists; either way they are not real product features.

### P317 — VR pair programming

- **Status:** `stub`
- **Why:** stub: only cataloged under parked_features / optional vanity flags if any. Not scheduled for product work — backlog marks these as distraction. Rated stub (surface only) rather than absent when a flag/catalog entry exists; either way they are not real product features.

### P318 — Emoji-only mode

- **Status:** `stub`
- **Why:** stub: only cataloged under parked_features / optional vanity flags if any. Not scheduled for product work — backlog marks these as distraction. Rated stub (surface only) rather than absent when a flag/catalog entry exists; either way they are not real product features.

### P319 — Meme responses

- **Status:** `stub`
- **Why:** stub: only cataloged under parked_features / optional vanity flags if any. Not scheduled for product work — backlog marks these as distraction. Rated stub (surface only) rather than absent when a flag/catalog entry exists; either way they are not real product features.

### P320 — Public user ranking

- **Status:** `stub`
- **Why:** stub: only cataloged under parked_features / optional vanity flags if any. Not scheduled for product work — backlog marks these as distraction. Rated stub (surface only) rather than absent when a flag/catalog entry exists; either way they are not real product features.

### P321 — Full IDE replacement

- **Status:** `stub`
- **Why:** stub: experimental/platform-overreach items intentionally not built as products. May have zero code or a refuse-to-prioritize note in parked catalog. SuperAI stays local-first orchestrator — not SaaS/IDE/OS/hardware replacement.

### P322 — Full browser OS agent

- **Status:** `stub`
- **Why:** stub: experimental/platform-overreach items intentionally not built as products. May have zero code or a refuse-to-prioritize note in parked catalog. SuperAI stays local-first orchestrator — not SaaS/IDE/OS/hardware replacement.

### P323 — Multi-tenant SaaS before local excellence

- **Status:** `stub`
- **Why:** Multi-tenant SaaS before local excellence rejected as strategy; local-first remains.

### P324 — Billing/Stripe product

- **Status:** `stub`
- **Why:** stub: experimental/platform-overreach items intentionally not built as products. May have zero code or a refuse-to-prioritize note in parked catalog. SuperAI stays local-first orchestrator — not SaaS/IDE/OS/hardware replacement.

### P325 — Marketplace payments

- **Status:** `stub`
- **Why:** stub: experimental/platform-overreach items intentionally not built as products. May have zero code or a refuse-to-prioritize note in parked catalog. SuperAI stays local-first orchestrator — not SaaS/IDE/OS/hardware replacement.

### P326 — Cryptocurrency payments

- **Status:** `stub`
- **Why:** stub: experimental/platform-overreach items intentionally not built as products. May have zero code or a refuse-to-prioritize note in parked catalog. SuperAI stays local-first orchestrator — not SaaS/IDE/OS/hardware replacement.

### P327 — Blockchain audit log

- **Status:** `stub`
- **Why:** stub: experimental/platform-overreach items intentionally not built as products. May have zero code or a refuse-to-prioritize note in parked catalog. SuperAI stays local-first orchestrator — not SaaS/IDE/OS/hardware replacement.

### P328 — Homomorphic encryption of prompts

- **Status:** `stub`
- **Why:** stub: experimental/platform-overreach items intentionally not built as products. May have zero code or a refuse-to-prioritize note in parked catalog. SuperAI stays local-first orchestrator — not SaaS/IDE/OS/hardware replacement.

### P329 — Federated learning across users

- **Status:** `stub`
- **Why:** stub: experimental/platform-overreach items intentionally not built as products. May have zero code or a refuse-to-prioritize note in parked catalog. SuperAI stays local-first orchestrator — not SaaS/IDE/OS/hardware replacement.

### P330 — On-device tiny LLM training

- **Status:** `stub`
- **Why:** stub: experimental/platform-overreach items intentionally not built as products. May have zero code or a refuse-to-prioritize note in parked catalog. SuperAI stays local-first orchestrator — not SaaS/IDE/OS/hardware replacement.

### P331 — Auto-fine-tune every repo by default

- **Status:** `stub`
- **Why:** stub: experimental/platform-overreach items intentionally not built as products. May have zero code or a refuse-to-prioritize note in parked catalog. SuperAI stays local-first orchestrator — not SaaS/IDE/OS/hardware replacement.

### P332 — 1000-node cluster scheduler

- **Status:** `stub`
- **Why:** stub: experimental/platform-overreach items intentionally not built as products. May have zero code or a refuse-to-prioritize note in parked catalog. SuperAI stays local-first orchestrator — not SaaS/IDE/OS/hardware replacement.

### P333 — Kubernetes operator early

- **Status:** `stub`
- **Why:** stub: experimental/platform-overreach items intentionally not built as products. May have zero code or a refuse-to-prioritize note in parked catalog. SuperAI stays local-first orchestrator — not SaaS/IDE/OS/hardware replacement.

### P334 — Service mesh integration

- **Status:** `stub`
- **Why:** stub: experimental/platform-overreach items intentionally not built as products. May have zero code or a refuse-to-prioritize note in parked catalog. SuperAI stays local-first orchestrator — not SaaS/IDE/OS/hardware replacement.

### P335 — Full observability vendor product

- **Status:** `stub`
- **Why:** stub: experimental/platform-overreach items intentionally not built as products. May have zero code or a refuse-to-prioritize note in parked catalog. SuperAI stays local-first orchestrator — not SaaS/IDE/OS/hardware replacement.

### P336 — Proprietary protocol instead of MCP

- **Status:** `stub`
- **Why:** No proprietary protocol replacing MCP — MCP parity is the direction (M093).

### P337 — Replace git

- **Status:** `stub`
- **Why:** stub: experimental/platform-overreach items intentionally not built as products. May have zero code or a refuse-to-prioritize note in parked catalog. SuperAI stays local-first orchestrator — not SaaS/IDE/OS/hardware replacement.

### P338 — Replace language servers wholesale

- **Status:** `stub`
- **Why:** stub: experimental/platform-overreach items intentionally not built as products. May have zero code or a refuse-to-prioritize note in parked catalog. SuperAI stays local-first orchestrator — not SaaS/IDE/OS/hardware replacement.

### P339 — Custom terminal emulator product

- **Status:** `stub`
- **Why:** stub: experimental/platform-overreach items intentionally not built as products. May have zero code or a refuse-to-prioritize note in parked catalog. SuperAI stays local-first orchestrator — not SaaS/IDE/OS/hardware replacement.

### P340 — Hardware appliance

- **Status:** `stub`
- **Why:** stub: experimental/platform-overreach items intentionally not built as products. May have zero code or a refuse-to-prioritize note in parked catalog. SuperAI stays local-first orchestrator — not SaaS/IDE/OS/hardware replacement.

### P341 — Phone companion app v1

- **Status:** `stub`
- **Why:** stub: experimental/platform-overreach items intentionally not built as products. May have zero code or a refuse-to-prioritize note in parked catalog. SuperAI stays local-first orchestrator — not SaaS/IDE/OS/hardware replacement.

### P342 — AR glasses integration

- **Status:** `stub`
- **Why:** stub: experimental/platform-overreach items intentionally not built as products. May have zero code or a refuse-to-prioritize note in parked catalog. SuperAI stays local-first orchestrator — not SaaS/IDE/OS/hardware replacement.

### P343 — Voice-only primary interface

- **Status:** `stub`
- **Why:** stub: experimental/platform-overreach items intentionally not built as products. May have zero code or a refuse-to-prioritize note in parked catalog. SuperAI stays local-first orchestrator — not SaaS/IDE/OS/hardware replacement.

### P344 — Always-listening mic daemon

- **Status:** `stub`
- **Why:** stub: experimental/platform-overreach items intentionally not built as products. May have zero code or a refuse-to-prioritize note in parked catalog. SuperAI stays local-first orchestrator — not SaaS/IDE/OS/hardware replacement.

### P345 — Webcam emotion detection

- **Status:** `stub`
- **Why:** stub: experimental/platform-overreach items intentionally not built as products. May have zero code or a refuse-to-prioritize note in parked catalog. SuperAI stays local-first orchestrator — not SaaS/IDE/OS/hardware replacement.

### P346 — Full SOC2 “as a feature”

- **Status:** `stub`
- **Why:** stub: enterprise_stubs / sso_status / rbac stubs only. No real SOC2/FedRAMP/SCIM/SIEM/DLP product. Intentionally parked until strategy changes.

### P347 — FedRAMP packaging

- **Status:** `stub`
- **Why:** stub: enterprise_stubs / sso_status / rbac stubs only. No real SOC2/FedRAMP/SCIM/SIEM/DLP product. Intentionally parked until strategy changes.

### P348 — Multi-region active-active cloud

- **Status:** `stub`
- **Why:** stub: enterprise_stubs / sso_status / rbac stubs only. No real SOC2/FedRAMP/SCIM/SIEM/DLP product. Intentionally parked until strategy changes.

### P349 — 50-role RBAC day one

- **Status:** `stub`
- **Why:** stub: enterprise_stubs / sso_status / rbac stubs only. No real SOC2/FedRAMP/SCIM/SIEM/DLP product. Intentionally parked until strategy changes.

### P350 — Deep LDAP

- **Status:** `stub`
- **Why:** stub: enterprise_stubs / sso_status / rbac stubs only. No real SOC2/FedRAMP/SCIM/SIEM/DLP product. Intentionally parked until strategy changes.

### P351 — Custom legal hold workflows

- **Status:** `stub`
- **Why:** stub: enterprise_stubs / sso_status / rbac stubs only. No real SOC2/FedRAMP/SCIM/SIEM/DLP product. Intentionally parked until strategy changes.

### P352 — eDiscovery UI

- **Status:** `stub`
- **Why:** stub: enterprise_stubs / sso_status / rbac stubs only. No real SOC2/FedRAMP/SCIM/SIEM/DLP product. Intentionally parked until strategy changes.

### P353 — Per-field data residency UI

- **Status:** `stub`
- **Why:** stub: enterprise_stubs / sso_status / rbac stubs only. No real SOC2/FedRAMP/SCIM/SIEM/DLP product. Intentionally parked until strategy changes.

### P354 — SIEM product

- **Status:** `stub`
- **Why:** stub: enterprise_stubs / sso_status / rbac stubs only. No real SOC2/FedRAMP/SCIM/SIEM/DLP product. Intentionally parked until strategy changes.

### P355 — Full DLP product

- **Status:** `stub`
- **Why:** stub: enterprise_stubs / sso_status / rbac stubs only. No real SOC2/FedRAMP/SCIM/SIEM/DLP product. Intentionally parked until strategy changes.

### P356 — MDM integration

- **Status:** `stub`
- **Why:** stub: enterprise_stubs / sso_status / rbac stubs only. No real SOC2/FedRAMP/SCIM/SIEM/DLP product. Intentionally parked until strategy changes.

### P357 — Air-gap CD productization

- **Status:** `stub`
- **Why:** stub: enterprise_stubs / sso_status / rbac stubs only. No real SOC2/FedRAMP/SCIM/SIEM/DLP product. Intentionally parked until strategy changes.

### P358 — Mandatory HSM

- **Status:** `stub`
- **Why:** stub: enterprise_stubs / sso_status / rbac stubs only. No real SOC2/FedRAMP/SCIM/SIEM/DLP product. Intentionally parked until strategy changes.

### P359 — Formal methods prover integration

- **Status:** `stub`
- **Why:** stub: enterprise_stubs / sso_status / rbac stubs only. No real SOC2/FedRAMP/SCIM/SIEM/DLP product. Intentionally parked until strategy changes.

### P360 — Quantum-safe crypto migration project

- **Status:** `stub`
- **Why:** stub: enterprise_stubs / sso_status / rbac stubs only. No real SOC2/FedRAMP/SCIM/SIEM/DLP product. Intentionally parked until strategy changes.

### P361 — ISO process automation suite

- **Status:** `stub`
- **Why:** stub: enterprise_stubs / sso_status / rbac stubs only. No real SOC2/FedRAMP/SCIM/SIEM/DLP product. Intentionally parked until strategy changes.

### P362 — Board compliance dashboard

- **Status:** `stub`
- **Why:** stub: enterprise_stubs / sso_status / rbac stubs only. No real SOC2/FedRAMP/SCIM/SIEM/DLP product. Intentionally parked until strategy changes.

### P363 — Customer success CRM inside SuperAI

- **Status:** `stub`
- **Why:** stub: enterprise_stubs / sso_status / rbac stubs only. No real SOC2/FedRAMP/SCIM/SIEM/DLP product. Intentionally parked until strategy changes.

### P364 — Sales quote generator

- **Status:** `stub`
- **Why:** stub: enterprise_stubs / sso_status / rbac stubs only. No real SOC2/FedRAMP/SCIM/SIEM/DLP product. Intentionally parked until strategy changes.

### P365 — Partner portal

- **Status:** `stub`
- **Why:** stub: enterprise_stubs / sso_status / rbac stubs only. No real SOC2/FedRAMP/SCIM/SIEM/DLP product. Intentionally parked until strategy changes.

### P366 — Reimplement vendor CLIs inside SuperAI

- **Status:** `full`
- **Why:** Agent-only prefer API over reimplementing vendor CLIs — strategy complete. Raised full.

### P367 — Fork and maintain all external agents

- **Status:** `stub`
- **Why:** No full reimplementation of vendor CLIs inside SuperAI (correctly avoided).

### P368 — Third memory stack “for completeness”

- **Status:** `full`
- **Why:** Chroma experimental opt-in gated; not dual default stacks. Raised full.

### P369 — Support every vector DB

- **Status:** `stub`
- **Why:** stub: overbuild / clone-every-SaaS items not implemented. Catalog entry only. SuperAI is not trying to be JupyterLab/Postman/Datadog/Jira/Notion/Figma/etc.

### P370 — Perfect every provider day one

- **Status:** `stub`
- **Why:** stub: overbuild / clone-every-SaaS items not implemented. Catalog entry only. SuperAI is not trying to be JupyterLab/Postman/Datadog/Jira/Notion/Figma/etc.

### P371 — Perfect voice without optional deps

- **Status:** `stub`
- **Why:** stub: overbuild / clone-every-SaaS items not implemented. Catalog entry only. SuperAI is not trying to be JupyterLab/Postman/Datadog/Jira/Notion/Figma/etc.

### P372 — Perfect browser without Playwright

- **Status:** `stub`
- **Why:** stub: overbuild / clone-every-SaaS items not implemented. Catalog entry only. SuperAI is not trying to be JupyterLab/Postman/Datadog/Jira/Notion/Figma/etc.

### P373 — Full JupyterLab clone

- **Status:** `stub`
- **Why:** stub: overbuild / clone-every-SaaS items not implemented. Catalog entry only. SuperAI is not trying to be JupyterLab/Postman/Datadog/Jira/Notion/Figma/etc.

### P374 — Full Postman clone

- **Status:** `stub`
- **Why:** stub: overbuild / clone-every-SaaS items not implemented. Catalog entry only. SuperAI is not trying to be JupyterLab/Postman/Datadog/Jira/Notion/Figma/etc.

### P375 — Full Datadog clone

- **Status:** `stub`
- **Why:** stub: overbuild / clone-every-SaaS items not implemented. Catalog entry only. SuperAI is not trying to be JupyterLab/Postman/Datadog/Jira/Notion/Figma/etc.

### P376 — Full Jira clone

- **Status:** `stub`
- **Why:** stub: overbuild / clone-every-SaaS items not implemented. Catalog entry only. SuperAI is not trying to be JupyterLab/Postman/Datadog/Jira/Notion/Figma/etc.

### P377 — Full Notion clone

- **Status:** `stub`
- **Why:** stub: overbuild / clone-every-SaaS items not implemented. Catalog entry only. SuperAI is not trying to be JupyterLab/Postman/Datadog/Jira/Notion/Figma/etc.

### P378 — Full Figma clone

- **Status:** `stub`
- **Why:** stub: overbuild / clone-every-SaaS items not implemented. Catalog entry only. SuperAI is not trying to be JupyterLab/Postman/Datadog/Jira/Notion/Figma/etc.

### P379 — In-CLI video editor

- **Status:** `stub`
- **Why:** stub: overbuild / clone-every-SaaS items not implemented. Catalog entry only. SuperAI is not trying to be JupyterLab/Postman/Datadog/Jira/Notion/Figma/etc.

### P380 — In-CLI music generation

- **Status:** `stub`
- **Why:** stub: overbuild / clone-every-SaaS items not implemented. Catalog entry only. SuperAI is not trying to be JupyterLab/Postman/Datadog/Jira/Notion/Figma/etc.

### P381 — Game engine

- **Status:** `stub`
- **Why:** stub: overbuild / clone-every-SaaS items not implemented. Catalog entry only. SuperAI is not trying to be JupyterLab/Postman/Datadog/Jira/Notion/Figma/etc.

### P382 — Excel-complete spreadsheet

- **Status:** `stub`
- **Why:** stub: overbuild / clone-every-SaaS items not implemented. Catalog entry only. SuperAI is not trying to be JupyterLab/Postman/Datadog/Jira/Notion/Figma/etc.

### P383 — CAD/CAM

- **Status:** `stub`
- **Why:** stub: overbuild / clone-every-SaaS items not implemented. Catalog entry only. SuperAI is not trying to be JupyterLab/Postman/Datadog/Jira/Notion/Figma/etc.

### P384 — Scientific HPC scheduler

- **Status:** `stub`
- **Why:** stub: overbuild / clone-every-SaaS items not implemented. Catalog entry only. SuperAI is not trying to be JupyterLab/Postman/Datadog/Jira/Notion/Figma/etc.

### P385 — Teaching LMS platform

- **Status:** `stub`
- **Why:** stub: overbuild / clone-every-SaaS items not implemented. Catalog entry only. SuperAI is not trying to be JupyterLab/Postman/Datadog/Jira/Notion/Figma/etc.

### P386 — Fully autonomous company-running agent

- **Status:** `refuse`
- **Why:** Fully autonomous company-running agent is unscoped and unsafe; refuse-closed.

### P387 — Recursive self-improvement without gates

- **Status:** `refuse`
- **Why:** Recursive self-improvement without gates is unsafe; refuse-closed.

### P388 — Unrestricted yolo as default

- **Status:** `refuse`
- **Why:** Unrestricted yolo as default would violate safe defaults (M005); refuse-closed.

### P389 — Internet-wide unconstrained browsing

- **Status:** `refuse`
- **Why:** Internet-wide unconstrained browsing violates SSRF/safety posture; refuse-closed.

### P390 — Auto-PRs to random public repos

- **Status:** `refuse`
- **Why:** Auto-PRs to random public repos is abuse-adjacent; refuse-closed.

### P391 — Auto-trading

- **Status:** `refuse`
- **Why:** Auto-trading is high-risk unscoped financial automation; refuse-closed.

### P392 — Auto-legal advice as certified

- **Status:** `refuse`
- **Why:** Certified legal advice agent is liability/unsafe scope; refuse-closed.

### P393 — Medical diagnosis agent

- **Status:** `refuse`
- **Why:** Medical diagnosis agent is liability/unsafe scope; refuse-closed.

### P394 — Jailbreak playground product

- **Status:** `refuse`
- **Why:** Jailbreak playground product would undermine safety; refuse-closed.

### P395 — Prompt-virus research tools

- **Status:** `refuse`
- **Why:** Prompt-virus research tools are dual-use abuse risk; refuse-closed.

### P396 — Deepfake media tools

- **Status:** `refuse`
- **Why:** Deepfake media tools are abuse-prone; refuse-closed.

### P397 — Mass scraping suite

- **Status:** `refuse`
- **Why:** Mass scraping suite is abuse/legal risk; refuse-closed.

### P398 — CAPTCHA farms

- **Status:** `refuse`
- **Why:** CAPTCHA farms are abuse infrastructure; refuse-closed.

### P399 — “AGI mode” branding

- **Status:** `refuse`
- **Why:** AGI mode branding is dishonest hype; refuse-closed for product integrity.

### P400 — Infinite backlog without Phase 6 smoke

- **Status:** `refuse`
- **Why:** Infinite backlog without Phase 6 smoke honesty gate undermines verification; refuse-closed as process anti-pattern.

## Bucket rollups

### Must M001–M100

| Status | Count |
|--------|------:|
| full | 98 |
| stub | 1 |
| host | 1 |

### Should S101–S200

| Status | Count |
|--------|------:|
| full | 62 |
| stub | 36 |
| absent | 2 |

### Nice N201–N300

| Status | Count |
|--------|------:|
| full | 29 |
| stub | 42 |
| absent | 29 |

### Parked P301–P400

| Status | Count |
|--------|------:|
| full | 2 |
| stub | 83 |
| refuse | 15 |

## How status decisions were made

1. **Compare backlog wording** to actual modules/CLI/tests in-repo.
2. **full** only if the stated intent is usable end-to-end for daily product use.
3. **foundation** if real code exists but universality, UX, or hardening is incomplete.
4. **stub** if only flags, samples, or placeholders exist.
5. **absent** if no meaningful implementation.
6. **host** if code is complete but live proof needs credentials.
7. **refuse** if policy intentionally blocks implementation (safety).

Regenerate: `python scripts/gen_v6_scorecard.py`

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

