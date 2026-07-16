# SuperAI Improvement V6 — World’s Best AI CLI Backlog

**Created:** 2026-07-16  
**Updated:** 2026-07-16  
**Status:** Phases **1–15 implemented** as code (foundations + prior V1–V5); Phase **6 partial** (live smoke host-only); Phase **16 park**; Phases **17–20 n/a**  
**Scope:** 400 items — 100 Must · 100 Should · 100 Nice · 100 Not important now  
**Product frame:** SuperAI as multi-model / multi-CLI **orchestrator** + agent + memory + cost control  

**Prior completed tracks:** V1–V5 plans, MoSCoW 100, not-important W1–W8, `core.superai_agent`, DoD-strict sweeps.

**Honesty:** Live multi-provider smoke (M089 / Phase 99) remains a **host gate**.  
**Report:** `superai v6-status`

---

## How to read this backlog

| Field | Meaning |
|-------|---------|
| **ID** | Stable id: `M###` must, `S###` should, `N###` nice, `P###` park/not-important-now |
| **Deps** | Other IDs that should exist first (soft unless noted **hard**) |
| **Pillar** | S=Strong · E=Efficient · C=Cost · F=Flexible · K=Complete (completeness) |

**Dependency legend**

- `—` none  
- `M010` depends on item M010  
- `M001+M002` needs both  

---

## Phased roadmap (high level)

```text
Phase 0   Foundation lock (already largely done; verify gaps only)
Phase 1   Trust & money truth          → M001–M020, M086–M090
Phase 2   Agent loop excellence        → M021–M040
Phase 3   Multi-model / multi-CLI      → M041–M055
Phase 4   Memory & learning            → M056–M070
Phase 5   CLI product quality          → M071–M085
Phase 6   Verification & honesty       → M086–M100  (+ host Phase 99)
Phase 7   Should: intelligence         → S101–S125
Phase 8   Should: cost/efficiency      → S126–S150
Phase 9   Should: routing & models     → S151–S170
Phase 10  Should: memory & team        → S171–S185
Phase 11  Should: polish               → S186–S200
Phase 12  Nice: power CLI              → N201–N230
Phase 13  Nice: deep coding            → N231–N260
Phase 14  Nice: orchestration theater  → N261–N280
Phase 15  Nice: ecosystem              → N281–N300
Phase 16  Parked (P301–P400)           → only if explicitly reopened
```

### Phase goals

| Phase | Goal | Exit criteria (definition of done) |
|------:|------|-------------------------------------|
| 1 | Safe to spend & automate | Every major spend path: budget + contract + error_code; safety tests green |
| 2 | Best-in-class agent loop | Session, tools, change-set, stream, cancel, roles documented + tested |
| 3 | Best multi-CLI orchestrator | Catalog, failover, boards, health, bakeoff under cost control |
| 4 | Memory that helps, not noise | Inject ranked; write-back gated; tenant-safe; backup/export |
| 5 | CLI people love daily | Front door, doctor, status, JSON, exit codes, Windows install |
| 6 | Proof | Unit + golden eval + smoke harness; live smoke when keys present |
| 7–11 | Differentiated shoulds | Prioritize by user pain; each phase has measurable metric |
| 12–15 | Nice depth | Only after Phase 6 exit; optional tracks |
| 16 | Park | Do not schedule unless product strategy changes |

### Suggested calendar (indicative, not binding)

| Window | Phases | Focus |
|--------|--------|--------|
| Q1 of “best CLI” push | 1–3 | Trust, agent, multi-CLI |
| Q2 | 4–6 | Memory, CLI UX, verification + live smoke |
| Q3 | 7–9 | Intelligence, cost, routing |
| Q4 | 10–11 + selective Nice | Team + polish; ecosystem only if demand |

---

## Cross-cutting dependency map

```text
M001 budget ──┬── M002 accurate cost
              ├── M003 preflight boards
              └── M019 explain-run

M005 plan-mode ── M025 change-set ── M026 diff check
M006 jail ── M043 CLI discovery ── M044 CLI models
M008 contract ── M009 error taxonomy ── M090 contract tests
M021 sessions ── M028 context pack ── M029 compact
M031 front-door ── M032 confidence ── S200 onboarding
M041 registry ── M046 catalog ── M050 bandit ── S151 refresh
M056 palace ── M059 smart inject ── S171 project memory
M073 doctor ── M088 smoke harness ── M089 live smoke (host)
M086 safety suite ── M087 golden eval ── Phase 6 exit
```

---

# Must have (M001–M100)

### Trust, safety, money (M001–M020)

| ID | Item | Pillar | Deps |
|----|------|--------|------|
| M001 | Hard budget ceilings on every spend path (CLI, MCP, HTTP, agent, boards) | C,S | — |
| M002 | Accurate cost from real tokens × registry rates | C | M001 |
| M003 | Pre-flight cost estimate before multi-member boards | C | M002 |
| M004 | Dry-run / plan mode cannot mutate disk or git | S | — |
| M005 | Permission model plan/ask/auto/yolo with safe defaults | S | M004 |
| M006 | Workspace jail fail-closed for tools and external CLIs | S | — |
| M007 | Side-effect audit log (write/delete/run, run_id) | S | M008 |
| M008 | Stable result contract on every public command | S,K | — |
| M009 | Error taxonomy for scripts (`budget`, `readiness`, `timeout`, …) | S,K | M008 |
| M010 | Provider readiness check before live calls | S | — |
| M011 | Failover ordered, bounded, logged | S,F | M010 |
| M012 | Secrets never printed in logs/errors/TUI | S | — |
| M013 | Keyring/env secret store with rotate/list | S,F | M012 |
| M014 | SSRF protection on URL/fetch tools | S | M006 |
| M015 | Prompt-injection defenses for tool loops | S | M021 |
| M016 | Tenant isolation for shared memory | S | M056 |
| M017 | Cancel / Ctrl+C stops workers cooperatively | S,E | M021 |
| M018 | Timeouts on model, CLI, and tool ops | S,E | M017 |
| M019 | Reproducible explain-run from `run_id` | K,S | M007,M008 |
| M020 | Offline mock mode never claims live success | S | M008 |

### Core agent loop (M021–M040)

| ID | Item | Pillar | Deps |
|----|------|--------|------|
| M021 | Reliable multi-turn agent session (resume/export/undo) | K,F | M008 |
| M022 | Strict tool protocol (JSON schema tools) | S | M021 |
| M023 | Parallel independent tools (read/grep/glob) | E | M022 |
| M024 | Idempotent file writes | E,S | M022 |
| M025 | Change-set staging + apply/reject | S,K | M005,M022 |
| M026 | Diff check before apply | S | M025 |
| M027 | Real token streaming where supported | E,K | M021 |
| M028 | Context packing under hard token budget | E,C | M021 |
| M029 | Session compaction preserving decisions/todos | E | M028 |
| M030 | Agent roles: build / plan / ask with boundaries | F,S | M021,M005 |
| M031 | Front-door routing: agent vs board vs orchestrator | F | M030,M054 |
| M032 | Front-door confidence when routing ambiguous | F | M031 |
| M033 | Local-first with escalate-to-premium on failure | C,F | M011,M041 |
| M034 | Cheap-first for summarize/plan steps | C | M034→M033,M047 |
| M035 | Complexity → board member count | C,E | M054 |
| M036 | Board early-exit on strong consensus | C,E | M054 |
| M037 | Worker diversity (1 premium + N cheap) | C,F | M046 |
| M038 | Worktree isolation for risky writes | S | M025,M006 |
| M039 | Test-driven loop (red/green) first-class | K | M022,M105(soft) |
| M040 | PR/diff review via multi-CLI + contracts | K | M054,M008 |

### Multi-model / multi-CLI (M041–M055)

| ID | Item | Pillar | Deps |
|----|------|--------|------|
| M041 | Universal OpenAI-compatible registration | F | — |
| M042 | First-class local: Ollama / LM Studio / vLLM | F,C | M041 |
| M043 | External CLI discovery on PATH (Windows-hardened) | F | — |
| M044 | CLI inner-model selection (`cli:name@model`) | F | M043 |
| M045 | Unified member catalog (API + CLI + local) | F | M041,M043 |
| M046 | Live probe of available members | F | M045 |
| M047 | Health circuits per provider | S,E | M010 |
| M048 | Rate-limit queue / backoff | S,E | M047 |
| M049 | Model blacklist after repeated failures | S | M047 |
| M050 | Bandit / learned routing from outcomes | C,E | M002,M047 |
| M051 | Bakeoff with report + pin winner | F,C | M041,M008 |
| M052 | Compare command with contract | F | M008,M041 |
| M053 | Council with voting modes | F | M041,M008 |
| M054 | Parallel multi-CLI opinions with merge | F,E | M043,M008 |
| M055 | Cost router shrinks boards under budget | C | M001,M003,M054 |

### Memory & learning (M056–M070)

| ID | Item | Pillar | Deps |
|----|------|--------|------|
| M056 | Central Memory Palace inject before major runs | K,E | — |
| M057 | Write-back of successful outcomes | K | M056,M008 |
| M058 | Semantic search with tenant tags | F,S | M056,M016 |
| M059 | Smart memory inject (rank + token cap) | E,C | M056,M028 |
| M060 | Memory forget / TTL / erase | S,K | M056 |
| M061 | Learning: promote durable patterns only | K | M057 |
| M062 | Conflict resolution for contradictory memories | S | M061 |
| M063 | Distill / deprecate redundant memories | E | M061 |
| M064 | Wings/rooms navigation | F,K | M056 |
| M065 | Encrypted backup of local SuperAI state | S | M012 |
| M066 | Profile export/import | F | M013 |
| M067 | Run history searchable by task/cost/model | K,C | M002,M019 |
| M068 | Preferences that bias routing | F,C | M050 |
| M069 | Skills library (reusable playbooks) | K,F | M022 |
| M070 | Skill permissions (what a skill may touch) | S | M005,M069 |

### CLI UX product quality (M071–M085)

| ID | Item | Pillar | Deps |
|----|------|--------|------|
| M071 | Zero-subcommand launches useful front door | K | M031 |
| M072 | One-shot `do "…"` routing | K | M031 |
| M073 | Doctor diagnoses real failures | K,S | M010,M047 |
| M074 | Status with spend + health + cache | C,K | M001,M047 |
| M075 | Install/onboard wizard (Windows-first) | K | M043 |
| M076 | Host-tools check/install matrix | K | M075 |
| M077 | Rich TUI: tools, cost, permission live | K | M021,M002 |
| M078 | Slash command palette + help | K | M077 |
| M079 | JSON output mode for automation | K,F | M008 |
| M080 | Trustworthy process exit codes | K | M009 |
| M081 | High-quality `--help` and examples | K | — |
| M082 | Shell completion | K | M081 |
| M083 | Config get/set with validation | S,K | M001 |
| M084 | Version / update check | K | — |
| M085 | Diagnostics zip for support | K,S | M007,M074 |

### Completeness & verification (M086–M100)

| ID | Item | Pillar | Deps |
|----|------|--------|------|
| M086 | Unit suite for safety/money (plan, budget, jail) | S | M001,M004,M006 |
| M087 | Golden offline eval set | K | M021,M020 |
| M088 | Smoke harness that never false-passes | S | M020 |
| M089 | Live multi-provider smoke matrix (host keys) | K | M088,M041 **host** |
| M090 | Contract tests on top 30 commands | S,K | M008 |
| M091 | Performance budgets for cold start | E | — |
| M092 | Deterministic mock fixtures for CI | S,K | M020 |
| M093 | MCP parity with CLI safety rules | S | M001,M005,M008 |
| M094 | Web API auth for non-loopback | S | M012 |
| M095 | Graph of runs (models/tools/cost) | K | M019,M002 |
| M096 | Schedule/goals with caps (no yolo inherit) | S | M005,M001 |
| M097 | Plugin install with sha256 verify | S | M012 |
| M098 | Constitution/policy hooks for org rules | S,F | M005 |
| M099 | Architecture + quickstart + threat docs | K | — |
| M100 | Honest dashboard: mock vs live | S,K | M008,M020 |

---

# Should have (S101–S200)

### Agent intelligence (S101–S125)

| ID | Item | Pillar | Deps |
|----|------|--------|------|
| S101 | Agent-maintained todo list across long tasks | K | M021,M029 |
| S102 | Spec-first: plan → approve → implement | S,K | M030,M005 |
| S103 | Architecture mode vs implementation mode | F | M030 |
| S104 | Self-critique pass before claiming done | S | M030 |
| S105 | Auto test discovery and run after edits | K | M039,M022 |
| S106 | Lint/typecheck integration post-edit | K | M022 |
| S107 | Repo map / workspace index for large trees | E | M006 |
| S108 | Symbol-aware navigation (beyond grep) | E | S107 |
| S109 | Fix CI failure from log paste | K | M022,S105 |
| S110 | Explain PR with file-level findings | K | M040 |
| S111 | Multi-file refactor with rename safety | K | S108,M025 |
| S112 | Dependency upgrade assistant | K | M022 |
| S113 | DB/schema migration dry-run helper | K | M004 |
| S114 | Security scan hooks (secrets, vulns) | S | M007 |
| S115 | License/compliance check on new deps | S | S112 |
| S116 | Commit message + branch naming helpers | K | M006 |
| S117 | Safe conflict assistance for merges | S | M006 |
| S118 | `git apply`-compatible patch format | K | M026 |
| S119 | Vision for UI bug screenshots | F | M041 |
| S120 | PDF/doc attach for requirements | F | M028 |
| S121 | Browser tool for local web verification | K | M014 |
| S122 | Notebook run/repair mode | K | M022 |
| S123 | SQL agent with allowlisted DBs | S,F | M006,M005 |
| S124 | Log triage mode (stack traces) | K | M022 |
| S125 | Continue last session smart resume | K | M021 |

### Cost & efficiency (S126–S150)

| ID | Item | Pillar | Deps |
|----|------|--------|------|
| S126 | Cross-session semantic result cache (opt-in) | C,E | M002 |
| S127 | Prompt/prefix cache for long system prompts | C,E | M028 |
| S128 | Speculative local draft → cloud polish | C,F | M033 |
| S129 | Mid-task model demotion when task simplifies | C | M050 |
| S130 | Escalate only on quality gate failure | C,S | M033,S105 |
| S131 | Per-project budget policies | C | M001 |
| S132 | Per-command budget overrides | C,F | M001 |
| S133 | Cost forecast before long boards | C | M003 |
| S134 | Daily/weekly spend reports | C,K | M002,M067 |
| S135 | Cache hit rate in status | C | M074,S126 |
| S136 | Token waterfall visualization | C,K | M002,M019 |
| S137 | Stagger expensive board members | C | M054 |
| S138 | Always-local for trivial “what is” questions | C | M031,M034 |
| S139 | Compress tool outputs before re-feed | E,C | M022 |
| S140 | Drop redundant reads via mtime index | E | M024,S107 |
| S141 | Shared embedding cache | E | M058 |
| S142 | Batch embeddings | E | S141 |
| S143 | Lazy-load heavy deps | E | M091 |
| S144 | Faster cold start (defer imports) | E | M091 |
| S145 | Optional background model warmup | E | M042 |
| S146 | Adaptive max_members from history | C | M035,M050 |
| S147 | Cancel generation on user interrupt | E | M017 |
| S148 | Partial stream cancel stops workers | E,C | M017,M027 |
| S149 | Sticky cheap mode per repo | C | M083 |
| S150 | A/B routing experiments with reports | C,F | M050 |

### Routing & models (S151–S170)

| ID | Item | Pillar | Deps |
|----|------|--------|------|
| S151 | Catalog auto-refresh (e.g. OpenRouter) | F | M041 |
| S152 | Capability tags (vision, tools, long-context) | F | M045 |
| S153 | Context window awareness per model | E,S | S152,M028 |
| S154 | JSON-mode enforcement for tools | S | M022 |
| S155 | Structured output validation + retry | S | M009,S154 |
| S156 | Native Anthropic/Google adapters (depth) | F | M041 |
| S157 | Better Windows CLI shim resolution | F | M043 |
| S158 | WSL/path interop helpers | F | M043 |
| S159 | Container sandbox for bash tools | S | M006 |
| S160 | Network allowlist for tools | S | M014 |
| S161 | Per-tool timeout configs | S,E | M018 |
| S162 | Per-provider concurrency caps | E,S | M048 |
| S163 | Priority queue interactive vs batch | E | M048 |
| S164 | Pin model per task type | F | M050 |
| S165 | Team-shared routing policies | F | M098 |
| S166 | Clear UX when local runtime down | K | M042,M073 |
| S167 | GPU/local resource detect for pick | C,F | M042 |
| S168 | OpenRouter strategy knobs | F | M041 |
| S169 | NVIDIA NIM first-class depth | F | M041 |
| S170 | Multi-key rotation per provider | S,F | M013 |

### Memory & team (S171–S185)

| ID | Item | Pillar | Deps |
|----|------|--------|------|
| S171 | Project-scoped vs global memory | F | M056 |
| S172 | Memory confidence scores | S | M061 |
| S173 | Human confirm before sensitive memory write | S | M005,M057 |
| S174 | Memory search in TUI | K | M058,M077 |
| S175 | “Why injected” citations | S,K | M059 |
| S176 | Conflict UI when memories disagree | S | M062 |
| S177 | Team palace export/import | F | M016,M065 |
| S178 | Org-level skills registry | F | M069 |
| S179 | Shared run templates | F | M069 |
| S180 | Secure messenger inbound tasking | F,S | M005,M012 |
| S181 | Notify only on approval-needed / done | C,K | S180 |
| S182 | Multi-user permission roles | S | M098 |
| S183 | Audit export for compliance | S | M007 |
| S184 | Retention policies | S | M060 |
| S185 | Encryption at rest for sessions | S | M012,M021 |

### Product polish (S186–S200)

| ID | Item | Pillar | Deps |
|----|------|--------|------|
| S186 | Web session browser | K | M021,M094 |
| S187 | SSE live progress for web | E,K | S186,M017 |
| S188 | VS Code: run + stream + apply set | K | M025,M027 |
| S189 | JetBrains thin plugin | K | S188 |
| S190 | Useful offline PWA shell | K | M094 |
| S191 | TUI themes | K | M077 |
| S192 | Keybind customization | F | M077 |
| S193 | Better multi-line editor / paste | K | M077 |
| S194 | Clipboard integration | K | M077 |
| S195 | `init` project templates | K | M075 |
| S196 | Recipe gallery (fix bug, add API, …) | K | M069 |
| S197 | Explain-run with mermaid graph | K | M019,M095 |
| S198 | Profile auto-suggest + one-key apply | C,K | M074,M050 |
| S199 | Onboarding quest (first 5 wins) | K | M075,M071 |
| S200 | In-CLI changelog / what’s new | K | M084 |

---

# Nice to have (N201–N300)

### Power-user CLI (N201–N230)

| ID | Item | Pillar | Deps |
|----|------|--------|------|
| N201 | Fuzzy command palette (Ctrl+K) | K | M078 |
| N202 | NL → any command with preview | F | M031 |
| N203 | Command macros / aliases | F | M083 |
| N204 | Pipelines between SuperAI modes | F | M079 |
| N205 | Watch mode (re-run on change) | E | M022 |
| N206 | Daemon for goals/schedules | F | M096 |
| N207 | Remote headless agent over SSH | F | M006,M012 |
| N208 | Multiplexed sessions (tmux-like) | F | M021 |
| N209 | Split-pane TUI | K | M077 |
| N210 | Vim keys in TUI | F | M077 |
| N211 | Optional mouse support | F | M077 |
| N212 | Image paste from clipboard | F | S119 |
| N213 | Optional voice channel | F | — |
| N214 | Full i18n for CLI/TUI | F | M081 |
| N215 | Screen-reader friendly TUI | K | M077 |
| N216 | Colorblind-safe palettes | K | S191 |
| N217 | High-contrast mode | K | S191 |
| N218 | Replay tape for demos | K | M092 |
| N219 | Publish session as markdown | K | M021 |
| N220 | Shareable sanitized run bundles | K | M019,M012 |
| N221 | Public benchmark harness | K | M087 |
| N222 | Private model leaderboard on your repo | C,F | M051 |
| N223 | Custom agents DSL (YAML) | F | M030 |
| N224 | Plugin marketplace UX | F | M097 |
| N225 | Signed plugins | S | M097 |
| N226 | Skill versioning | F | M069 |
| N227 | Pre/post tool hooks | F | M022 |
| N228 | Simple policy-as-code | S | M098 |
| N229 | Enterprise SSO for web API | S | M094 |
| N230 | SCIM provisioning (stretch) | F | N229 |

### Deep coding (N231–N260)

| ID | Item | Pillar | Deps |
|----|------|--------|------|
| N231 | LSP diagnostics integration | E,K | S107 |
| N232 | Go-to-definition via LSP | E | N231 |
| N233 | Rename symbol across project | K | N232 |
| N234 | Extract method/function assist | K | N231 |
| N235 | Dead code detection | K | S107 |
| N236 | Complexity hotspots map | K | S107 |
| N237 | Coverage-guided test generation | K | M039 |
| N238 | Mutation testing opt-in | K | M039 |
| N239 | Flaky test hunter | K | S105 |
| N240 | Snapshot test updates with review | S | M005 |
| N241 | Docker compose helpers | F | M006 |
| N242 | K8s dry-run helpers | F | M004 |
| N243 | Terraform plan explain | K | M004 |
| N244 | GraphQL schema assist | K | M022 |
| N245 | OpenAPI generate + validate | K | M022 |
| N246 | Proto/gRPC helpers | K | M022 |
| N247 | Mobile build log triage | K | S124 |
| N248 | Game-engine log modes (niche) | F | S124 |
| N249 | Dataframe/SQL notebook hybrid | F | S122,S123 |
| N250 | Local vector search over repo chunks | E | S107,S141 |
| N251 | AST-based edit tools | S,E | M022 |
| N252 | Format-on-write | K | M022 |
| N253 | Import organizer | K | N252 |
| N254 | License header inject | K | S115 |
| N255 | CODEOWNERS-aware routing | F | M040 |
| N256 | Monorepo package awareness | F | S107 |
| N257 | Build system detect (make/nx/bazel) | F | S107 |
| N258 | Incremental index updates | E | S107 |
| N259 | Semantic diff summaries | K | M040 |
| N260 | One-command “why did CI fail” | K | S109 |

### Orchestration theater (N261–N280)

| ID | Item | Pillar | Deps |
|----|------|--------|------|
| N261 | Multi-agent debate with roles | F | M053,M030 |
| N262 | Red team vs blue team security review | S | M040,S114 |
| N263 | PM agent → engineer agent handoff | F | M030,S101 |
| N264 | QA agent sees only diffs | S | M040,M005 |
| N265 | Release captain checklist agent | K | S101 |
| N266 | Incident commander mode | K | S124 |
| N267 | On-call runbook executor | S | M005,M098 |
| N268 | Multi-repo cross-PR coordination | F | M040 |
| N269 | Dependency PR stack helper | K | S112 |
| N270 | Feature flag rollout assistant | K | — |
| N271 | Canary analysis helper | K | — |
| N272 | Metrics anomaly explain | K | — |
| N273 | Cloud bill cost anomaly (opt-in) | C | M013 |
| N274 | SLA report generator | K | — |
| N275 | ADR writer | K | M069 |
| N276 | RFC co-author | K | M069 |
| N277 | Meeting notes → tasks | F | S101 |
| N278 | Ticket sync (Jira/Linear/GitHub) | F | M013 |
| N279 | Design token consistency checks | K | — |
| N280 | Web UI accessibility audit assist | K | S121 |

### Ecosystem (N281–N300)

| ID | Item | Pillar | Deps |
|----|------|--------|------|
| N281 | Homebrew / winget / choco packages | K | M075 |
| N282 | Official Docker image | K | M075 |
| N283 | Nix flake | F | M075 |
| N284 | GitHub Action “superai review” | K | M040 |
| N285 | GitLab CI component | K | M040 |
| N286 | Pre-commit hook | K | M004 |
| N287 | Devcontainer feature | K | N282 |
| N288 | Codespaces template | K | N287 |
| N289 | Raycast/Alfred extension | K | M072 |
| N290 | Discord bot thin client | F | S180 |
| N291 | Telegram production hardening | S | S180 |
| N292 | Slack slash commands | F | S180 |
| N293 | Notion sync when key present | F | M013 |
| N294 | Obsidian vault export | F | M021 |
| N295 | Browser extension send-to-SuperAI | F | M072 |
| N296 | Figma comment → task (stretch) | F | S101 |
| N297 | Datadog/NewRelic log pull (opt-in) | F | M013,M014 |
| N298 | Cloud provider CLIs as gated tools | F,S | M005,M043 |
| N299 | Community skills marketplace | F | N224 |
| N300 | Public awesome-recipes catalog | K | S196 |

---

# Not important now (P301–P400) — park

> These are **parked**, not forbidden forever. Do not schedule into Phases 1–6 unless strategy changes.  
> Listed so the roadmap stays focused.

### Brand / vanity (P301–P320)

| ID | Item | Why park |
|----|------|----------|
| P301 | Rebrand SuperAI to another product name | Distracts from quality |
| P302 | Pixel-match OpenCode/Claude Code UI | Not our differentiator |
| P303 | Marketing site redesign as engineering work | Wrong team queue |
| P304 | Animated splash screens | Zero user value |
| P305 | NFT/badge gamification | Noise |
| P306 | Social share buttons in CLI | Not CLI-core |
| P307 | Custom ASCII art every run | Noise |
| P308 | Seasonal themes (required) | Optional later as S191 |
| P309 | Mascot program | Marketing |
| P310 | Startup sounds | Accessibility conflict |
| P311 | “AI CEO” persona as default | Trust risk |
| P312 | Hype agent names | Confuses roles |
| P313 | Brand-war dark-mode mandates | Theme already Should |
| P314 | Consumer app-store packaging | Premature distribution |
| P315 | Mobile-first full agent | CLI is primary |
| P316 | Electron desktop shell v1 | Web may suffice |
| P317 | VR pair programming | Speculative |
| P318 | Emoji-only mode | Gimmick |
| P319 | Meme responses | Unprofessional default |
| P320 | Public user ranking | Privacy/toxicity |

### Speculative platforms (P321–P345)

| ID | Item | Why park |
|----|------|----------|
| P321 | Full IDE replacement | Scope explosion |
| P322 | Full browser OS agent | Scope explosion |
| P323 | Multi-tenant SaaS before local excellence | Wrong order |
| P324 | Billing/Stripe product | Premature business layer |
| P325 | Marketplace payments | Depends P324 |
| P326 | Cryptocurrency payments | Unnecessary |
| P327 | Blockchain audit log | Overhead |
| P328 | Homomorphic encryption of prompts | Research |
| P329 | Federated learning across users | Privacy/research |
| P330 | On-device tiny LLM training | Research |
| P331 | Auto-fine-tune every repo by default | Cost/risk |
| P332 | 1000-node cluster scheduler | Wrong product |
| P333 | Kubernetes operator early | Premature ops |
| P334 | Service mesh integration | Premature |
| P335 | Full observability vendor product | Not core |
| P336 | Proprietary protocol instead of MCP | Fragments ecosystem |
| P337 | Replace git | Non-goal for coding CLI |
| P338 | Replace language servers wholesale | Use LSP instead (N231) |
| P339 | Custom terminal emulator product | Separate product |
| P340 | Hardware appliance | Not now |
| P341 | Phone companion app v1 | After CLI excellence |
| P342 | AR glasses integration | Speculative |
| P343 | Voice-only primary interface | Optional voice is enough |
| P344 | Always-listening mic daemon | Privacy risk |
| P345 | Webcam emotion detection | Creepy / useless |

### Premature enterprise (P346–P365)

| ID | Item | Why park |
|----|------|----------|
| P346 | Full SOC2 “as a feature” | Process, not backlog item |
| P347 | FedRAMP packaging | Too early |
| P348 | Multi-region active-active cloud | SaaS-first trap |
| P349 | 50-role RBAC day one | Overdesign |
| P350 | Deep LDAP | After SSO need proven |
| P351 | Custom legal hold workflows | Niche |
| P352 | eDiscovery UI | Niche |
| P353 | Per-field data residency UI | Overdesign |
| P354 | SIEM product | Wrong product |
| P355 | Full DLP product | Wrong product |
| P356 | MDM integration | Device mgmt |
| P357 | Air-gap CD productization | Special sales motion |
| P358 | Mandatory HSM | Optional later |
| P359 | Formal methods prover integration | Research |
| P360 | Quantum-safe crypto migration project | Premature |
| P361 | ISO process automation suite | Consulting |
| P362 | Board compliance dashboard | Salesware |
| P363 | Customer success CRM inside SuperAI | Wrong product |
| P364 | Sales quote generator | Wrong product |
| P365 | Partner portal | Premature |

### Overbuild / wrong layer (P366–P385)

| ID | Item | Why park |
|----|------|----------|
| P366 | Reimplement vendor CLIs inside SuperAI | Orchestrate, don’t clone |
| P367 | Fork and maintain all external agents | Unmaintainable |
| P368 | Third memory stack “for completeness” | Ops cost |
| P369 | Support every vector DB | Indecision tax |
| P370 | Perfect every provider day one | Incremental (M041+) |
| P371 | Perfect voice without optional deps | Nice N213 later |
| P372 | Perfect browser without Playwright | S121 is enough |
| P373 | Full JupyterLab clone | S122 subset |
| P374 | Full Postman clone | Out of scope |
| P375 | Full Datadog clone | Out of scope |
| P376 | Full Jira clone | N278 integrate, don’t clone |
| P377 | Full Notion clone | N293 sync only |
| P378 | Full Figma clone | Out of scope |
| P379 | In-CLI video editor | Out of scope |
| P380 | In-CLI music generation | Out of scope |
| P381 | Game engine | Out of scope |
| P382 | Excel-complete spreadsheet | Out of scope |
| P383 | CAD/CAM | Out of scope |
| P384 | Scientific HPC scheduler | Out of scope |
| P385 | Teaching LMS platform | Out of scope |

### Research / unsafe rabbit holes (P386–P400)

| ID | Item | Why park |
|----|------|----------|
| P386 | Fully autonomous company-running agent | Unsafe / unscoped |
| P387 | Recursive self-improvement without gates | Unsafe |
| P388 | Unrestricted yolo as default | Violates M005 |
| P389 | Internet-wide unconstrained browsing | SSRF/abuse |
| P390 | Auto-PRs to random public repos | Abuse |
| P391 | Auto-trading | Liability |
| P392 | Auto-legal advice as certified | Liability |
| P393 | Medical diagnosis agent | Liability |
| P394 | Jailbreak playground product | Abuse |
| P395 | Prompt-virus research tools | Abuse |
| P396 | Deepfake media tools | Abuse |
| P397 | Mass scraping suite | Legal/ToS |
| P398 | CAPTCHA farms | Abuse |
| P399 | “AGI mode” branding | Dishonest hype |
| P400 | Infinite backlog without Phase 6 smoke | Process failure |

---

## Phase-by-phase execution checklist

### Phase 1 — Trust & money (hard gate for “best”)

**IDs:** M001–M020, plus M086–M090 as validation  
**Hard deps:** none beyond current V4 baseline  
**Exit:** safety suite + budget/contract audit doc for top entrypoints  

### Phase 2 — Agent loop

**IDs:** M021–M040  
**Hard deps:** Phase 1 M004–M009, M017–M018  
**Exit:** agent session + tools + change-set + roles documented; unit tests  

### Phase 3 — Multi-model / multi-CLI

**IDs:** M041–M055  
**Hard deps:** M001, M008, M010–M011  
**Exit:** members catalog, boards, failover, bakeoff under cost router  

### Phase 4 — Memory & learning

**IDs:** M056–M070  
**Hard deps:** M016 (with M056), M005 for skill perms  
**Exit:** inject quality metric; backup/export works  

### Phase 5 — CLI product quality

**IDs:** M071–M085  
**Hard deps:** M031, M073←M010  
**Exit:** new user can install on Windows and complete first task  

### Phase 6 — Verification & honesty

**IDs:** M086–M100  
**Hard deps:** Phases 1–5 core complete  
**Host gate:** M089 live smoke when keys available  
**Exit:** CI green on M086–M088,M090–M092; smoke harness never false-pass  

### Phases 7–11 — Should tracks

| Phase | IDs | Priority rule |
|------:|-----|---------------|
| 7 | S101–S125 | Pick top 10 by coding-user pain |
| 8 | S126–S150 | Pick items that cut $ or latency ≥20% |
| 9 | S151–S170 | Provider coverage demand-driven |
| 10 | S171–S185 | Only if multi-user demand |
| 11 | S186–S200 | UX polish after daily-driver metrics |

### Phases 12–15 — Nice tracks

Schedule only with spare capacity or partner demand. Prefer N231–N260 (deep coding) and N284–N286 (CI) over vanity ecosystem.

### Phase 16 — Parked (P301–P400)

Do not pull into active sprints without an explicit product decision note in `docs/PENDING_WORK.md`.

---

## Metrics (to know if SuperAI is becoming world’s best CLI)

| Metric | Target direction | Tied to |
|--------|------------------|---------|
| % spend paths with budget+contract | → 100% | M001,M008 |
| Median $ per successful coding task | ↓ | M002,M033–M036,S126–S130 |
| Time-to-first-token | ↓ | M027,S144 |
| Tool-loop success rate (tests pass) | ↑ | M039,S105 |
| False “success” under mock | = 0 | M020,M088 |
| New-user time-to-first-win | ↓ | M075,M071,S199 |
| Multi-CLI board cache hit rate | ↑ useful | M055,S126 |
| User-reported “trust I can yolo never” | high on plan-mode | M004,M005 |

---

## Tracking conventions

1. When implementing, open a child plan `docs/IMPROVEMENT_V6_PHASE{n}.md` with only that phase’s IDs.  
2. Mark IDs `[x]` only with **code + tests** (same honesty rule as MoSCoW 100).  
3. Host-only items (M089 and live messenger/rclone/Postgres E2E) stay `[!]` until real environment proof.  
4. Do not renumber IDs; append V6.1+ for new items if needed.

---

## Related docs

| Doc | Role |
|-----|------|
| `docs/IMPROVEMENT_V4_PLAN.md` | Prior depth (trust/cost/agent UX) |
| `docs/IMPROVEMENT_V5_PLAN.md` | Ops maturity |
| `docs/MOSCOW_100_PLAN.md` | Prior MoSCoW honesty track |
| `docs/SUPERAI_AGENT.md` | Agent product surface |
| `docs/PENDING_WORK.md` | Host gates summary |
| `docs/UNIVERSAL_MODELS_PLAN.md` | Phase 99 smoke |

---

## Summary counts

| Bucket | Count | ID range |
|--------|------:|----------|
| Must | 100 | M001–M100 |
| Should | 100 | S101–S200 |
| Nice | 100 | N201–N300 |
| Not important now | 100 | P301–P400 |
| **Total** | **400** | |

**Recommended start:** Phase 1 (M001–M020) gap analysis against current tree, then close only residual musts—not a full rewrite.
